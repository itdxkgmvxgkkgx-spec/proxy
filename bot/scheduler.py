"""حلقه اصلی: اسکن خودکار هر N دقیقه + تست + ذخیره مداوم (commit دیتابیس به ریپو)."""
import asyncio
import subprocess
import time

from . import database as db
from .config import DEFAULT_SCAN_INTERVAL_MIN, DEFAULT_THREADS
from .scraper.scraper import scrape_all
from .tester.tester import test_batch

import json


async def full_scan(progress_cb=None):
    extra = json.loads(db.get_setting("extra_sources", "[]"))
    new = await scrape_all(extra)
    untested = db.get_proxies(status="new", limit=5000, order="id ASC")
    threads = int(db.get_setting("threads", DEFAULT_THREADS))
    alive = await test_batch(untested, threads=threads, progress_cb=progress_cb)
    counts = db.count_proxies()
    db.execute("INSERT INTO runs(started_at,ended_at,proxies_found,alive) VALUES(?,?,?,?)",
               (db.now(), db.now(), new, alive))
    return new, counts.get("alive", 0), counts.get("dead", 0)


def commit_data():
    """ذخیره ثانیه‌ای/دوره‌ای دیتابیس داخل ریپو تا بین ران‌ها چیزی گم نشه."""
    try:
        subprocess.run(["git", "config", "user.name", "proxy-bot[bot]"], check=False)
        subprocess.run(["git", "config", "user.email",
                        "proxy-bot[bot]@users.noreply.github.com"], check=False)
        subprocess.run(["git", "add", "data/"], check=False)
        r = subprocess.run(["git", "diff", "--cached", "--quiet"], check=False)
        if r.returncode != 0:
            subprocess.run(["git", "commit", "-m", f"💾 autosave {int(time.time())}"],
                           check=False)
            subprocess.run(["git", "push"], check=False)
            db.log("info", "persist", "database committed to repo")
    except Exception as e:
        db.log("error", "persist", f"commit failed: {e}")


async def autosave_loop():
    while True:
        await asyncio.sleep(60)  # هر ۶۰ ثانیه کامیت (commit در هر ثانیه I/O سنگینه؛ DB خودش real-time ذخیره می‌کنه)
        commit_data()


async def scheduler_loop(progress_cb=None):
    while True:
        try:
            await full_scan(progress_cb)
            commit_data()
        except Exception as e:
            db.log("error", "scheduler", str(e))
        interval = int(db.get_setting("scan_interval", DEFAULT_SCAN_INTERVAL_MIN))
        await asyncio.sleep(interval * 60)
