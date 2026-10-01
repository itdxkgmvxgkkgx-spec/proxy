"""کیبوردها — هم صفحه شیشه‌ای (Inline روی چت) هم کیبورد معمولی (روی کیبورد گوشی)."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

from ..i18n import LANG_NAMES, t


def main_inline(lang, is_admin=False, public=False):
    rows = [
        [InlineKeyboardButton(t("btn_list", lang), callback_data="list"),
         InlineKeyboardButton(t("btn_scan", lang), callback_data="scan")],
        [InlineKeyboardButton(t("btn_settings", lang), callback_data="settings"),
         InlineKeyboardButton(t("btn_lang", lang), callback_data="lang")],
        [InlineKeyboardButton(t("btn_log", lang), callback_data="log"),
         InlineKeyboardButton(t("btn_help", lang), callback_data="help")],
        [InlineKeyboardButton(t("btn_ai", lang), callback_data="ai")],
    ]
    if is_admin:
        rows.append([InlineKeyboardButton(t("btn_admin", lang), callback_data="admins"),
                     InlineKeyboardButton(("🌍 " if not public else "🔒 ") + t("btn_public", lang),
                                          callback_data="public")])
    return InlineKeyboardMarkup(rows)


def main_reply(lang):
    """کیبورد پایین صفحه گوشی."""
    keys = [
        [t("btn_list", lang), t("btn_scan", lang)],
        [t("btn_settings", lang), t("btn_lang", lang)],
        [t("btn_log", lang), t("btn_help", lang)],
        [t("btn_ai", lang)],
    ]
    return ReplyKeyboardMarkup(keys, resize_keyboard=True)


def back(lang):
    return InlineKeyboardMarkup([[InlineKeyboardButton(t("btn_back", lang), callback_data="back")]])


def languages():
    rows, row = [], []
    for code, name in LANG_NAMES.items():
        row.append(InlineKeyboardButton(name, callback_data=f"lang:{code}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


def send_mode(lang):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(t("btn_file", lang), callback_data="send:file"),
        InlineKeyboardButton(t("btn_inline", lang), callback_data="send:text")],
        [InlineKeyboardButton(t("btn_back", lang), callback_data="back")]])


def settings(lang):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🕐 Interval", callback_data="set:interval"),
         InlineKeyboardButton("🧵 Threads", callback_data="set:threads")],
        [InlineKeyboardButton("📦 Batch", callback_data="set:batch")],
        [InlineKeyboardButton(t("btn_back", lang), callback_data="back")]])


def admins_kb(lang):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add admin", callback_data="adm:add"),
         InlineKeyboardButton("➖ Remove admin", callback_data="adm:del")],
        [InlineKeyboardButton(t("btn_back", lang), callback_data="back")]])


def models_kb(models):
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(m, callback_data=f"model:{m}")] for m in models[:20]])


def approve_kb(action_id):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Approve", callback_data=f"approve:{action_id}"),
        InlineKeyboardButton("❌ Deny", callback_data="deny")]])
