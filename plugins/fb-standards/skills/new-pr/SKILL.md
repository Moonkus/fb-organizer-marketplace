---
name: new-pr
description: Use when the user wants a pull request for the current fb-organizer branch — checks the branch is committed, scanned and synced, runs the security review when needed, drafts the PR and creates it after approval.
---

# New pull request

1. The branch is not `main` and the working tree is clean (otherwise offer `fb-standards:new-commit`).
2. `git fetch origin`; if `git log --oneline HEAD..origin/main` is not empty, offer `git rebase origin/main`.
3. Scan everything the PR adds: `bash "${CLAUDE_PLUGIN_ROOT}/scripts/scan-changes.sh" origin/main`.
   Exit 1 or 2 → stop. If a secret was committed, tell the user to rotate it and propose how to remove it
   from the branch history — rewrite history only with their explicit agreement.
4. If the change hits a security trigger (core rule 2) and `fb-standards:security-scanner` has not reviewed
   it yet, run it now; Critical findings stop the PR.
5. From `git log origin/main..HEAD` and `git diff origin/main...HEAD --stat`: if the diff exceeds ~500 changed
   lines or mixes unrelated work, suggest a split.
6. Draft the PR:
   - **Title** in the commit format of `${CLAUDE_PLUGIN_ROOT}/rules/git.md`;
   - **What and why** (2–5 bullets) · **How verified** (commands, tests, manual checks) ·
     **Risks / rollback** · **Task** link only if one exists.
7. After the user agrees: `git push -u origin <branch>`, then
   `gh pr create --base main --title "…" --body-file <tmp file>`.
