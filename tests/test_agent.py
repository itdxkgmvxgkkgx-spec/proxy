"""Agent loop test against a fake OpenAI-compatible server (aiohttp) — no real LLM needed."""
import json

import pytest
from aiohttp import web

from proxybot.ai import agent as A


class FakeLLM:
    """Scripted responses: each call pops the next item."""

    def __init__(self):
        self.script = []
        self.requests = []

    async def handle(self, request: web.Request):
        body = await request.json()
        self.requests.append(body)
        step = self.script.pop(0) if self.script else {"content": "fallback"}
        msg = {"role": "assistant", "content": step.get("content")}
        if "tool" in step:
            msg["tool_calls"] = [{"id": f"call{len(self.requests)}", "type": "function",
                                  "function": {"name": step["tool"], "arguments": json.dumps(step.get("args", {}))}}]
        return web.json_response({"choices": [{"message": msg, "finish_reason": "stop"}]})

    async def models(self, request):
        return web.json_response({"data": [{"id": "fake-1"}, {"id": "fake-2"}]})


@pytest.fixture()
async def llm(db, aiohttp_server):
    f = FakeLLM()
    app = web.Application()
    app.router.add_post("/v1/chat/completions", f.handle)
    app.router.add_get("/v1/models", f.models)
    server = await aiohttp_server(app)
    db.set("ai_base_url", f"http://{server.host}:{server.port}/v1")
    db.set("ai_api_key", "k")
    db.set("ai_model", "fake-1")
    return f


@pytest.mark.asyncio
async def test_list_models(llm, db):
    models = await A.list_models(db.get("ai_base_url"), "k")
    assert models == ["fake-1", "fake-2"]


@pytest.mark.asyncio
async def test_safe_tool_then_answer(llm, db):
    llm.script = [{"tool": "bot_status"}, {"content": "status ok"}]
    events = []

    async def on_tool(n, a):
        events.append(("tool", n))
    ag = A.ProxyAgent(1000, "en", A.Callbacks(on_tool=on_tool))
    res = await ag.run_turn("status?")
    assert res.text == "status ok" and res.tool_calls == 1 and events == [("tool", "bot_status")]
    # tool result was fed back
    roles = [m["role"] for m in llm.requests[1]["messages"]]
    assert roles[-2:] == ["assistant", "tool"]
    assert llm.requests[0]["messages"][0]["role"] == "system"
    assert "Proxy AI" in llm.requests[0]["messages"][0]["content"]


@pytest.mark.asyncio
async def test_memory_notification(llm, db):
    llm.script = [{"tool": "memory", "args": {"action": "add", "target": "user", "content": "User wants to be called داداش"}},
                  {"content": "باشه داداش"}]
    notes = []

    async def on_memory(action, target, text):
        notes.append((action, target, text))
    ag = A.ProxyAgent(1000, "fa", A.Callbacks(on_memory=on_memory))
    res = await ag.run_turn("منو داداش صدا کن")
    assert res.text == "باشه داداش"
    assert notes == [("add", "user", "User wants to be called داداش")]
    from proxybot.ai import memory as mem
    assert "داداش" in mem.user_profile().entries()[0]


@pytest.mark.asyncio
async def test_dangerous_tool_is_staged_then_approved(llm, db, tmp_path, monkeypatch):
    from proxybot.ai import tools as T
    monkeypatch.setattr(T, "ROOT", tmp_path)
    llm.script = [{"tool": "write_file", "args": {"path": "notes.txt", "content": "hello"}},
                  {"content": "waiting for approval"}]
    approvals = []

    async def on_approval(pid, tool, args, reason):
        approvals.append((pid, tool))
    ag = A.ProxyAgent(1000, "en", A.Callbacks(on_approval=on_approval))
    res = await ag.run_turn("write notes")
    assert res.staged and approvals[0][1] == "write_file"
    assert res.text == "waiting for approval"
    assert not (tmp_path / "notes.txt").exists()
    assert len(db.ai_pending(1000)) == 1
    # approve → executes → model gets result → answers
    llm.script = [{"content": "written!"}]
    res2 = await ag.resume_pending(approvals[0][0], True)
    assert res2.text == "written!"
    assert (tmp_path / "notes.txt").read_text() == "hello"
    assert db.ai_pending(1000) == []
    last_user = [m for m in llm.requests[-1]["messages"] if m["role"] == "user"][-1]["content"]
    assert "APPROVED and executed" in last_user


@pytest.mark.asyncio
async def test_hardline_blocked(llm, db):
    llm.script = [{"tool": "run_shell", "args": {"command": "rm -rf /"}}, {"content": "blocked"}]
    ag = A.ProxyAgent(1000, "en")
    res = await ag.run_turn("wipe")
    assert res.text == "blocked" and not res.staged
    tool_msg = [m for m in llm.requests[1]["messages"] if m["role"] == "tool"][-1]["content"]
    assert "BLOCKED" in tool_msg


@pytest.mark.asyncio
async def test_denied(llm, db):
    llm.script = [{"tool": "set_setting", "args": {"key": "top_n", "value": "99"}}, {"content": "ok waiting"}]
    ag = A.ProxyAgent(1000, "en")
    res = await ag.run_turn("set top_n 99")
    pid = res.staged[0]
    llm.script = [{"content": "understood"}]
    res2 = await ag.resume_pending(pid, False)
    assert res2.text == "understood" and db.get("top_n") != 99
