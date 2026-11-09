## What and why

<!-- What changed in the plugin and why. -->

## Release

- [ ] `version` bumped in `plugins/fb-standards/.claude-plugin/plugin.json` (MAJOR if anything is breaking)
- [ ] `CHANGELOG.md` entry for that version (`### Breaking` first, if any)

## Security checklist

Plugins run with the user's permissions on every machine that installs them. Tick or explain:

- [ ] Hooks: matchers are as narrow as possible; no network calls; guards fail closed; new/changed hooks have tests
- [ ] MCP: no new MCP server or MCP tool reference without a reason stated above
- [ ] Executables (`hooks/`, `scripts/`): no download-and-run, no `eval`, no unpinned remote code
- [ ] Env vars / secrets: nothing reads `.env*`, tokens or keys; no secret printed or logged
- [ ] Network: no new outbound calls; egress rules not loosened
- [ ] Dependencies: none added, or pinned and checked for known CVEs
- [ ] Templates: permission rules not widened (`templates/project-settings.json`)
- [ ] 4-criteria filter: new components meet ≥ 2 of 4 (see `docs/CONTRIBUTING.md`)

## How verified

<!-- validate.py, claude plugin validate --strict, unit tests, live check -->
