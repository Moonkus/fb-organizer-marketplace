# Workflow — agents, pipeline, orchestration

The main session orchestrates. Agents give each role a clean context and an independent view; use the
stages a change needs and skip the ones that add nothing. **Exception:** `security-scanner` is mandatory
for any change hitting a security trigger (core rule 2).

## Agents (`fb-standards:<name>`)

| Agent | Use for |
|---|---|
| `architect` | non-trivial/unclear request or model/integration change → acceptance criteria, risk flags, contract, stages to run |
| `developer` | implementation end to end — Django layers, templates, HTMX, Tailwind/DaisyUI |
| `tester` | `recon` before work · `red` for bugs · `cover` after work; always isolation tests |
| `qa` | browser walk-through + visual check of changed pages — mandatory when templates, CSS or page-rendering views change |
| `debugger` | root cause of a bug/failure — before any fix |
| `security-scanner` | security review (see exception above) |
| `reviewer` | independent code review before merge |
| `docs-writer` | `docs/architecture/**` after a domain changes |
| `devops` | Docker, compose, Caddy, CI, dependencies, backups |

## Pipelines

- **Feature:** `architect` → [`tester` recon] → `developer`
  → checks (core rule 3, main session) → `tester` cover ‖ `docs-writer` ‖ `qa` (if UI) ‖ [`security-scanner`]
  → `reviewer` → skills `new-commit` / `new-pr` (main session).
- **Bug:** `debugger` → `tester` red → `developer` → checks → `tester` (whole area) → `reviewer`.
- **Small change** (one file, no model change): main session + checks; `reviewer` optional. A security
  trigger still requires `security-scanner`.
- **Large/new domain:** write a plan in `docs/plans/YYYY-MM-DD-<feature>.md` first; skill `django-feature` for scaffolding.
- Critical/Important findings from `reviewer`/`security-scanner` → back to the earliest affected stage.

## Orchestration

- Subagents get rules from the SubagentStart hook: fb-standards agents receive `core.md` + the rules in
  their `rules:` frontmatter; other subagents (Explore, Plan…) receive `core.md` + the topic index.
  Pass the task and the relevant file paths in the prompt.
- Agents are draft-only — commits, pushes and PRs happen in the main session after the user agrees.
- Parallel only on disjoint files: never `developer` and `tester` on the same files at once; `tester` and
  `qa` not at the same time (they share the dev database).
- Before `qa`: make sure the dev server is running (start it if needed, tell the user) and pass its URL plus
  test accounts with sample data (a manager and two colleagues who each have feedback); do not restart a
  server the user started.
