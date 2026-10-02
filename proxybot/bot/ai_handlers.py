"""Proxy AI Telegram surface: /ai chat, /ai_setup wizard, approvals, memory & skills views, auto-discovery."""
from __future__ import annotations

import asyncio
import html
import json
import logging
import time

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from ..ai import memory as mem
from ..ai import skills as sk
from ..ai import tools as T
from ..ai.agent import AIConfigError, Callbacks, ProxyAgent, ai_config, is_configured, list_models
from ..ai.prompts import DISCOVERY_PROMPT
from ..core.config import SECRETS
from ..core.database import get_db
from ..i18n import t
from . import keyboards as K
from .state import RT, has_perm, lang_of

log = logging.getLogger("proxybot.bot.ai")
router = Router(name="ai")


def esc(s) -> str:
    return html.escape(str(s if s is not None else ""))


def _fmt_args(args: dict, limit: int = 700) -> str:
    s = json.dumps(args, ensure_ascii=False, indent=1)
    return esc(s[:limit] + ("…" if len(s) > limit else ""))


def make_callbacks(bot: Bot, chat_id: int, lang: str) -> Callbacks:
    async def on_tool(name, args):
        short = json.dumps(args, ensure_ascii=False)
        try:
            await bot.send_message(chat_id, t(lang, "ai_tool", tool=esc(name), args=esc(short[:200])), disable_web_page_preview=True)
        except Exception:  # noqa: BLE001
            pass

    async def on_approval(pid, name, args, reason):
        await bot.send_message(chat_id, t(lang, "ai_approval", id=pid, tool=esc(name), reason=esc(reason), args=_fmt_args(args)),
                               reply_markup=K.approval_kb(lang, pid))

    async def on_memory(action, target, text):
        await bot.send_message(chat_id, t(lang, "ai_memory_saved", action=esc(action), target=esc(target), text=esc(text)))

    async def on_skill(name, action):
        await bot.send_message(chat_id, t(lang, "ai_skill_saved", name=esc(name), action=esc(action)))

    async def notify(text):
        await bot.send_message(chat_id, text, disable_web_page_preview=True)

    return Callbacks(on_tool, on_approval, on_memory, on_skill, notify)


async def send_long(bot: Bot, chat_id: int, text: str, **kw) -> None:
    text = text.strip() or "…"
    for i in range(0, len(text), 3900):
        chunk = text[i:i + 3900]
        try:
            await bot.send_message(chat_id, chunk, disable_web_page_preview=True, **kw)
        except Exception:  # noqa: BLE001  (bad HTML from the model → send plain)
            await bot.send_message(chat_id, esc(chunk), parse_mode=None, disable_web_page_preview=True)


# ---------------------------------------------------------------- menu
async def menu_ai(ev: Message | CallbackQuery, lang: str):
    from .handlers import edit_or_send
    db = get_db()
    uid = ev.from_user.id
    if not is_configured():
        return await edit_or_send(ev, t(lang, "ai_not_configured"), K.ai_kb(lang, 0))
    sid = db.ai_session(uid)
    msgs = db.fetchone("SELECT COUNT(*) c FROM ai_messages WHERE session_id=?", (sid,))["c"]
    pending = len(db.ai_pending(uid))
    text = t(lang, "ai_menu", model=esc(ai_config()["model"]), sid=sid, msgs=msgs, pending=pending,
             mem_pct=mem.memory().pct(), user_pct=mem.user_profile().pct(), tools=esc(", ".join(T.tool_names())))
    await edit_or_send(ev, text, K.ai_kb(lang, pending))


@router.message(Command("ai"))
async def cmd_ai(m: Message, bot: Bot):
    lang = lang_of(m.from_user)
    if not has_perm(m.from_user.id, "ai"):
        return await m.answer(t(lang, "admin_only"))
    parts = (m.text or "").split(maxsplit=1)
    if len(parts) > 1:
        return await chat(m, bot, lang, parts[1])
    await menu_ai(m, lang)


@router.message(Command("ai_new"))
async def cmd_ai_new(m: Message):
    lang = lang_of(m.from_user)
    if not has_perm(m.from_user.id, "ai"):
        return await m.answer(t(lang, "admin_only"))
    get_db().ai_session(m.from_user.id, new=True)
    await m.answer(t(lang, "ai_new_session"))


@router.callback_query(F.data.startswith("ai:"))
async def cb_ai(c: CallbackQuery, bot: Bot):
    lang = lang_of(c.from_user)
    if not has_perm(c.from_user.id, "ai"):
        return await c.answer(t(lang, "admin_only"), show_alert=True)
    action = c.data.split(":")[1]
    db = get_db()
    from .handlers import edit_or_send
    if action == "new":
        db.ai_session(c.from_user.id, new=True)
        await c.answer(t(lang, "ai_new_session"))
        return await menu_ai(c, lang)
    await c.answer()
    if action == "setup":
        return await start_setup(c.message, c.from_user.id, lang)
    if action == "model":
        return await pick_model(c, lang)
    if action == "memory":
        m, u = mem.memory(), mem.user_profile()
        return await edit_or_send(c, t(lang, "ai_memory_view", m_used=m.used(), m_max=m.limit, memory=esc(m.path.read_text() or "(empty)"),
                                       u_used=u.used(), u_max=u.limit, user=esc(u.path.read_text() or "(empty)"))[:4000], K.back_kb(lang, "ai"))
    if action == "skills":
        lst = "\n".join(f"• <b>{esc(s['name'])}</b> — {esc(s['description'])}" for s in sk.skills_list()) or "—"
        return await edit_or_send(c, t(lang, "ai_skills_view", list=lst), K.back_kb(lang, "ai"))
    if action == "pending":
        return await show_pending(c, lang)
    if action == "discover":
        return await start_discovery(c, lang, bot)


# ------------------------------------------------------------- setup
async def start_setup(msg: Message, uid: int, lang: str):
    RT.pending_input[uid] = {"kind": "ai_url"}
    await msg.answer(t(lang, "ai_setup_url"), reply_markup=K.cancel_kb(lang))


@router.message(Command("ai_setup"))
async def cmd_ai_setup(m: Message):
    lang = lang_of(m.from_user)
    if not has_perm(m.from_user.id, "ai"):
        return await m.answer(t(lang, "admin_only"))
    await start_setup(m, m.from_user.id, lang)


async def pick_model(ev: Message | CallbackQuery, lang: str):
    cfg = ai_config()
    uid = ev.from_user.id
    msg = ev.message if isinstance(ev, CallbackQuery) else ev
    if not (cfg["base_url"] and cfg["api_key"]):
        return await msg.answer(t(lang, "ai_not_configured"))
    try:
        models = await list_models(cfg["base_url"], cfg["api_key"])
    except Exception as e:  # noqa: BLE001
        RT.pending_input[uid] = {"kind": "ai_model"}
        return await msg.answer(t(lang, "ai_setup_models_fail", err=esc(e)), reply_markup=K.cancel_kb(lang))
    if not models:
        RT.pending_input[uid] = {"kind": "ai_model"}
        return await msg.answer(t(lang, "ai_setup_models_fail", err="empty list"), reply_markup=K.cancel_kb(lang))
    RT.model_cache[uid] = models
    RT.pending_input[uid] = {"kind": "ai_model"}
    await msg.answer(t(lang, "ai_setup_models", n=len(models)), reply_markup=K.models_kb(models))


@router.callback_query(F.data.startswith("mdlp:"))
async def cb_model_page(c: CallbackQuery):
    page = int(c.data.split(":")[1])
    models = RT.model_cache.get(c.from_user.id, [])
    await c.answer()
    try:
        await c.message.edit_reply_markup(reply_markup=K.models_kb(models, page))
    except Exception:  # noqa: BLE001
        pass


@router.callback_query(F.data.startswith("mdl:"))
async def cb_model_pick(c: CallbackQuery):
    lang = lang_of(c.from_user)
    if not has_perm(c.from_user.id, "ai"):
        return await c.answer(t(lang, "admin_only"), show_alert=True)
    idx = int(c.data.split(":")[1])
    models = RT.model_cache.get(c.from_user.id, [])
    if idx >= len(models):
        return await c.answer("?")
    await _finish_setup(c.message, c.from_user.id, lang, models[idx])
    await c.answer()


async def _finish_setup(msg: Message, uid: int, lang: str, model: str):
    db = get_db()
    db.set("ai_model", model)
    RT.pending_input.pop(uid, None)
    await msg.answer(t(lang, "ai_setup_done", model=esc(model), url=esc(db.get("ai_base_url"))))


async def handle_ai_input(m: Message, lang: str) -> bool:
    """Setup-wizard text steps. Returns True if consumed."""
    uid = m.from_user.id
    p = RT.pending_input.get(uid)
    if not p or not p["kind"].startswith("ai_"):
        return False
    db = get_db()
    text = (m.text or "").strip()
    if p["kind"] == "ai_url":
        if not text.startswith("http"):
            await m.answer(t(lang, "ai_setup_url"))
            return True
        db.set("ai_base_url", text.rstrip("/"))
        RT.pending_input[uid] = {"kind": "ai_key"}
        await m.answer(t(lang, "ai_setup_key"), reply_markup=K.cancel_kb(lang))
    elif p["kind"] == "ai_key":
        db.set("ai_api_key", text)
        try:
            await m.delete()
        except Exception:  # noqa: BLE001
            pass
        await pick_model(m, lang)
    elif p["kind"] == "ai_model":
        await _finish_setup(m, uid, lang, text)
    else:
        return False
    return True


# -------------------------------------------------------------- chat
async def chat(m: Message, bot: Bot, lang: str, text: str):
    uid = m.from_user.id
    if not is_configured():
        return await m.answer(t(lang, "ai_not_configured"))
    if uid in RT.ai_busy:
        return await m.answer(t(lang, "ai_busy"))
    RT.ai_busy.add(uid)
    thinking = await m.answer(t(lang, "ai_thinking"))
    try:
        agent = ProxyAgent(uid, lang, make_callbacks(bot, m.chat.id, lang))
        res = await agent.run_turn(text)
        if res.error:
            await send_long(bot, m.chat.id, t(lang, "ai_error", err=esc(res.error)))
        elif res.text:
            await send_long(bot, m.chat.id, res.text)
    except AIConfigError as e:
        await m.answer(t(lang, "ai_error", err=esc(e)))
    except Exception as e:  # noqa: BLE001
        log.exception("ai chat failed")
        await m.answer(t(lang, "ai_error", err=esc(e)))
    finally:
        RT.ai_busy.discard(uid)
        try:
            await thinking.delete()
        except Exception:  # noqa: BLE001
            pass


# ---------------------------------------------------------- approvals
async def show_pending(ev: Message | CallbackQuery, lang: str):
    rows = get_db().ai_pending(ev.from_user.id)
    msg = ev.message if isinstance(ev, CallbackQuery) else ev
    if not rows:
        return await msg.answer(t(lang, "ai_no_pending"))
    for r in rows:
        await msg.answer(t(lang, "ai_approval", id=r["id"], tool=esc(r["tool"]), reason=esc(r["reason"]), args=_fmt_args(json.loads(r["args"]))),
                         reply_markup=K.approval_kb(lang, r["id"]))


@router.message(Command("pending"))
async def cmd_pending(m: Message):
    lang = lang_of(m.from_user)
    if not has_perm(m.from_user.id, "ai"):
        return await m.answer(t(lang, "admin_only"))
    await show_pending(m, lang)


@router.callback_query(F.data.startswith("ap:"))
async def cb_approve(c: CallbackQuery, bot: Bot):
    lang = lang_of(c.from_user)
    uid = c.from_user.id
    if not has_perm(uid, "ai"):
        return await c.answer(t(lang, "admin_only"), show_alert=True)
    _, yn, target = c.data.split(":")
    approve = yn == "y"
    db = get_db()
    ids = [r["id"] for r in db.ai_pending(uid)] if target == "all" else [int(target)]
    await c.answer()
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:  # noqa: BLE001
        pass
    if not ids:
        return await c.message.answer(t(lang, "ai_no_pending"))
    if uid in RT.ai_busy:
        return await c.message.answer(t(lang, "ai_busy"))
    RT.ai_busy.add(uid)
    try:
        agent = ProxyAgent(uid, lang, make_callbacks(bot, c.message.chat.id, lang))
        for pid in ids:
            row = db.fetchone("SELECT session_id FROM ai_pending WHERE id=?", (pid,))
            if row and row["session_id"]:
                agent.session_id = row["session_id"]
            await c.message.answer(t(lang, "ai_approved" if approve else "ai_denied", id=pid))
            res = await agent.resume_pending(pid, approve)
            if res.error and res.error != "not pending":
                await send_long(bot, c.message.chat.id, t(lang, "ai_error", err=esc(res.error)))
            elif res.text:
                await send_long(bot, c.message.chat.id, res.text)
    except Exception as e:  # noqa: BLE001
        log.exception("approval failed")
        await c.message.answer(t(lang, "ai_error", err=esc(e)))
    finally:
        RT.ai_busy.discard(uid)


# ---------------------------------------------------------- discovery
async def start_discovery(ev: Message | CallbackQuery, lang: str, bot: Bot):
    msg = ev.message if isinstance(ev, CallbackQuery) else ev
    uid = ev.from_user.id
    if not is_configured():
        return await msg.answer(t(lang, "ai_not_configured"))
    if not SECRETS.tavily_key:
        return await msg.answer("⚠️ TAVILY_API_KEY secret is not set.")
    await msg.answer(t(lang, "ai_discover_started"))
    asyncio.get_running_loop().create_task(run_discovery(bot, msg.chat.id, uid, lang))


async def run_discovery(bot: Bot | None, chat_id: int | None, uid: int, lang: str = "en") -> str:
    """Autonomous source discovery (also used by the scheduler). add_source is auto-approved for this
    unattended task because it is harmless and reversible; everything else still needs approval."""
    if not is_configured() or not SECRETS.tavily_key:
        return "skipped"
    cb = make_callbacks(bot, chat_id, lang) if bot and chat_id else Callbacks()
    agent = ProxyAgent(uid, lang, cb)
    agent.new_session()
    orig = T.REGISTRY["add_source"].danger
    T.REGISTRY["add_source"].danger = lambda a: "safe"
    try:
        res = await agent.run_turn(DISCOVERY_PROMPT)
        text = res.text or res.error or "done"
    finally:
        T.REGISTRY["add_source"].danger = orig
    get_db().kv_set("last_discovery", {"ts": time.time(), "text": text[:500]})
    if bot and chat_id:
        await send_long(bot, chat_id, text)
    return text


# --------------------------------------------------- free text → AI chat
@router.message(F.text & ~F.text.startswith("/"))
async def free_text(m: Message, bot: Bot):
    from .handlers import handle_pending_input
    lang = lang_of(m.from_user)
    if await handle_ai_input(m, lang):
        return
    if await handle_pending_input(m, lang):
        return
    if not has_perm(m.from_user.id, "ai"):
        return  # silently ignore chatter from non-admins
    await chat(m, bot, lang, m.text)
