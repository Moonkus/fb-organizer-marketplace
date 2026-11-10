# Django — structure, conventions, admin, tasks, Google integrations

Follow the structure the code already has; where nothing exists yet, use the conventions below.

## Structure
- Apps per domain (e.g. `accounts`, `feedback`, `integrations`), each with the usual `models.py`, `views.py`, `forms.py`, `admin.py`, `urls.py`, `templates/<app>/`, `tests/`.
- Keep views thin: multi-step logic and side effects (email, calendar, background tasks) go into plain
  functions in the app (e.g. `services.py`), not into views or templates. Multi-step writes run in
  `transaction.atomic`; side effects that must not happen on rollback go through `transaction.on_commit`.
- Data visibility (core rule 1) is a custom QuerySet/Manager method, e.g. `Feedback.objects.for_user(user)`;
  views, admin, exports and tasks all go through it.

## Users and roles
- Custom user model from the first migration; email required and unique case-insensitively
  (`UniqueConstraint(Lower("email"), …)`, stored normalised) — Google SSO links accounts by email later.
- Roles are Django Groups `manager` and `colleague`; managers are `is_staff` and get admin permissions
  through the group, not as superusers. Stage 1 auth: `django.contrib.auth` login/password,
  accounts created by the manager, password reset by email. Stage 2: django-allauth + Google SSO.

## Conventions
- `ModelForm` for validation; `TextChoices`; explicit `on_delete`; constraints/indexes in `Meta`; `__str__`.
- Avoid N+1 with `select_related` / `prefetch_related`.
- `USE_TZ=True`.

## Migrations
- Reversible; `RunPython` always has `reverse_code`; data migrations separate from schema migrations.
- Backward-compatible with the previous release (add → migrate → remove later), so rolling back the
  image works without rolling back the database.

## Admin (the manager's cabinet)
- CRUD for feedback, colleagues and accounts; access through the `manager` group.
- CSV/XLSX export via `django-import-export` (+ `openpyxl`); exports respect the same visibility rules.

## Background tasks (django-q2, PostgreSQL/ORM broker)
- Reminders and delayed sending run as tasks; Google API calls only in tasks, never in the request cycle.
- Tasks are idempotent and set retry/timeout. django-q2 needs `manage.py qcluster` running next to `web`.

## Google Calendar and Gmail (per-user OAuth — setup in the project `CLAUDE.md`)
- Each user connects their own account ("Connect Google"); `google-auth-oauthlib` flow with `state` + PKCE,
  redirect URI from env; API calls via `google-api-python-client`. Scopes: `openid email profile`,
  `calendar.events` (read + create events), `gmail.send` — nothing more.
- All Google API access goes through one wrapper in the `integrations` app, so tests use fakes.
- Consent screen may be External + Testing: refresh tokens then expire after 7 days. Treat
  `invalid_grant` as "connection expired" — mark it, ask the user to reconnect; 429 → back off.
- Mail is sent on the manager's behalf through a `django.core.mail` backend, so Gmail API and SMTP are
  interchangeable;
  fallback without Calendar API: an `.ics` invitation sent by email.
