"""دیتابیس لوکال SQLite — همه‌چیز اینجا ذخیره می‌شه و بین ران‌ها هیچی گم نمی‌شه."""
import os
import sqlite3
import threading
from datetime import datetime, timezone

from .config import DB_PATH, DATA_DIR

_lock = threading.Lock()


def _conn():
    os.makedirs(DATA_DIR, exist_ok=True)
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _lock, _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS proxies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server TEXT NOT NULL,
            port INTEGER NOT NULL,
            secret TEXT NOT NULL,
            source TEXT,
            ping_ms REAL,
            dl_kbps REAL,
            ul_kbps REAL,
            score REAL,
            status TEXT DEFAULT 'new',      -- new | alive | dead
            first_seen TEXT,
            last_seen TEXT,
            UNIQUE(server, port, secret)
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY,
            role TEXT DEFAULT 'admin',       -- owner | admin | viewer
            added_at TEXT
        );
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            lang TEXT DEFAULT 'en',
            first_seen TEXT
        );
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT,
            ended_at TEXT,
            proxies_found INTEGER DEFAULT 0,
            alive INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            level TEXT,
            stage TEXT,
            message TEXT
        );
        CREATE TABLE IF NOT EXISTS ai_memory (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS ai_skills (
            name TEXT PRIMARY KEY,
            content TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS ai_config (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        """)


def now():
    return datetime.now(timezone.utc).isoformat()


def execute(query, params=(), fetch=None):
    with _lock, _conn() as c:
        cur = c.execute(query, params)
        if fetch == "one":
            return cur.fetchone()
        if fetch == "all":
            return cur.fetchall()
        return cur.lastrowid


# ---------- settings ----------
def get_setting(key, default=None):
    r = execute("SELECT value FROM settings WHERE key=?", (key,), fetch="one")
    return r["value"] if r else default


def set_setting(key, value):
    execute("INSERT INTO settings(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))


# ---------- proxies ----------
def upsert_proxy(server, port, secret, source):
    execute("""INSERT INTO proxies(server,port,secret,source,first_seen,last_seen)
               VALUES(?,?,?,?,?,?)
               ON CONFLICT(server,port,secret) DO UPDATE SET last_seen=excluded.last_seen""",
            (server, port, secret, source, now(), now()))


def update_proxy_result(pid, ping, dl, ul, score, status):
    execute("""UPDATE proxies SET ping_ms=?, dl_kbps=?, ul_kbps=?, score=?, status=?, last_seen=?
               WHERE id=?""", (ping, dl, ul, score, status, now(), pid))


def get_proxies(status=None, limit=50, order="score DESC"):
    q = "SELECT * FROM proxies"
    if status:
        q += f" WHERE status='{status}'"
    q += f" ORDER BY {order} LIMIT ?"
    return execute(q, (limit,), fetch="all") or []


def count_proxies():
    r = execute("SELECT status, COUNT(*) c FROM proxies GROUP BY status", fetch="all")
    return {x["status"]: x["c"] for x in (r or [])}


# ---------- admins / users ----------
def add_admin(uid, role="admin"):
    execute("INSERT INTO admins(user_id,role,added_at) VALUES(?,?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET role=excluded.role", (uid, role, now()))


def remove_admin(uid):
    execute("DELETE FROM admins WHERE user_id=? AND role!='owner'", (uid,))


def list_admins():
    return execute("SELECT * FROM admins", fetch="all") or []


def is_admin(uid):
    return bool(execute("SELECT 1 FROM admins WHERE user_id=?", (uid,), fetch="one"))


def get_role(uid):
    r = execute("SELECT role FROM admins WHERE user_id=?", (uid,), fetch="one")
    return r["role"] if r else None


def upsert_user(uid, username):
    execute("""INSERT INTO users(user_id,username,first_seen) VALUES(?,?,?)
               ON CONFLICT(user_id) DO UPDATE SET username=excluded.username""",
            (uid, username, now()))


def get_user_lang(uid):
    r = execute("SELECT lang FROM users WHERE user_id=?", (uid,), fetch="one")
    return r["lang"] if r else "en"


def set_user_lang(uid, lang):
    execute("INSERT INTO users(user_id,lang,first_seen) VALUES(?,?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET lang=excluded.lang", (uid, lang, now()))


# ---------- logs ----------
def log(level, stage, message):
    execute("INSERT INTO logs(ts,level,stage,message) VALUES(?,?,?,?)",
            (now(), level, stage, str(message)[:500]))


def get_logs(limit=20):
    return execute("SELECT * FROM logs ORDER BY id DESC LIMIT ?", (limit,), fetch="all") or []


# ---------- AI memory / skills ----------
def memory_set(key, value):
    execute("INSERT INTO ai_memory(key,value,updated_at) VALUES(?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (key, value, now()))


def memory_get(key=None):
    if key:
        r = execute("SELECT value FROM ai_memory WHERE key=?", (key,), fetch="one")
        return r["value"] if r else None
    return execute("SELECT * FROM ai_memory ORDER BY updated_at DESC", fetch="all") or []


def skill_save(name, content):
    execute("INSERT INTO ai_skills(name,content,created_at) VALUES(?,?,?) "
            "ON CONFLICT(name) DO UPDATE SET content=excluded.content", (name, content, now()))


def skill_list():
    return execute("SELECT name, created_at FROM ai_skills", fetch="all") or []


def skill_get(name):
    r = execute("SELECT content FROM ai_skills WHERE name=?", (name,), fetch="one")
    return r["content"] if r else None


def ai_cfg_get(key, default=None):
    r = execute("SELECT value FROM ai_config WHERE key=?", (key,), fetch="one")
    return r["value"] if r else default


def ai_cfg_set(key, value):
    execute("INSERT INTO ai_config(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))
