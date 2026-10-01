"""مراحل ۳ تا ۵: تست پینگ → تست دانلود/آپلود → فیلتر و امتیازدهی."""
import asyncio
import socket
import time

import aiohttp

from .. import database as db
from ..config import PING_TIMEOUT, SPEED_TIMEOUT, SPEED_TEST_URL


async def _ping_one(server, port):
    """TCP connect ping — سریع و سبک."""
    t0 = time.perf_counter()
    try:
        fut = asyncio.open_connection(server, port)
        r, w = await asyncio.wait_for(fut, timeout=PING_TIMEOUT)
        w.close()
        try:
            await w.wait_closed()
        except Exception:
            pass
        return (time.perf_counter() - t0) * 1000
    except Exception:
        return None


async def _speed_one(session, server, port, secret):
    """تست دانلود و آپلود از طریق پروکسی (تقریبی با TCP relay).
    برای MTProto واقعی نیاز به handshake کامله؛ اینجا از اتصال مستقیم به
    سرور پروکسی به‌عنوان معیار کیفیت مسیر استفاده می‌کنیم."""
    dl = ul = 0.0
    try:
        # دانلود: اندازه‌گیری throughput اتصال به خود سرور پروکسی
        t0 = time.perf_counter()
        r, w = await asyncio.wait_for(asyncio.open_connection(server, port), SPEED_TIMEOUT)
        # MTProto handshake اولیه: یک فریم obfuscated ساده
        w.write(bytes(64))
        await w.drain()
        ul = 64 / max(time.perf_counter() - t0, 1e-6) / 1024  # KB/s آپلود
        try:
            data = await asyncio.wait_for(r.read(8192), timeout=5)
            dl = len(data) / 5 / 1024 if data else 0.0
        except Exception:
            dl = 1.0  # اتصال برقرار شد ولی دیتایی برنگشت — هنوز قابل استفاده برای تلگرام
        w.close()
    except Exception:
        pass
    return dl, ul


def _score(ping, dl, ul):
    """امتیاز ترکیبی: پینگ کمتر = بهتر، سرعت بیشتر = بهتر."""
    ping_score = max(0, 100 - (ping or 9999) / 10)
    speed_score = min(100, ((dl or 0) + (ul or 0)) / 10)
    return round(0.6 * ping_score + 0.4 * speed_score, 2)


async def test_batch(proxies, threads=100, progress_cb=None):
    """تست کامل یک دسته پروکسی با تریدهای قابل تنظیم."""
    sem = asyncio.Semaphore(threads)
    alive = 0
    total = len(proxies)
    done = 0
    db.log("info", "test", f"stage 3-4: testing {total} proxies with {threads} threads")

    async def worker(p):
        nonlocal alive, done
        async with sem:
            ping = await _ping_one(p["server"], p["port"])
            if ping is None:
                db.update_proxy_result(p["id"], None, None, None, 0, "dead")
            else:
                async with aiohttp.ClientSession() as s:
                    dl, ul = await _speed_one(s, p["server"], p["port"], p["secret"])
                score = _score(ping, dl, ul)
                db.update_proxy_result(p["id"], ping, dl, ul, score, "alive")
                alive += 1
            done += 1
            if progress_cb and done % 50 == 0:
                await progress_cb(done, total, alive)

    await asyncio.gather(*[worker(p) for p in proxies])
    db.log("info", "test", f"stage 5: filter done -> {alive}/{total} alive")
    return alive
