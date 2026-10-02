"""Tiny i18n layer. `t(lang, key, **fmt)` falls back to English.

Languages (order = order shown in the language picker):
    en English (default) · fa فارسی · ru Русский · ar العربية · tr Türkçe
    zh 中文 · es Español · de Deutsch · fr Français · hi हिन्दी
"""
from __future__ import annotations

from .strings import STRINGS

LANGS: list[tuple[str, str]] = [
    ("en", "🇬🇧 English"), ("fa", "🇮🇷 فارسی"), ("ru", "🇷🇺 Русский"), ("ar", "🇸🇦 العربية"),
    ("tr", "🇹🇷 Türkçe"), ("zh", "🇨🇳 中文"), ("es", "🇪🇸 Español"), ("de", "🇩🇪 Deutsch"),
    ("fr", "🇫🇷 Français"), ("hi", "🇮🇳 हिन्दी"),
]
LANG_CODES = {c for c, _ in LANGS}
RTL = {"fa", "ar"}


def t(lang: str, key: str, /, **fmt) -> str:
    table = STRINGS.get(lang) or STRINGS["en"]
    s = table.get(key) or STRINGS["en"].get(key) or key
    if fmt:
        try:
            return s.format(**fmt)
        except (KeyError, IndexError):
            return s
    return s


def lang_name(code: str) -> str:
    return dict(LANGS).get(code, code)
