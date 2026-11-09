# Security policy

Plugins run with the user's own permissions — there is no sandbox, and Anthropic does not review third-party
marketplaces. A bad hook (for example a `PreToolUse` matcher that quietly calls the network) runs on every
machine that installs `fb-standards`, so security issues here are treated as top priority.

## Reporting a vulnerability

- Do **not** open a public issue. Use GitHub's private vulnerability reporting on this repository
  (Security → Report a vulnerability) or contact the maintainer listed in [README.md](README.md).
- Include: affected file(s) and version (`plugins/fb-standards/.claude-plugin/plugin.json`), what an attacker or
  a careless command can do, and steps to reproduce.
- Expect an acknowledgement within 2 working days and a fix or mitigation plan within 7.

## In scope

- Hooks and scripts that execute on users' machines (`plugins/fb-standards/hooks/`, `plugins/fb-standards/scripts/`):
  bypasses of the secret, egress, push or git-safety guards; anything that reads secrets or sends data out.
- Agent/skill instructions that could make Claude leak secrets or personal data, or weaken the app's data isolation.
- Templates copied into consumer repos (`plugins/fb-standards/templates/`), e.g. permission rules that allow too much.

## If a secret leaked

Rotate it first (assume it is already exposed), then remove it from the history and add a regression case to
`plugins/fb-standards/hooks/secret-patterns.txt` and `tests/hooks/`.
