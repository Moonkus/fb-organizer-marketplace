# Testing — what to test and how

Use the test command from the project `CLAUDE.md` (default tooling: `pytest` + `pytest-django`).

- Tests run against PostgreSQL, not SQLite.
- Unit tests for model/queryset methods and service functions; view tests through the Django test client.
  Browser (e2e) tests only for key HTMX flows, if and when they are set up.
- Google clients are faked — tests never touch the network; freeze time for reminder/scheduling logic.
- One behaviour per test, named for it (`test_colleague_cannot_open_others_feedback`); arrange–act–assert.
- Factories/fixtures instead of copy-pasted setup; `parametrize` for input variants; fakes over mocks.
- No `sleep`, no dependence on test order or wall-clock time.
- Assert outcomes (status code, DB state, `mail.outbox`), not implementation details.
- Never change production code just to make a test pass.
