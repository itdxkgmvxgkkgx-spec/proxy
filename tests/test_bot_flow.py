"""End-to-end handler test with aiogram's dispatcher and a mocked Bot session."""
import json

import pytest
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.base import BaseSession
from aiogram.enums import ParseMode
from aiogram.methods import TelegramMethod
from aiogram.types import CallbackQuery, Chat, Message, Update, User


class FakeSession(BaseSession):
    """Records every API call; returns a plausible result."""

    def __init__(self):
        super().__init__()
        self.calls: list[tuple[str, dict]] = []
        self._mid = 100

    async def close(self):
        pass

    async def make_request(self, bot, method: TelegramMethod, timeout=None):
        name = type(method).__name__
        data = method.model_dump(exclude_none=True)
        self.calls.append((name, data))
        if name in ("SendMessage", "EditMessageText", "SendDocument"):
            self._mid += 1
            return Message(message_id=self._mid, date=0, chat=Chat(id=data.get("chat_id", 1), type="private"),
                           text=data.get("text", "x"))
        if name == "GetMe":
            return User(id=42, is_bot=True, first_name="bot", username="proxybot")
        return True

    async def stream_content(self, *a, **k):  # pragma: no cover
        yield b""

    def texts(self):
        return [d.get("text", "") for n, d in self.calls if n in ("SendMessage", "EditMessageText")]


_DP = None


def _dispatcher():
    global _DP
    if _DP is None:
        from proxybot.bot import ai_handlers, handlers
        _DP = Dispatcher()
        _DP.include_router(handlers.router)
        _DP.include_router(ai_handlers.router)
    return _DP


@pytest.fixture()
async def tg(db):
    from proxybot.bot.state import RT
    RT.pending_input.clear()
    RT.ai_busy.clear()
    session = FakeSession()
    bot = Bot("123:TEST", session=session, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    return bot, _dispatcher(), session


def user(uid=1000):
    return User(id=uid, is_bot=False, first_name="Ali", username="ali", language_code="fa")


def msg(text, uid=1000, mid=1):
    return Update(update_id=mid, message=Message(message_id=mid, date=0, chat=Chat(id=uid, type="private"), from_user=user(uid), text=text))


def cb(data, uid=1000, mid=2):
    m = Message(message_id=50, date=0, chat=Chat(id=uid, type="private"), from_user=User(id=42, is_bot=True, first_name="bot"), text="menu")
    return Update(update_id=mid, callback_query=CallbackQuery(id="1", from_user=user(uid), chat_instance="x", data=data, message=m))


@pytest.mark.asyncio
async def test_start_language_and_menu(tg, db):
    bot, dp, s = tg
    await dp.feed_update(bot, msg("/start"))
    assert any("ProxyBot" in t for t in s.texts())  # language picker on first start
    await dp.feed_update(bot, cb("lang:fa"))
    assert db.user_lang(1000) == "fa"
    assert any("منوی اصلی" in t for t in s.texts())


@pytest.mark.asyncio
async def test_private_mode_blocks_strangers_and_public_allows(tg, db):
    bot, dp, s = tg
    await dp.feed_update(bot, msg("/proxies", uid=5555))
    assert any("private" in t for t in s.texts())
    db.set("public_mode", 1)
    s.calls.clear()
    await dp.feed_update(bot, msg("/proxies", uid=5555))
    assert any("Proxies" in t for t in s.texts())
    # admin-only still blocked for strangers
    s.calls.clear()
    await dp.feed_update(bot, msg("/settings", uid=5555))
    assert any("Admins only" in t for t in s.texts())


@pytest.mark.asyncio
async def test_settings_flow(tg, db):
    bot, dp, s = tg
    await dp.feed_update(bot, cb("se:threads"))
    assert any("threads" in t for t in s.texts())
    await dp.feed_update(bot, msg("abc", mid=3))
    assert any("Invalid value" in t for t in s.texts())
    await dp.feed_update(bot, msg("200", mid=4))
    assert db.get("threads") == 200
    await dp.feed_update(bot, cb("st:auto_scan"))
    assert db.get("auto_scan") == 0


@pytest.mark.asyncio
async def test_admin_add_with_perms(tg, db):
    bot, dp, s = tg
    await dp.feed_update(bot, cb("ad:add"))
    await dp.feed_update(bot, msg("7777", mid=3))
    await dp.feed_update(bot, msg("scan logs", mid=4))
    assert db.has_perm(7777, "scan") and not db.has_perm(7777, "ai")
    # new admin can scan-menu but not AI
    s.calls.clear()
    await dp.feed_update(bot, msg("/ai", uid=7777))
    assert any("Admins only" in t for t in s.texts())


@pytest.mark.asyncio
async def test_proxy_delivery_modes(tg, db):
    bot, dp, s = tg
    for i in range(3):
        pid = db.upsert_proxy(f"1.1.1.{i}", 443, "aa" * 16, f"https://t.me/proxy?server=1.1.1.{i}&port=443&secret={'aa' * 16}", None, "plain")
        db.record_test(pid, True, 100 + i, 2.0, 0.8, 1)
        db.set_score(pid, 80 - i)
    await dp.feed_update(bot, cb("px:list"))
    assert any("1.1.1.0" in t for t in s.texts())
    s.calls.clear()
    await dp.feed_update(bot, cb("px:single"))
    assert sum(1 for n, _ in s.calls if n == "SendMessage") >= 3
    s.calls.clear()
    await dp.feed_update(bot, cb("px:file"))
    assert sum(1 for n, _ in s.calls if n == "SendDocument") == 2


@pytest.mark.asyncio
async def test_explain_log_history(tg, db):
    bot, dp, s = tg
    await dp.feed_update(bot, msg("/explain"))
    assert any("5 stages" in t or "Pipeline" in t for t in s.texts())
    await dp.feed_update(bot, msg("/log"))
    assert any("Log" in t for t in s.texts())
    await dp.feed_update(bot, msg("/history"))
    assert any("No history" in t for t in s.texts())


@pytest.mark.asyncio
async def test_ai_setup_wizard(tg, db, monkeypatch):
    bot, dp, s = tg
    from proxybot.bot import ai_handlers

    async def fake_models(url, key):
        return ["m-a", "m-b"]
    monkeypatch.setattr(ai_handlers, "list_models", fake_models)
    await dp.feed_update(bot, msg("/ai_setup"))
    await dp.feed_update(bot, msg("https://api.example.com/v1", mid=3))
    await dp.feed_update(bot, msg("sk-secret", mid=4))
    assert db.get("ai_base_url") == "https://api.example.com/v1" and db.get("ai_api_key") == "sk-secret"
    assert any(n == "DeleteMessage" for n, _ in s.calls)  # key message deleted
    await dp.feed_update(bot, cb("mdl:1"))
    assert db.get("ai_model") == "m-b"
    s.calls.clear()
    await dp.feed_update(bot, msg("/ai"))
    assert any("m-b" in t for t in s.texts())
