#!/usr/bin/env bash
# fb-standards — PreToolUse hook for Bash
# Reads JSON from stdin, scans tool_input.command for hardcoded secrets,
# exits 2 (block) with stderr message if matched.
#
# Reference: rules/security.md
set -euo pipefail

input="$(cat)"

# jq is a hard prerequisite. A sed fallback cannot reliably unescape
# multi-line / quoted command JSON and would silently under-match secrets,
# so fail closed (block) when jq is missing rather than degrade.
if ! command -v jq >/dev/null 2>&1; then
  echo "🛑 fb-standards secret scanner: jq not found — failing closed. Install jq." >&2
  exit 2
fi
cmd="$(printf '%s' "$input" | jq -r '.tool_input.command // empty')"

[ -z "$cmd" ] && exit 0

# Canonical patterns live in secret-patterns.txt (shared with the write guard).
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
patterns_file="$script_dir/secret-patterns.txt"
if [ ! -r "$patterns_file" ]; then
  echo "🛑 fb-standards secret scanner: pattern file missing ($patterns_file) — failing closed." >&2
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
grep -E -q -f <(printf '%s\n' "$regexes") <<< "$cmd"
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
  if grep -E -q -- "$regex" <<< "$cmd"; then
    {
      echo "==============================="
      echo "🛑 fb-standards secret scanner: BLOCKED"
      echo "==============================="
      echo "Pattern matched: $name"
      echo
      echo "Bash command was refused because it contains what looks like a"
      echo "hardcoded secret. Per fb-standards hard rules (security.md), credentials"
      echo "must never appear in shell commands."
      echo
      echo "If this is a false positive, investigate and rephrase the command."
      echo "If it's real, rotate the credential — assume it's already exposed."
    } >&2
    exit 2
  fi
done < "$patterns_file"

exit 0
