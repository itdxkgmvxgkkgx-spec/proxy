"""Proxy AI agent loop (Hermes-style AIAgent, async, OpenAI-compatible).

    user text → load session history (SQLite) → system prompt → chat.completions
    with tools → execute tool calls (safe immediately; dangerous → staged) →
    loop until no tool calls or max_steps → persist every message.

Callbacks (all async, optional):
    on_tool(name, args)                  progress line in chat
    on_approval(pending_id, tool, args, reason)  show ✅/❌ card
    on_memory(action, target, text)      💾 notification
    on_skill(name, action)               📚 notification
    notify(text)                         plain message to the user

Approved actions are executed by `resume_pending()` and their result is fed
back as a tool message, after which the loop continues (a new model turn).
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional

import aiohttp

from ..core.database import get_db
from . import tools as T
from .prompts import build_system_prompt

log = logging.getLogger("proxybot.ai")


@dataclass
class Callbacks:
    on_tool: Optional[Callable[[str, dict], Awaitable[None]]] = None
    on_approval: Optional[Callable[[int, str, dict, str], Awaitable[None]]] = None
    on_memory: Optional[Callable[[str, str, str], Awaitable[None]]] = None
    on_skill: Optional[Callable[[str, str], Awaitable[None]]] = None
    notify: Optional[Callable[[str], Awaitable[None]]] = None


@dataclass
class TurnResult:
    text: str = ""
    staged: list[int] = field(default_factory=list)
    steps: int = 0
    error: str = ""
    tool_calls: int = 0


class AIConfigError(RuntimeError):
    pass


# --------------------------------------------------------------- provider
def ai_config() -> dict:
    db = get_db()
    return {"base_url": str(db.get("ai_base_url", "")).rstrip("/"), "api_key": str(db.get("ai_api_key", "")),
            "model": str(db.get("ai_model", "")), "temperature": float(db.get("ai_temperature", 0.3)),
            "max_steps": int(db.get("ai_max_steps", 25))}


def is_configured() -> bool:
    c = ai_config()
    return bool(c["base_url"] and c["api_key"] and c["model"])


async def list_models(base_url: str, api_key: str) -> list[str]:
    url = base_url.rstrip("/") + "/models"
    async with aiohttp.ClientSession() as s:
        async with s.get(url, headers={"Authorization": f"Bearer {api_key}"}, timeout=aiohttp.ClientTimeout(total=30)) as r:
            data = await r.json(content_type=None)
            if r.status != 200:
                raise AIConfigError(f"HTTP {r.status}: {str(data)[:200]}")
    items = data.get("data") if isinstance(data, dict) else data
    ids = []
    for m in items or []:
        mid = m.get("id") if isinstance(m, dict) else str(m)
        if mid:
            ids.append(mid)
    return sorted(set(ids))


async def chat_completion(messages: list[dict], tools: list[dict] | None, cfg: dict) -> dict:
    body: dict[str, Any] = {"model": cfg["model"], "messages": messages, "temperature": cfg["temperature"]}
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"
    headers = {"Authorization": f"Bearer {cfg['api_key']}", "Content-Type": "application/json",
               "HTTP-Referer": "https://github.com/proxybot", "X-Title": "ProxyBot"}
    last_err = ""
    for attempt in range(3):
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(cfg["base_url"] + "/chat/completions", json=body, headers=headers,
                                  timeout=aiohttp.ClientTimeout(total=180)) as r:
                    data = await r.json(content_type=None)
                    if r.status == 200 and "choices" in data:
                        return data
                    last_err = f"HTTP {r.status}: {json.dumps(data)[:400]}"
                    if r.status in (400, 401, 403, 404):
                        break
        except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError) as e:
            last_err = f"{type(e).__name__}: {e}"
        await asyncio.sleep(2 * (attempt + 1))
    raise AIConfigError(last_err or "unknown provider error")


# ------------------------------------------------------------------ agent
class ProxyAgent:
    def __init__(self, user_id: int, lang: str = "en", callbacks: Callbacks | None = None):
        self.user_id = user_id
        self.lang = lang
        self.cb = callbacks or Callbacks()
        self.db = get_db()
        self.session_id = self.db.ai_session(user_id)

    # ------------------------------------------------------------ helpers
    def _tool_schemas(self) -> list[dict]:
        return T.schemas()

    async def _notify_memory_or_skill(self, name: str, args: dict, result: str) -> None:
        mode = str(self.db.get("ai_memory_notify", "verbose"))
        if mode == "off":
            return
        try:
            if name == "memory" and self.cb.on_memory:
                res = json.loads(result)
                if res.get("success"):
                    text = (args.get("content") or args.get("old_text") or "")[:160] if mode == "verbose" else ""
                    await self.cb.on_memory(args.get("action", ""), args.get("target", ""), text)
            elif name == "skill_manage" and self.cb.on_skill and not result.startswith("error"):
                await self.cb.on_skill(args.get("name", ""), args.get("action", ""))
        except Exception:  # noqa: BLE001
            pass

    async def execute_tool(self, name: str, args: dict) -> str:
        tool = T.REGISTRY.get(name)
        if not tool:
            return f"error: unknown tool {name}"
        kwargs = dict(args)
        if name == "session_search":
            kwargs["_user_id"] = self.user_id
        if name == "send_message":
            kwargs["_notify"] = self.cb.notify
        try:
            result = await asyncio.wait_for(tool.fn(**kwargs), timeout=320)
        except asyncio.TimeoutError:
            result = "error: tool timed out"
        except TypeError as e:
            result = f"error: bad arguments: {e}"
        except Exception as e:  # noqa: BLE001
            log.exception("tool %s failed", name)
            result = f"error: {type(e).__name__}: {e}"
        await self._notify_memory_or_skill(name, args, result)
        return str(result)[:12000]

    async def _dispatch(self, name: str, args: dict) -> tuple[str, int | None]:
        """Run or stage a tool. Returns (tool_result_text, pending_id|None)."""
        tool = T.REGISTRY.get(name)
        if not tool:
            return f"error: unknown tool {name}", None
        level = tool.danger(args)
        if level == "hardline":
            why = T.classify_shell(args.get("command", ""))[1] if name == "run_shell" else "protected target"
            return f"BLOCKED (hardline): {why}. This action is never allowed. Explain to the user and stop.", None
        if level == "approve":
            reason = tool.reason or "needs approval"
            if name == "run_shell":
                reason = T.classify_shell(args.get("command", ""))[1]
            pid = self.db.ai_stage_action(self.user_id, self.session_id, name, args, reason)
            if self.cb.on_approval:
                await self.cb.on_approval(pid, name, args, reason)
            return f"STAGED #{pid}: waiting for user approval in Telegram. Stop and tell the user briefly what this will do.", pid
        if self.cb.on_tool:
            await self.cb.on_tool(name, args)
        return await self.execute_tool(name, args), None

    # --------------------------------------------------------------- loop
    async def run_turn(self, user_text: str | None, extra_tool_results: list[dict] | None = None) -> TurnResult:
        if not is_configured():
            raise AIConfigError("AI not configured")
        cfg = ai_config()
        res = TurnResult()
        if user_text is not None:
            self.db.ai_add_message(self.session_id, "user", user_text)
        for tm in extra_tool_results or []:
            self.db.ai_add_message(self.session_id, "tool", tm["content"], tool_call_id=tm["tool_call_id"], name=tm.get("name"))

        system = {"role": "system", "content": build_system_prompt(self.user_id, self.lang)}
        for step in range(cfg["max_steps"]):
            res.steps = step + 1
            history = self.db.ai_messages(self.session_id, limit=80)
            try:
                data = await chat_completion([system] + history, self._tool_schemas(), cfg)
            except AIConfigError as e:
                res.error = str(e)
                return res
            choice = data["choices"][0]
            msg = choice.get("message", {})
            content = msg.get("content") or ""
            tool_calls = msg.get("tool_calls") or []
            # some providers return tool calls inside content as JSON — ignore, treat as text
            self.db.ai_add_message(self.session_id, "assistant", content if content else None,
                                   tool_calls=tool_calls if tool_calls else None)
            if not tool_calls:
                res.text = content.strip()
                return res
            staged_now = False
            for tc in tool_calls:
                res.tool_calls += 1
                fn = tc.get("function", {})
                name = fn.get("name", "")
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                    if not isinstance(args, dict):
                        args = {}
                except json.JSONDecodeError:
                    args = {}
                    result = "error: arguments were not valid JSON"
                    self.db.ai_add_message(self.session_id, "tool", result, tool_call_id=tc.get("id"), name=name)
                    continue
                result, pid = await self._dispatch(name, args)
                if pid:
                    res.staged.append(pid)
                    staged_now = True
                    self.db.execute("UPDATE ai_pending SET result=? WHERE id=?", (json.dumps({"tool_call_id": tc.get("id")}), pid))
                self.db.ai_add_message(self.session_id, "tool", result, tool_call_id=tc.get("id"), name=name)
            if staged_now:
                # let the model produce its one-line "waiting for approval" message, then stop
                history = self.db.ai_messages(self.session_id, limit=80)
                try:
                    data = await chat_completion([system] + history, None, cfg)
                    text = (data["choices"][0].get("message", {}).get("content") or "").strip()
                except AIConfigError:
                    text = ""
                if text:
                    self.db.ai_add_message(self.session_id, "assistant", text)
                res.text = text
                return res
        res.text = res.text or "(stopped: max steps reached — tell me to continue if needed)"
        self.db.ai_add_message(self.session_id, "assistant", res.text)
        return res

    # ----------------------------------------------------------- approvals
    async def resume_pending(self, pending_id: int, approve: bool) -> TurnResult:
        row = self.db.ai_resolve(pending_id, "approved" if approve else "denied")
        if not row or row["status"] != "pending":
            return TurnResult(text="", error="not pending")
        args = json.loads(row["args"])
        meta = {}
        try:
            meta = json.loads(row["result"] or "{}")
        except json.JSONDecodeError:
            pass
        tc_id = meta.get("tool_call_id") or f"pending-{pending_id}"
        if approve:
            if self.cb.on_tool:
                await self.cb.on_tool(row["tool"], args)
            result = await self.execute_tool(row["tool"], args)
            self.db.execute("UPDATE ai_pending SET result=? WHERE id=?", (result[:4000], pending_id))
            feed = f"APPROVED and executed #{pending_id} ({row['tool']}). Result:\n{result}"
        else:
            feed = f"DENIED #{pending_id} ({row['tool']}) by the user. Do not retry it another way; ask what they prefer."
        # Feed the outcome as a user-visible system note so the model continues the task.
        return await self.run_turn(f"[approval outcome] {feed}")

    def new_session(self) -> int:
        self.session_id = self.db.ai_session(self.user_id, new=True)
        return self.session_id
