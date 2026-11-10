# Architecture — how fb-standards reaches a session

One marketplace, one plugin (`fb-standards`). Design goal: the fewest instructions that keep quality
up for a single developer. Process rules inform and never gate the workflow; security controls
(secrets, egress, data isolation) are enforced and never relaxed. General
techniques (brainstorming, TDD, debugging method) come from Claude Code and superpowers; this plugin adds
the project-specific roles, rules and guards.

| Part | Delivery |
|---|---|
| `rules/core.md` | SessionStart hook pins it verbatim (≤ 40 lines: project non-negotiables + working principles) |
| `rules/<topic>.md` | SessionStart hook indexes title + path; read on demand (`FB_STANDARDS_INJECT_FULL=1` inlines all) |
| `agents/*.md` | 9 role agents (`fb-standards:<name>`); pipeline in `rules/workflow.md`. Agent bodies hold only the role and method; the rules they need are declared in frontmatter `rules:` and injected by the SubagentStart hook — rule text is never copied into agents |
| `skills/*` | `new-commit` and `new-pr` (both run `scripts/scan-changes.sh`: secrets / forbidden files / dumps / large files in the staged diff or a commit range), `new-pr`, `review`, `django-feature` |
| MCP dependencies | `context7` (doc checks, core rule 5 — tools granted to architect, developer, tester, debugger, devops, reviewer, security-scanner) and `chrome-devtools-mcp` (`qa`); both enabled via the app's `.claude/settings.json` |

## Hooks

| Script | Event | Behaviour | On failure |
|---|---|---|---|
| `session-start-context.sh` | SessionStart | pin `core.md` + index topic rules | fail-open, visible warning |
| `subagent-start-context.sh` | SubagentStart | fb-standards agents: `core.md` + rules from their `rules:`; other subagents (Explore, Plan…): `core.md` + topic index. Must fit 10 000 chars — `validate.py` checks | fail-open, stderr warning |
| `user-prompt-secret-scan.sh` | UserPromptSubmit | cancel a prompt that contains a secret (`secret-patterns.txt`) before it reaches the model or transcript | fail-open (never locks the user out) |
| `pre-bash-secret-scan.sh` | PreToolUse Bash | block commands containing secrets (`secret-patterns.txt`) | fail-closed |
| `pre-bash-commit-scan.sh` | PreToolUse Bash | on any `git commit`: run `scripts/scan-changes.sh` on the staged diff (secrets, dumps, `.env`/keys, `.qa/`, files > 10 MB); refuse `git commit -a` | fail-closed when the scan cannot run |
| `pre-bash-git-push-guard.sh` | PreToolUse Bash | push only to `github.com/Moonkus/…` (exfiltration guard); refuse `--force`/`-f`/`--mirror`/`+refspec` anywhere in the push; `--force-with-lease` only off the default branch | pass-through without `jq` (secret-scan already blocks) |
| `pre-bash-sensitive-guard.py` | PreToolUse Bash | refuse commands naming a secret file (`cat .env`, `cp credentials.json …`; `.env.example` allowed) and network tools in command position anywhere (`/usr/bin/curl`, `env curl`, `xargs wget`, `ssh`…) — permission rules only match prefixes | python3 stdlib; quoted multi-word strings are prose, not paths |
| `pre-bash-git-safety-guard.py` | PreToolUse Bash | **ask** before `reset --hard`, `clean -f`, `checkout -- .`, `branch -D`…; refuse ref-less `stash pop/apply/drop`; plugin subagents get read-only git | python3 stdlib |
| `pre-file-secret-guard.sh` | PreToolUse Read\|Write\|Edit | refuse reading/writing `.env`, `.env.*` (except `.env.example`…), `*.pem`, `*.key`, `secrets/**`, `client_secret*.json`, `credentials.json`, `token.json`; scan written content for secrets | fail-closed |

Deliberately **not** hooks: formatting/linting (an auto-`ruff --fix` after each edit deletes imports Claude
adds one edit before using them — ruff runs in the quality gate instead) and file-size/dump checks (done
on the staged diff by `plugins/fb-standards/scripts/scan-changes.sh`, which also catches files changed outside Claude).

Hooks prevent accidents; they are not a security boundary. Scripts fall back to their own `dirname`
when `${CLAUDE_PLUGIN_ROOT}` is unset, so they run from a checkout:

```bash
plugins/fb-standards/hooks/session-start-context.sh </dev/null | jq -r .hookSpecificOutput.additionalContext
```

## Versioning

The version lives only in `plugins/fb-standards/.claude-plugin/plugin.json`; consumers get a new build
only when it changes. CI fails a PR that changes the plugin without a bump.
