---
name: bug-fixing
description: How to investigate and fix a bug in this project safely, with tests
version: 1.0.0
---
# Bug fixing workflow

## Procedure
1. Reproduce: `read_file` the module, `db_query` relevant rows, `read_logs(level="ERROR")`.
2. If unsure about a library/protocol, `web_search` + `web_extract` the docs.
3. Make the smallest change with `patch_file` (unique old_string). Explain the change in one line.
4. Verify: `run_shell("python -m pytest tests -q")` and, for pipeline bugs, `test_proxy_link` on a live proxy.
5. `git_commit("fix: <what>")` — the user decides when to push/redeploy; tell them the fix is live after the next run.
6. Record the pitfall in the relevant skill (`skill_manage patch`) so it is not repeated.

## Pitfalls
- Every write/shell action needs user approval; batch related edits before asking.
- Don't rewrite whole files when a patch suffices (patch keeps the diff reviewable in Telegram).
