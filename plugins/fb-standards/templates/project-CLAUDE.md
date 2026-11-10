# fb-organizer

Internal feedback app: a manager leaves feedback for colleagues, creates Google Calendar events and
sends emails on their behalf; colleagues log in separately and see only their own feedback history;
CSV/XLSX export. The company is on Google Workspace **without Workspace admin rights**. Deployed to our
own server with Docker. General rules come from the **fb-standards** plugin; this file holds what is
specific to this repo.

## Stack — the source of stack decisions (core rule 4)

| Layer | Choice | Notes |
|---|---|---|
| Language / framework | Python 3.12+, Django 5.x | server-rendered, no SPA, no separate API |
| UI | Django templates + HTMX + Tailwind CSS + DaisyUI | interactivity without a separate frontend |
| Manager's cabinet | Django Admin | CRUD for feedback, colleagues, accounts |
| Database | PostgreSQL 16 | |
| Auth, stage 1 | `django.contrib.auth` (login/password) | manager creates accounts; password reset by email |
| Auth, stage 2 | django-allauth + Google SSO | later; existing accounts are linked by email |
| Roles | Django Groups `manager`, `colleague` | a colleague sees only their own feedback |
| Calendar | Google Calendar API (`google-api-python-client`, `google-auth-oauthlib`) | user's own OAuth, scope `calendar.events` |
| Mail | Gmail API (`gmail.send`) or SMTP via `django.core.mail` | sent on the manager's behalf |
| Background tasks | django-q2, broker = the same PostgreSQL | reminders, delayed sending |
| Export | django-import-export + openpyxl | CSV, XLSX |
| Secrets | django-environ + `.env`; `cryptography` (Fernet) | OAuth refresh tokens stored encrypted |
| App server / proxy | gunicorn / Caddy | automatic TLS |
| Deploy | Docker + docker-compose: `web`, `worker` (django-q2 `qcluster`), `db`, `caddy` | backups with `pg_dump` |

**Google without admin rights:** no service account or domain-wide delegation — each user connects their
own calendar and mail via OAuth ("Connect Google"). Own Google Cloud project with a Web OAuth client,
Calendar and Gmail APIs enabled. Consent screen **Internal** if the organisation allows it, otherwise
**External + Testing** (refresh tokens live 7 days — users must reconnect). Fallback without the API:
an `.ics` invitation by plain email. Scopes: `openid email profile`, `calendar.events`, `gmail.send`.

**Agreed from the start:** user email is unique and required (for Google SSO later); all configuration
comes from environment variables, only `.env.example` is in the repo.

## Status

The Django project does not exist yet. When the skeleton is created, fill in the commands below and keep
this file the single place agents take commands from.

## Commands

> TODO: fill in when the skeleton exists. Proposed tooling (to be agreed and added to the Stack table):
> `uv` for dependencies, `ruff` (lint + format), `mypy` + `django-stubs`, `pytest` + `pytest-django`, `pip-audit`.

| Task | Command |
|---|---|
| Dev server | TODO |
| Tests | TODO |
| Lint / format | TODO |
| Type check | TODO |
| Migrations | `python manage.py makemigrations --check --dry-run` and `python manage.py migrate` (via the project env) |
| Dependency audit | TODO |
| Deploy check | `python manage.py check --deploy` with production settings |

## Checks before calling work done

Lint/format, type check, migrations check + `migrate`, tests for the touched area. When dependencies
changed: dependency audit. When a change hits a security trigger (core rule 2 of fb-standards): the
`fb-standards:security-scanner` agent.

## Where things are

- Architecture map: `docs/architecture/README.md`; one `docs/architecture/<domain>.md` per domain.
- Plans: `docs/plans/YYYY-MM-DD-<feature>.md`. Tasks (optional): Notion, IDs `FB-123`.
- `harness/` — local, gitignored symlink to `../fb-organizer-marketplace` (the fb-standards plugin source).
  Harness changes go there and ship via a version bump; the app never depends on the symlink.
