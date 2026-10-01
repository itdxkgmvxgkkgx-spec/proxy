"""Proxy AI — ایجنت داخلی پروژه با معماری الهام‌گرفته از Hermes Agent:
- حافظه لایه‌ای (پروفایل کاربر + دانش پروژه همیشه توی پرامپت)
- اسکیل‌های قابل یادگیری (Markdown ذخیره در DB)
- اجرای ابزار با تأیید برای کارهای حساس (مثل Hermes که قبل از shell اجازه می‌گیره)
- سرچ Tavily برای کشف منابع جدید پروکسی
- شناخت کامل معماری پروژه (فایل نقشه پروژه توی سیستم پرامپت)"""

import json

import aiohttp

from .. import database as db
from ..config import TAVILY_API_KEY, BASE_DIR

PROJECT_MAP = """
# نقشه کامل پروژه Proxy Hunter Bot
bot/main.py            → نقطه شروع: راه‌اندازی DB، بات تلگرام، scheduler
bot/config.py          → تمام تنظیمات و env ها (توکن‌ها، تایم‌اوت‌ها، مسیرها)
bot/database.py        → دیتابیس SQLite: جداول proxies, settings, admins, users, logs, ai_memory, ai_skills, ai_config
bot/scraper/scraper.py → مرحله ۱و۲: جمع‌آوری + dedupe پروکسی‌ها
bot/scraper/sources.py → لیست منابع داخلی (منابع AI هم توی DB اضافه می‌شن)
bot/tester/tester.py   → مرحله ۳ تا ۵: پینگ، سرعت، فیلتر و امتیاز
bot/telegram_bot/      → رابط کاربری: handlers.py, keyboards.py
bot/ai/agent.py        → خودِ من (Proxy AI)
bot/scheduler.py       → حلقه اسکن خودکار + ذخیره ثانیه‌ای + ری‌استارت ران
data/proxybot.sqlite3  → دیتابیس لوکال (کامیت می‌شه به ریپو، هیچی گم نمی‌شه)
.github/workflows/proxy-bot.yml → ورک‌فلو: اجرا، ذخیره، ری‌استارت خودکار
برای تغییر هر رفتار باید فایل مربوطه رو اصلاح کرد و کامیت زد.
"""

SYSTEM_PROMPT = """You are **Proxy AI**, the built-in agent of the Proxy Hunter Bot project.
You speak the user's language (default Persian-friendly tone, call the user by their preferred name if stored in memory).
You have FULL knowledge of the project architecture (see PROJECT MAP) and can:
- search the internet with Tavily to find NEW MTProto proxy sources and add them
- read/modify project files (with the edit tools) — SENSITIVE actions (file edits, commits,
  changing settings, deleting data) REQUIRE user approval first: ask, wait for approval, then act.
- run terminal commands for diagnostics when asked
- learn SKILLS: when the user teaches you a procedure, save it as a skill (markdown) for reuse
- MEMORY: store facts about the user and project (e.g. "call me داداش") permanently in ai_memory.
  Whenever memory updates, briefly notify the user what was saved.
- BUGFIX workflow: user reports a bug → search the web to learn the fix → edit the file
  (after approval) → run tests to verify → report.

You NEVER act on your own without being asked, and NEVER do sensitive things silently.
Keep answers concise, friendly, and technical when needed.

{project_map}

# Long-term memory (always loaded):
{memory}

# Learned skills:
{skills}
"""


def build_system_prompt():
    mem = "\n".join(f"- {r['key']}: {r['value']}" for r in db.memory_get()) or "(empty)"
    skills = "\n".join(f"- {r['name']}" for r in db.skill_list()) or "(none)"
    return SYSTEM_PROMPT.format(project_map=PROJECT_MAP, memory=mem, skills=skills)


# ---------- AI provider ----------
async def list_models(base_url, api_key):
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{base_url.rstrip('/')}/models",
                             headers={"Authorization": f"Bearer {api_key}"},
                             timeout=aiohttp.ClientTimeout(total=15)) as r:
                data = await r.json()
                return [m["id"] for m in data.get("data", [])]
    except Exception:
        return []


async def chat(messages):
    base = db.ai_cfg_get("base_url")
    key = db.ai_cfg_get("api_key")
    model = db.ai_cfg_get("model", "gpt-4o-mini")
    if not base or not key:
        return None
    payload = {"model": model, "messages": messages, "temperature": 0.4}
    async with aiohttp.ClientSession() as s:
        async with s.post(f"{base.rstrip('/')}/chat/completions",
                          headers={"Authorization": f"Bearer {key}"},
                          json=payload, timeout=aiohttp.ClientTimeout(total=60)) as r:
            data = await r.json()
            return data["choices"][0]["message"]["content"]


# ---------- ابزارها ----------
def tool_remember(key, value):
    db.memory_set(key, value)
    return f"🧠 Saved to memory: `{key}` = {value}"


def tool_learn_skill(name, content):
    db.skill_save(name, content)
    return f"📚 Skill learned: {name}"


async def tool_find_sources(query="MTProto proxy list telegram github raw"):
    """سرچ Tavily برای منابع جدید و افزودن به لیست منابع."""
    if not TAVILY_API_KEY:
        return "❌ Tavily key not set."
    async with aiohttp.ClientSession() as s:
        async with s.post("https://api.tavily.com/search",
                          json={"api_key": TAVILY_API_KEY, "query": query,
                                "max_results": 10},
                          timeout=aiohttp.ClientTimeout(total=30)) as r:
            data = await r.json()
    urls = [x["url"] for x in data.get("results", [])]
    existing = json.loads(db.get_setting("extra_sources", "[]"))
    new = [u for u in urls if u not in existing]
    existing.extend(new)
    db.set_setting("extra_sources", json.dumps(existing))
    return f"🔎 Found {len(new)} new sources (total extra: {len(existing)})"
