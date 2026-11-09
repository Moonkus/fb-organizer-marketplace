# Core rules — always apply

1. **Data isolation.** A colleague sees and changes only their own feedback.
   - Visibility is defined once per model (a QuerySet/Manager method), never ad hoc in views or templates.
   - Fetch with `get_object_or_404(<scoped qs>, pk=...)`; someone else's object → 404, not 403.
   - Check ownership before any side effect (email, calendar event, background task).
   - Every visibility rule has a test: colleague A cannot see or change B's data.
2. **Security is never relaxed or deferred** — not for speed, not because one person works on it.
   - Config only from env (`django-environ`); never read or write `.env` / `.env.*` or key files
     (`.env.example` with placeholders is the exception).
   - No secrets in code, commands, fixtures or commits; never log secrets, tokens or feedback content.
     OAuth tokens are stored encrypted.
   - No outbound network except through the app's integration clients; personal data
     (feedback, emails) never goes to external services.
   - **Security triggers** — auth/login, roles or visibility, views/admin/exports, Google/OAuth code,
     settings, dependencies, templates rendering user input. A change hitting any of them gets the
     `fb-standards:security-scanner` agent before it is called done; Critical findings block it.
3. **Done means verified.** Before calling work done, run the checks from the project `CLAUDE.md`
   for the touched area; migrations are applied with `migrate`, not just generated.
   If a check could not run, say so instead of claiming success.
4. **Stay within the stack.** The Stack section of the project `CLAUDE.md` is the source of stack decisions: a library, layer or
   tool it does not mention needs the user's agreement first. If `docs/architecture/<domain>.md` exists,
   read it before changing that domain and update it in the same change.
5. **Check decisions against current docs.** Verify every design/implementation choice that relies on a
   library (Django, HTMX, DaisyUI, django-q2, allauth, Google clients…) in context7 (`resolve-library-id`
   → `query-docs`), not from memory; without context7, use the official docs. Name the source checked.
6. **Git hygiene.** Commit through skill `fb-standards:new-commit` (it scans the staged diff for
   secrets and dumps). Stage explicit paths (no `git add -A`); no `--force` push (only `--force-with-lease` on your own
   feature branch after a rebase), no `--no-verify`;
   destructive git (`reset --hard`, `clean -f`) only when the user asks.
7. **How to work** (bias to care over speed; for trivial tasks use judgment):
   - *Think first.* State assumptions; if a request has several readings or something is unclear, ask —
     don't pick silently. Say so when a simpler approach exists.
   - *Simplicity.* Minimum code that solves the task: no unrequested features, single-use abstractions,
     speculative configurability or handling of impossible cases. Reuse an existing helper first.
   - *Surgical changes.* Touch only what the task needs and match the existing style; don't reformat or
     refactor unrelated code; mention dead code instead of deleting it; remove only what your change
     orphaned. Every changed line traces to the request.
   - *Goal-driven.* Turn the task into checks that prove it (bug → failing test first, feature → tests for
     it); for multi-step work state a short plan with a verify step each, and loop until they pass.
