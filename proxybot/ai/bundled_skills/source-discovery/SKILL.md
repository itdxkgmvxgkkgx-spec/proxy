---
name: source-discovery
description: Find new MTProto proxy sources on the web with Tavily and add the good ones
version: 1.0.0
---
# Discover new proxy sources

## When to use
User asks for more/new sources, or the periodic auto-discovery runs (`ai_auto_discover`).

## Procedure
1. `web_search` with 3-6 varied queries, e.g.:
   - "MTProto proxy list github raw tg://proxy"  - "پروکسی تلگرام mtproto لیست رایگان"
   - "t.me/proxy?server= secret=ee telegram channel proxy"  - "mtproto proxies txt updated daily"
   - "پروکسی mtproto کانال تلگرام"  - "free telegram proxy api json mtproto"
2. For each promising URL call `probe_source(url)` — it downloads and counts parsable proxies. Prefer raw GitHub
   files (`raw.githubusercontent.com/...`), JSON APIs and `https://t.me/s/<channel>` pages.
3. Convert GitHub blob URLs to raw: `github.com/U/R/blob/B/path` → `raw.githubusercontent.com/U/R/B/path`.
   Convert `t.me/<channel>` → `https://t.me/s/<channel>`.
4. Add only sources where `probe_source` found ≥ 3 proxies: `add_source(url, note="found via tavily: <query>")`.
5. Report: how many queries, how many probed, how many added, total proxies they contained.

## Pitfalls
- Pages that only list SOCKS5/HTTP proxies are useless — we need `secret=` MTProto links.
- Don't add the same host twice with different query strings.
- Sources failing 10× get auto-disabled; do not re-add them unless probe succeeds now.
