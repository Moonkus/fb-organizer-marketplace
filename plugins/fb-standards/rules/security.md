# Security — tokens, auth, egress, production settings

Security controls (secret guards, egress limits, permission denies) are not loosened for convenience.

- `.env.example` lists every variable with placeholders only; real values live in the server's `.env`.
- OAuth refresh tokens: encrypted model field (`cryptography` Fernet, key from env; `MultiFernet` for rotation).
- Google SSO (allauth, phase 2): link an existing account by email only when Google reports
  `email_verified`.
- Templates autoescape; raw SQL only with parameters.
- Password reset and login never reveal whether an account exists.
- Production: `manage.py check --deploy` is clean; `SECURE_PROXY_SSL_HEADER` behind Caddy; secure
  cookies and HSTS; admin not mounted at `/admin/`; login is rate-limited.
- No network tools from the agent (`curl`, `wget`, `ssh`, `scp`, `rsync`, `nc`… — hook-enforced anywhere in
  a command) and no shell access to secret files (`cat .env` — hook-enforced). Check local HTTP through
  the Django test client or a short Python snippet against `localhost` only.
- Git pushes go only to `github.com/Moonkus/…` (hook-enforced).
- CSV/XLSX exports escape formula prefixes (`= + - @`).
- Audit dependencies for known vulnerabilities (`pip-audit`) when they change and before every release.
