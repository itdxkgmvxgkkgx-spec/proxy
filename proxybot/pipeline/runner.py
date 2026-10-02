"""The 5-stage proxy pipeline.

    1. collect   fetch every enabled source concurrently, parse proxies
    2. dedupe    (host, port, secret) unique; also drop proxies already dead 3x
    3. ping      full MTProto handshake with `threads` concurrency
    4. speed     throughput probe on alive proxies with `speed_threads`
    5. filter    score = f(ping, down, up, stability, iran_ok); keep top_n

`PipelineRunner.run()` is safe to call from the scheduler or from the bot
(/scan). A `asyncio.Lock` makes sure two runs never overlap. Progress is
published via `logger.set_stage()` so the /log menu can show it live, and
everything is written to SQLite immediately (nothing is kept only in RAM).
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field

import aiohttp

from ..core.database import Database, get_db
from ..core.logger import set_stage
from . import iran_check
from .mtproto import test_proxy
from .parser import Proxy, extract_proxies
from .sources import builtin_sources, discover_github_sources

log = logging.getLogger("proxybot.pipeline")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"


@dataclass
class RunStats:
    run_id: int = 0
    started: float = field(default_factory=time.time)
    sources_ok: int = 0
    sources_failed: int = 0
    found: int = 0
    uniq: int = 0
    alive: int = 0
    speed_tested: int = 0
    listed: int = 0
    iran_checked: int = 0
    stage: str = "idle"
    errors: list[str] = field(default_factory=list)

    @property
    def elapsed(self) -> float:
        return time.time() - self.started

    def as_dict(self) -> dict:
        return {k: getattr(self, k) for k in ("run_id", "sources_ok", "sources_failed", "found", "uniq", "alive",
                                               "speed_tested", "listed", "iran_checked", "stage")} | {"elapsed_s": round(self.elapsed, 1)}


def seed_sources(db: Database) -> int:
    added = 0
    for url, kind in builtin_sources():
        if db.add_source(url, kind=kind, added_by="builtin"):
            added += 1
    return added


def compute_score(ping_ms: int | None, down: float | None, up: float | None, fails: int, iran_ok: int,
                  history_ok_ratio: float = 1.0) -> float:
    """0..100 composite. Lower ping & higher throughput & stability = better."""
    if ping_ms is None:
        return 0.0
    ping_score = max(0.0, 1.0 - min(ping_ms, 3000) / 3000.0) * 45  # 45 pts
    down = down or 0.0
    up = up or 0.0
    speed_score = min(1.0, (down + up) / 6.0) * 30                  # 30 pts  (handshake-probe cap ~6 KB/s)
    stab_score = history_ok_ratio * 15                              # 15 pts
    iran_score = {1: 10, -1: 5, 0: -40}.get(iran_ok, 5)             # 10 pts, heavy penalty when blocked
    score = ping_score + speed_score + stab_score + iran_score - fails * 5
    return round(max(0.0, min(100.0, score)), 2)


class PipelineRunner:
    def __init__(self, db: Database | None = None):
        self.db = db or get_db()
        self.lock = asyncio.Lock()
        self.stats = RunStats()
        self.last_stats: RunStats | None = None
        self.on_progress = None  # optional async callback(stats)

    # ---------------------------------------------------------------- utils
    @property
    def running(self) -> bool:
        return self.lock.locked()

    def _stage(self, stage: str, detail: str = "", progress: str = "") -> None:
        self.stats.stage = stage
        set_stage(stage, detail, progress)
        if self.stats.run_id:
            self.db.update_run(self.stats.run_id, stage=stage)
        log.info("[%s] %s %s", stage, detail, progress)

    # -------------------------------------------------------------- stage 1
    async def _fetch(self, session: aiohttp.ClientSession, src, timeout: float) -> tuple[int, set[Proxy], bool]:
        try:
            async with session.get(src["url"], headers={"User-Agent": UA}, timeout=aiohttp.ClientTimeout(total=timeout),
                                   allow_redirects=True) as r:
                if r.status >= 400:
                    return src["id"], set(), False
                text = await r.text(errors="ignore")
            found = extract_proxies(text)
            if src["kind"] == "channel":
                # also pick proxies hidden in <a href="tg://proxy?..."> of the preview
                for m in re.finditer(r'href="([^"]+)"', text):
                    found |= extract_proxies(m.group(1))
            return src["id"], found, True
        except Exception as e:  # noqa: BLE001
            log.debug("source %s failed: %s", src["url"], e)
            return src["id"], set(), False

    async def _github_discovery(self) -> int:
        """Every N runs, grow the source list from GitHub search (free, no AI needed)."""
        every = int(self.db.get("github_discover_every", 4))
        if every <= 0 or int(self.db.kv_get("run_counter", 0)) % every != 0:
            return 0
        self._stage("collect", "github discovery")
        added = 0
        try:
            async with aiohttp.ClientSession() as session:
                async def probe(url: str) -> int:
                    async with session.get(url, headers={"User-Agent": UA}, timeout=aiohttp.ClientTimeout(total=15)) as r:
                        if r.status != 200:
                            return 0
                        return len(extract_proxies(await r.text(errors="ignore")))
                for url in await discover_github_sources(session, probe):
                    if self.db.add_source(url, kind="raw", added_by="github", note="github search"):
                        added += 1
        except Exception as e:  # noqa: BLE001
            log.warning("github discovery failed: %s", e)
        if added:
            log.info("github discovery added %d sources", added)
        return added

    async def collect(self) -> dict[Proxy, int]:
        await self._github_discovery()
        self._stage("collect", "fetching sources")
        sources = self.db.sources(enabled_only=True)
        timeout = float(self.db.get("source_timeout", 20))
        result: dict[Proxy, int] = {}
        conn = aiohttp.TCPConnector(limit=40, ssl=False)
        async with aiohttp.ClientSession(connector=conn) as session:
            tasks = [self._fetch(session, s, timeout) for s in sources]
            done = 0
            for coro in asyncio.as_completed(tasks):
                sid, found, ok = await coro
                done += 1
                self.db.source_result(sid, len(found), ok)
                if ok:
                    self.stats.sources_ok += 1
                else:
                    self.stats.sources_failed += 1
                for p in found:
                    result.setdefault(p, sid)
                self.stats.found = sum(1 for _ in result)
                if done % 10 == 0:
                    self._stage("collect", f"{done}/{len(sources)} sources", f"{len(result)} proxies")
        # auto-disable sources that keep failing
        for s in self.db.sources(enabled_only=True):
            if s["fail_count"] >= 10 and s["added_by"] != "manual":
                self.db.set_source_enabled(s["id"], False)
                log.info("disabled dead source %s", s["url"])
        self.stats.found = len(result)
        return result

    # -------------------------------------------------------------- stage 2
    def dedupe(self, found: dict[Proxy, int]) -> list[tuple[int, Proxy]]:
        self._stage("dedupe", f"{len(found)} raw")
        seen: set[tuple] = set()
        out: list[tuple[int, Proxy]] = []
        for p, sid in found.items():
            if p.key() in seen:
                continue
            seen.add(p.key())
            pid = self.db.upsert_proxy(p.host, p.port, p.secret, p.link, sid, p.secret_type)
            out.append((pid, p))
        # re-test previously alive proxies too, even if no source lists them any more
        known = {k for k in seen}
        for row in self.db.fetchall("SELECT id, host, port, secret FROM proxies WHERE status IN ('alive','flaky','new') "
                                    "ORDER BY score DESC LIMIT 2000"):
            p = Proxy(row["host"], row["port"], row["secret"])
            if p.key() not in known:
                known.add(p.key())
                out.append((row["id"], p))
        self.stats.uniq = len(out)
        self.db.update_run(self.stats.run_id, found=self.stats.found, uniq=self.stats.uniq)
        return out

    # -------------------------------------------------------------- stage 3
    async def ping_stage(self, items: list[tuple[int, Proxy]]) -> list[tuple[int, Proxy, int]]:
        threads = max(1, int(self.db.get("threads", 64)))
        timeout = float(self.db.get("ping_timeout", 4.0))
        self._stage("ping", f"{len(items)} proxies, {threads} threads")
        sem = asyncio.Semaphore(threads)
        alive: list[tuple[int, Proxy, int]] = []
        done = 0

        async def one(pid: int, p: Proxy):
            nonlocal done
            async with sem:
                res = await test_proxy(p, timeout=timeout)
            done += 1
            if res.ok:
                alive.append((pid, p, res.ping_ms or 0))
                self.db.record_test(pid, True, res.ping_ms, None, None, self.stats.run_id)
            else:
                self.db.record_test(pid, False, None, None, None, self.stats.run_id)
            if done % 50 == 0:
                self.stats.alive = len(alive)
                self._stage("ping", f"{done}/{len(items)}", f"{len(alive)} alive")
                if self.on_progress:
                    await self.on_progress(self.stats)

        await asyncio.gather(*(one(pid, p) for pid, p in items))
        self.stats.alive = len(alive)
        self.db.update_run(self.stats.run_id, alive=len(alive))
        alive.sort(key=lambda t: t[2])
        return alive

    # -------------------------------------------------------------- stage 4
    async def speed_stage(self, alive: list[tuple[int, Proxy, int]]) -> None:
        threads = max(1, int(self.db.get("speed_threads", 12)))
        timeout = float(self.db.get("speed_timeout", 8.0))
        nbytes = int(self.db.get("speed_bytes", 65536))
        n_req = max(8, min(200, nbytes // 40))
        # speed-test the best 3*top_n by ping (others would never be listed anyway)
        candidates = alive[: max(30, int(self.db.get("top_n", 30)) * 3)]
        self._stage("speed", f"{len(candidates)} proxies, {threads} threads")
        sem = asyncio.Semaphore(threads)
        done = 0

        async def one(pid: int, p: Proxy):
            nonlocal done
            async with sem:
                res = await test_proxy(p, timeout=timeout, speed=True, speed_requests=n_req, speed_timeout=timeout)
            done += 1
            if res.ok:
                self.db.record_test(pid, True, res.ping_ms, res.down_kbps, res.up_kbps, self.stats.run_id)
                self.stats.speed_tested += 1
            if done % 10 == 0:
                self._stage("speed", f"{done}/{len(candidates)}")

        await asyncio.gather(*(one(pid, p) for pid, p, _ in candidates))
        self.db.update_run(self.stats.run_id, speed_tested=self.stats.speed_tested)

    # -------------------------------------------------------------- stage 5
    async def filter_stage(self) -> list:
        self._stage("filter", "scoring")
        max_ping = int(self.db.get("max_ping_ms", 1500))
        top_n = int(self.db.get("top_n", 30))
        min_score = float(self.db.get("min_score", 20))
        rows = self.db.fetchall("SELECT * FROM proxies WHERE status='alive'")
        for r in rows:
            hist = self.db.fetchone("SELECT AVG(ok) ratio FROM (SELECT ok FROM proxy_history WHERE proxy_id=? ORDER BY id DESC LIMIT 10)",
                                    (r["id"],))
            ratio = float(hist["ratio"] or 1.0) if hist else 1.0
            score = compute_score(r["ping_ms"], r["down_kbps"], r["up_kbps"], r["fails"], r["iran_ok"], ratio)
            if r["ping_ms"] is not None and r["ping_ms"] > max_ping:
                score = min(score, min_score - 1)
            self.db.set_score(r["id"], score)
        # Iran reachability for the top candidates (cheap, rate-limited)
        if int(self.db.get("iran_check", 1)):
            top = self.db.best_proxies(min(top_n, 15), min_score)
            targets = [(r["id"], r["host"], r["port"]) for r in top if r["iran_ok"] == -1]
            if targets:
                self._stage("filter", f"iran check {len(targets)}")
                res = await iran_check.check_many(targets)
                for pid, ok in res.items():
                    self.db.execute("UPDATE proxies SET iran_ok=? WHERE id=?", (ok, pid))
                    row = self.db.fetchone("SELECT * FROM proxies WHERE id=?", (pid,))
                    self.db.set_score(pid, compute_score(row["ping_ms"], row["down_kbps"], row["up_kbps"], row["fails"], ok))
                self.stats.iran_checked = len(res)
        best = self.db.best_proxies(top_n, min_score)
        self.stats.listed = len(best)
        self.db.update_run(self.stats.run_id, listed=len(best))
        return best

    # ------------------------------------------------------------------ run
    async def run(self, gh_run_id: str = "local") -> RunStats:
        if self.lock.locked():
            raise RuntimeError("pipeline already running")
        async with self.lock:
            self.stats = RunStats()
            self.stats.run_id = self.db.start_run(gh_run_id)
            try:
                found = await self.collect()
                items = self.dedupe(found)
                alive = await self.ping_stage(items)
                await self.speed_stage(alive)
                await self.filter_stage()
                self.db.purge_old(int(self.db.get("retention_days", 30)))
                self.db.finish_run(self.stats.run_id, f"ok found={self.stats.found} alive={self.stats.alive} listed={self.stats.listed}")
                self._stage("idle", f"done in {self.stats.elapsed:.0f}s", f"{self.stats.listed} listed")
            except Exception as e:  # noqa: BLE001
                log.exception("pipeline failed")
                self.stats.errors.append(str(e))
                self.db.finish_run(self.stats.run_id, f"error: {e}")
                self._stage("idle", f"failed: {e}")
            self.db.kv_set("last_run_stats", self.stats.as_dict())
            self.db.kv_set("run_counter", int(self.db.kv_get("run_counter", 0)) + 1)
            self.last_stats = self.stats
            return self.stats


_runner: PipelineRunner | None = None


def get_runner() -> PipelineRunner:
    global _runner
    if _runner is None:
        _runner = PipelineRunner()
    return _runner
