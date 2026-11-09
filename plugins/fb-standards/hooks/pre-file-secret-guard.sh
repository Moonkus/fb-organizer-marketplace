#!/usr/bin/env bash
# fb-standards — PreToolUse hook for Read|Write|Edit
# Two layers of defence:
#   1. PATH guard — refuses reading or writing protected secret paths (.env, .env.*,
#      *.pem, *.key, secrets/**, client_secret*.json, credentials.json, token.json).
#      Placeholder env files (.env.example etc.) are allowed — permission rules cannot
#      express that exception, which is why this hook owns the .env.* policy.
#   2. CONTENT guard — scans the content being written for real secrets, so an
#      allowed file (e.g. .env.example) can never carry a live key. Uses the same
#      single-source pattern list as pre-bash-secret-scan.sh.
# managed-settings.json also denies the protected paths via permissions.deny;
# this hook makes the refusal visible and adds the content check.
#
# Reference: rules/security.md
set -euo pipefail

input="$(cat)"

# jq is a hard prerequisite — fail closed (block) if missing rather than
# fall back to a brittle sed parse that could miss a protected path/secret.
if ! command -v jq >/dev/null 2>&1; then
  echo "🛑 fb-standards secret-file guard: jq not found — failing closed. Install jq." >&2
  exit 2
fi
path="$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty')"

[ -z "$path" ] && exit 0

# ---- Layer 1: path guard ----------------------------------------------------
basename="$(basename "$path")"

matched_pattern=""
case "$basename" in
  # Placeholder/template env files are allowed by path — the content guard
  # below still blocks any real secret pasted into them.
  .env.example|.env.sample|.env.template|.env.dist) matched_pattern="" ;;
  .env|.env.*)         matched_pattern=".env*" ;;
  *.pem)               matched_pattern="*.pem" ;;
  *.key)               matched_pattern="*.key" ;;
  # Google OAuth client secret downloaded from Cloud Console (both names Google's docs use),
  # and the token file the Google quickstart writes
  client_secret*.json) matched_pattern="client_secret*.json" ;;
  credentials.json)    matched_pattern="credentials.json" ;;
  token.json)          matched_pattern="token.json" ;;
esac

case "$path" in
  */secrets/*|secrets/*) matched_pattern="secrets/**" ;;
esac

if [ -n "$matched_pattern" ]; then
  {
    echo "==============================="
    echo "🛑 fb-standards secret-file guard: BLOCKED (path)"
    echo "==============================="
    echo "Refused to read or write: $path"
    echo "Pattern: $matched_pattern"
    echo
    echo "Per fb-standards hard rules (security.md), these paths are off-limits:"
    echo "  - .env*               — environment files (configure via django-environ)"
    echo "  - *.pem/*.key         — private keys (never in git)"
    echo "  - secrets/**          — anything in a secrets directory"
    echo "  - client_secret*.json, credentials.json — Google OAuth client secret"
    echo "  - token.json          — stored OAuth tokens (keep them Fernet-encrypted in the DB)"
    echo
    echo "To document required variables, use .env.example with placeholder"
    echo "values only (e.g. API_KEY=replace-me), never real credentials."
  } >&2
  exit 2
fi

# ---- Layer 2: content guard (writes only) -----------------------------------
[ "$(printf '%s' "$input" | jq -r '.tool_name // empty')" = "Read" ] && exit 0
# Scan the new content (Write -> content, Edit -> new_string) for live secrets,
# so an allowed file such as .env.example cannot smuggle a real key.
content="$(printf '%s' "$input" | jq -r '.tool_input.content // .tool_input.new_string // empty')"

[ -z "$content" ] && exit 0

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
patterns_file="$script_dir/secret-patterns.txt"
if [ ! -r "$patterns_file" ]; then
  echo "🛑 fb-standards secret-file guard: pattern file missing ($patterns_file) — failing closed." >&2
  exit 2
fi

# One pass over every pattern (2 processes), not one grep per pattern. The
# per-pattern loop below runs only on the block path, to name what matched.
regexes="$(sed -nE '/^[^#][^|]*[|]/{s/^[^|]*[|]//;p;}' "$patterns_file")"
[ -n "$regexes" ] || { echo "🛑 fb-standards secret scanner: pattern file has no patterns — failing closed." >&2; exit 2; }
# The subject goes through a here-string (a file), never a pipe: under pipefail a
# `grep -q` that stops early would SIGPIPE the writer and the pipeline would read
# as "no match". Exit status: 0 match, 1 none, anything else is a grep error and
# fails closed.
set +e
grep -E -q -f <(printf '%s\n' "$regexes") <<< "$content"
rc=$?
set -e
case "$rc" in
  1) exit 0 ;;
  0) : ;;
  *) echo "🛑 fb-standards secret scanner: grep failed (status $rc) — failing closed." >&2; exit 2 ;;
esac

while IFS= read -r entry; do
  case "$entry" in ''|\#*) continue ;; esac
  name="${entry%%|*}"
  regex="${entry#*|}"
  if grep -E -q -- "$regex" <<< "$content"; then
    {
      echo "==============================="
      echo "🛑 fb-standards secret-file guard: BLOCKED (content)"
      echo "==============================="
      echo "File: $path"
      echo "Pattern matched: $name"
      echo
      echo "The content contains what looks like a real credential. Even in an"
      echo "example/template file, use obvious placeholders (e.g. <your-key>,"
      echo "replace-me) — never a live key. If this is real, rotate it now."
    } >&2
    exit 2
  fi
done < "$patterns_file"

exit 0
