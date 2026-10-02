"""Configuration: environment secrets + persisted runtime settings.

Secrets (GitHub Actions `secrets.*` → env):
    BOT_TOKEN       Telegram bot token (required)
    ADMIN_ID        Initial owner Telegram user id (required on first run)
    GH_PAT          GitHub PAT with `repo` + `workflow` scope — used to
                    re-dispatch the workflow and to push the data/ directory
    TAVILY_API_KEY  Tavily search key for the Proxy AI source discovery
    GITHUB_REPOSITORY, GITHUB_RUN_ID, GITHUB_WORKFLOW  injected by Actions

Runtime settings (changeable from the bot, stored in SQLite `settings` table)
are declared in DEFAULT_SETTINGS. Everything the user can tune lives there so
that the AI agent and the bot share one source of truth.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "proxybot.db"
MEMORY_DIR = DATA_DIR / "memory"
SKILLS_DIR = DATA_DIR / "skills"
LOG_DIR = DATA_DIR / "logs"
TMP_DIR = DATA_DIR / "tmp"

for _d in (DATA_DIR, MEMORY_DIR, SKILLS_DIR, LOG_DIR, TMP_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Runtime settings (persisted). key -> (default, type, description)
# ---------------------------------------------------------------------------
DEFAULT_SETTINGS: dict[str, tuple] = {
    # scheduler
    "scan_interval_min": (15, int, "Minutes between automatic proxy hunts"),
    "auto_scan": (1, int, "1 = run the pipeline automatically on the interval"),
    # pipeline
    "threads": (64, int, "Concurrent connections during ping test"),
    "speed_threads": (12, int, "Concurrent connections during speed test"),
    "ping_timeout": (4.0, float, "Seconds before a TCP/MTProto handshake is considered dead"),
    "speed_timeout": (8.0, float, "Seconds budget for each download/upload probe"),
    "speed_bytes": (65536, int, "Bytes pushed/pulled per speed probe"),
    "max_ping_ms": (1500, int, "Filter: discard proxies slower than this"),
    "min_score": (20.0, float, "Filter: minimum composite score to be listed"),
    "top_n": (30, int, "How many proxies the final list keeps"),
    "iran_check": (1, int, "1 = also test through Iranian HTTP relays when available"),
    "source_timeout": (20.0, float, "Seconds per source fetch"),
    "retention_days": (30, int, "Keep proxy history for this many days"),
    "github_discover_every": (4, int, "Search GitHub for new source repos every N runs (0 = never)"),
    # bot
    "public_mode": (0, int, "1 = anyone may /start; sensitive menus still admin-only"),
    "default_lang": ("en", str, "Language for new users"),
    "send_mode": ("single", str, "single | batch | file — default proxy delivery style"),
    "send_count": (5, int, "Default number of proxies to send"),
    # persistence
    "save_interval_sec": (30, int, "How often data/ is committed & pushed"),
    # ai
    "ai_base_url": ("", str, "OpenAI-compatible base URL"),
    "ai_api_key": ("", str, "API key for the AI provider"),
    "ai_model": ("", str, "Selected model id"),
    "ai_temperature": (0.3, float, "Sampling temperature"),
    "ai_max_steps": (25, int, "Max tool-call iterations per turn"),
    "ai_memory_notify": ("verbose", str, "off | on | verbose — memory write notifications"),
    "ai_auto_discover": (1, int, "1 = AI hunts for new sources with Tavily every N scans"),
    "ai_discover_every": (6, int, "Run Tavily source discovery every N pipeline runs"),
}


@dataclass
class Secrets:
    bot_token: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", "").strip())
    admin_id: int = field(default_factory=lambda: int(os.getenv("ADMIN_ID", "0") or 0))
    gh_pat: str = field(default_factory=lambda: os.getenv("GH_PAT", "").strip())
    tavily_key: str = field(default_factory=lambda: os.getenv("TAVILY_API_KEY", "").strip())
    repo: str = field(default_factory=lambda: os.getenv("GITHUB_REPOSITORY", "").strip())
    run_id: str = field(default_factory=lambda: os.getenv("GITHUB_RUN_ID", "local"))
    workflow_file: str = field(default_factory=lambda: os.getenv("WORKFLOW_FILE", "proxybot.yml"))
    # GitHub Actions jobs are hard-capped at 6h; we hand over before that.
    run_budget_min: int = field(default_factory=lambda: int(os.getenv("RUN_BUDGET_MIN", "330")))

    @property
    def in_actions(self) -> bool:
        return bool(os.getenv("GITHUB_ACTIONS"))

    def validate(self) -> list[str]:
        problems = []
        if not self.bot_token:
            problems.append("BOT_TOKEN missing")
        if not self.admin_id:
            problems.append("ADMIN_ID missing (first owner)")
        if self.in_actions and not self.gh_pat:
            problems.append("GH_PAT missing — cannot chain runs or persist data")
        return problems


SECRETS = Secrets()
