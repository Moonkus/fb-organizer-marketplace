#!/usr/bin/env bash
# fb-standards — UserPromptSubmit hook.
# Blocks a prompt that contains a secret (hooks/secret-patterns.txt) before it reaches the model or the
# transcript: exit 2 cancels the prompt and shows the reason to the user only.
# Fails OPEN (exit 0) when it cannot scan — a missing jq must not lock the user out of the session.
set -uo pipefail

input="$(cat)"
command -v jq >/dev/null 2>&1 || exit 0
prompt="$(printf '%s' "$input" | jq -r '.prompt // empty')"
[ -n "$prompt" ] || exit 0

patterns="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/secret-patterns.txt"
[ -r "$patterns" ] || exit 0

while IFS= read -r entry; do
  case "$entry" in ''|\#*) continue ;; esac
  name="${entry%%|*}"; regex="${entry#*|}"
  if grep -Eq -- "$regex" <<< "$prompt"; then
    {
      echo "🛑 fb-standards: your message was NOT sent — it contains what looks like a secret ($name)."
      echo "Remove or mask it (e.g. GOCSPX-****) and send again. If it is real, rotate it — it was on your clipboard."
    } >&2
    exit 2
  fi
done < "$patterns"
exit 0
