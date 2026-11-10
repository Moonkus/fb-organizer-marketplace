#!/usr/bin/env bash
# fb-standards — SessionStart hook.
# A plugin's rules/ are not auto-loaded in a consumer repo, so this hook delivers them:
# rules/core.md verbatim + an index of the other rules (path + `# title`) to read on demand.
# FB_STANDARDS_INJECT_FULL=1 inlines every rule instead of indexing.
# Fails open (never blocks a session) but visibly: stderr + in-context warning.
set -uo pipefail

root="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
rules="$root/rules"

if ! command -v jq >/dev/null 2>&1; then
  echo 'fb-standards SessionStart: jq not found — rules were NOT injected. Install jq.' >&2
  exit 0
fi

emit() { jq -n --arg ctx "$1" '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $ctx}}'; }

if [ ! -s "$rules/core.md" ]; then
  echo 'fb-standards SessionStart: rules/core.md missing — rules were NOT injected.' >&2
  emit "⚠️ fb-standards rules were NOT injected (rules/core.md missing) — check the plugin install."
  exit 0
fi

topics=""
for f in "$rules"/*.md; do
  [ "$(basename "$f")" = "core.md" ] && continue
  if [ "${FB_STANDARDS_INJECT_FULL:-0}" = "1" ]; then
    topics+=$'\n'"$(cat "$f")"$'\n'
  else
    topics+="- $(grep -m1 '^# ' "$f" | sed 's/^# *//') → $f"$'\n'
  fi
done

emit "# fb-standards — fb-organizer (Django 5 · HTMX · Tailwind/DaisyUI · PostgreSQL · django-q2 · Google API)

$(cat "$rules/core.md")

## Topic rules — read the matching file before working in that area

$topics
Agents and pipelines: see the workflow rule above. Skills: \`fb-standards:new-commit\`, \`fb-standards:new-pr\`, \`fb-standards:review\`, \`fb-standards:django-feature\`."
