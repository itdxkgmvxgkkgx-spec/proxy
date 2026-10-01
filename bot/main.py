"""نقطه شروع اصلی — همه‌چیز از اینجا بالا میاد."""
import asyncio
import signal

from telegram import BotCommand
from telegram.ext import Application

from . import database as db
from .config import TELEGRAM_BOT_TOKEN, INITIAL_ADMIN_ID, RUN_ID
from .scheduler import scheduler_loop, autosave_loop, commit_data
from .telegram_bot.handlers import register


async def post_init(app: Application):
    await app.bot.set_my_commands([
        BotCommand("start", "🏠 Main menu"),
        BotCommand("list", "📋 Best proxies"),
        BotCommand("log", "📜 Live log"),
        BotCommand("menu", "🎛 Control panel"),
    ])


async def main():
    db.init_db()
    if INITIAL_ADMIN_ID:
        db.add_admin(INITIAL_ADMIN_ID, "owner")
    db.log("info", "boot", f"run {RUN_ID} started")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    register(app)

    async with app:
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)  # سریع‌ترین حالت
        tasks = [
            asyncio.create_task(scheduler_loop()),
            asyncio.create_task(autosave_loop()),
        ]
        stop = asyncio.Event()
        try:
            await stop.wait()
        finally:
            commit_data()
            for tsk in tasks:
                tsk.cancel()
            await app.updater.stop()
            await app.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        commit_data()
