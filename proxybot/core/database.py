"""SQLite persistence layer (WAL mode, thread-safe, no data ever lost).

Single file `data/proxybot.db`. Every table is created idempotently so the bot
can be upgraded in place. All timestamps are UTC ISO-8601 strings.

Tables
------
settings        key/value runtime settings (see config.DEFAULT_SETTINGS)
users           every Telegram user that talked to the bot (+ language)
admins          admin ids with JSON permission list
sources         proxy source URLs (built-in + AI discovered + manual)
proxies         current proxy table — one row per (host, port, secret)
proxy_history   per-run measurement history (ping/speed) for date queries
runs            pipeline run log (stages, counters)
logs            structured log lines shown by the /log menu
ai_sessions     chat sessions of the Proxy AI (one active per user)
ai_messages     full message history of each session
ai_pending      staged dangerous actions waiting for approval
kv              generic key/value store (scheduler state, run chain, etc.)
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from .config import DB_PATH, DEFAULT_SETTINGS


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, lang TEXT DEFAULT 'en',
  created_at TEXT, last_seen TEXT, banned INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS admins (
  user_id INTEGER PRIMARY KEY, permissions TEXT NOT NULL DEFAULT '["*"]',
  added_by INTEGER, added_at TEXT, is_owner INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sources (
  id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT UNIQUE NOT NULL, kind TEXT DEFAULT 'auto',
  enabled INTEGER DEFAULT 1, added_by TEXT DEFAULT 'builtin', added_at TEXT,
  last_fetch TEXT, last_count INTEGER DEFAULT 0, total_found INTEGER DEFAULT 0,
  fail_count INTEGER DEFAULT 0, note TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS proxies (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  host TEXT NOT NULL, port INTEGER NOT NULL, secret TEXT NOT NULL,
  link TEXT NOT NULL, first_seen TEXT, last_seen TEXT, last_ok TEXT,
  ping_ms INTEGER, down_kbps REAL, up_kbps REAL, score REAL DEFAULT 0,
  iran_ok INTEGER DEFAULT -1, status TEXT DEFAULT 'new', fails INTEGER DEFAULT 0,
  source_id INTEGER, country TEXT DEFAULT '', secret_type TEXT DEFAULT '',
  UNIQUE(host, port, secret)
);
CREATE INDEX IF NOT EXISTS idx_proxies_status ON proxies(status, score DESC);
CREATE INDEX IF NOT EXISTS idx_proxies_last_ok ON proxies(last_ok);

CREATE TABLE IF NOT EXISTS proxy_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT, proxy_id INTEGER NOT NULL, ts TEXT NOT NULL,
  ping_ms INTEGER, down_kbps REAL, up_kbps REAL, ok INTEGER, run_id INTEGER,
  FOREIGN KEY(proxy_id) REFERENCES proxies(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_history_ts ON proxy_history(ts);
CREATE INDEX IF NOT EXISTS idx_history_proxy ON proxy_history(proxy_id, ts);

CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT, started TEXT, finished TEXT, stage TEXT DEFAULT 'idle',
  found INTEGER DEFAULT 0, uniq INTEGER DEFAULT 0, alive INTEGER DEFAULT 0,
  speed_tested INTEGER DEFAULT 0, listed INTEGER DEFAULT 0, note TEXT DEFAULT '',
  gh_run_id TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, level TEXT NOT NULL,
  stage TEXT DEFAULT '', msg TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_logs_ts ON logs(ts);

CREATE TABLE IF NOT EXISTS ai_sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, created TEXT,
  title TEXT DEFAULT '', active INTEGER DEFAULT 1, summary TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS ai_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER NOT NULL, role TEXT NOT NULL,
  content TEXT, tool_calls TEXT, tool_call_id TEXT, name TEXT, ts TEXT NOT NULL,
  FOREIGN KEY(session_id) REFERENCES ai_sessions(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_ai_msgs ON ai_messages(session_id, id);

CREATE TABLE IF NOT EXISTS ai_pending (
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, session_id INTEGER,
  tool TEXT NOT NULL, args TEXT NOT NULL, reason TEXT DEFAULT '', created TEXT,
  status TEXT DEFAULT 'pending', result TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT, updated TEXT);
"""


class Database:
    """Thread-safe SQLite wrapper. One instance per process (see `db`)."""

    def __init__(self, path: Path | str = DB_PATH):
        self.path = str(path)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(SCHEMA)
        self._seed_settings()

    # ------------------------------------------------------------------ core
    @contextmanager
    def tx(self):
        with self._lock:
            self._conn.execute("BEGIN")
            try:
                yield self._conn
                self._conn.execute("COMMIT")
            except Exception:
                self._conn.execute("ROLLBACK")
                raise

    def execute(self, sql: str, params: Iterable = ()) -> sqlite3.Cursor:
        with self._lock:
            return self._conn.execute(sql, tuple(params))

    def executemany(self, sql: str, rows: Iterable[Iterable]) -> None:
        with self._lock:
            self._conn.executemany(sql, [tuple(r) for r in rows])

    def fetchone(self, sql: str, params: Iterable = ()) -> Optional[sqlite3.Row]:
        return self.execute(sql, params).fetchone()

    def fetchall(self, sql: str, params: Iterable = ()) -> list[sqlite3.Row]:
        return self.execute(sql, params).fetchall()

    def checkpoint(self) -> None:
        """Flush WAL into the main file so a git commit captures everything."""
        with self._lock:
            try:
                self._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            except sqlite3.Error:
                pass

    def close(self) -> None:
        with self._lock:
            self.checkpoint()
            self._conn.close()

    # -------------------------------------------------------------- settings
    def _seed_settings(self) -> None:
        for key, (default, _t, _d) in DEFAULT_SETTINGS.items():
            self.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?, ?)", (key, json.dumps(default)))

    def get(self, key: str, default: Any = None) -> Any:
        row = self.fetchone("SELECT value FROM settings WHERE key=?", (key,))
        if row is None:
            if key in DEFAULT_SETTINGS:
                return DEFAULT_SETTINGS[key][0]
            return default
        try:
            return json.loads(row["value"])
        except json.JSONDecodeError:
            return row["value"]

    def set(self, key: str, value: Any) -> Any:
        if key in DEFAULT_SETTINGS:
            caster = DEFAULT_SETTINGS[key][1]
            value = caster(value)
        self.execute("INSERT OR REPLACE INTO settings(key, value) VALUES(?, ?)", (key, json.dumps(value)))
        return value

    def all_settings(self) -> dict[str, Any]:
        return {r["key"]: json.loads(r["value"]) for r in self.fetchall("SELECT key, value FROM settings")}

    # -------------------------------------------------------------------- kv
    def kv_get(self, key: str, default: Any = None) -> Any:
        row = self.fetchone("SELECT value FROM kv WHERE key=?", (key,))
        if row is None:
            return default
        try:
            return json.loads(row["value"])
        except (json.JSONDecodeError, TypeError):
            return row["value"]

    def kv_set(self, key: str, value: Any) -> None:
        self.execute("INSERT OR REPLACE INTO kv(key, value, updated) VALUES(?, ?, ?)",
                     (key, json.dumps(value), utcnow()))

    # ----------------------------------------------------------------- users
    def touch_user(self, user_id: int, username: str = "", first_name: str = "", lang: str | None = None) -> sqlite3.Row:
        now = utcnow()
        row = self.fetchone("SELECT * FROM users WHERE id=?", (user_id,))
        if row is None:
            self.execute(
                "INSERT INTO users(id, username, first_name, lang, created_at, last_seen) VALUES(?,?,?,?,?,?)",
                (user_id, username, first_name, lang or self.get("default_lang", "en"), now, now))
        else:
            self.execute("UPDATE users SET username=?, first_name=?, last_seen=? WHERE id=?",
                         (username or row["username"], first_name or row["first_name"], now, user_id))
        return self.fetchone("SELECT * FROM users WHERE id=?", (user_id,))

    def user_lang(self, user_id: int) -> str:
        row = self.fetchone("SELECT lang FROM users WHERE id=?", (user_id,))
        return row["lang"] if row else self.get("default_lang", "en")

    def set_user_lang(self, user_id: int, lang: str) -> None:
        self.execute("UPDATE users SET lang=? WHERE id=?", (lang, user_id))

    def user_count(self) -> int:
        return self.fetchone("SELECT COUNT(*) c FROM users")["c"]

    # ---------------------------------------------------------------- admins
    def ensure_owner(self, owner_id: int) -> None:
        if owner_id and not self.fetchone("SELECT 1 FROM admins WHERE user_id=?", (owner_id,)):
            self.execute("INSERT INTO admins(user_id, permissions, added_by, added_at, is_owner) VALUES(?,?,?,?,1)",
                         (owner_id, json.dumps(["*"]), owner_id, utcnow()))

    def is_admin(self, user_id: int) -> bool:
        return bool(self.fetchone("SELECT 1 FROM admins WHERE user_id=?", (user_id,)))

    def is_owner(self, user_id: int) -> bool:
        row = self.fetchone("SELECT is_owner FROM admins WHERE user_id=?", (user_id,))
        return bool(row and row["is_owner"])

    def admin_perms(self, user_id: int) -> list[str]:
        row = self.fetchone("SELECT permissions FROM admins WHERE user_id=?", (user_id,))
        return json.loads(row["permissions"]) if row else []

    def has_perm(self, user_id: int, perm: str) -> bool:
        perms = self.admin_perms(user_id)
        return "*" in perms or perm in perms

    def add_admin(self, user_id: int, perms: list[str], added_by: int) -> None:
        self.execute("INSERT OR REPLACE INTO admins(user_id, permissions, added_by, added_at, is_owner) "
                     "VALUES(?,?,?,?, COALESCE((SELECT is_owner FROM admins WHERE user_id=?),0))",
                     (user_id, json.dumps(perms), added_by, utcnow(), user_id))

    def remove_admin(self, user_id: int) -> bool:
        if self.is_owner(user_id):
            return False
        self.execute("DELETE FROM admins WHERE user_id=?", (user_id,))
        return True

    def list_admins(self) -> list[sqlite3.Row]:
        return self.fetchall("SELECT a.*, u.username, u.first_name FROM admins a LEFT JOIN users u ON u.id=a.user_id "
                             "ORDER BY is_owner DESC, added_at")

    # --------------------------------------------------------------- sources
    def add_source(self, url: str, kind: str = "auto", added_by: str = "builtin", note: str = "") -> bool:
        url = url.strip()
        if not url:
            return False
        cur = self.execute("INSERT OR IGNORE INTO sources(url, kind, added_by, added_at, note) VALUES(?,?,?,?,?)",
                           (url, kind, added_by, utcnow(), note))
        return cur.rowcount > 0

    def sources(self, enabled_only: bool = True) -> list[sqlite3.Row]:
        q = "SELECT * FROM sources" + (" WHERE enabled=1" if enabled_only else "") + " ORDER BY id"
        return self.fetchall(q)

    def source_result(self, source_id: int, count: int, ok: bool) -> None:
        if ok:
            self.execute("UPDATE sources SET last_fetch=?, last_count=?, total_found=total_found+?, fail_count=0 WHERE id=?",
                         (utcnow(), count, count, source_id))
        else:
            self.execute("UPDATE sources SET last_fetch=?, last_count=0, fail_count=fail_count+1 WHERE id=?",
                         (utcnow(), source_id))

    def set_source_enabled(self, source_id: int, enabled: bool) -> None:
        self.execute("UPDATE sources SET enabled=? WHERE id=?", (1 if enabled else 0, source_id))

    def remove_source(self, source_id: int) -> None:
        self.execute("DELETE FROM sources WHERE id=?", (source_id,))

    # --------------------------------------------------------------- proxies
    def upsert_proxy(self, host: str, port: int, secret: str, link: str, source_id: int | None,
                     secret_type: str = "") -> int:
        now = utcnow()
        self.execute(
            "INSERT INTO proxies(host, port, secret, link, first_seen, last_seen, source_id, secret_type) "
            "VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(host, port, secret) DO UPDATE SET last_seen=excluded.last_seen",
            (host, port, secret, link, now, now, source_id, secret_type))
        return self.fetchone("SELECT id FROM proxies WHERE host=? AND port=? AND secret=?", (host, port, secret))["id"]

    def record_test(self, proxy_id: int, ok: bool, ping_ms: int | None, down_kbps: float | None,
                    up_kbps: float | None, run_id: int | None, iran_ok: int | None = None) -> None:
        now = utcnow()
        self.execute("INSERT INTO proxy_history(proxy_id, ts, ping_ms, down_kbps, up_kbps, ok, run_id) VALUES(?,?,?,?,?,?,?)",
                     (proxy_id, now, ping_ms, down_kbps, up_kbps, 1 if ok else 0, run_id))
        if ok:
            self.execute("UPDATE proxies SET last_ok=?, ping_ms=?, down_kbps=COALESCE(?, down_kbps), "
                         "up_kbps=COALESCE(?, up_kbps), fails=0, status='alive', iran_ok=COALESCE(?, iran_ok) WHERE id=?",
                         (now, ping_ms, down_kbps, up_kbps, iran_ok, proxy_id))
        else:
            self.execute("UPDATE proxies SET fails=fails+1, status=CASE WHEN fails+1>=3 THEN 'dead' ELSE 'flaky' END WHERE id=?",
                         (proxy_id,))

    def set_score(self, proxy_id: int, score: float) -> None:
        self.execute("UPDATE proxies SET score=? WHERE id=?", (score, proxy_id))

    def best_proxies(self, n: int = 10, min_score: float = 0.0) -> list[sqlite3.Row]:
        return self.fetchall("SELECT * FROM proxies WHERE status='alive' AND score>=? ORDER BY score DESC, ping_ms ASC LIMIT ?",
                             (min_score, n))

    def proxies_by_status(self, status: str | None = None, limit: int = 500) -> list[sqlite3.Row]:
        if status:
            return self.fetchall("SELECT * FROM proxies WHERE status=? ORDER BY score DESC LIMIT ?", (status, limit))
        return self.fetchall("SELECT * FROM proxies ORDER BY score DESC LIMIT ?", (limit,))

    def proxy_stats(self) -> dict[str, int]:
        rows = self.fetchall("SELECT status, COUNT(*) c FROM proxies GROUP BY status")
        out = {r["status"]: r["c"] for r in rows}
        out["total"] = sum(out.values())
        return out

    def history_dates(self, days: int = 30) -> list[sqlite3.Row]:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        return self.fetchall(
            "SELECT substr(ts,1,10) day, COUNT(DISTINCT proxy_id) tested, SUM(ok) alive, "
            "ROUND(AVG(CASE WHEN ok=1 THEN ping_ms END)) avg_ping FROM proxy_history WHERE ts>=? GROUP BY day ORDER BY day DESC",
            (since,))

    def history_for_day(self, day: str, limit: int = 50) -> list[sqlite3.Row]:
        return self.fetchall(
            "SELECT p.link, p.host, p.port, h.ping_ms, h.down_kbps, h.up_kbps, h.ts FROM proxy_history h "
            "JOIN proxies p ON p.id=h.proxy_id WHERE h.ok=1 AND substr(h.ts,1,10)=? ORDER BY h.ping_ms LIMIT ?",
            (day, limit))

    def purge_old(self, days: int) -> int:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        c1 = self.execute("DELETE FROM proxy_history WHERE ts<?", (cutoff,)).rowcount
        c2 = self.execute("DELETE FROM proxies WHERE status='dead' AND last_seen<?", (cutoff,)).rowcount
        c3 = self.execute("DELETE FROM logs WHERE ts<?", (cutoff,)).rowcount
        return c1 + c2 + c3

    # ------------------------------------------------------------------ runs
    def start_run(self, gh_run_id: str) -> int:
        cur = self.execute("INSERT INTO runs(started, stage, gh_run_id) VALUES(?, 'collect', ?)", (utcnow(), gh_run_id))
        return cur.lastrowid

    def update_run(self, run_id: int, **fields: Any) -> None:
        if not fields:
            return
        cols = ", ".join(f"{k}=?" for k in fields)
        self.execute(f"UPDATE runs SET {cols} WHERE id=?", (*fields.values(), run_id))

    def finish_run(self, run_id: int, note: str = "") -> None:
        self.execute("UPDATE runs SET finished=?, stage='done', note=? WHERE id=?", (utcnow(), note, run_id))

    def last_runs(self, n: int = 5) -> list[sqlite3.Row]:
        return self.fetchall("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (n,))

    # ------------------------------------------------------------------ logs
    def log(self, level: str, msg: str, stage: str = "") -> None:
        self.execute("INSERT INTO logs(ts, level, stage, msg) VALUES(?,?,?,?)", (utcnow(), level, stage, msg[:2000]))

    def recent_logs(self, n: int = 30, level: str | None = None) -> list[sqlite3.Row]:
        if level:
            return self.fetchall("SELECT * FROM logs WHERE level=? ORDER BY id DESC LIMIT ?", (level, n))
        return self.fetchall("SELECT * FROM logs ORDER BY id DESC LIMIT ?", (n,))

    # -------------------------------------------------------------------- ai
    def ai_session(self, user_id: int, new: bool = False) -> int:
        if not new:
            row = self.fetchone("SELECT id FROM ai_sessions WHERE user_id=? AND active=1 ORDER BY id DESC", (user_id,))
            if row:
                return row["id"]
        self.execute("UPDATE ai_sessions SET active=0 WHERE user_id=?", (user_id,))
        return self.execute("INSERT INTO ai_sessions(user_id, created) VALUES(?, ?)", (user_id, utcnow())).lastrowid

    def ai_add_message(self, session_id: int, role: str, content: str | None, tool_calls: Any = None,
                       tool_call_id: str | None = None, name: str | None = None) -> None:
        self.execute("INSERT INTO ai_messages(session_id, role, content, tool_calls, tool_call_id, name, ts) VALUES(?,?,?,?,?,?,?)",
                     (session_id, role, content, json.dumps(tool_calls) if tool_calls else None, tool_call_id, name, utcnow()))

    def ai_messages(self, session_id: int, limit: int = 60) -> list[dict]:
        rows = self.fetchall("SELECT * FROM (SELECT * FROM ai_messages WHERE session_id=? ORDER BY id DESC LIMIT ?) ORDER BY id",
                             (session_id, limit))
        out = []
        for r in rows:
            m: dict[str, Any] = {"role": r["role"], "content": r["content"] if r["content"] is not None else ""}
            if r["tool_calls"]:
                m["tool_calls"] = json.loads(r["tool_calls"])
                if not r["content"]:
                    m["content"] = None  # OpenAI format: assistant tool-call turns carry null content
            if r["tool_call_id"]:
                m["tool_call_id"] = r["tool_call_id"]
            if r["name"]:
                m["name"] = r["name"]
            out.append(m)
        # A tool result must follow its assistant call; trim a dangling head.
        while out and out[0]["role"] == "tool":
            out.pop(0)
        return out

    def ai_search(self, user_id: int, query: str, limit: int = 8) -> list[sqlite3.Row]:
        like = f"%{query}%"
        return self.fetchall(
            "SELECT m.role, m.content, m.ts, m.session_id FROM ai_messages m JOIN ai_sessions s ON s.id=m.session_id "
            "WHERE s.user_id=? AND m.content LIKE ? AND m.role IN ('user','assistant') ORDER BY m.id DESC LIMIT ?",
            (user_id, like, limit))

    def ai_stage_action(self, user_id: int, session_id: int, tool: str, args: dict, reason: str) -> int:
        return self.execute("INSERT INTO ai_pending(user_id, session_id, tool, args, reason, created) VALUES(?,?,?,?,?,?)",
                            (user_id, session_id, tool, json.dumps(args, ensure_ascii=False), reason, utcnow())).lastrowid

    def ai_pending(self, user_id: int | None = None) -> list[sqlite3.Row]:
        if user_id is None:
            return self.fetchall("SELECT * FROM ai_pending WHERE status='pending' ORDER BY id")
        return self.fetchall("SELECT * FROM ai_pending WHERE status='pending' AND user_id=? ORDER BY id", (user_id,))

    def ai_resolve(self, pending_id: int, status: str, result: str = "") -> Optional[sqlite3.Row]:
        row = self.fetchone("SELECT * FROM ai_pending WHERE id=?", (pending_id,))
        if row:
            self.execute("UPDATE ai_pending SET status=?, result=? WHERE id=?", (status, result[:4000], pending_id))
        return row


_db: Database | None = None
_db_lock = threading.Lock()


def get_db(path: Path | str | None = None) -> Database:
    global _db
    with _db_lock:
        if _db is None:
            _db = Database(path or DB_PATH)
        return _db


def reset_db_for_tests(path: Path | str) -> Database:
    global _db
    with _db_lock:
        if _db is not None:
            _db.close()
        _db = Database(path)
        return _db
