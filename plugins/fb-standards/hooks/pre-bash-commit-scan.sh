#!/usr/bin/env bash
# fb-standards — PreToolUse(Bash) gate for `git commit`.
# Runs scripts/scan-changes.sh on the staged diff before ANY commit the agent makes — not only when the
# new-commit skill is invoked (skills can fail to trigger; a hook cannot be skipped). Findings — secrets,
# DB dumps, .env/keys/credentials, QA artifacts, files > 10 MB — block the commit (exit 2).
#
# `git commit -a/--all` is refused: it stages tracked changes at commit time, past the scan and past
# explicit staging (core rule 6). Stage paths with `git add <path>` first.
# Fails CLOSED when the scan cannot run; passes through commands that are not a commit.
set -uo pipefail

root="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
input="$(cat)"
command -v jq >/dev/null 2>&1 || exit 0          # pre-bash-secret-scan.sh already blocks without jq
cmd="$(printf '%s' "$input" | jq -r '.tool_input.command // empty')"
cwd="$(printf '%s' "$input" | jq -r '.cwd // empty')"
[ -n "$cmd" ] || exit 0

# a real `git [-C <dir>] commit` at a command boundary (not prose inside a message)
commit_re='(^|[;&|(]|&&|\|\|)[[:space:]]*git([[:space:]]+-C[[:space:]]+[^[:space:]]+)*[[:space:]]+commit([[:space:]]|$)'
printf '%s' "$cmd" | grep -Eq "$commit_re" || exit 0

block() {
  {
    echo "==============================="
    echo "🛑 fb-standards commit gate: BLOCKED"
    echo "==============================="
    printf '%s\n' "$@"
  } >&2
  exit 2
}

seg="$(printf '%s' "$cmd" | grep -Eo 'git([[:space:]]+-C[[:space:]]+[^[:space:]]+)*[[:space:]]+commit[^;&|]*' | head -1)"
# options before the message (-m/-F/--message/--file) only — the message text itself is not parsed
set -f
for w in ${seg#*commit}; do
  case "$w" in
    -m|-m*|-F|-F*|--message|--message=*|--file|--file=*) break ;;
    --all) all=1 ;;
    --*) : ;;
    -*a*) all=1 ;;          # -a, -am, -sa …: short flags combined with a
  esac
  [ "${all:-0}" = 1 ] && break
done
set +f
if [ "${all:-0}" = 1 ]; then
  block "\`git commit -a\` stages tracked changes past the scan and past explicit staging (core rule 6)." \
    "Stage the paths you mean with \`git add <path>\`, then commit."
fi

dir="$cwd"
c_dir="$(printf '%s' "$seg" | sed -nE 's/^git[[:space:]]+-C[[:space:]]+([^[:space:]]+).*/\1/p')"
[ -n "$c_dir" ] && case "$c_dir" in /*) dir="$c_dir" ;; *) dir="${cwd:+$cwd/}$c_dir" ;; esac
[ -n "$dir" ] && [ -d "$dir" ] || dir="$(pwd)"
top="$(git -C "$dir" rev-parse --show-toplevel 2>/dev/null)" || exit 0   # not a repo: git itself will fail

out="$(cd "$top" && bash "$root/scripts/scan-changes.sh" 2>&1)"
case $? in
  0) exit 0 ;;
  1) block "The staged changes contain something that must not be committed:" "$out" "" \
       "Unstage it (\`git restore --staged <path>\`) or remove the secret. If a real secret was ever written to" \
       "disk, rotate it." ;;
  *) block "The pre-commit scan could not run — refusing the commit rather than skipping the check:" "$out" ;;
esac
