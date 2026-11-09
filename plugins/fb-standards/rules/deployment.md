# Deployment — Docker Compose, Caddy, backups

- Own server, Docker + docker-compose: `web` (gunicorn), `db` (postgres:16 + volume), `caddy` (automatic TLS).
  django-q2 also needs `manage.py qcluster` running — a second service from the same image.
- Image: slim Python 3.12, non-root user, no secrets baked in; config only via env. Dependencies pinned in a
  lock file.
- Caddy terminates HTTPS and sets security headers; Django trusts it via `SECURE_PROXY_SSL_HEADER`.
- The release step runs `migrate` and `collectstatic`; services have healthchecks.
- CI (GitHub Actions) runs the checks from the project `CLAUDE.md` with a PostgreSQL service, plus a
  dependency audit.
- Backups via `pg_dump` on a schedule; restore one now and then to prove they work.
- Rollback = previous image (migrations are backward-compatible — see the Django rule).
