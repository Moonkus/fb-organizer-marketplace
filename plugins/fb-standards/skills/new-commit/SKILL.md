---
name: new-commit
description: Use when the user asks to commit in fb-organizer — scans the staged diff for secrets, dumps, forbidden and large files, checks it has one purpose, drafts the message and commits after approval.
---

# New commit

1. Stage explicit paths only (never `git add -A` / `git add .`). Show `git diff --cached --stat`.
2. Run `bash "${CLAUDE_PLUGIN_ROOT}/scripts/scan-changes.sh"` from the repo root.
   Exit 1 (findings) or 2 (could not scan): **stop** — unstage the offending files or remove the secret.
   If a real secret was ever written to disk, tell the user to rotate it.
3. Read `git diff --cached`. If it mixes unrelated purposes, propose a split (paths per commit) and let
   the user choose. Point out leftover debug code.
4. Draft the message in the format of `${CLAUDE_PLUGIN_ROOT}/rules/git.md`.
5. Show it; commit only after the user agrees. Never `--no-verify`.
