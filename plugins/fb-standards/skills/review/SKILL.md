---
name: review
description: Use when the user asks to review the current fb-organizer changes — runs the reviewer agent and, when a security trigger applies, the security-scanner agent in parallel, then merges findings by severity.
---

# Review

1. Scope: `git diff main...HEAD` plus uncommitted changes, or what the user named. List the changed paths.
2. Dispatch in parallel, passing the scope and the changed paths (the agents get their rules automatically):
   - `fb-standards:reviewer` — always;
   - `fb-standards:security-scanner` — when the change hits a security trigger (core rule 2).
3. Merge the findings into one list: Critical → Important → Minor, de-duplicated, each with `file:line`.
   Critical security findings block the change until fixed.
4. Offer to fix; after fixes, re-run only the agent(s) that reported them.
