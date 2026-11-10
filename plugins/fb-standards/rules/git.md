# Git and GitHub

- Conventional commits: `<type>: <summary>` (`feat`, `fix`, `refactor`, `test`, `docs`, `chore`).
  Add `[FB-123]` (`feat[FB-123]: …`) only when a Notion task exists — never invent one.
- Small commits with one purpose; the body explains *why* when it is not obvious.
- Committing to `main` or using a feature branch + PR are both fine; open a PR when CI or a
  second look is wanted.
- `gh` for GitHub operations.
- Never commit DB dumps (`*.dump`, `*.sql.gz`, `backups/`) — they hold personal data — or files > 10 MB;
  the `new-commit` skill's scan catches both.
