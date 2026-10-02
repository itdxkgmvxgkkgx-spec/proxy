"""Reachability check *from inside Iran* using check-host.net Iranian nodes.

GitHub runners sit outside Iran, so a proxy that answers here may still be
blocked by Iranian ISPs. check-host.net offers free TCP checks from nodes
physically located in Iran (ir1/ir3/ir5…). We only run this on the top
candidates (cheap, rate-limited) and store the result in `proxies.iran_ok`.

Result: 1 = reachable from >=1 Iranian node, 0 = all Iranian nodes failed,
-1 = unknown (service unavailable).
"""
from __future__ import annotations

import asyncio
import logging

import aiohttp

log = logging.getLogger("proxybot.iran")
API = "https://check-host.net"
IR_NODES = ["ir1.node.check-host.net", "ir3.node.check-host.net", "ir5.node.check-host.net", "ir6.node.check-host.net"]
_HDR = {"Accept": "application/json", "User-Agent": "proxybot/1.0"}


async def check_from_iran(host: str, port: int, session: aiohttp.ClientSession, timeout: float = 25.0) -> int:
    params = [("host", f"{host}:{port}")] + [("node", n) for n in IR_NODES]
    try:
        async with session.get(f"{API}/check-tcp", params=params, headers=_HDR,
                               timeout=aiohttp.ClientTimeout(total=15)) as r:
            if r.status != 200:
                return -1
            data = await r.json(content_type=None)
        rid = data.get("request_id")
        nodes = list((data.get("nodes") or {}).keys())
        if not rid or not nodes:
            return -1
        deadline = asyncio.get_running_loop().time() + timeout
        while asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(3)
            async with session.get(f"{API}/check-result/{rid}", headers=_HDR,
                                   timeout=aiohttp.ClientTimeout(total=15)) as r:
                if r.status != 200:
                    continue
                res = await r.json(content_type=None)
            pending = [n for n in nodes if res.get(n) is None]
            ok_nodes = 0
            for n in nodes:
                v = res.get(n)
                if v and isinstance(v, list) and v and isinstance(v[0], dict) and "time" in v[0] and "error" not in v[0]:
                    ok_nodes += 1
            if ok_nodes:
                return 1
            if not pending:
                return 0
        return -1
    except Exception as e:  # noqa: BLE001
        log.debug("iran check failed for %s:%s: %s", host, port, e)
        return -1


async def check_many(targets: list[tuple[int, str, int]], concurrency: int = 2) -> dict[int, int]:
    """targets = [(proxy_id, host, port)]  ->  {proxy_id: iran_ok}"""
    out: dict[int, int] = {}
    sem = asyncio.Semaphore(concurrency)
    async with aiohttp.ClientSession() as s:
        async def one(pid, host, port):
            async with sem:
                out[pid] = await check_from_iran(host, port, s)
                await asyncio.sleep(1.5)  # be polite: free API
        await asyncio.gather(*(one(*t) for t in targets))
    return out
