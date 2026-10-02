"""ProxyBot — self-restarting Telegram MTProto proxy hunter with a Hermes-style AI agent.

Package layout (see ARCHITECTURE.md for the full map):
    core/      config, database (SQLite), persistence (git), logging
    pipeline/  5-stage proxy pipeline: collect → dedupe → ping → speed → filter
    bot/       aiogram Telegram bot (i18n, keyboards, handlers, admins)
    ai/        Proxy AI agent (tools, approval gate, memory, skills, Tavily)
    i18n/      translations for 10 languages
"""

__version__ = "1.0.0"
