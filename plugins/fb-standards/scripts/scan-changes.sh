#!/usr/bin/env bash
# Scans changes for secrets, forbidden files, database dumps and large files.
#   scan-changes.sh            → the staged changes (before a commit)
#   scan-changes.sh <base>     → everything <base>...HEAD adds (before a PR / push), e.g. origin/main
# The PreToolUse hooks only see command text and content Claude writes itself;
# files changed outside Claude (or generated) are only caught here.
# Exit 0 = clean, 1 = findings (printed), 2 = could not scan (treat as a block).
set -uo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
patterns="$here/../hooks/secret-patterns.txt"
[ -r "$patterns" ] || { echo "scan-changes: pattern file missing ($patterns)" >&2; exit 2; }
git rev-parse --git-dir >/dev/null 2>&1 || { echo "scan-changes: not a git repository" >&2; exit 2; }

if [ $# -gt 0 ]; then
  git rev-parse --verify --quiet "$1" >/dev/null || { echo "scan-changes: unknown base '$1'" >&2; exit 2; }
  range=("$1...HEAD")
else
  range=(--cached)
fi
found=0

# 1. Forbidden paths
while IFS= read -r f; do
  [ -n "$f" ] || continue
  base="$(basename "$f")"
  case "$base" in
    .env.example|.env.sample|.env.template) ;;
    .env|.env.*|*.pem|*.key|client_secret*.json|credentials.json|token.json)
      echo "FORBIDDEN FILE: $f"; found=1 ;;
    # database dumps carry personal data (feedback) — never in git, whatever their size
    *.dump|*.sql.gz|*.sql.zst|*.backup|*.bak)
      echo "DATABASE DUMP: $f"; found=1 ;;
  esac
  case "$f" in
    secrets/*|*/secrets/*) echo "FORBIDDEN FILE: $f"; found=1 ;;
    backups/*|*/backups/*) echo "DATABASE DUMP: $f"; found=1 ;;
    .qa/*) echo "QA ARTIFACT (screenshots may hold personal data): $f"; found=1 ;;
  esac
done < <(git diff "${range[@]}" --name-only --diff-filter=ACMR)

# 2. Large files (> 10 MB)
while IFS= read -r f; do
  if [ "${range[0]}" = --cached ]; then
    size=$(git cat-file -s ":$f" 2>/dev/null || echo 0)
  else
    size=$(git cat-file -s "HEAD:$f" 2>/dev/null || echo 0)
  fi
  [ "$size" -gt $((10 * 1024 * 1024)) ] && { echo "LARGE FILE: $f ($((size / 1048576)) MB)"; found=1; }
done < <(git diff "${range[@]}" --name-only --diff-filter=ACMR)

# 3. Secret patterns in added lines
added="$(git diff "${range[@]}" --unified=0 --no-color | grep -E '^\+' | grep -vE '^\+\+\+ ' || true)"
if [ -n "$added" ]; then
  while IFS= read -r entry; do
    case "$entry" in ''|\#*) continue ;; esac
    name="${entry%%|*}"; regex="${entry#*|}"
    if grep -Eq -- "$regex" <<< "$added"; then
      echo "SECRET PATTERN: $name"; found=1
    fi
  done < "$patterns"
fi

if [ "$found" = 0 ]; then echo "scan-changes: clean"; fi
exit "$found"
