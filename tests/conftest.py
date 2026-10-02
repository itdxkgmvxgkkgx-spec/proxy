import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("BOT_TOKEN", "123:TEST")
os.environ.setdefault("ADMIN_ID", "1000")


@pytest.fixture()
def db(tmp_path, monkeypatch):
    from proxybot.core import database
    from proxybot.ai import memory, skills
    monkeypatch.setattr(memory, "FILES", {"memory": tmp_path / "MEMORY.md", "user": tmp_path / "USER.md"})
    monkeypatch.setattr(skills, "SKILLS_DIR", tmp_path / "skills")
    d = database.reset_db_for_tests(tmp_path / "test.db")
    d.ensure_owner(1000)
    yield d
