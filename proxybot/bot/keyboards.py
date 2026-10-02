"""Keyboards: inline (glass buttons under messages) + reply keyboard + command list."""
from __future__ import annotations

from aiogram.types import (BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton,
                           ReplyKeyboardMarkup)

from ..core.config import DEFAULT_SETTINGS
from ..i18n import LANGS, t

SETTING_GROUPS = {
    "sched": ["scan_interval_min", "auto_scan", "retention_days", "save_interval_sec", "github_discover_every"],
    "pipe": ["threads", "speed_threads", "ping_timeout", "speed_timeout", "speed_bytes", "max_ping_ms", "min_score", "top_n",
             "iran_check", "source_timeout"],
    "bot": ["public_mode", "default_lang", "send_mode", "send_count"],
    "ai": ["ai_model", "ai_temperature", "ai_max_steps", "ai_memory_notify", "ai_auto_discover", "ai_discover_every"],
}


def ib(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data[:64])


def lang_kb() -> InlineKeyboardMarkup:
    rows, row = [], []
    for code, name in LANGS:
        row.append(ib(name, f"lang:{code}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def main_inline(lang: str, is_admin: bool, public: bool) -> InlineKeyboardMarkup:
    rows = [[ib(t(lang, "btn_proxies"), "m:proxies"), ib(t(lang, "btn_status"), "m:status")],
            [ib(t(lang, "btn_history"), "m:history"), ib(t(lang, "btn_explain"), "m:explain")]]
    if is_admin:
        rows.insert(1, [ib(t(lang, "btn_scan"), "m:scan"), ib(t(lang, "btn_log"), "m:log")])
        rows.append([ib(t(lang, "btn_settings"), "m:settings"), ib(t(lang, "btn_sources"), "m:sources")])
        rows.append([ib(t(lang, "btn_ai"), "m:ai"), ib(t(lang, "btn_admins"), "m:admins")])
        rows.append([ib(t(lang, "btn_public", state=t(lang, "on" if public else "off")), "m:public")])
    rows.append([ib(t(lang, "btn_lang"), "m:lang"), ib(t(lang, "btn_help"), "m:help")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def main_reply(lang: str, is_admin: bool) -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text=t(lang, "btn_proxies")), KeyboardButton(text=t(lang, "btn_status"))],
            [KeyboardButton(text=t(lang, "btn_history")), KeyboardButton(text=t(lang, "btn_explain"))]]
    if is_admin:
        rows.insert(1, [KeyboardButton(text=t(lang, "btn_scan")), KeyboardButton(text=t(lang, "btn_log"))])
        rows.append([KeyboardButton(text=t(lang, "btn_settings")), KeyboardButton(text=t(lang, "btn_ai"))])
    rows.append([KeyboardButton(text=t(lang, "btn_lang")), KeyboardButton(text=t(lang, "btn_help"))])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, is_persistent=True)


def reply_button_map(lang: str) -> dict[str, str]:
    """reply-keyboard text -> menu action"""
    return {t(lang, k): v for k, v in (("btn_proxies", "proxies"), ("btn_status", "status"), ("btn_history", "history"),
                                        ("btn_explain", "explain"), ("btn_scan", "scan"), ("btn_log", "log"),
                                        ("btn_settings", "settings"), ("btn_ai", "ai"), ("btn_lang", "lang"), ("btn_help", "help"))}


def back_kb(lang: str, to: str = "main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[ib(t(lang, "back"), f"m:{to}")]])


def proxies_kb(lang: str, count: int, top_n: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [ib(t(lang, "btn_list", n=top_n), "px:list")],
        [ib(t(lang, "btn_send_single"), "px:single"), ib(t(lang, "btn_send_batch"), "px:batch")],
        [ib(t(lang, "btn_send_file"), "px:file"), ib(t(lang, "btn_count", n=count), "px:count")],
        [ib(t(lang, "back"), "m:main")],
    ])


def log_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [ib(t(lang, "btn_log_refresh"), "log:all"), ib(t(lang, "btn_log_errors"), "log:err")],
        [ib(t(lang, "back"), "m:main")]])


def settings_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [ib(t(lang, "grp_sched"), "sg:sched"), ib(t(lang, "grp_pipe"), "sg:pipe")],
        [ib(t(lang, "grp_bot"), "sg:bot"), ib(t(lang, "grp_ai"), "sg:ai")],
        [ib(t(lang, "back"), "m:main")]])


def settings_group_kb(lang: str, group: str, values: dict) -> InlineKeyboardMarkup:
    rows = []
    for key in SETTING_GROUPS[group]:
        val = values.get(key, DEFAULT_SETTINGS[key][0])
        if key in ("auto_scan", "iran_check", "public_mode", "ai_auto_discover"):
            label = f"{key}: {'✅' if int(val) else '❌'}"
            rows.append([ib(label, f"st:{key}")])
        else:
            rows.append([ib(f"{key}: {val}", f"se:{key}")])
    rows.append([ib(t(lang, "back"), "m:settings")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def history_kb(lang: str, days: list) -> InlineKeyboardMarkup:
    rows = [[ib(t(lang, "history_row", day=d["day"], tested=d["tested"], alive=d["alive"] or 0, avg=int(d["avg_ping"] or 0)), f"hd:{d['day']}")]
            for d in days[:14]]
    rows.append([ib(t(lang, "back"), "m:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admins_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [ib(t(lang, "btn_add_admin"), "ad:add"), ib(t(lang, "btn_del_admin"), "ad:del")],
        [ib(t(lang, "btn_perm_admin"), "ad:perm")], [ib(t(lang, "back"), "m:main")]])


def admin_pick_kb(lang: str, admins, action: str) -> InlineKeyboardMarkup:
    rows = [[ib(f"{a['user_id']} {('@' + a['username']) if a['username'] else (a['first_name'] or '')}{' 👑' if a['is_owner'] else ''}",
                f"adp:{action}:{a['user_id']}")] for a in admins if not a["is_owner"]]
    rows.append([ib(t(lang, "back"), "m:admins")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def sources_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [ib(t(lang, "btn_add_source"), "src:add"), ib(t(lang, "btn_list_sources"), "src:top")],
        [ib(t(lang, "btn_bad_sources"), "src:bad"), ib(t(lang, "btn_ai_discover"), "src:ai")],
        [ib(t(lang, "back"), "m:main")]])


def ai_kb(lang: str, pending: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [ib(t(lang, "btn_ai_new"), "ai:new"), ib(t(lang, "btn_ai_pending", n=pending), "ai:pending")],
        [ib(t(lang, "btn_ai_memory"), "ai:memory"), ib(t(lang, "btn_ai_skills"), "ai:skills")],
        [ib(t(lang, "btn_ai_model"), "ai:model"), ib(t(lang, "btn_ai_setup"), "ai:setup")],
        [ib(t(lang, "btn_ai_discover"), "ai:discover")],
        [ib(t(lang, "back"), "m:main")]])


def approval_kb(lang: str, pid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [ib(t(lang, "btn_approve"), f"ap:y:{pid}"), ib(t(lang, "btn_deny"), f"ap:n:{pid}")],
        [ib(t(lang, "btn_approve_all"), "ap:y:all"), ib(t(lang, "btn_deny_all"), "ap:n:all")]])


def models_kb(models: list[str], page: int = 0) -> InlineKeyboardMarkup:
    per = 16
    chunk = models[page * per:(page + 1) * per]
    rows = [[ib(m[:40], f"mdl:{i + page * per}")] for i, m in enumerate(chunk)]
    nav = []
    if page > 0:
        nav.append(ib("◀️", f"mdlp:{page - 1}"))
    if (page + 1) * per < len(models):
        nav.append(ib("▶️", f"mdlp:{page + 1}"))
    if nav:
        rows.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def cancel_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[ib(t(lang, "cancel"), "m:cancel")]])


def bot_commands() -> list[BotCommand]:
    return [BotCommand(command=c, description=d) for c, d in (
        ("start", "Main menu"), ("proxies", "Get proxies"), ("scan", "Run a scan now"), ("status", "Status"),
        ("log", "Live log"), ("history", "Proxy history by date"), ("settings", "Settings"), ("sources", "Proxy sources"),
        ("ai", "Talk to Proxy AI"), ("ai_new", "New AI session"), ("ai_setup", "Configure AI provider"),
        ("pending", "Approve AI actions"), ("admins", "Manage admins"), ("public", "Toggle public mode"),
        ("lang", "Language"), ("explain", "How the bot works"), ("ping", "Bot latency"), ("cancel", "Cancel input"))]
