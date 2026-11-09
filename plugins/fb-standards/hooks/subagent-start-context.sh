#!/usr/bin/env bash
# fb-standards — SubagentStart hook.
# Subagents do not see the SessionStart injection, so this hook gives each one the rules it needs:
#   - fb-standards agents: rules/core.md + every rule named in the agent's frontmatter `rules:` list
#     (e.g. `rules: python, django, frontend`) — one source of truth, nothing copied into agent bodies;
#   - any other subagent (Explore, Plan, general-purpose…): rules/core.md + the index of topic rules.
# Claude Code caps additionalContext at 10 000 characters; scripts/validate.py checks every agent fits.
# Fails open (never blocks a subagent) but visibly on stderr.
set -uo pipefail

root="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
rules="$root/rules"
input="$(cat)"

if ! command -v jq >/dev/null 2>&1; then
  echo 'fb-standards SubagentStart: jq not found — rules were NOT injected.' >&2
  exit 0
fi
if [ ! -s "$rules/core.md" ]; then
  echo 'fb-standards SubagentStart: rules/core.md missing — rules were NOT injected.' >&2
  exit 0
fi

agent="$(printf '%s' "$input" | jq -r '.agent_type // .agent_name // .subagent_type // empty' 2>/dev/null)"
name="${agent##*:}"           # "fb-standards:developer" → "developer"
plugin="${agent%%:*}"
agent_file="$root/agents/$name.md"

ctx="# fb-standards rules for this subagent

$(cat "$rules/core.md")"

if [ "$plugin" = "fb-standards" ] && [ "$name" != "$agent" ] && [ -f "$agent_file" ]; then
  wanted="$(awk 'NR==1 && $0=="---" {fm=1; next} fm && $0=="---" {exit} fm && /^rules:/ {sub(/^rules:[[:space:]]*/, ""); print}' "$agent_file")"
  IFS=',' read -r -a list <<< "$wanted"
  for r in "${list[@]}"; do
    r="$(printf '%s' "$r" | tr -d '[:space:]')"
    [ -n "$r" ] || continue
    if [ -f "$rules/$r.md" ]; then
      ctx+=$'\n\n---\n\n'"$(cat "$rules/$r.md")"
    else
      echo "fb-standards SubagentStart: agent $name lists unknown rule '$r'." >&2
    fi
  done
else
  index=""
  for f in "$rules"/*.md; do
    [ "$(basename "$f")" = "core.md" ] && continue
    index+="- $(grep -m1 '^# ' "$f" | sed 's/^# *//') → $f"$'\n'
  done
  ctx+=$'\n\n'"## Topic rules — read the matching file before working in that area"$'\n\n'"$index"
fi

jq -n --arg ctx "$ctx" '{hookSpecificOutput: {hookEventName: "SubagentStart", additionalContext: $ctx}}'
