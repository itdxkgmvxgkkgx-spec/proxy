"""Logging that goes to stdout, a rotating file AND the SQLite `logs` table.

The bot's /log menu reads from SQLite so the user sees exactly what the
pipeline is doing right now (stage + counters), even after a restart.
"""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from .config import LOG_DIR

_STATE = {"stage": "idle", "detail": "", "progress": ""}


class _DBHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            from .database import get_db
            get_db().log(record.levelname, self.format(record), getattr(record, "stage", _STATE["stage"]))
        except Exception:
            pass


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    root = logging.getLogger()
    if root.handlers:
        return logging.getLogger("proxybot")
    root.setLevel(level)
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s", "%H:%M:%S")
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    root.addHandler(sh)
    fh = RotatingFileHandler(LOG_DIR / "proxybot.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    fh.setFormatter(fmt)
    root.addHandler(fh)
    dbh = _DBHandler()
    dbh.setFormatter(logging.Formatter("%(message)s"))
    dbh.setLevel(logging.INFO)
    root.addHandler(dbh)
    for noisy in ("aiogram", "aiohttp", "asyncio", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    return logging.getLogger("proxybot")


def set_stage(stage: str, detail: str = "", progress: str = "") -> None:
    """Pipeline tells the world what it is doing; the /log menu reads it."""
    _STATE.update(stage=stage, detail=detail, progress=progress)


def current_stage() -> dict[str, str]:
    return dict(_STATE)
