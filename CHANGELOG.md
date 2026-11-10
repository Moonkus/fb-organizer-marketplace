# Changelog — fb-standards

All notable changes to the `fb-standards` plugin. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [Semantic Versioning](https://semver.org/). Each release lists **Breaking** first — anything a
consumer must change (renamed agent/skill, removed rule, stricter guard, new required plugin) is breaking and
bumps MAJOR.

## [Unreleased]

## [0.1.0] - 2026-11-09

### Added
- Rules: `core` (always on) + `workflow`, `python`, `django`, `frontend`, `security`, `testing`, `git`, `deployment`.
- Agents: `architect`, `developer`, `tester`, `qa`, `debugger`, `security-scanner`, `reviewer`, `docs-writer`, `devops`.
- Skills: `new-commit`, `new-pr`, `review`, `django-feature`.
- Hooks: SessionStart and SubagentStart rule injection; secret scan, sensitive-command guard, git push guard
  (egress + force), git safety guard, secret-file guard (Read/Write/Edit).
- `scripts/scan-changes.sh` — staged/range scan for secrets, dumps, forbidden and large files.
- Skills: trigger phrases in English and Ukrainian, `$ARGUMENTS`, checklists and Gotchas from real use.
- Skill trigger evals (`evals/`, 20 cases) — `claude plugin eval`; optional CI step.
- Hooks: commit gate (`pre-bash-commit-scan.sh` — staged scan on every `git commit`, `-a` refused) and
  prompt secret filter (`user-prompt-secret-scan.sh`, UserPromptSubmit).
