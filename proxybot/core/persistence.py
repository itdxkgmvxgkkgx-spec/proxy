"""Persistence & run chaining through GitHub.

* `Persister` commits `data/` (SQLite + memory + skills) to the repo every
  `save_interval_sec` seconds and pushes with GH_PAT.  On a new run the repo
  is checked out fresh so the DB is exactly where the last run left it.
  A safety net also uploads the DB as a workflow artifact (handled in YAML).
* `chain_next_run()` fires `workflow_dispatch` for the same workflow so the
  bot is effectively always on (GitHub caps a job at 6h).
* `cancel_other_runs()` makes sure only one instance polls Telegram
  (two pollers -> TelegramConflictError).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import time
from pathlib import Path

import aiohttp

from .config import DATA_DIR, ROOT, SECRETS
from .database import get_db

log = logging.getLogger("proxybot.persist")
API = "https://api.github.com"


def _gh_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {SECRETS.gh_pat}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "proxybot",
    }


def _run(cmd: list[str], cwd: Path = ROOT, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)


class Persister:
    """Periodically commit + push the data directory."""

    def __init__(self):
        self._lock = asyncio.Lock()
        self.last_save: float = 0.0
        self.saves = 0
        self.enabled = SECRETS.in_actions and bool(SECRETS.gh_pat) and bool(SECRETS.repo)
        if self.enabled:
            self._configure_git()

    def _configure_git(self) -> None:
        _run(["git", "config", "user.name", "proxybot[bot]"])
        _run(["git", "config", "user.email", "proxybot@users.noreply.github.com"])
        remote = f"https://x-access-token:{SECRETS.gh_pat}@github.com/{SECRETS.repo}.git"
        _run(["git", "remote", "set-url", "origin", remote])

    async def save(self, reason: str = "periodic") -> bool:
        """Checkpoint DB, commit data/, push. Returns True if something was pushed."""
        async with self._lock:
            db = get_db()
            db.checkpoint()
            if not self.enabled:
                return False
            return await asyncio.get_running_loop().run_in_executor(None, self._commit_push, reason)

    def _commit_push(self, reason: str) -> bool:
        rel = str(DATA_DIR.relative_to(ROOT))
        try:
            _run(["git", "add", "-A", rel])
            if _run(["git", "diff", "--cached", "--quiet"]).returncode == 0:
                return False  # nothing changed
            msg = f"data: {reason} [skip ci] run={SECRETS.run_id} {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}"
            c = _run(["git", "commit", "-q", "-m", msg])
            if c.returncode != 0:
                log.warning("git commit failed: %s", c.stderr.strip()[:300])
                return False
            for attempt in range(4):
                p = _run(["git", "push", "-q", "origin", "HEAD:main"], timeout=180)
                if p.returncode == 0:
                    self.last_save = time.time()
                    self.saves += 1
                    return True
                log.warning("push failed (attempt %d): %s", attempt + 1, p.stderr.strip()[:300])
                _run(["git", "fetch", "-q", "origin", "main"])
                rb = _run(["git", "rebase", "-X", "theirs", "origin/main"])
                if rb.returncode != 0:
                    # data files conflict: the live DB is authoritative
                    _run(["git", "checkout", "--theirs", "--", rel])
                    _run(["git", "add", "-A", rel])
                    _run(["git", "-c", "core.editor=true", "rebase", "--continue"])
                time.sleep(2 + attempt * 3)
            log.error("giving up push after retries; artifact upload is the fallback")
            return False
        except Exception as e:  # noqa: BLE001
            log.error("persist error: %s", e)
            return False

    async def loop(self, stop: asyncio.Event) -> None:
        db = get_db()
        while not stop.is_set():
            interval = max(10, int(db.get("save_interval_sec", 30)))
            try:
                await asyncio.wait_for(stop.wait(), timeout=interval)
            except asyncio.TimeoutError:
                pass
            try:
                await self.save("periodic")
            except Exception as e:  # noqa: BLE001
                log.error("periodic save failed: %s", e)


# ------------------------------------------------------------------ chaining
async def gh_request(method: str, path: str, session: aiohttp.ClientSession | None = None, **kw):
    own = session is None
    session = session or aiohttp.ClientSession()
    try:
        async with session.request(method, f"{API}{path}", headers=_gh_headers(),
                                   timeout=aiohttp.ClientTimeout(total=30), **kw) as r:
            return r.status, await r.text()
    finally:
        if own:
            await session.close()


async def chain_next_run(reason: str = "handover") -> bool:
    """Dispatch the next workflow run. Idempotent: skips if one is already queued."""
    if not (SECRETS.gh_pat and SECRETS.repo):
        log.info("not in Actions / no GH_PAT - skip chaining")
        return False
    wf = SECRETS.workflow_file
    status, text = await gh_request("GET", f"/repos/{SECRETS.repo}/actions/workflows/{wf}/runs?status=queued&per_page=5")
    if status == 200:
        try:
            if json.loads(text).get("total_count", 0) > 0:
                log.info("a queued run already exists - not dispatching another")
                return True
        except json.JSONDecodeError:
            pass
    status, text = await gh_request(
        "POST", f"/repos/{SECRETS.repo}/actions/workflows/{wf}/dispatches",
        json={"ref": "main", "inputs": {"reason": reason, "parent_run": str(SECRETS.run_id)}})
    ok = status in (201, 204)
    log.info("chain_next_run(%s) -> %s %s", reason, status, "" if ok else text[:200])
    get_db().kv_set("last_chain", {"ts": time.time(), "ok": ok, "reason": reason, "status": status})
    return ok


async def cancel_other_runs() -> int:
    """Cancel in-progress runs of this workflow that are older than us."""
    if not (SECRETS.gh_pat and SECRETS.repo and SECRETS.in_actions):
        return 0
    cancelled = 0
    async with aiohttp.ClientSession() as s:
        status, text = await gh_request(
            "GET", f"/repos/{SECRETS.repo}/actions/workflows/{SECRETS.workflow_file}/runs?status=in_progress&per_page=20", s)
        if status != 200:
            return 0
        for run in json.loads(text).get("workflow_runs", []):
            rid = str(run.get("id"))
            if rid != str(SECRETS.run_id) and int(rid or 0) < int(SECRETS.run_id or 0):
                st, _ = await gh_request("POST", f"/repos/{SECRETS.repo}/actions/runs/{rid}/cancel", s)
                if st == 202:
                    cancelled += 1
                    log.info("cancelled older run %s", rid)
    return cancelled


def run_elapsed_min() -> float:
    started = float(os.getenv("RUN_STARTED_EPOCH", "0") or 0)
    return (time.time() - started) / 60.0 if started else 0.0


def should_hand_over() -> bool:
    return SECRETS.in_actions and run_elapsed_min() >= SECRETS.run_budget_min
