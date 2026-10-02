"""Scheduler: periodic pipeline runs + periodic AI source discovery + 6h handover."""
from __future__ import annotations

import asyncio
import logging
import time

from aiogram import Bot

from ..core.config import SECRETS
from ..core.database import get_db
from ..core.persistence import chain_next_run, should_hand_over
from ..pipeline.runner import get_runner
from .state import RT

log = logging.getLogger("proxybot.sched")


class Scheduler:
    def __init__(self, bot: Bot, stop: asyncio.Event):
        self.bot = bot
        self.stop = stop
        self.db = get_db()
        self.next_run: float = time.time() + 20  # first scan shortly after boot
        self._wake = asyncio.Event()

    def reschedule(self) -> None:
        interval = max(1, int(self.db.get("scan_interval_min", 15)))
        self.next_run = time.time() + interval * 60
        self._wake.set()

    async def _notify_owner(self, text: str) -> None:
        for a in self.db.list_admins():
            if a["is_owner"]:
                try:
                    await self.bot.send_message(a["user_id"], text, disable_web_page_preview=True)
                except Exception:  # noqa: BLE001
                    pass

    async def loop(self) -> None:
        runner = get_runner()
        while not self.stop.is_set():
            # handover check (GitHub 6h cap)
            if should_hand_over():
                log.info("run budget reached — handing over")
                await self._notify_owner("♻️ Run budget reached — handing over to a fresh GitHub run.")
                self.stop.set()
                break
            delay = max(1.0, self.next_run - time.time())
            self._wake.clear()
            try:
                await asyncio.wait_for(asyncio.wait([asyncio.ensure_future(self.stop.wait()), asyncio.ensure_future(self._wake.wait())],
                                                    return_when=asyncio.FIRST_COMPLETED), timeout=min(delay, 30))
            except asyncio.TimeoutError:
                pass
            if self.stop.is_set():
                break
            if time.time() < self.next_run or not int(self.db.get("auto_scan", 1)):
                if not int(self.db.get("auto_scan", 1)):
                    self.next_run = time.time() + 30
                continue
            if runner.running:
                self.next_run = time.time() + 60
                continue
            try:
                await runner.run(SECRETS.run_id)
            except Exception as e:  # noqa: BLE001
                log.error("scheduled run failed: %s", e)
            self.next_run = time.time() + max(1, int(self.db.get("scan_interval_min", 15))) * 60
            await self._maybe_discover()

    async def _maybe_discover(self) -> None:
        db = self.db
        if not int(db.get("ai_auto_discover", 1)):
            return
        every = max(1, int(db.get("ai_discover_every", 6)))
        counter = int(db.kv_get("run_counter", 0))
        if counter % every != 0:
            return
        try:
            from ..ai.agent import is_configured
            from .ai_handlers import run_discovery
            if not is_configured() or not SECRETS.tavily_key:
                return
            owner = next((a for a in db.list_admins() if a["is_owner"]), None)
            if not owner:
                return
            lang = db.user_lang(owner["user_id"])
            log.info("running periodic AI source discovery")
            await run_discovery(self.bot, owner["user_id"], owner["user_id"], lang)
        except Exception as e:  # noqa: BLE001
            log.error("discovery failed: %s", e)


async def handover(bot: Bot) -> None:
    """Called at shutdown when the run budget is exhausted: save & chain."""
    if RT.persister:
        await RT.persister.save("handover")
    if SECRETS.in_actions:
        ok = await chain_next_run("handover")
        log.info("handover dispatch: %s", ok)
