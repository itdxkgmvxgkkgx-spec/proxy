"""Tool registry for the Proxy AI (Hermes-style: tools self-register at import).

Each tool = schema (OpenAI function format) + async implementation + a
`danger` classifier. Dangerous calls are *staged* in `ai_pending` and executed
only after the owner/admin presses ✅ in Telegram (see agent.py).

Danger levels
    safe      runs immediately (reads, searches, listing, memory/skills — these notify)
    approve   needs a button press (shell, file writes, DB writes, settings, git, pipeline)
    hardline  never executed (rm -rf /, secrets exfil, fork bombs, deleting data/)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shlex
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable

import aiohttp

from ..core.config import DATA_DIR, DEFAULT_SETTINGS, ROOT, SECRETS
from ..core.database import get_db
from ..core.logger import current_stage
from ..pipeline.mtproto import test_proxy
from ..pipeline.parser import extract_proxies, parse_link
from . import memory as mem
from . import skills as sk

log = logging.getLogger("proxybot.ai.tools")

ToolFn = Callable[..., Awaitable[str]]


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    fn: ToolFn
    danger: Callable[[dict], str]  # returns safe | approve | hardline
    reason: str = ""

    def schema(self) -> dict:
        return {"type": "function", "function": {"name": self.name, "description": self.description, "parameters": self.parameters}}


REGISTRY: dict[str, Tool] = {}


def register(name: str, description: str, parameters: dict, danger="safe", reason: str = ""):
    def deco(fn: ToolFn):
        d = danger if callable(danger) else (lambda a, _lvl=danger: _lvl)
        REGISTRY[name] = Tool(name, description, parameters, fn, d, reason)
        return fn
    return deco


def _p(props: dict, required: list[str] | None = None) -> dict:
    return {"type": "object", "properties": props, "required": required or []}


def _s(desc: str, **kw) -> dict:
    return {"type": "string", "description": desc, **kw}


def _i(desc: str) -> dict:
    return {"type": "integer", "description": desc}


def _j(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


# ------------------------------------------------------------- danger rules
HARDLINE = [
    (r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*r)[a-zA-Z]*\s+(/|~|\$HOME|\.\.|data/?|\*)(\s|$)", "recursive delete of root/home/data"),
    (r":\(\)\s*\{\s*:\|:&\s*\};:", "fork bomb"),
    (r"\bmkfs\b|\bdd\s+if=.*of=/dev/", "disk destroy"),
    (r"(BOT_TOKEN|GH_PAT|TAVILY_API_KEY|ai_api_key)\b.*(curl|wget|nc\b|http)", "secret exfiltration"),
    (r"\b(curl|wget)\b.*\|\s*(ba|z|da)?sh\b", "pipe remote script to shell"),
    (r"\bgit\s+push\s+.*(-f|--force)", "force push"),
    (r"\bgit\s+(reset\s+--hard|clean\s+-fd)", "destructive git"),
    (r"\bDROP\s+TABLE\b|\bDELETE\s+FROM\s+\w+\s*;?\s*$", "destructive SQL"),
    (r"\.ssh/|/etc/(passwd|shadow)|authorized_keys", "system credentials"),
    (r"\bshutdown\b|\breboot\b|\bkill\s+-9\s+-1\b|\bpkill\s+-f\s+python", "kill the bot/host"),
]
_HARD_RE = [(re.compile(p, re.I), d) for p, d in HARDLINE]

SAFE_SHELL = re.compile(
    r"^\s*(ls|cat|head|tail|wc|grep|rg|find|git\s+(status|log|diff|show|branch)|python3?\s+-m\s+pytest|pytest|"
    r"python3?\s+-c\s+['\"]print|pip\s+(list|show|freeze)|du|df|date|uptime|echo|pwd|whoami|env\s*$|printenv\s+PATH|"
    r"sqlite3\s+\S+\s+['\"]?\s*select)\b", re.I)


def classify_shell(cmd: str) -> tuple[str, str]:
    for rx, desc in _HARD_RE:
        if rx.search(cmd):
            return "hardline", desc
    if re.search(r"\b(BOT_TOKEN|GH_PAT|TAVILY_API_KEY)\b", cmd) and re.search(r"\becho\b|\bprintenv\b|\benv\b|\bcat\b", cmd):
        return "hardline", "printing a secret"
    if SAFE_SHELL.match(cmd) and not re.search(r"[;&|>]|\$\(|`", cmd.split("|", 1)[0] if "|" not in cmd else cmd):
        return "safe", "read-only command"
    return "approve", "shell command"


def _secret_leak(text: str) -> str:
    for v in (SECRETS.bot_token, SECRETS.gh_pat, SECRETS.tavily_key, str(get_db().get("ai_api_key", ""))):
        if v and len(v) > 8 and v in text:
            text = text.replace(v, "[REDACTED]")
    return text


def _safe_path(rel: str) -> Path | None:
    try:
        p = (ROOT / rel).resolve()
    except OSError:
        return None
    if not str(p).startswith(str(ROOT.resolve())):
        return None
    if ".git" in p.parts:
        return None
    return p


def _file_danger(args: dict) -> str:
    rel = args.get("path", "")
    p = _safe_path(rel)
    if p is None:
        return "hardline"
    if p == DATA_DIR / "proxybot.db" or rel.endswith((".db", ".db-wal", ".db-shm")):
        return "hardline"
    if rel in (".github/workflows/proxybot.yml",) or rel.startswith(".github/"):
        return "approve"
    return "approve"


# ============================================================ READ TOOLS ===
@register("read_file", "Read a project file (relative to repo root). Returns up to 400 lines from `offset`.",
          _p({"path": _s("relative path e.g. proxybot/pipeline/parser.py"), "offset": _i("1-based start line"), "limit": _i("lines, default 400")}, ["path"]))
async def read_file(path: str, offset: int = 1, limit: int = 400) -> str:
    p = _safe_path(path)
    if p is None or not p.exists():
        return f"error: not found: {path}"
    if p.is_dir():
        return "\n".join(sorted(f"{'d ' if c.is_dir() else '  '}{c.name}" for c in p.iterdir() if c.name != "__pycache__"))
    if p.suffix in (".db", ".db-wal", ".db-shm", ".pyc"):
        return "error: binary file — use db_query for the database"
    lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
    sel = lines[max(0, offset - 1): max(0, offset - 1) + max(1, min(limit, 400))]
    body = "\n".join(f"{i + offset:5d}| {l}" for i, l in enumerate(sel))
    return _secret_leak(f"{path} ({len(lines)} lines)\n{body}")


@register("list_files", "List the project tree (depth-limited).", _p({"path": _s("subdirectory, default '.'"), "depth": _i("default 2")}))
async def list_files(path: str = ".", depth: int = 2) -> str:
    base = _safe_path(path)
    if base is None or not base.is_dir():
        return "error: not a directory"
    out = []
    for p in sorted(base.rglob("*")):
        rel = p.relative_to(base)
        if len(rel.parts) > depth or any(x in rel.parts for x in ("__pycache__", ".git", ".pytest_cache")):
            continue
        out.append(("📁 " if p.is_dir() else "   ") + str(rel) + (f"  ({p.stat().st_size}B)" if p.is_file() else ""))
    return "\n".join(out[:400])


@register("search_files", "Regex search across project text files (like grep -rn).",
          _p({"pattern": _s("regex"), "path": _s("subdir, default '.'"), "glob": _s("filename glob e.g. *.py")}, ["pattern"]))
async def search_files(pattern: str, path: str = ".", glob: str = "*") -> str:
    base = _safe_path(path)
    if base is None:
        return "error: bad path"
    rx = re.compile(pattern)
    hits = []
    for p in base.rglob(glob):
        if not p.is_file() or p.suffix in (".db", ".pyc", ".db-wal", ".db-shm") or ".git" in p.parts or "__pycache__" in p.parts:
            continue
        try:
            for i, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                if rx.search(line):
                    hits.append(f"{p.relative_to(ROOT)}:{i}: {line.strip()[:160]}")
                    if len(hits) >= 200:
                        return _secret_leak("\n".join(hits) + "\n…(truncated)")
        except OSError:
            pass
    return _secret_leak("\n".join(hits) or "no matches")


@register("db_query", "Run a read-only SQL SELECT on data/proxybot.db. Tables: settings, users, admins, sources, proxies, "
          "proxy_history, runs, logs, ai_sessions, ai_messages, ai_pending, kv.", _p({"sql": _s("SELECT … (LIMIT applied, max 200 rows)")}, ["sql"]))
async def db_query(sql: str) -> str:
    s = sql.strip().rstrip(";")
    if not re.match(r"^(select|with|pragma table_info|explain)\b", s, re.I) or re.search(r"\b(insert|update|delete|drop|alter|create|replace|attach)\b", s, re.I):
        return "error: only SELECT allowed here — use db_execute for writes"
    if not re.search(r"\blimit\b", s, re.I):
        s += " LIMIT 200"
    try:
        rows = get_db().fetchall(s)
    except Exception as e:  # noqa: BLE001
        return f"error: {e}"
    out = [dict(r) for r in rows]
    for r in out:
        if "value" in r and r.get("key") == "ai_api_key":
            r["value"] = "[REDACTED]"
    return _secret_leak(_j({"rows": len(out), "data": out}))


@register("get_settings", "Return all runtime settings with descriptions.", _p({}))
async def get_settings() -> str:
    db = get_db()
    out = {k: {"value": ("[set]" if k == "ai_api_key" and db.get(k) else db.get(k)), "desc": DEFAULT_SETTINGS[k][2]} for k in DEFAULT_SETTINGS}
    return _j(out)


@register("bot_status", "Current pipeline stage, proxy counts, last run stats, sources, users, run chain info.", _p({}))
async def bot_status() -> str:
    db = get_db()
    return _j({"stage": current_stage(), "proxies": db.proxy_stats(), "last_run": db.kv_get("last_run_stats"),
               "run_counter": db.kv_get("run_counter", 0), "sources": {"enabled": len(db.sources()), "all": len(db.sources(False))},
               "users": db.user_count(), "admins": len(db.list_admins()), "gh_run": SECRETS.run_id,
               "last_chain": db.kv_get("last_chain"), "pending_approvals": len(db.ai_pending())})


@register("read_logs", "Recent log lines from the bot (what the pipeline is doing / errors).",
          _p({"n": _i("count, default 40"), "level": _s("INFO|WARNING|ERROR, optional")}))
async def read_logs(n: int = 40, level: str | None = None) -> str:
    rows = get_db().recent_logs(min(n, 200), level or None)
    return _secret_leak("\n".join(f"{r['ts']} {r['level']} [{r['stage']}] {r['msg']}" for r in reversed(rows)) or "(empty)")


@register("list_proxies", "Best proxies currently known (alive, scored).", _p({"n": _i("default 10"), "status": _s("alive|flaky|dead|all")}))
async def list_proxies(n: int = 10, status: str = "alive") -> str:
    db = get_db()
    rows = db.best_proxies(min(n, 50)) if status == "alive" else db.proxies_by_status(None if status == "all" else status, min(n, 50))
    return _j([{k: r[k] for k in ("host", "port", "ping_ms", "down_kbps", "up_kbps", "score", "iran_ok", "status", "last_ok", "link")} for r in rows])


@register("test_proxy_link", "Run the real MTProto handshake test on one proxy link (tg://proxy… or t.me/proxy…).",
          _p({"link": _s("proxy link"), "speed": {"type": "boolean", "description": "also measure throughput"}}, ["link"]))
async def test_proxy_link(link: str, speed: bool = False) -> str:
    p = parse_link(link)
    if not p:
        return "error: cannot parse link"
    r = await test_proxy(p, timeout=6, speed=speed, speed_requests=20, speed_timeout=8)
    return _j({"host": p.host, "port": p.port, "type": p.secret_type, **r.__dict__})


@register("probe_source", "Download a URL and count how many MTProto proxies it contains (use before add_source).", _p({"url": _s("http(s) url")}, ["url"]))
async def probe_source(url: str) -> str:
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=20), headers={"User-Agent": "Mozilla/5.0"}) as r:
                text = await r.text(errors="ignore")
                status = r.status
        found = extract_proxies(text)
        return _j({"status": status, "bytes": len(text), "proxies": len(found), "sample": [p.link for p in list(found)[:3]]})
    except Exception as e:  # noqa: BLE001
        return f"error: {e}"


@register("list_sources", "List proxy sources with stats.", _p({"enabled_only": {"type": "boolean"}, "n": _i("default 60")}))
async def list_sources(enabled_only: bool = True, n: int = 60) -> str:
    rows = get_db().sources(enabled_only)
    return _j([{k: r[k] for k in ("id", "url", "kind", "enabled", "added_by", "last_count", "total_found", "fail_count")} for r in rows[:n]])


# ============================================================ WEB TOOLS ===
@register("web_search", "Search the web with Tavily. Use for finding new proxy sources, docs, or fixing bugs.",
          _p({"query": _s("search query"), "max_results": _i("default 8"), "include_raw": {"type": "boolean", "description": "include page text"}}, ["query"]))
async def web_search(query: str, max_results: int = 8, include_raw: bool = False) -> str:
    if not SECRETS.tavily_key:
        return "error: TAVILY_API_KEY secret is not set"
    body = {"api_key": SECRETS.tavily_key, "query": query, "max_results": min(max_results, 15), "search_depth": "advanced",
            "include_raw_content": include_raw, "include_answer": False}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post("https://api.tavily.com/search", json=body, timeout=aiohttp.ClientTimeout(total=40)) as r:
                data = await r.json(content_type=None)
                if r.status != 200:
                    return f"error: tavily {r.status}: {str(data)[:300]}"
        out = [{"title": x.get("title"), "url": x.get("url"), "content": (x.get("raw_content") or x.get("content") or "")[:1500 if include_raw else 400]}
               for x in data.get("results", [])]
        return _j(out)
    except Exception as e:  # noqa: BLE001
        return f"error: {e}"


@register("web_extract", "Fetch a URL and return its readable text (max 12k chars).", _p({"url": _s("http(s) url")}, ["url"]))
async def web_extract(url: str) -> str:
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=25), headers={"User-Agent": "Mozilla/5.0"}) as r:
                text = await r.text(errors="ignore")
        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.S | re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text[:12000]
    except Exception as e:  # noqa: BLE001
        return f"error: {e}"


# ========================================================= MEMORY/SKILLS ===
@register("memory", "Persistent memory across sessions. target='memory' = your notes about the project/environment; "
          "target='user' = facts about the user (name, how to address them, preferences). Actions: add | replace | remove. "
          "Write declarative facts ('User wants to be called داداش'), never instructions.",
          _p({"action": _s("add|replace|remove"), "target": _s("memory|user"), "content": _s("entry text (add/replace)"),
              "old_text": _s("unique substring of the entry to replace/remove")}, ["action", "target"]))
async def memory_tool(action: str, target: str, content: str = "", old_text: str = "") -> str:
    store = mem.MemoryStore(target)
    if action == "add":
        r = store.add(content)
    elif action == "replace":
        r = store.replace(old_text, content)
    elif action == "remove":
        r = store.remove(old_text)
    else:
        return "error: action must be add|replace|remove"
    return _j({"success": r.success, "message": r.message, "usage": r.usage, "current_entries": r.entries if not r.success else None})


@register("skills_list", "List available skills (name + description).", _p({}))
async def skills_list_tool() -> str:
    return _j(sk.skills_list())


@register("skill_view", "Load a skill's full SKILL.md, or one of its reference files.", _p({"name": _s("skill name"), "path": _s("optional reference path")}, ["name"]))
async def skill_view_tool(name: str, path: str | None = None) -> str:
    return sk.skill_view(name, path)


@register("skill_manage", "Create/patch/delete your own skills (procedural memory). Save a skill after a non-trivial workflow.",
          _p({"action": _s("create|patch|delete|write_file|remove_file"), "name": _s("skill name (kebab-case)"), "content": _s("full SKILL.md (create / full rewrite)"),
              "description": _s("one-line description (create)"), "old_string": _s("patch: text to replace"), "new_string": _s("patch: replacement"),
              "file_path": _s("write_file: e.g. references/notes.md"), "file_content": _s("write_file content")}, ["action", "name"]))
async def skill_manage_tool(**kw) -> str:
    return sk.skill_manage(**kw)


@register("session_search", "Search your past conversations with this user (older sessions).", _p({"query": _s("keywords"), "limit": _i("default 8")}, ["query"]))
async def session_search(query: str, limit: int = 8, _user_id: int = 0) -> str:
    rows = get_db().ai_search(_user_id, query, limit)
    return _j([{"ts": r["ts"], "role": r["role"], "session": r["session_id"], "text": (r["content"] or "")[:400]} for r in rows])


# ======================================================== APPROVE TOOLS ===
@register("run_shell", "Run a shell command in the repo root (timeout 120s). Read-only commands run directly; anything else is staged for user approval.",
          _p({"command": _s("bash command"), "timeout": _i("seconds, max 300")}, ["command"]),
          danger=lambda a: classify_shell(a.get("command", ""))[0], reason="shell command")
async def run_shell(command: str, timeout: int = 120) -> str:
    def _go():
        try:
            r = subprocess.run(command, shell=True, cwd=str(ROOT), capture_output=True, text=True, timeout=min(timeout, 300),
                               env={**os.environ, "BOT_TOKEN": "***", "GH_PAT": "***", "TAVILY_API_KEY": "***"})
            out = (r.stdout + ("\n[stderr]\n" + r.stderr if r.stderr else "")).strip()
            return f"exit={r.returncode}\n{out[-6000:]}"
        except subprocess.TimeoutExpired:
            return "error: timeout"
    return _secret_leak(await asyncio.get_running_loop().run_in_executor(None, _go))


@register("write_file", "Create or overwrite a project file (needs approval). Prefer patch_file for edits.",
          _p({"path": _s("relative path"), "content": _s("full content")}, ["path", "content"]), danger=_file_danger, reason="writes a file")
async def write_file(path: str, content: str) -> str:
    p = _safe_path(path)
    if p is None:
        return "error: path outside repo"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"wrote {path} ({len(content)} chars)"


@register("patch_file", "Replace one unique occurrence of old_string with new_string in a file (needs approval).",
          _p({"path": _s("relative path"), "old_string": _s("exact text to find (must be unique)"), "new_string": _s("replacement")},
             ["path", "old_string", "new_string"]), danger=_file_danger, reason="edits a file")
async def patch_file(path: str, old_string: str, new_string: str) -> str:
    p = _safe_path(path)
    if p is None or not p.exists():
        return "error: file not found"
    text = p.read_text(encoding="utf-8")
    n = text.count(old_string)
    if n == 0:
        return "error: old_string not found"
    if n > 1:
        return f"error: old_string occurs {n} times — make it unique"
    p.write_text(text.replace(old_string, new_string, 1), encoding="utf-8")
    return f"patched {path}"


@register("delete_file", "Delete a project file (needs approval; data/ and .github protected).", _p({"path": _s("relative path")}, ["path"]),
          danger=lambda a: "hardline" if a.get("path", "").startswith(("data", ".github", "run.py")) else "approve", reason="deletes a file")
async def delete_file(path: str) -> str:
    p = _safe_path(path)
    if p is None or not p.is_file():
        return "error: not a file"
    p.unlink()
    return f"deleted {path}"


@register("db_execute", "Run a write SQL statement (UPDATE/INSERT/DELETE with WHERE) on the database (needs approval).",
          _p({"sql": _s("SQL statement")}, ["sql"]),
          danger=lambda a: "hardline" if re.search(r"\b(drop|truncate|alter)\b|delete\s+from\s+\w+\s*;?\s*$", a.get("sql", ""), re.I) else "approve",
          reason="modifies the database")
async def db_execute(sql: str) -> str:
    try:
        cur = get_db().execute(sql)
        return f"ok, rows affected: {cur.rowcount}"
    except Exception as e:  # noqa: BLE001
        return f"error: {e}"


@register("set_setting", "Change a runtime setting (needs approval). Keys: see get_settings.", _p({"key": _s("setting key"), "value": _s("new value")}, ["key", "value"]),
          danger="approve", reason="changes a setting")
async def set_setting(key: str, value: str) -> str:
    if key not in DEFAULT_SETTINGS:
        return f"error: unknown key {key}"
    if key == "ai_api_key":
        return "error: the API key can only be changed via /ai_setup"
    try:
        v = get_db().set(key, value)
    except (TypeError, ValueError) as e:
        return f"error: {e}"
    return f"{key} = {v}"


@register("add_source", "Add a proxy source URL to the sources table (needs approval).", _p({"url": _s("url"), "note": _s("why / where found")}, ["url"]),
          danger="approve", reason="adds a proxy source")
async def add_source(url: str, note: str = "") -> str:
    url = url.strip()
    if not url.startswith("http"):
        return "error: must be http(s)"
    kind = "channel" if "t.me/s/" in url else "raw"
    ok = get_db().add_source(url, kind=kind, added_by="ai", note=note[:200])
    return "added" if ok else "already exists"


@register("toggle_source", "Enable/disable or delete a source by id (needs approval).",
          _p({"source_id": _i("id"), "action": _s("enable|disable|delete")}, ["source_id", "action"]), danger="approve", reason="changes sources")
async def toggle_source(source_id: int, action: str) -> str:
    db = get_db()
    if action == "delete":
        db.remove_source(source_id)
    else:
        db.set_source_enabled(source_id, action == "enable")
    return f"source {source_id}: {action}"


@register("run_pipeline", "Start a full proxy scan now (needs approval). Returns immediately; check bot_status for progress.", _p({}),
          danger="approve", reason="starts a scan")
async def run_pipeline() -> str:
    from ..pipeline.runner import get_runner
    runner = get_runner()
    if runner.running:
        return "a scan is already running"
    asyncio.get_running_loop().create_task(runner.run(SECRETS.run_id))
    return "scan started"


@register("git_commit", "git add -A && git commit (needs approval). Push happens automatically with the persister.",
          _p({"message": _s("commit message")}, ["message"]), danger="approve", reason="commits code")
async def git_commit(message: str) -> str:
    def _go():
        subprocess.run(["git", "add", "-A"], cwd=str(ROOT), capture_output=True)
        r = subprocess.run(["git", "commit", "-m", message[:200]], cwd=str(ROOT), capture_output=True, text=True)
        return (r.stdout + r.stderr).strip()[-800:]
    return await asyncio.get_running_loop().run_in_executor(None, _go)


@register("send_message", "Send a Telegram message to the current user right now (e.g. progress during a long task).",
          _p({"text": _s("message text (HTML allowed)")}, ["text"]))
async def send_message(text: str, _notify=None) -> str:
    if _notify:
        await _notify(_secret_leak(text)[:4000])
        return "sent"
    return "no channel"


def schemas() -> list[dict]:
    return [t.schema() for t in REGISTRY.values()]


def tool_names() -> list[str]:
    return list(REGISTRY)
