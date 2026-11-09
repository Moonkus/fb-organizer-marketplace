# fb-organizer-marketplace

## What this is

A Claude Code plugin marketplace with one plugin — **`fb-standards`** — the harness for the
[fb-organizer](https://github.com/Moonkus/fb-organizer) feedback app
(Python 3.12 · Django 5 · HTMX · Tailwind+DaisyUI · PostgreSQL 16 · django-q2 · Google API · Docker+Caddy).
A marketplace is just this git repo plus `.claude-plugin/marketplace.json` — no service behind it.

Built for one developer: process rules never block, security controls are never relaxed. Working principles in
`core.md` (rule 7) are adapted from [andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills) (MIT).

## How to add it to Claude Code

Per machine:

```bash
claude plugin marketplace add Moonkus/fb-organizer-marketplace
claude plugin install fb-standards@fb-organizer-marketplace --scope user
```

Per repo (no manual steps for others — Claude Code offers the marketplace after the folder is trusted):
copy `extraKnownMarketplaces` and `enabledPlugins` from `plugins/fb-standards/templates/project-settings.json`
into the app's `.claude/settings.json`.

Things that bite:
- The key in `extraKnownMarketplaces` **must equal** `marketplace.json` `name` (`fb-organizer-marketplace`).
- The plugin has a `version`, so consumers get new content **only after a version bump**; auto-update for
  third-party marketplaces is off by default — run `claude plugin marketplace update fb-organizer-marketplace`
  or enable auto-update in `/plugin` → Marketplaces. New versions apply from the next session.
- Private repo → git auth is needed (`gh auth login` or SSH).
- Requires `jq`, `bash`, `python3` (3.9+). Depends on the official `context7` and `chrome-devtools-mcp`
  plugins (enabled by the app's settings); without them agents fall back to official docs / stop and report.

## Plugins

| Plugin | What it gives | Version |
|---|---|---|
| `fb-standards` | always-on core rules + 8 topic rules; 9 role agents with a pipeline; skills `new-commit`, `new-pr`, `review`, `django-feature`; guard hooks (secrets, sensitive commands, push egress/force, destructive git) | see `plugins/fb-standards/.claude-plugin/plugin.json`, history in [CHANGELOG.md](CHANGELOG.md) |

How it works: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Maintainers

- a.kharchuk (GitHub `@Moonkus`) — owner; review routing in [.github/CODEOWNERS](.github/CODEOWNERS).

## Contributing

[docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) — local loop, checks, the 4-criteria filter for new components,
semver and the release flow. Security issues: [SECURITY.md](SECURITY.md).

## Contacts

a.kharchuk@spd-ukraine.com — questions and access. Vulnerabilities: privately, as described in [SECURITY.md](SECURITY.md).
