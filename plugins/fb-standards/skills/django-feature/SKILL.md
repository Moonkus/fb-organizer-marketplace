---
name: django-feature
description: Use when starting a new domain/app in fb-organizer — creates the Django app in the project's layout, wires it up, sets up visibility and its isolation test, and starts the domain's architecture doc.
---

# New Django app (domain)

1. Get the app name (singular, snake_case) and one sentence on what it owns.
2. Look at how existing apps are laid out (location, `apps.py`, URL wiring) and do the same. If this is
   the first app, create it with `manage.py startapp` and tell the user where it went.
3. Keep the generated files minimal — no placeholder classes; add `services.py` / `tasks.py` only when
   there is logic or background work for them.
4. Register it in `INSTALLED_APPS` and include its `urls.py` in the root URLconf.
5. If it holds per-colleague data, set up visibility and its isolation test as core rule 1 and
   `${CLAUDE_PLUGIN_ROOT}/rules/django.md` require.
6. Dispatch `fb-standards:docs-writer` to create `docs/architecture/<domain>.md` and its row in
   `docs/architecture/README.md`.
7. Run `manage.py check` and the app's tests with the commands from the project `CLAUDE.md`.
