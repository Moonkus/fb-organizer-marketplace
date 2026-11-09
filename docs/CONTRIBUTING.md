# Contributing to fb-standards

Writing conventions: [`.claude/rules/plugin-conventions.md`](../.claude/rules/plugin-conventions.md).

## Local loop

```bash
# use this checkout instead of GitHub
claude plugin marketplace remove fb-organizer-marketplace
claude plugin marketplace add /Users/shad0w/WorkSpace/AI-Enabler/fb-organizer-marketplace
claude plugin install fb-standards@fb-organizer-marketplace --scope user
# after a change: refresh, then start a new session in the app repo
claude plugin marketplace update fb-organizer-marketplace

# back to GitHub
claude plugin marketplace remove fb-organizer-marketplace
claude plugin marketplace add Moonkus/fb-organizer-marketplace
claude plugin install fb-standards@fb-organizer-marketplace --scope user
```

While the marketplace is unpublished, the app repo's `.claude/settings.json` only has `enabledPlugins`
(project settings override user settings, so a GitHub source there would shadow the local folder).
After the first push to GitHub, add the `extraKnownMarketplaces` block from `templates/project-settings.json`.

For browsing/editing the harness while working in the app, the app repo has a gitignored symlink:

```bash
cd /Users/shad0w/WorkSpace/AI-Enabler/fb-organizer && ln -sfn ../fb-organizer-marketplace harness
```

Edit files through `harness/` (or this repo), never in `~/.claude/plugins/cache/` — that copy is replaced on update.

## What belongs in the plugin — the 4-criteria filter

A new rule, agent, skill or hook goes in only if it meets **at least 2 of 4**:
1. **Pain is real** — the same problem hit us more than once (not a hypothetical).
2. **Standardize** — variation here is harmful (commit format, secret scan, review checklist).
3. **Capture knowledge** — it codifies something that would otherwise live only in someone's head.
4. **Safety guardrail** — executable code that blocks a dangerous action (only code can block; prose can't).

Meets only one → keep it as a personal tool in `~/.claude/`, not in the plugin.

## Checks

```bash
claude plugin validate . --strict && claude plugin validate plugins/fb-standards --strict
python3 scripts/validate.py
bash scripts/check-version-bump.sh origin/main   # before pushing plugin changes
python3 -m unittest discover -s tests/hooks
```

## Versioning (semver)

The version lives **only** in `plugins/fb-standards/.claude-plugin/plugin.json` — the docs say not to set it
in both manifests, and `plugin.json` wins anyway. Consumers get new content only when it changes.
- **MAJOR** — anything a consumer must react to: renamed/removed agent, skill or rule; a stricter guard that
  blocks something it used to allow; a new required plugin or tool. Until 1.0.0, breaking changes bump MINOR.
- **MINOR** — new agent/skill/rule/check that changes nothing existing.
- **PATCH** — fixes and wording.

## Release

1. Bump `version` in `plugin.json` (CI fails a plugin change without a bump — `scripts/check-version-bump.sh`).
2. Move `[Unreleased]` in `CHANGELOG.md` to `## [x.y.z] - YYYY-MM-DD`, `### Breaking` first if any.
3. Merge to `main` with green CI.
4. Tag from a clean `main`: `claude plugin tag plugins/fb-standards --push` (creates `fb-standards--vX.Y.Z`;
   `--dry-run` to preview).
5. Consumers: `claude plugin marketplace update fb-organizer-marketplace` (or auto-update) — applies from the
   next session.
