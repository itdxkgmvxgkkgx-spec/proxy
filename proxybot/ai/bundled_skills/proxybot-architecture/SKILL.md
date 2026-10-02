---
name: proxybot-architecture
description: Map of this project — where every file, table and setting lives and what to change for each kind of task
version: 1.0.0
---
# ProxyBot architecture (you are running inside it)

## When to use
Before touching any file, changing a setting, or answering "where is X stored".

## Layout
```
run.py                         entry: starts bot + scheduler + persister + handover watchdog
proxybot/core/config.py        DEFAULT_SETTINGS (every runtime setting), paths, Secrets (env)
proxybot/core/database.py      SQLite schema + all queries (tables below)
proxybot/core/persistence.py   git commit/push of data/, chain_next_run (workflow_dispatch), handover
proxybot/core/logger.py        logging -> stdout + data/logs + `logs` table; set_stage() for /log
proxybot/pipeline/sources.py   built-in RAW_SOURCES + TELEGRAM_CHANNELS (seeded once into `sources`)
proxybot/pipeline/parser.py    extract_proxies(): tg://proxy, t.me/proxy, JSON, host:port:secret
proxybot/pipeline/mtproto.py   real MTProto handshake tester (fake-TLS, obfuscated2, req_pq_multi) + throughput
proxybot/pipeline/iran_check.py check-host.net Iranian nodes TCP check
proxybot/pipeline/runner.py    PipelineRunner: collect→dedupe→ping→speed→filter, compute_score()
proxybot/bot/                  aiogram handlers (menus, settings, admins, sources, ai chat), keyboards, scheduler
proxybot/ai/agent.py           the agent loop (OpenAI-compatible chat.completions with tools)
proxybot/ai/tools.py           tool registry + implementations + dangerous-action detection
proxybot/ai/prompts.py         system prompt tiers (identity, guidance, architecture, memory, skills)
proxybot/ai/memory.py          MEMORY.md / USER.md stores (data/memory/)
proxybot/ai/skills.py          skills (data/skills/<name>/SKILL.md)
proxybot/i18n/strings.py       UI strings for 10 languages
.github/workflows/proxybot.yml the always-on workflow (chained with GH_PAT)
data/proxybot.db               THE database (committed to git every save_interval_sec)
```

## Tables (data/proxybot.db)
settings(key,value json) · users · admins(user_id, permissions json, is_owner) · sources(url, kind, enabled, fail_count, added_by)
proxies(host,port,secret,link,ping_ms,down_kbps,up_kbps,score,iran_ok,status alive|flaky|dead|new,fails) ·
proxy_history(proxy_id, ts, ping_ms, down_kbps, up_kbps, ok, run_id) · runs · logs · ai_sessions · ai_messages · ai_pending · kv

## Change recipes
- Change scan frequency / thresholds / threads → `set_setting` tool (keys in DEFAULT_SETTINGS). Never edit config.py for that.
- Add a proxy source → `add_source` tool (goes into `sources` table, survives restarts).
- Fix a parsing bug → edit proxybot/pipeline/parser.py, then `run_shell("python -m pytest tests -q")`.
- Fix a tester bug → proxybot/pipeline/mtproto.py; verify with `test_proxy_link` tool on a known-alive proxy.
- Change bot texts → proxybot/i18n/strings.py (EN + FA at least).
- Code changes only take effect after the user commits+pushes and the next run starts (tell them). You can `git_commit` the change; the workflow run restarts on its own at handover or the user can cancel the run.

## Pitfalls
- Never put secrets in memory, files or logs. BOT_TOKEN/GH_PAT/TAVILY/ai_api_key are off-limits to print.
- The DB is written by the running bot; use `db_query` (read) and `db_execute` (write, needs approval) instead of editing the file.
- GitHub kills the job at 6h; long shell commands must finish in minutes.
