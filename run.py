#!/usr/bin/env python3
"""ProxyBot entry point.

    python run.py            # start the bot (polling) + scheduler + persister
    python run.py --scan     # one pipeline run, then exit (CI smoke test)
    python run.py --check    # validate config and exit

Lifecycle inside GitHub Actions:
    boot → cancel older runs → seed sources/skills → start polling
         → every save_interval_sec commit+push data/
         → at RUN_BUDGET_MIN (default 330) stop, save, workflow_dispatch next run
"""
from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from proxybot.core.config import SECRETS  # noqa: E402
from proxybot.core.database import get_db  # noqa: E402
from proxybot.core.logger import setup_logging  # noqa: E402

log = setup_logging()


async def main() -> int:
    from aiogram import Bot, Dispatcher
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode
    from aiogram.exceptions import TelegramConflictError

    from proxybot.ai.skills import seed_bundled
    from proxybot.bot import ai_handlers, handlers
    from proxybot.bot.keyboards import bot_commands
    from proxybot.bot.scheduler import Scheduler, handover
    from proxybot.bot.state import RT
    from proxybot.core.persistence import Persister, cancel_other_runs, chain_next_run
    from proxybot.pipeline.runner import get_runner, seed_sources

    problems = SECRETS.validate()
    if problems:
        for p in problems:
            log.error("CONFIG: %s", p)
        if "BOT_TOKEN missing" in problems or "ADMIN_ID missing (first owner)" in problems:
            return 2

    db = get_db()
    db.ensure_owner(SECRETS.admin_id)
    log.info("seeded %d sources, %d skills", seed_sources(db), seed_bundled())
    db.kv_set("boot", {"ts": time.time(), "gh_run": SECRETS.run_id})
    db.log("INFO", f"boot gh_run={SECRETS.run_id}", "boot")

    cancelled = await cancel_other_runs()
    if cancelled:
        log.info("cancelled %d older runs", cancelled)
        await asyncio.sleep(8)  # let the old poller release the token

    stop = asyncio.Event()
    bot = Bot(SECRETS.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(handlers.router)
    dp.include_router(ai_handlers.router)

    RT.persister = Persister()
    RT.scheduler = Scheduler(bot, stop)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            pass

    try:
        await bot.set_my_commands(bot_commands())
        me = await bot.get_me()
        log.info("bot @%s online", me.username)
    except Exception as e:  # noqa: BLE001
        log.error("Telegram unreachable: %s", e)
        return 3

    tasks = [
        asyncio.create_task(RT.persister.loop(stop), name="persister"),
        asyncio.create_task(RT.scheduler.loop(), name="scheduler"),
    ]

    async def poll():
        backoff = 5
        while not stop.is_set():
            try:
                await dp.start_polling(bot, handle_signals=False, allowed_updates=["message", "callback_query"],
                                       polling_timeout=20, close_bot_session=False)
                break  # start_polling returned → stop requested
            except TelegramConflictError:
                log.warning("another poller is active — retrying in %ss", backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)
            except Exception as e:  # noqa: BLE001
                log.error("polling crashed: %s — restarting", e)
                await asyncio.sleep(5)

    poll_task = asyncio.create_task(poll(), name="polling")

    await stop.wait()
    log.info("stopping…")
    try:
        await dp.stop_polling()
    except Exception:  # noqa: BLE001
        pass
    for tsk in tasks + [poll_task]:
        tsk.cancel()
    await asyncio.gather(*tasks, poll_task, return_exceptions=True)
    db.log("INFO", "shutdown / handover", "boot")
    await handover(bot)
    await bot.session.close()
    db.close()
    return 0


async def one_scan() -> int:
    from proxybot.pipeline.runner import get_runner, seed_sources
    db = get_db()
    seed_sources(db)
    st = await get_runner().run(SECRETS.run_id)
    print(st.as_dict())
    db.close()
    return 0 if not st.errors else 1


if __name__ == "__main__":
    if "--check" in sys.argv:
        probs = SECRETS.validate()
        print("OK" if not probs else "\n".join(probs))
        sys.exit(0 if not probs else 1)
    if "--scan" in sys.argv:
        sys.exit(asyncio.run(one_scan()))
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        sys.exit(0)
