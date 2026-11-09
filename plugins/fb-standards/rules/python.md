# Python — language practices (3.12+)

Code must pass the project's formatter, linter and type checker (from the project `CLAUDE.md`; until they
exist, write for `ruff`, line length 100, and `mypy` with `django-stubs`).

## Types and data
- Type hints on every signature, modern syntax (`list[str]`, `X | None`, `type` aliases). No `Any` for
  structured data — `dataclass` (`frozen=True`, `slots=True` where it fits), `TypedDict`, `TextChoices`.
- Datetimes are timezone-aware: `django.utils.timezone.now()`, never `datetime.now()`/`utcnow()`.

## Errors
- Catch specific exceptions; never bare `except:` or a silent `except Exception: pass`.
- `raise NewError(...) from exc`; `logger.exception(...)` where an error is handled.
- Small domain exceptions for expected failures (e.g. `GoogleConnectionExpired`), not `None`/`False`
  returns. `assert` is not validation (it disappears with `-O`).

## Code shape
- No mutable default arguments; no DB, network or settings-dependent work at import time.
- `logger = logging.getLogger(__name__)`, no `print`; lazy logging args (`logger.info("sent %s", event_id)`).
- No `import *`; no circular imports between apps.
- Docstrings only where name and types don't explain the behaviour: one summary line, at most two more.

## Safety
- Never `eval`/`exec`, `pickle`/`marshal` on untrusted data, `yaml.load` (use `safe_load`),
  `subprocess` with `shell=True`, or string-built SQL.
- Tokens and random IDs from `secrets`; compare secrets with `hmac.compare_digest`.
- Dependencies (core rule 4) are pinned in the lock file; never `pip install` ad hoc into the environment.
