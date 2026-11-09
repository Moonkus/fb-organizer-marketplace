---
name: new-pr
description: Open a pull request safely. Use whenever the user asks for a PR or to push work for review — "create a PR", "open a pull request", "push and make a PR", "створи PR", "зроби пул-реквест", "запуш і створи PR". Checks the branch is committed, scanned and synced, runs the security review when needed, drafts the PR and creates it after approval.
---

# New pull request

Arguments (optional): `$ARGUMENTS` — base branch (default `main`).

## Steps

- [ ] The branch is not the base and the working tree is clean (otherwise run `fb-standards:new-commit`).
- [ ] `git fetch origin`; if `git log --oneline HEAD..origin/<base>` is not empty, offer `git rebase origin/<base>`.
- [ ] Scan everything the PR adds: `bash "${CLAUDE_PLUGIN_ROOT}/scripts/scan-changes.sh" origin/<base>`.
      Exit 1 or 2 → stop. If a secret was committed, tell the user to rotate it and propose how to remove it
      from the branch history — rewrite history only with their explicit agreement.
- [ ] If the change hits a security trigger (core rule 2) and `fb-standards:security-scanner` has not reviewed
      it yet, run it now; Critical findings stop the PR.
- [ ] From `git log origin/<base>..HEAD` and `git diff origin/<base>...HEAD --stat`: if the diff exceeds ~500
      changed lines or mixes unrelated work, suggest a split.
- [ ] Draft the PR — **Title** in the commit format of `${CLAUDE_PLUGIN_ROOT}/rules/git.md`; **What and why**
      (2–5 bullets) · **How verified** (commands, tests, manual checks — numbers you actually saw) ·
      **Risks / rollback** · **Task** link only if one exists. In the plugin repo use its PR template.
- [ ] After the user agrees: `git push -u origin <branch>`, then
      `gh pr create --base <base> --title "…" --body-file <tmp file>`.
- [ ] Watch CI: `gh pr checks <n> --watch` (or `gh run watch <id>`); report the result.

## Gotchas

- **Empty remote repo.** A PR needs a base: commit `.gitignore` alone to `main`, push `main`, then branch.
- **`gh` missing** → the user runs `brew install gh`. **No credentials** (`could not read Username for
  'https://github.com'`) → the user runs `gh auth login` in a regular terminal (inside Claude Code's `!` the
  one-time device code is not shown): GitHub.com → HTTPS → "Authenticate Git" = Yes. Never handle the code.
- **Push guard.** Pushes go only to `github.com/Moonkus/…`; `--force` is refused — after a rebase of your own
  branch use `--force-with-lease`.
- **Numbers in the description.** Quote counts (tests, files) from command output, not from memory.
