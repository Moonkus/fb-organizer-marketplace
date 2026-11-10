---
name: django-feature
description: Scaffold a new Django app (domain) in fb-organizer. Use when starting a new domain or app — "new app", "add a domain", "create the feedback app", "створи новий app", "новий домен", "додай застосунок". Creates the app in the project's layout, wires it up, sets up visibility and its isolation test, and starts the domain's architecture doc.
---

# New Django app (domain)

Arguments (optional): `$ARGUMENTS` — the app name (singular, snake_case); if empty, ask for it.

## Steps

- [ ] App name from `$ARGUMENTS` (or ask) and one sentence on what it owns.
- [ ] Look at how existing apps are laid out (location, `apps.py`, URL wiring) and do the same. If this is
      the first app, create it with `manage.py startapp` and tell the user where it went.
- [ ] Keep the generated files minimal — no placeholder classes; add `services.py` / `tasks.py` only when
      there is logic or background work for them.
- [ ] Register it in `INSTALLED_APPS` and include its `urls.py` in the root URLconf.
- [ ] If it holds per-colleague data, set up visibility and its isolation test as core rule 1 and
      `${CLAUDE_PLUGIN_ROOT}/rules/django.md` require.
- [ ] Dispatch `fb-standards:docs-writer` to create `docs/architecture/<domain>.md` and its row in
      `docs/architecture/README.md`.
- [ ] Run `manage.py check` and the app's tests with the commands from the project `CLAUDE.md`.

## Gotchas

- **No Django project yet** (no `manage.py`): stop — the skeleton comes first (see "Status" in the project
  `CLAUDE.md`); don't create an app in an empty repo.
- **Custom user model before the first migration.** If this is the `accounts` app, set `AUTH_USER_MODEL`
  before running any `migrate` — switching later means rebuilding the database.
- **Commands not filled in yet** in the project `CLAUDE.md`: say which check you could not run instead of
  inventing a command (core rule 3).
