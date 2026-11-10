# fb-standards

Project rules, guard hooks and a review agent for the fb-organizer Django/HTMX app.

```bash
claude plugin marketplace add Moonkus/fb-organizer-marketplace
claude plugin install fb-standards@fb-organizer-marketplace --scope user
```

| Path | Contents |
|---|---|
| `rules/` | `core.md` (every session) + `workflow`, `python`, `django`, `frontend`, `security`, `testing`, `git`, `deployment` (on demand) |
| `agents/` | `architect`, `developer`, `tester`, `qa`, `debugger`, `security-scanner`, `reviewer`, `docs-writer`, `devops` — pipeline in `rules/workflow.md` |
| `skills/` | `new-commit` (staged secret scan + commit), `new-pr`, `review` (reviewer + security-scanner), `django-feature` |
| `hooks/` | rule injection for the session and for every subagent, secret guards (commands + written files), git push egress guard, destructive-git guard |
| `templates/` | `.claude/settings.json`, `CLAUDE.md`, docs map for the app repo |

How it works: [`../../docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md).
