# Plugin conventions

- **Minimum that works.** Add a rule only when its absence produced a real mistake. Prefer a tool
  (ruff, mypy, a test, a hook) over prose. Never duplicate what Claude Code or superpowers already do.
- **Help, don't gate — except security.** One developer: process rules never block normal work.
  Security controls (secret guards, egress limits, permission denies, security review) are the
  exception: they are never loosened for convenience.
- **Rules** (`plugins/fb-standards/rules/`): `# Title` on line 1 (the index uses it), imperative bullets,
  ≤ 80 lines. `core.md` is in every session — ≤ 40 lines, true non-negotiables only.
- **Agents**: frontmatter `name` (= file name), `description`, `tools` (minimum), `model`, and `rules:`
  (topic rules the SubagentStart hook injects with `core.md`). The body holds only the role, method and
  output format — never copy rule text into an agent; add or fix it in `rules/` once.
- **One source of truth**: each instruction lives in exactly one rule file; agents and skills reference it.
- **Skills**: `skills/<name>/SKILL.md`, `name` (= directory), `description` starting "Use when …".
- **Hooks**: `${CLAUDE_PLUGIN_ROOT}` with `dirname` fallback; guards exit 2 with an explanation;
  test first in `tests/hooks/`; never put a literal secret in a test.
- Content is in English. Task IDs (`FB-123`) are always optional. Bump `plugin.json` `version` on any plugin change.
