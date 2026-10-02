"""Telegram handlers: menus, proxies, scan, status, log, history, settings, admins, sources, language, public."""
from __future__ import annotations

import asyncio
import html
import io
import json
import logging
import time

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from ..core.config import DEFAULT_SETTINGS, SECRETS
from ..core.database import get_db
from ..core.logger import current_stage
from ..i18n import LANG_CODES, lang_name, t
from ..pipeline.runner import get_runner
from . import keyboards as K
from .state import MENU_PERM, PERMS, RT, allowed, fmt_next_scan, has_perm, is_admin, lang_of

log = logging.getLogger("proxybot.bot")
router = Router(name="main")


# ------------------------------------------------------------------ utils
def esc(s) -> str:
    return html.escape(str(s if s is not None else ""))


async def edit_or_send(ev: Message | CallbackQuery, text: str, kb=None) -> None:
    if isinstance(ev, CallbackQuery):
        try:
            await ev.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
            return
        except Exception:  # noqa: BLE001  (message not modified / too old)
            pass
        await ev.message.answer(text, reply_markup=kb, disable_web_page_preview=True)
    else:
        await ev.answer(text, reply_markup=kb, disable_web_page_preview=True)


def iran_txt(lang: str, v: int) -> str:
    return t(lang, {1: "iran_ok", 0: "iran_bad"}.get(v, "iran_unknown"))


def proxy_card(lang: str, i: int, r) -> str:
    return t(lang, "proxy_card", i=i, host=esc(r["host"]), port=r["port"], ping=r["ping_ms"] or "?",
             down=r["down_kbps"] or 0, up=r["up_kbps"] or 0, score=r["score"], iran=iran_txt(lang, r["iran_ok"]),
             stype=r["secret_type"] or "?", link=esc(r["link"]))


def main_text(lang: str) -> str:
    db = get_db()
    st = db.proxy_stats()
    stage = current_stage()
    status = f"{stage['stage']} {stage['detail']}".strip()
    listed = len(db.best_proxies(int(db.get("top_n", 30)), float(db.get("min_score", 20))))
    return t(lang, "main_menu", status=esc(status), alive=st.get("alive", 0), listed=listed, total=st.get("total", 0), next=fmt_next_scan())


async def show_main(ev: Message | CallbackQuery, lang: str) -> None:
    uid = ev.from_user.id
    adm = is_admin(uid)
    public = bool(int(get_db().get("public_mode", 0)))
    if isinstance(ev, Message):
        await ev.answer(main_text(lang), reply_markup=K.main_reply(lang, adm), disable_web_page_preview=True)
        await ev.answer("⬇️", reply_markup=K.main_inline(lang, adm, public))
    else:
        await edit_or_send(ev, main_text(lang), K.main_inline(lang, adm, public))


# ---------------------------------------------------------------- /start
@router.message(CommandStart())
async def cmd_start(m: Message):
    db = get_db()
    uid = m.from_user.id
    db.ensure_owner(SECRETS.admin_id)
    new = db.fetchone("SELECT 1 FROM users WHERE id=?", (uid,)) is None
    lang = lang_of(m.from_user)
    if not allowed(uid):
        await m.answer(t(lang, "not_allowed"))
        return
    if new or m.text.strip().endswith("lang"):
        await m.answer(t("en", "welcome"), reply_markup=K.lang_kb())
        return
    await show_main(m, lang)


@router.message(Command("lang"))
async def cmd_lang(m: Message):
    await m.answer(t(lang_of(m.from_user), "welcome"), reply_markup=K.lang_kb())


@router.callback_query(F.data.startswith("lang:"))
async def cb_lang(c: CallbackQuery, bot: Bot):
    code = c.data.split(":")[1]
    if code not in LANG_CODES:
        return await c.answer()
    get_db().touch_user(c.from_user.id, c.from_user.username or "", c.from_user.first_name or "")
    get_db().set_user_lang(c.from_user.id, code)
    await c.answer(t(code, "lang_set", lang=lang_name(code)))
    if not allowed(c.from_user.id):
        return await c.message.edit_text(t(code, "not_allowed"))
    try:
        await c.message.delete()
    except Exception:  # noqa: BLE001
        pass
    await send_main(bot, c.message.chat.id, c.from_user.id, code)


async def send_main(bot: Bot, chat_id: int, uid: int, lang: str) -> None:
    adm = is_admin(uid)
    public = bool(int(get_db().get("public_mode", 0)))
    await bot.send_message(chat_id, main_text(lang), reply_markup=K.main_reply(lang, adm), disable_web_page_preview=True)
    await bot.send_message(chat_id, "⬇️", reply_markup=K.main_inline(lang, adm, public))


# ------------------------------------------------------------- menu router
@router.callback_query(F.data.startswith("m:"))
async def cb_menu(c: CallbackQuery, bot: Bot):
    action = c.data.split(":", 1)[1]
    uid = c.from_user.id
    lang = lang_of(c.from_user)
    if not allowed(uid):
        return await c.answer(t(lang, "not_allowed"), show_alert=True)
    perm = MENU_PERM.get(action)
    if perm and not has_perm(uid, perm):
        return await c.answer(t(lang, "admin_only"), show_alert=True)
    await c.answer()
    await dispatch_menu(action, c, lang, bot)


async def dispatch_menu(action: str, ev: Message | CallbackQuery, lang: str, bot: Bot):
    uid = ev.from_user.id
    if action == "main":
        await show_main(ev, lang)
    elif action == "cancel":
        RT.pending_input.pop(uid, None)
        await edit_or_send(ev, t(lang, "cancelled"), K.back_kb(lang))
    elif action == "proxies":
        await menu_proxies(ev, lang)
    elif action == "scan":
        await do_scan(ev, lang, bot)
    elif action == "status":
        await menu_status(ev, lang)
    elif action == "log":
        await menu_log(ev, lang, "all")
    elif action == "history":
        await menu_history(ev, lang)
    elif action == "settings":
        await edit_or_send(ev, t(lang, "settings_title"), K.settings_kb(lang))
    elif action == "sources":
        await menu_sources(ev, lang)
    elif action == "admins":
        await menu_admins(ev, lang)
    elif action == "public":
        await toggle_public(ev, lang)
    elif action == "lang":
        await edit_or_send(ev, t(lang, "welcome"), K.lang_kb())
    elif action == "explain":
        await edit_or_send(ev, t(lang, "explain"), K.back_kb(lang))
    elif action == "help":
        await edit_or_send(ev, t(lang, "help"), K.back_kb(lang))
    elif action == "ai":
        from .ai_handlers import menu_ai
        await menu_ai(ev, lang)


# ------------------------------------------------------------- reply keys
@router.message(F.text, lambda m: m.text in K.reply_button_map(lang_of(m.from_user)))
async def reply_buttons(m: Message, bot: Bot):
    lang = lang_of(m.from_user)
    action = K.reply_button_map(lang)[m.text]
    if not allowed(m.from_user.id):
        return await m.answer(t(lang, "not_allowed"))
    perm = MENU_PERM.get(action)
    if perm and not has_perm(m.from_user.id, perm):
        return await m.answer(t(lang, "admin_only"))
    await dispatch_menu(action, m, lang, bot)


# ---------------------------------------------------------------- proxies
async def menu_proxies(ev, lang: str):
    db = get_db()
    st = db.proxy_stats()
    top_n = int(db.get("top_n", 30))
    listed = len(db.best_proxies(top_n, float(db.get("min_score", 20))))
    cnt = int(db.kv_get(f"count:{ev.from_user.id}", db.get("send_count", 5)))
    await edit_or_send(ev, t(lang, "proxies_menu", n=st.get("alive", 0), listed=listed), K.proxies_kb(lang, cnt, top_n))


@router.message(Command("proxies"))
async def cmd_proxies(m: Message):
    lang = lang_of(m.from_user)
    if not allowed(m.from_user.id):
        return await m.answer(t(lang, "not_allowed"))
    await menu_proxies(m, lang)


@router.callback_query(F.data.startswith("px:"))
async def cb_proxies(c: CallbackQuery):
    lang = lang_of(c.from_user)
    uid = c.from_user.id
    if not allowed(uid):
        return await c.answer(t(lang, "not_allowed"), show_alert=True)
    db = get_db()
    action = c.data.split(":")[1]
    top_n = int(db.get("top_n", 30))
    min_score = float(db.get("min_score", 20))
    cnt = int(db.kv_get(f"count:{uid}", db.get("send_count", 5)))
    if action == "count":
        RT.pending_input[uid] = {"kind": "count"}
        await c.answer()
        return await c.message.answer(t(lang, "ask_count", max=top_n), reply_markup=K.cancel_kb(lang))
    rows = db.best_proxies(top_n if action == "list" else cnt, min_score) or db.best_proxies(top_n if action == "list" else cnt, 0)
    if not rows:
        return await c.answer(t(lang, "no_proxies"), show_alert=True)
    await c.answer()
    if action == "list":
        text = "\n".join(t(lang, "proxy_line", i=i + 1, ping=r["ping_ms"] or "?", score=int(r["score"]), link=esc(r["link"]),
                           host=esc(r["host"]), port=r["port"]) for i, r in enumerate(rows))
        return await c.message.answer(text[:4000], disable_web_page_preview=True, reply_markup=K.back_kb(lang, "proxies"))
    if action == "single":
        for i, r in enumerate(rows):
            await c.message.answer(proxy_card(lang, i + 1, r), disable_web_page_preview=True)
            await asyncio.sleep(0.15)
    elif action == "batch":
        chunks, cur = [], ""
        for i, r in enumerate(rows):
            card = proxy_card(lang, i + 1, r) + "\n\n"
            if len(cur) + len(card) > 3900:
                chunks.append(cur)
                cur = ""
            cur += card
        chunks.append(cur)
        for ch in chunks:
            await c.message.answer(ch, disable_web_page_preview=True)
    elif action == "file":
        ts = time.strftime("%Y-%m-%d_%H-%M", time.gmtime())
        txt = "\n".join(r["link"] for r in rows)
        js = json.dumps([{k: r[k] for k in ("host", "port", "secret", "link", "ping_ms", "down_kbps", "up_kbps", "score", "iran_ok")} for r in rows],
                        ensure_ascii=False, indent=1)
        await c.message.answer_document(BufferedInputFile(txt.encode(), f"proxies_{ts}.txt"), caption=t(lang, "file_caption", n=len(rows), ts=ts))
        await c.message.answer_document(BufferedInputFile(js.encode(), f"proxies_{ts}.json"))


# ------------------------------------------------------------------ scan
async def do_scan(ev, lang: str, bot: Bot):
    runner = get_runner()
    if runner.running:
        return await edit_or_send(ev, t(lang, "scan_running", stage=runner.stats.stage), K.back_kb(lang))
    await edit_or_send(ev, t(lang, "scan_started"), K.back_kb(lang))
    chat_id = ev.message.chat.id if isinstance(ev, CallbackQuery) else ev.chat.id

    async def _go():
        st = await runner.run(SECRETS.run_id)
        try:
            await bot.send_message(chat_id, t(lang, "scan_done", sec=int(st.elapsed), ok=st.sources_ok, failed=st.sources_failed,
                                              found=st.found, uniq=st.uniq, alive=st.alive, speed=st.speed_tested, listed=st.listed))
        except Exception:  # noqa: BLE001
            pass
    asyncio.get_running_loop().create_task(_go())


@router.message(Command("scan"))
async def cmd_scan(m: Message, bot: Bot):
    lang = lang_of(m.from_user)
    if not has_perm(m.from_user.id, "scan"):
        return await m.answer(t(lang, "admin_only"))
    await do_scan(m, lang, bot)


# ---------------------------------------------------------------- status
async def menu_status(ev, lang: str):
    db = get_db()
    st = db.proxy_stats()
    stage = current_stage()
    p = RT.persister
    from ..ai.agent import ai_config, is_configured
    ai = ai_config()["model"] if is_configured() else "not configured"
    text = t(lang, "status", stage=esc(stage["stage"]), detail=esc(stage["detail"]), progress=esc(stage["progress"]),
             run=db.kv_get("run_counter", 0), gh=SECRETS.run_id, uptime=RT.uptime(), alive=st.get("alive", 0),
             flaky=st.get("flaky", 0), dead=st.get("dead", 0), total=st.get("total", 0), src_on=len(db.sources()),
             src_all=len(db.sources(False)), users=db.user_count(), admins=len(db.list_admins()),
             auto="✅" if int(db.get("auto_scan", 1)) else "❌", interval=db.get("scan_interval_min"), next=fmt_next_scan(),
             save=(time.strftime("%H:%M:%S", time.gmtime(p.last_save)) if p and p.last_save else "—"), saves=p.saves if p else 0, ai=esc(ai))
    await edit_or_send(ev, text, K.back_kb(lang))


@router.message(Command("status"))
async def cmd_status(m: Message):
    lang = lang_of(m.from_user)
    if not allowed(m.from_user.id):
        return await m.answer(t(lang, "not_allowed"))
    await menu_status(m, lang)


@router.message(Command("ping"))
async def cmd_ping(m: Message):
    t0 = time.perf_counter()
    msg = await m.answer("🏓")
    ms = int((time.perf_counter() - t0) * 1000)
    await msg.edit_text(t(lang_of(m.from_user), "ping", ms=ms))


# ------------------------------------------------------------------- log
async def menu_log(ev, lang: str, mode: str):
    db = get_db()
    rows = db.recent_logs(25, "ERROR" if mode == "err" else None)
    if mode == "err":
        rows = rows or db.recent_logs(25, "WARNING")
    stage = current_stage()
    head = t(lang, "log_title", stage=esc(stage["stage"]), detail=esc(stage["detail"]), progress=esc(stage["progress"]))
    body = "\n".join(f"<code>{r['ts'][11:19]}</code> {'⚠️' if r['level'] != 'INFO' else '•'} [{esc(r['stage'])}] {esc(r['msg'][:150])}" for r in reversed(rows))
    await edit_or_send(ev, (head + (body or t(lang, "log_empty")))[:4000], K.log_kb(lang))


@router.message(Command("log"))
async def cmd_log(m: Message):
    lang = lang_of(m.from_user)
    if not has_perm(m.from_user.id, "logs"):
        return await m.answer(t(lang, "admin_only"))
    await menu_log(m, lang, "all")


@router.callback_query(F.data.startswith("log:"))
async def cb_log(c: CallbackQuery):
    lang = lang_of(c.from_user)
    if not has_perm(c.from_user.id, "logs"):
        return await c.answer(t(lang, "admin_only"), show_alert=True)
    await c.answer()
    await menu_log(c, lang, c.data.split(":")[1])


# --------------------------------------------------------------- history
async def menu_history(ev, lang: str):
    db = get_db()
    days = db.history_dates(int(db.get("retention_days", 30)))
    if not days:
        return await edit_or_send(ev, t(lang, "history_empty"), K.back_kb(lang))
    await edit_or_send(ev, t(lang, "history_title", days=db.get("retention_days", 30)), K.history_kb(lang, days))


@router.message(Command("history"))
async def cmd_history(m: Message):
    lang = lang_of(m.from_user)
    if not allowed(m.from_user.id):
        return await m.answer(t(lang, "not_allowed"))
    await menu_history(m, lang)


@router.callback_query(F.data.startswith("hd:"))
async def cb_history_day(c: CallbackQuery):
    lang = lang_of(c.from_user)
    if not allowed(c.from_user.id):
        return await c.answer(t(lang, "not_allowed"), show_alert=True)
    day = c.data.split(":")[1]
    rows = get_db().history_for_day(day, 40)
    text = t(lang, "history_day", day=day, n=len(rows)) + "\n".join(
        f"{i + 1}. ⏱{r['ping_ms']}ms ⬇️{r['down_kbps'] or 0} ⬆️{r['up_kbps'] or 0} <a href=\"{esc(r['link'])}\">{esc(r['host'])}:{r['port']}</a>"
        for i, r in enumerate(rows))
    await c.answer()
    await edit_or_send(c, text[:4000], K.back_kb(lang, "history"))


# -------------------------------------------------------------- settings
@router.message(Command("settings"))
async def cmd_settings(m: Message):
    lang = lang_of(m.from_user)
    if not has_perm(m.from_user.id, "settings"):
        return await m.answer(t(lang, "admin_only"))
    await m.answer(t(lang, "settings_title"), reply_markup=K.settings_kb(lang))


@router.callback_query(F.data.startswith("sg:"))
async def cb_settings_group(c: CallbackQuery):
    lang = lang_of(c.from_user)
    if not has_perm(c.from_user.id, "settings"):
        return await c.answer(t(lang, "admin_only"), show_alert=True)
    group = c.data.split(":")[1]
    await c.answer()
    await edit_or_send(c, t(lang, "settings_title"), K.settings_group_kb(lang, group, get_db().all_settings()))


def _group_of(key: str) -> str:
    for g, keys in K.SETTING_GROUPS.items():
        if key in keys:
            return g
    return "pipe"


@router.callback_query(F.data.startswith("st:"))
async def cb_setting_toggle(c: CallbackQuery):
    lang = lang_of(c.from_user)
    if not has_perm(c.from_user.id, "settings"):
        return await c.answer(t(lang, "admin_only"), show_alert=True)
    key = c.data.split(":")[1]
    db = get_db()
    db.set(key, 0 if int(db.get(key, 0)) else 1)
    if key == "scan_interval_min" or key == "auto_scan":
        RT.scheduler and RT.scheduler.reschedule()
    await c.answer(t(lang, "set_ok", key=key, val=db.get(key)))
    await edit_or_send(c, t(lang, "settings_title"), K.settings_group_kb(lang, _group_of(key), db.all_settings()))


@router.callback_query(F.data.startswith("se:"))
async def cb_setting_edit(c: CallbackQuery):
    lang = lang_of(c.from_user)
    if not has_perm(c.from_user.id, "settings"):
        return await c.answer(t(lang, "admin_only"), show_alert=True)
    key = c.data.split(":")[1]
    if key == "ai_model":
        from .ai_handlers import pick_model
        await c.answer()
        return await pick_model(c, lang)
    RT.pending_input[c.from_user.id] = {"kind": "setting", "key": key}
    await c.answer()
    cur = get_db().get(key)
    await c.message.answer(t(lang, "set_prompt", key=key, desc=esc(DEFAULT_SETTINGS[key][2]), cur=esc(cur)), reply_markup=K.cancel_kb(lang))


# ---------------------------------------------------------------- public
async def toggle_public(ev, lang: str):
    db = get_db()
    new = 0 if int(db.get("public_mode", 0)) else 1
    db.set("public_mode", new)
    await edit_or_send(ev, t(lang, "public_on" if new else "public_off"), K.back_kb(lang))


@router.message(Command("public"))
async def cmd_public(m: Message):
    lang = lang_of(m.from_user)
    if not has_perm(m.from_user.id, "admins"):
        return await m.answer(t(lang, "admin_only"))
    await toggle_public(m, lang)


# ---------------------------------------------------------------- admins
async def menu_admins(ev, lang: str):
    db = get_db()
    lines = []
    for a in db.list_admins():
        name = ("@" + a["username"]) if a["username"] else (a["first_name"] or "")
        lines.append(f"{'👑' if a['is_owner'] else '👮'} <code>{a['user_id']}</code> {esc(name)} — <code>{esc(' '.join(json.loads(a['permissions'])))}</code>")
    await edit_or_send(ev, t(lang, "admins_title", list="\n".join(lines)), K.admins_kb(lang))


@router.message(Command("admins"))
async def cmd_admins(m: Message):
    lang = lang_of(m.from_user)
    if not has_perm(m.from_user.id, "admins"):
        return await m.answer(t(lang, "admin_only"))
    await menu_admins(m, lang)


@router.callback_query(F.data.startswith("ad:"))
async def cb_admins(c: CallbackQuery):
    lang = lang_of(c.from_user)
    if not has_perm(c.from_user.id, "admins"):
        return await c.answer(t(lang, "admin_only"), show_alert=True)
    action = c.data.split(":")[1]
    await c.answer()
    if action == "add":
        RT.pending_input[c.from_user.id] = {"kind": "admin_id"}
        await c.message.answer(t(lang, "ask_admin_id"), reply_markup=K.cancel_kb(lang))
    else:
        await edit_or_send(c, t(lang, "admin_pick"), K.admin_pick_kb(lang, get_db().list_admins(), action))


@router.callback_query(F.data.startswith("adp:"))
async def cb_admin_pick(c: CallbackQuery):
    lang = lang_of(c.from_user)
    if not has_perm(c.from_user.id, "admins"):
        return await c.answer(t(lang, "admin_only"), show_alert=True)
    _, action, uid = c.data.split(":")
    uid = int(uid)
    db = get_db()
    if action == "del":
        if not db.remove_admin(uid):
            return await c.answer(t(lang, "admin_cannot_remove_owner"), show_alert=True)
        await c.answer(t(lang, "admin_removed", id=uid))
        await menu_admins(c, lang)
    else:
        RT.pending_input[c.from_user.id] = {"kind": "admin_perms", "id": uid}
        await c.answer()
        await c.message.answer(t(lang, "ask_admin_perms"), reply_markup=K.cancel_kb(lang))


# --------------------------------------------------------------- sources
async def menu_sources(ev, lang: str):
    db = get_db()
    allsrc = db.sources(False)
    on = [s for s in allsrc if s["enabled"]]
    by = {"builtin": 0, "ai": 0, "manual": 0}
    for s in allsrc:
        by[s["added_by"] if s["added_by"] in by else "manual"] += 1
    stats = db.kv_get("last_run_stats") or {}
    await edit_or_send(ev, t(lang, "sources_title", on=len(on), all=len(allsrc), ok=stats.get("sources_ok", 0),
                             failed=stats.get("sources_failed", 0), builtin=by["builtin"], ai=by["ai"], manual=by["manual"]), K.sources_kb(lang))


@router.message(Command("sources"))
async def cmd_sources(m: Message):
    lang = lang_of(m.from_user)
    if not has_perm(m.from_user.id, "sources"):
        return await m.answer(t(lang, "admin_only"))
    await menu_sources(m, lang)


@router.callback_query(F.data.startswith("src:"))
async def cb_sources(c: CallbackQuery, bot: Bot):
    lang = lang_of(c.from_user)
    if not has_perm(c.from_user.id, "sources"):
        return await c.answer(t(lang, "admin_only"), show_alert=True)
    action = c.data.split(":")[1]
    db = get_db()
    await c.answer()
    if action == "add":
        RT.pending_input[c.from_user.id] = {"kind": "source_url"}
        return await c.message.answer(t(lang, "ask_source_url"), reply_markup=K.cancel_kb(lang))
    if action == "top":
        rows = db.fetchall("SELECT * FROM sources WHERE enabled=1 ORDER BY last_count DESC, total_found DESC LIMIT 25")
        text = "\n".join(f"{i + 1}. [{r['last_count']}/{r['total_found']}] {esc(r['url'][:70])}" for i, r in enumerate(rows))
        return await edit_or_send(c, text or "—", K.back_kb(lang, "sources"))
    if action == "bad":
        rows = db.fetchall("SELECT * FROM sources WHERE fail_count>0 OR enabled=0 ORDER BY fail_count DESC LIMIT 25")
        text = "\n".join(f"{'❌' if not r['enabled'] else '⚠️'} fails={r['fail_count']} {esc(r['url'][:70])}" for r in rows)
        return await edit_or_send(c, text or "—", K.back_kb(lang, "sources"))
    if action == "ai":
        from .ai_handlers import start_discovery
        await start_discovery(c, lang, bot)


# ------------------------------------------------------- pending text input
@router.message(Command("cancel"))
async def cmd_cancel(m: Message):
    RT.pending_input.pop(m.from_user.id, None)
    await m.answer(t(lang_of(m.from_user), "cancelled"))


async def handle_pending_input(m: Message, lang: str) -> bool:
    """Returns True if the message was consumed by a pending prompt."""
    uid = m.from_user.id
    p = RT.pending_input.get(uid)
    if not p:
        return False
    db = get_db()
    text = (m.text or "").strip()
    kind = p["kind"]
    if kind == "count":
        if not text.isdigit() or not 1 <= int(text) <= 100:
            await m.answer(t(lang, "invalid_number"))
            return True
        db.kv_set(f"count:{uid}", int(text))
        RT.pending_input.pop(uid)
        await menu_proxies(m, lang)
    elif kind == "setting":
        try:
            val = db.set(p["key"], text)
        except (ValueError, TypeError) as e:
            await m.answer(t(lang, "set_err", err=esc(e)))
            return True
        RT.pending_input.pop(uid)
        if p["key"] in ("scan_interval_min", "auto_scan") and RT.scheduler:
            RT.scheduler.reschedule()
        await m.answer(t(lang, "set_ok", key=p["key"], val=esc(val)), reply_markup=K.settings_group_kb(lang, _group_of(p["key"]), db.all_settings()))
    elif kind == "admin_id":
        if m.forward_from:
            new_id = m.forward_from.id
        elif text.lstrip("-").isdigit():
            new_id = int(text)
        else:
            await m.answer(t(lang, "invalid_number"))
            return True
        RT.pending_input[uid] = {"kind": "admin_perms", "id": new_id}
        await m.answer(t(lang, "ask_admin_perms"), reply_markup=K.cancel_kb(lang))
    elif kind == "admin_perms":
        perms = ["*"] if text == "*" else [x for x in text.lower().split() if x in PERMS]
        if not perms:
            await m.answer(t(lang, "ask_admin_perms"))
            return True
        db.add_admin(p["id"], perms, uid)
        RT.pending_input.pop(uid)
        await m.answer(t(lang, "admin_added", id=p["id"], perms=esc(" ".join(perms))))
        await menu_admins(m, lang)
    elif kind == "source_url":
        if not text.startswith("http"):
            await m.answer(t(lang, "ask_source_url"))
            return True
        kind2 = "channel" if "t.me/" in text else "raw"
        if "t.me/" in text and "/s/" not in text:
            text = text.replace("t.me/", "t.me/s/", 1)
        ok = db.add_source(text, kind=kind2, added_by="manual")
        RT.pending_input.pop(uid)
        await m.answer(t(lang, "source_added" if ok else "source_exists"))
        await menu_sources(m, lang)
    else:
        return False
    return True


@router.message(Command("explain"))
async def cmd_explain(m: Message):
    lang = lang_of(m.from_user)
    if not allowed(m.from_user.id):
        return await m.answer(t(lang, "not_allowed"))
    await m.answer(t(lang, "explain"), disable_web_page_preview=True)


@router.message(Command("help"))
async def cmd_help(m: Message):
    await m.answer(t(lang_of(m.from_user), "help"))
