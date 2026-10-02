"""Built-in proxy sources.

Three kinds:
    raw      — plain text / JSON lists on GitHub & pastebins (most reliable)
    channel  — public Telegram channels via t.me/s/<name> HTML preview
    search   — GitHub code search for freshly committed tg://proxy links

The Proxy AI adds new sources to the `sources` table at runtime via Tavily;
these built-ins are only seeded once. Anything that fails 10 times in a row is
auto-disabled (see pipeline.collect).
"""

RAW_SOURCES = [
    # GitHub aggregated lists (verified live 2026-10)
    "https://raw.githubusercontent.com/tgmtproxy/telegram-mtproto-proxy-list/main/proxies.txt",
    "https://raw.githubusercontent.com/tgproxypink/telegram-proxy-list/main/proxies.json",
    "https://raw.githubusercontent.com/tgproxypink/telegram-proxy-list/main/mtproto.txt",
    "https://raw.githubusercontent.com/Therealwh/MTPproxyLIST/main/verified/proxy_all_verified.json",
    "https://raw.githubusercontent.com/Therealwh/MTPproxyLIST/main/verified/proxy_eu_verified.txt",
    "https://raw.githubusercontent.com/SoliSpirit/mtproto/master/all_proxies.txt",
    "https://raw.githubusercontent.com/Iliya3ProX/good_proxies/main/proxies.txt",
    "https://raw.githubusercontent.com/MhdiTaheri/ProxyCollector/main/proxy.txt",
    "https://raw.githubusercontent.com/ALIILAPRO/MTProtoProxy/main/mtproto.txt",
    "https://raw.githubusercontent.com/hookzof/socks5_list/master/tg/mtproto.json",
    "https://raw.githubusercontent.com/leshchenko1979/tgproxy/main/proxies.txt",
    "https://raw.githubusercontent.com/ferhatacer90/mtproto-proxy-ru-list/main/proxies.txt",
    "https://raw.githubusercontent.com/nortyxk/ProxyHub/main/mtproto.txt",
    "https://raw.githubusercontent.com/horizonpaz-create/mtproto-live/main/proxies.txt",
    "https://raw.githubusercontent.com/Aniskhoso/Telegram-MTProto-Proxy-List-2026/main/proxies.txt",
    "https://raw.githubusercontent.com/rezashaporabadi/telegram-mtproto-proxy/main/proxies.txt",
    "https://raw.githubusercontent.com/yukeme/free-mtproto-proxy-list/main/proxies.txt",
    "https://raw.githubusercontent.com/zakky8/mtproto-proxy-pro/main/proxies.txt",
    # non-GitHub aggregators
    "https://mtpro.xyz/api/?type=mtproto",
    "https://mtproto.me/api/proxies",
]

# Public channels that post MTProto proxies many times a day.
TELEGRAM_CHANNELS = [
    "ProxyMTProto", "MTProtoProxies", "iMTProto", "MTProxyT", "ProxyMTProtoFree",
    "mtproxy_ir", "Proxy_MTProto_IR", "FreeMTProxy", "mtprotoproxy_tg", "ProxyHagh",
    "MTProto_Proxies", "proxy_mtproto_telegram", "mtproto_proxy_free", "iranproxy_mtproto",
    "ProxyFast", "ProxyKing1", "proxymtproto", "MProxyCh", "HiProxy", "proxyroxy",
    "ProxyGhost", "Proxy_Dast", "Proxy_Ir", "pr0xychannel", "ProxyLimit", "MTProtoChannel",
    "proxy_manager", "MTProtoProxyList", "TeleProxy_IR", "ProxyUpdate",
    "proxiesxx", "ProxyTelegram_Ir", "ProxyTel1", "ProxyRapid", "ProxyNiceCH",
    "mtprotoproxy", "Mtproxy_Channel", "ProxySpeeds", "ProxyMarket_IR", "ProxyIranians",
]

# GitHub code search queries (requires GH_PAT; optional).
GITHUB_SEARCH_QUERIES = [
    "tg://proxy?server= secret=ee",
    "t.me/proxy?server= port= secret=",
    "filename:mtproto.txt tg://proxy",
]


def channel_url(name: str) -> str:
    return f"https://t.me/s/{name}"


def builtin_sources() -> list[tuple[str, str]]:
    out = [(u, "raw") for u in RAW_SOURCES]
    out += [(channel_url(c), "channel") for c in TELEGRAM_CHANNELS]
    return out


# --------------------------------------------------------------------------
# GitHub auto-discovery (no token needed; 10 req/min anonymous is plenty)
# --------------------------------------------------------------------------
GITHUB_REPO_QUERIES = [
    "mtproto proxy list in:name,description",
    "telegram proxy mtproto in:name,description",
    "پروکسی تلگرام mtproto",
]


async def discover_github_sources(session, probe, limit_repos: int = 12) -> list[str]:
    """Search GitHub for recently pushed proxy-list repos, list their .txt/.json
    files and return URLs that actually contain >=3 proxies (via `probe(url)`)."""
    import asyncio
    found: list[str] = []
    seen_repos: set[str] = set()
    for q in GITHUB_REPO_QUERIES:
        try:
            async with session.get("https://api.github.com/search/repositories",
                                   params={"q": q, "sort": "updated", "per_page": 15},
                                   headers={"Accept": "application/vnd.github+json", "User-Agent": "proxybot"},
                                   timeout=20) as r:
                if r.status != 200:
                    continue
                items = (await r.json(content_type=None)).get("items", [])
        except Exception:  # noqa: BLE001
            continue
        for repo in items:
            full, branch = repo["full_name"], repo["default_branch"]
            if full in seen_repos or len(seen_repos) >= limit_repos:
                continue
            seen_repos.add(full)
            try:
                async with session.get(f"https://api.github.com/repos/{full}/git/trees/{branch}?recursive=1",
                                       headers={"Accept": "application/vnd.github+json", "User-Agent": "proxybot"}, timeout=20) as r:
                    if r.status != 200:
                        continue
                    tree = (await r.json(content_type=None)).get("tree", [])
            except Exception:  # noqa: BLE001
                continue
            cands = [f"https://raw.githubusercontent.com/{full}/{branch}/{t['path']}" for t in tree
                     if t.get("type") == "blob" and t["path"].lower().endswith((".txt", ".json"))
                     and 200 < t.get("size", 0) < 3_000_000][:6]
            results = await asyncio.gather(*(probe(u) for u in cands), return_exceptions=True)
            for u, n in zip(cands, results):
                if isinstance(n, int) and n >= 3:
                    found.append(u)
        await asyncio.sleep(1)
    return found
