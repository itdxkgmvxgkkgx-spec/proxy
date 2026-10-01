"""هندلرهای بات تلگرام — سریع، بدون بلاک شدن (پینگ نزدیک صفر)."""
import io
import json
import time

from telegram import Update
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler,
                          ContextTypes, MessageHandler, filters)

from .. import database as db
from ..config import INITIAL_ADMIN_ID, DEFAULT_SCAN_INTERVAL_MIN, DEFAULT_THREADS
from ..i18n import t, LANG_NAMES
from ..ai import agent as ai
from ..scheduler import full_scan
from . import keyboards as kb

# state موقت کاربر (مثلاً منتظر ورودی عددی)
_user_state = {}
_ai_sessions = {}
_pending_actions = {}


def lang_of(uid):
    return db.get_user_lang(uid)


def allowed(uid):
    return db.is_admin(uid) or db.get_setting("public_mode", "0") == "1"


def sensitive_ok(uid):
    return db.is_admin(uid)


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    db.upsert_user(u.id, u.username or "")
    if INITIAL_ADMIN_ID and not db.list_admins():
        db.add_admin(INITIAL_ADMIN_ID, "owner")
    if not allowed(u.id):
        await update.message.reply_text("⛔ This bot is private.")
        return
    lang = lang_of(u.id)
    await update.message.reply_text(
        t("welcome", lang), parse_mode="Markdown",
        reply_markup=kb.main_reply(lang))
    await update.message.reply_text(
        "🎛 Control panel:",
        reply_markup=kb.main_inline(lang, db.is_admin(u.id),
                                    db.get_setting("public_mode", "0") == "1"))


async def cmd_menu(update: Update, ctx):
    await cmd_start(update, ctx)


async def cmd_list(update: Update, ctx):
    await _send_proxies(update.message.reply_text, update.effective_user.id)


async def cmd_log(update: Update, ctx):
    await _send_log(update.message.reply_text, update.effective_user.id)


async def _send_proxies(reply, uid, as_file=None):
    lang = lang_of(uid)
    proxies = db.get_proxies(status="alive", limit=int(db.get_setting("batch", 20)))
    if not proxies:
        await reply(t("no_proxies", lang))
        return
    lines = [t("proxy_line", lang, s=p["server"], p=p["port"], k=p["secret"],
               ping=round(p["ping_ms"] or 0), dl=round(p["dl_kbps"] or 0, 1),
               ul=round(p["ul_kbps"] or 0, 1), score=p["score"]) for p in proxies]
    # ارسال متنی دسته‌ای (پیش‌فرض سریع)
    for i in range(0, len(lines), 8):
        await reply("\n\n".join(lines[i:i + 8]), parse_mode="Markdown")


async def _send_log(reply, uid):
    lang = lang_of(uid)
    logs = db.get_logs(15)
    if not logs:
        await reply(t("log_empty", lang))
        return
    counts = db.count_proxies()
    txt = f"📜 **Live log**\n🗄 DB: {counts}\n\n" + "\n".join(
        f"`{l['ts'][11:19]}` [{l['stage']}] {l['message']}" for l in logs)
    await reply(txt, parse_mode="Markdown")


# ---------- Callbacks ----------
async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()  # پاسخ فوری — پینگ صفر
    uid = q.from_user.id
    lang = lang_of(uid)
    data = q.data

    if not allowed(uid):
        await q.edit_message_text("⛔")
        return

    if data == "back":
        await q.edit_message_text(t("welcome", lang), parse_mode="Markdown",
                                  reply_markup=kb.main_inline(lang, db.is_admin(uid),
                                                              db.get_setting("public_mode", "0") == "1"))
    elif data == "list":
        proxies = db.get_proxies(status="alive", limit=int(db.get_setting("batch", 20)))
        if not proxies:
            await q.edit_message_text(t("no_proxies", lang), reply_markup=kb.back(lang))
        else:
            _user_state[uid] = {"proxies_cache": [
                f"tg://proxy?server={p['server']}&port={p['port']}&secret={p['secret']}"
                for p in proxies]}
            await q.edit_message_text(f"📦 {len(proxies)} proxies ready. How to send?",
                                      reply_markup=kb.send_mode(lang))
    elif data.startswith("send:"):
        mode = data.split(":")[1]
        lines = _user_state.get(uid, {}).get("proxies_cache", [])
        if mode == "file":
            f = io.BytesIO("\n".join(lines).encode())
            f.name = "proxies.txt"
            await q.message.reply_document(document=f, caption="📄 Proxy list")
        else:
            for line in lines:
                await q.message.reply_text(f"`{line}`", parse_mode="Markdown")
    elif data == "scan":
        if not sensitive_ok(uid):
            await q.answer(t("admin_only", lang), show_alert=True)
            return
        await q.edit_message_text(t("scanning", lang))

        async def progress(done, total, alive):
            try:
                await q.edit_message_text(f"⏳ {done}/{total} tested — ✅ {alive} alive")
            except Exception:
                pass

        new, alive, dead = await full_scan(progress)
        await q.edit_message_text(t("scan_done", lang, new=new, alive=alive, dead=dead),
                                  reply_markup=kb.back(lang))
    elif data == "settings":
        await q.edit_message_text(
            t("settings_txt", lang,
              interval=db.get_setting("scan_interval", DEFAULT_SCAN_INTERVAL_MIN),
              threads=db.get_setting("threads", DEFAULT_THREADS),
              batch=db.get_setting("batch", 20)),
            parse_mode="Markdown", reply_markup=kb.settings(lang))
    elif data.startswith("set:"):
        if not sensitive_ok(uid):
            await q.answer(t("admin_only", lang), show_alert=True)
            return
        key = data.split(":")[1]
        _user_state[uid] = {"await": key}
        prompt = {"interval": t("set_interval", lang),
                  "threads": t("set_threads", lang),
                  "batch": t("set_batch", lang)}[key]
        await q.edit_message_text(prompt, reply_markup=kb.back(lang))
    elif data == "lang":
        await q.edit_message_text(t("choose_lang", lang), reply_markup=kb.languages())
    elif data.startswith("lang:"):
        code = data.split(":")[1]
        db.set_user_lang(uid, code)
        await q.edit_message_text(t("saved", code) + " " + LANG_NAMES[code],
                                  reply_markup=kb.back(code))
    elif data == "log":
        logs = db.get_logs(10)
        txt = "📜 " + ("\n".join(f"`{l['ts'][11:19]}` [{l['stage']}] {l['message'][:80]}"
                                 for l in logs) or t("log_empty", lang))
        await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=kb.back(lang))
    elif data == "help":
        await q.edit_message_text(t("help", lang), parse_mode="Markdown",
                                  reply_markup=kb.back(lang))
    elif data == "public":
        if not sensitive_ok(uid):
            await q.answer(t("admin_only", lang), show_alert=True)
            return
        cur = db.get_setting("public_mode", "0")
        db.set_setting("public_mode", "0" if cur == "1" else "1")
        msg = t("public_off", lang) if cur == "1" else t("public_on", lang)
        await q.edit_message_text(msg, reply_markup=kb.back(lang))
    elif data == "admins":
        if not sensitive_ok(uid):
            await q.answer(t("admin_only", lang), show_alert=True)
            return
        lst = "\n".join(f"• `{a['user_id']}` ({a['role']})" for a in db.list_admins())
        await q.edit_message_text(t("admin_list", lang, list=lst),
                                  parse_mode="Markdown", reply_markup=kb.admins_kb(lang))
    elif data.startswith("adm:"):
        if not sensitive_ok(uid):
            await q.answer(t("admin_only", lang), show_alert=True)
            return
        _user_state[uid] = {"await": data.split(":")[1]}
        prompt = t("admin_add", lang) if data.endswith("add") else t("admin_del", lang)
        await q.edit_message_text(prompt, reply_markup=kb.back(lang))
    elif data == "ai":
        await _ai_entry(q, uid, lang)
    elif data.startswith("model:"):
        db.ai_cfg_set("model", data.split(":", 1)[1])
        _ai_sessions[uid] = []
        await q.edit_message_text(t("ai_ready", lang), reply_markup=kb.back(lang))
    elif data.startswith("approve:"):
        action = _pending_actions.pop(data.split(":", 1)[1], None)
        if action:
            await q.edit_message_text(f"✅ Approved. Executing...\n{action}")
            # اینجا اکشن حساس اجرا می‌شه (در نسخه فعلی: فقط لاگ + اجرای ابزار)
            db.log("info", "ai", f"approved action: {action[:100]}")
    elif data == "deny":
        await q.edit_message_text("❌ Denied.", reply_markup=kb.back(lang))


async def _ai_entry(q, uid, lang):
    if not sensitive_ok(uid):
        await q.answer(t("admin_only", lang), show_alert=True)
        return
    if not db.ai_cfg_get("base_url"):
        _user_state[uid] = {"await": "ai_base_url"}
        await q.edit_message_text(t("ai_need_cfg", lang), reply_markup=kb.back(lang))
    elif not db.ai_cfg_get("api_key"):
        _user_state[uid] = {"await": "ai_key"}
        await q.edit_message_text(t("ai_need_key", lang), reply_markup=kb.back(lang))
    elif not db.ai_cfg_get("model"):
        models = await ai.list_models(db.ai_cfg_get("base_url"), db.ai_cfg_get("api_key"))
        if models:
            await q.edit_message_text(t("ai_pick", lang), reply_markup=kb.models_kb(models))
        else:
            db.ai_cfg_set("model", "gpt-4o-mini")
            await q.edit_message_text(t("ai_ready", lang), reply_markup=kb.back(lang))
    else:
        await q.edit_message_text(t("ai_ready", lang), reply_markup=kb.back(lang))


# ---------- پیام‌های متنی ----------
async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not allowed(uid):
        return
    lang = lang_of(uid)
    text = update.message.text.strip()
    state = _user_state.get(uid, {})
    awaiting = state.get("await")

    # دکمه‌های کیبورد معمولی
    for code in ("en", "fa"):
        m = {
            t("btn_list", code): "list", t("btn_scan", code): "scan",
            t("btn_settings", code): "settings", t("btn_lang", code): "lang",
            t("btn_log", code): "log", t("btn_help", code): "help",
            t("btn_ai", code): "ai",
        }
        if text in m:
            fake = type("Q", (), {"data": m[text], "from_user": update.effective_user,
                                  "answer": lambda *a, **k: None,
                                  "edit_message_text": update.message.reply_text,
                                  "message": update.message})
            await on_callback(type("U", (), {"callback_query": fake})(), ctx)
            return

    if awaiting:
        _user_state.pop(uid, None)
        if awaiting in ("interval", "threads", "batch") and text.isdigit():
            key = {"interval": "scan_interval", "threads": "threads",
                   "batch": "batch"}[awaiting]
            db.set_setting(key, text)
            await update.message.reply_text(t("saved", lang))
        elif awaiting == "adm_add" and text.isdigit():
            db.add_admin(int(text))
            await update.message.reply_text(t("saved", lang))
        elif awaiting == "adm_del" and text.isdigit():
            db.remove_admin(int(text))
            await update.message.reply_text(t("saved", lang))
        elif awaiting == "ai_base_url":
            db.ai_cfg_set("base_url", text)
            _user_state[uid] = {"await": "ai_key"}
            await update.message.reply_text(t("ai_need_key", lang))
        elif awaiting == "ai_key":
            db.ai_cfg_set("api_key", text)
            await update.message.reply_text(t("ai_models", lang))
            models = await ai.list_models(db.ai_cfg_get("base_url"), text)
            if models:
                await update.message.reply_text(t("ai_pick", lang),
                                                reply_markup=kb.models_kb(models))
            else:
                db.ai_cfg_set("model", "gpt-4o-mini")
                await update.message.reply_text(t("ai_ready", lang))
        return

    # چت با Proxy AI (اگر سشن فعاله یا پیام با /ai شروع شده)
    if db.ai_cfg_get("model") and db.is_admin(uid):
        history = _ai_sessions.setdefault(uid, [])
        if not history:
            history.append({"role": "system", "content": ai.build_system_prompt()})
        history.append({"role": "user", "content": text})
        # ابزارهای ساده: دستورات کلیدی
        if text.lower().startswith("remember "):
            kv = text[9:].split("=", 1)
            if len(kv) == 2:
                await update.message.reply_text(ai.tool_remember(kv[0].strip(), kv[1].strip()),
                                                parse_mode="Markdown")
                return
        if text.lower().startswith("find sources"):
            await update.message.reply_text("🔎 Searching with Tavily...")
            await update.message.reply_text(await ai.tool_find_sources())
            return
        try:
            resp = await ai.chat(history[-20:])
            history.append({"role": "assistant", "content": resp or ""})
            await update.message.reply_text(resp or "…")
        except Exception as e:
            await update.message.reply_text(f"⚠️ AI error: {e}")
        return


def register(app: Application):
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("log", cmd_log))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
