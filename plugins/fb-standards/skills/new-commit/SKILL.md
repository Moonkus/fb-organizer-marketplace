---
name: new-commit
description: Commit changes safely. Use whenever the user asks to commit or save work to git — "commit", "commit this", "make a commit", "закоміть", "зроби коміт", "закомітити зміни" — and before any `git commit`. Scans the staged diff for secrets, dumps, forbidden and large files, checks the commit has one purpose, drafts a conventional message and commits after approval.
---

# New commit

Arguments (optional): `$ARGUMENTS` — paths to stage; if empty, propose the paths from `git status`.

## Steps

- [ ] Stage explicit paths only (never `git add -A` / `git add .`). Show `git diff --cached --stat`.
- [ ] Run `bash "${CLAUDE_PLUGIN_ROOT}/scripts/scan-changes.sh"` from the repo root.
      Exit 1 (findings) or 2 (could not scan): **stop** — unstage the offending files or remove the secret.
      If a real secret was ever written to disk, tell the user to rotate it.
- [ ] Read `git diff --cached`. If it mixes unrelated purposes, propose a split (paths per commit) and let
      the user choose. Point out leftover debug code.
- [ ] Draft the message in the format of `${CLAUDE_PLUGIN_ROOT}/rules/git.md`.
- [ ] Show it; commit only after the user agrees. Never `--no-verify`.

## Gotchas

- **A hook re-checks every commit.** `pre-bash-commit-scan.sh` runs the same scan on any `git commit` and
  refuses `git commit -a` — stage explicit paths first.
- **Plan mode blocks commits.** If the session is in plan mode, say so and stop — the user leaves plan mode.
- **Run the scan from the repo root.** Elsewhere it exits 2 ("not a git repository" / wrong paths).
- **Plugin repo (`fb-organizer-marketplace`).** A change under `plugins/` needs a higher `version` in
  `plugins/fb-standards/.claude-plugin/plugin.json` *and* a `## [x.y.z]` entry in `CHANGELOG.md`, or CI fails.
- **Empty repo (no commits yet).** `git mv` does nothing useful there — move files with plain `mv`, then stage.
