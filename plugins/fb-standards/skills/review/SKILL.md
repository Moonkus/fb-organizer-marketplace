---
name: review
description: Review code changes. Use whenever the user asks to review, check or audit changes before merging — "review this", "review my changes", "check the diff", "зроби рев'ю", "переглянь зміни", "перевір код". Runs the reviewer agent and, when a security trigger applies, the security-scanner agent in parallel, then merges findings by severity.
---

# Review

Arguments (optional): `$ARGUMENTS` — scope (paths, a commit range or a PR number); if empty, the current changes.

## Steps

- [ ] Scope: `$ARGUMENTS` if given; otherwise `git diff main...HEAD` plus uncommitted changes. List the changed paths.
- [ ] Dispatch in parallel, passing the scope and the changed paths (the agents get their rules automatically):
      `fb-standards:reviewer` — always; `fb-standards:security-scanner` — when the change hits a security
      trigger (core rule 2).
- [ ] Merge the findings into one list: Critical → Important → Minor, de-duplicated, each with `file:line`.
      Critical security findings block the change until fixed.
- [ ] Offer to fix; after fixes, re-run only the agent(s) that reported them.

## Gotchas

- **No `main` yet** (fresh repo): review `git diff HEAD` and the staged diff instead of `main...HEAD`.
- **Agents without rules.** Rules reach agents via the SubagentStart hook; in a session started before the
  plugin was installed or updated, run `/reload-plugins` first.
- **Verify before reporting.** A finding the agent could not confirm is labelled as unverified, not dropped
  and not overstated.
