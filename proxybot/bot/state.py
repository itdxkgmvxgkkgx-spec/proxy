"""Shared bot runtime state + access helpers."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from aiogram.types import CallbackQuery, Message, User

from ..core.config import SECRETS
from ..core.database import get_db
from ..i18n import LANG_CODES

PERMS = ("scan", "settings", "sources", "ai", "admins", "logs")
MENU_PERM = {"scan": "scan", "log": "logs", "settings": "settings", "sources": "sources", "ai": "ai", "admins": "admins",
             "public": "admins"}


@dataclass
class Runtime:
    started: float = field(default_factory=time.time)
    persister: Any = None
    scheduler: Any = None
    pending_input: dict[int, dict] = field(default_factory=dict)   # user_id -> {"kind":..., ...}
    ai_busy: set[int] = field(default_factory=set)
    model_cache: dict[int, list[str]] = field(default_factory=dict)

    def uptime(self) -> str:
        s = int(time.time() - self.started)
        return f"{s // 3600}h{(s % 3600) // 60:02d}m"


RT = Runtime()


def user_of(ev: Message | CallbackQuery) -> User:
    return ev.from_user


def lang_of(user: User) -> str:
    db = get_db()
    row = db.touch_user(user.id, user.username or "", user.first_name or "")
    lang = row["lang"]
    if lang not in LANG_CODES:
        lang = "en"
    return lang


def is_admin(uid: int) -> bool:
    db = get_db()
    db.ensure_owner(SECRETS.admin_id)
    return db.is_admin(uid)


def allowed(uid: int) -> bool:
    """May this user use the public part of the bot?"""
    return is_admin(uid) or bool(int(get_db().get("public_mode", 0)))


def has_perm(uid: int, perm: str) -> bool:
    return is_admin(uid) and get_db().has_perm(uid, perm)


def fmt_next_scan() -> str:
    sch = RT.scheduler
    if not sch or not int(get_db().get("auto_scan", 1)):
        return "—"
    left = int(sch.next_run - time.time())
    if left <= 0:
        return "now"
    return f"{left // 60}m{left % 60:02d}s"
