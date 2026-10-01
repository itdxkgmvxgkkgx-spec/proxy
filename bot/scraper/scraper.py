"""مرحله ۱ و ۲: جمع‌آوری پروکسی از همه منابع + حذف تکراری."""
import asyncio
import json
import re

import aiohttp

from .. import database as db
from .sources import BUILTIN_SOURCES

# الگوهای استخراج MTProto
TG_LINK = re.compile(r"tg://proxy\?server=([\w.\-]+)&port=(\d+)&secret=([\w]+)")
RAW_LINE = re.compile(r"\b([\w.\-]{3,}):(\d{2,5}):([0-9a-fA-F]{16,})\b")
JSON_SRC = re.compile(r"proxy", re.I)


def _extract(text, source):
    found = []
    for server, port, secret in TG_LINK.findall(text or ""):
        found.append((server, int(port), secret, source))
    for server, port, secret in RAW_LINE.findall(text or ""):
        found.append((server, int(port), secret, source))
    # تلاش برای JSON
    try:
        data = json.loads(text)
        items = data if isinstance(data, list) else data.get("proxies", [])
        for it in items:
            if isinstance(it, dict) and "server" in it:
                found.append((it["server"], int(it.get("port", 443)),
                              it.get("secret", ""), source))
    except Exception:
        pass
    return found


async def _fetch(session, url):
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as r:
            if r.status == 200:
                return url, await r.text()
    except Exception as e:
        db.log("warn", "scrape", f"source failed {url}: {e}")
    return url, ""


async def scrape_all(extra_sources=None):
    """همه منابع رو همزمان می‌گیره، استخراج و dedupe می‌کنه."""
    sources = list(dict.fromkeys(BUILTIN_SOURCES + (extra_sources or [])))
    db.log("info", "scrape", f"stage 1: scraping {len(sources)} sources")
    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as s:
        results = await asyncio.gather(*[_fetch(s, u) for u in sources])

    seen, total = set(), 0
    for url, text in results:
        for server, port, secret in _extract(text, url):
            key = (server, port, secret)
            if key in seen or not secret:
                continue
            seen.add(key)
            db.upsert_proxy(server, port, secret, url)
            total += 1
    db.log("info", "scrape", f"stage 2: deduped -> {total} unique proxies")
    return total
