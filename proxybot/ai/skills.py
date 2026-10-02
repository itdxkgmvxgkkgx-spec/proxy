"""Skills — Hermes-style procedural memory with progressive disclosure.

    data/skills/<name>/SKILL.md          (frontmatter + body, required)
    data/skills/<name>/references/*.md   (loaded on demand)

Level 0: skills_list()        -> name + description (cheap, in system prompt)
Level 1: skill_view(name)     -> full SKILL.md
Level 2: skill_view(name, path) -> a reference file

Agent-created skills go through `skill_manage` (create / patch / delete /
write_file). A security scan rejects dangerous content exactly like memory.
Bundled skills live in proxybot/ai/bundled_skills and are seeded on first run.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from ..core.config import SKILLS_DIR
from .memory import _INJECTION, _INVISIBLE

BUNDLED = Path(__file__).parent / "bundled_skills"
_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9\-_]{1,60}$")


def _frontmatter(text: str) -> tuple[dict, str]:
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta, m.group(2)


def seed_bundled() -> int:
    n = 0
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    if BUNDLED.exists():
        for d in BUNDLED.iterdir():
            if d.is_dir() and (d / "SKILL.md").exists() and not (SKILLS_DIR / d.name).exists():
                shutil.copytree(d, SKILLS_DIR / d.name)
                n += 1
    return n


def skills_list() -> list[dict]:
    out = []
    if not SKILLS_DIR.exists():
        return out
    for d in sorted(SKILLS_DIR.iterdir()):
        f = d / "SKILL.md"
        if d.is_dir() and f.exists():
            meta, _ = _frontmatter(f.read_text(encoding="utf-8", errors="ignore"))
            out.append({"name": d.name, "description": meta.get("description", "")[:120],
                        "version": meta.get("version", ""), "files": sorted(p.name for p in (d / "references").glob("*")) if (d / "references").exists() else []})
    return out


def skill_view(name: str, path: str | None = None) -> str:
    d = SKILLS_DIR / name
    if not d.is_dir():
        return f"error: skill '{name}' not found"
    target = d / "SKILL.md" if not path else (d / path)
    try:
        target = target.resolve()
        if not str(target).startswith(str(d.resolve())):
            return "error: path escapes skill directory"
        if not target.exists():
            return f"error: file '{path}' not found in skill '{name}'"
        return target.read_text(encoding="utf-8", errors="ignore")[:20000]
    except OSError as e:
        return f"error: {e}"


def _scan(content: str) -> str | None:
    if _INVISIBLE.search(content):
        return "content contains invisible unicode"
    if _INJECTION.search(content):
        return "content matches a dangerous pattern (injection / credential exfil)"
    return None


def skill_manage(action: str, name: str, content: str = "", old_string: str = "", new_string: str = "",
                 file_path: str = "", file_content: str = "", description: str = "") -> str:
    if not _NAME_RE.match(name or ""):
        return "error: name must be lowercase letters, digits, - or _ (2-60 chars)"
    d = SKILLS_DIR / name
    if action == "create":
        if d.exists():
            return f"error: skill '{name}' exists — use patch"
        if not content.strip():
            return "error: content required"
        bad = _scan(content)
        if bad:
            return "error: " + bad
        if not content.startswith("---"):
            content = f"---\nname: {name}\ndescription: {description or name}\nversion: 1.0.0\n---\n" + content
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(content, encoding="utf-8")
        return f"created skill '{name}'"
    if not d.exists():
        return f"error: skill '{name}' not found"
    if action == "patch":
        f = d / "SKILL.md"
        text = f.read_text(encoding="utf-8")
        if content:
            new = content
        else:
            if not old_string or old_string not in text:
                return "error: old_string not found in SKILL.md"
            if text.count(old_string) > 1:
                return "error: old_string is not unique"
            new = text.replace(old_string, new_string, 1)
        bad = _scan(new)
        if bad:
            return "error: " + bad
        f.write_text(new, encoding="utf-8")
        return f"patched skill '{name}'"
    if action == "delete":
        shutil.rmtree(d)
        return f"deleted skill '{name}'"
    if action == "write_file":
        if not file_path or ".." in file_path or file_path.startswith("/"):
            return "error: file_path must be a relative path like references/notes.md"
        bad = _scan(file_content)
        if bad:
            return "error: " + bad
        p = d / file_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(file_content, encoding="utf-8")
        return f"wrote {file_path} in skill '{name}'"
    if action == "remove_file":
        p = d / file_path
        if ".." in file_path or not p.exists():
            return "error: file not found"
        p.unlink()
        return f"removed {file_path} from skill '{name}'"
    return f"error: unknown action '{action}'"


def skills_index_block() -> str:
    items = skills_list()
    if not items:
        return "## Skills\n(none yet — create one with skill_manage when you work out a reusable procedure)"
    lines = ["## Skills (load with skill_view(name) before relying on one)"]
    for s in items:
        lines.append(f"- {s['name']}: {s['description']}")
    return "\n".join(lines)
