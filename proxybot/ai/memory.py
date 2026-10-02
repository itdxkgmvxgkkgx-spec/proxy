"""Hermes-style bounded memory: MEMORY.md (agent notes) + USER.md (user profile).

* Entries are separated by `§`, char-limited (2200 / 1375 like Hermes).
* No auto-compaction: when full the tool returns an error listing entries so
  the model consolidates itself.
* `replace`/`remove` use unique-substring matching.
* Injection scan: entries with imperative prompt-injection / exfil patterns or
  invisible unicode are rejected.
* Files live in data/memory/ and are committed by the Persister.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ..core.config import MEMORY_DIR

SEP = "§"
LIMITS = {"memory": 2200, "user": 1375}
FILES = {"memory": MEMORY_DIR / "MEMORY.md", "user": MEMORY_DIR / "USER.md"}

_INJECTION = re.compile(
    r"(ignore (all|any|previous|the above) instructions|you are now|disregard .{0,30}(rules|instructions)|"
    r"curl .{0,80}\|\s*(ba)?sh|base64 -d|/etc/passwd|\.ssh/|authorized_keys|BOT_TOKEN|GH_PAT|api[_-]?key\s*[:=]\s*\S{8,})",
    re.IGNORECASE,
)
_INVISIBLE = re.compile(r"[\u200b-\u200f\u2028-\u202e\u2060-\u2064\ufeff]")


@dataclass
class MemResult:
    success: bool
    message: str
    entries: list[str]
    usage: str


class MemoryStore:
    def __init__(self, target: str):
        if target not in FILES:
            raise ValueError("target must be 'memory' or 'user'")
        self.target = target
        self.path: Path = FILES[target]
        self.limit = LIMITS[target]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("", encoding="utf-8")

    # ----------------------------------------------------------------- io
    def entries(self) -> list[str]:
        raw = self.path.read_text(encoding="utf-8")
        return [e.strip() for e in raw.split(SEP) if e.strip()]

    def _write(self, entries: list[str]) -> None:
        self.path.write_text(f"\n{SEP}\n".join(entries), encoding="utf-8")

    def used(self) -> int:
        return len(f"\n{SEP}\n".join(self.entries()))

    def usage(self) -> str:
        return f"{self.used()}/{self.limit}"

    def pct(self) -> int:
        return int(100 * self.used() / self.limit)

    # ------------------------------------------------------------ actions
    def _scan(self, content: str) -> str | None:
        if _INVISIBLE.search(content):
            return "entry contains invisible unicode characters"
        if _INJECTION.search(content):
            return "entry matches a prompt-injection / credential pattern and was blocked"
        return None

    def add(self, content: str) -> MemResult:
        content = content.strip()
        if not content:
            return MemResult(False, "empty content", self.entries(), self.usage())
        bad = self._scan(content)
        if bad:
            return MemResult(False, bad, self.entries(), self.usage())
        ents = self.entries()
        if content in ents:
            return MemResult(True, "no duplicate added (entry already exists)", ents, self.usage())
        new_len = len(f"\n{SEP}\n".join(ents + [content]))
        if new_len > self.limit:
            return MemResult(False,
                             f"{self.target} at {self.used()}/{self.limit} chars. Adding this entry ({len(content)} chars) would "
                             f"exceed the limit. Consolidate now: use 'replace' to merge overlapping entries into shorter ones or "
                             f"'remove' stale entries (see current entries), then retry this add — all in this turn.",
                             ents, self.usage())
        ents.append(content)
        self._write(ents)
        return MemResult(True, "added", ents, self.usage())

    def _match(self, old_text: str, ents: list[str]) -> int | str:
        if old_text in ents:
            return ents.index(old_text)
        hits = [i for i, e in enumerate(ents) if old_text in e]
        if not hits:
            return f"no entry contains '{old_text}'"
        if len(hits) > 1:
            return f"'{old_text}' matches {len(hits)} entries — use a more specific substring"
        return hits[0]

    def replace(self, old_text: str, content: str) -> MemResult:
        ents = self.entries()
        idx = self._match(old_text.strip(), ents)
        if isinstance(idx, str):
            return MemResult(False, idx, ents, self.usage())
        content = content.strip()
        bad = self._scan(content)
        if bad:
            return MemResult(False, bad, ents, self.usage())
        new = ents[:idx] + ([content] if content else []) + ents[idx + 1:]
        if len(f"\n{SEP}\n".join(new)) > self.limit:
            return MemResult(False, "replacement would exceed the limit — shorten it or remove another entry", ents, self.usage())
        self._write(new)
        return MemResult(True, f"replaced: '{ents[idx][:60]}' → '{content[:60]}'", new, self.usage())

    def remove(self, old_text: str) -> MemResult:
        ents = self.entries()
        idx = self._match(old_text.strip(), ents)
        if isinstance(idx, str):
            return MemResult(False, idx, ents, self.usage())
        removed = ents.pop(idx)
        self._write(ents)
        return MemResult(True, f"removed: '{removed[:80]}'", ents, self.usage())

    # ------------------------------------------------------------- render
    def render_block(self) -> str:
        ents = self.entries()
        title = "MEMORY (your personal notes)" if self.target == "memory" else "USER PROFILE"
        head = f"══════════════════════════════════════════════\n{title} [{self.pct()}% — {self.usage()} chars]\n══════════════════════════════════════════════\n"
        return head + (f"\n{SEP}\n".join(ents) if ents else "(empty)")


def memory() -> MemoryStore:
    return MemoryStore("memory")


def user_profile() -> MemoryStore:
    return MemoryStore("user")
