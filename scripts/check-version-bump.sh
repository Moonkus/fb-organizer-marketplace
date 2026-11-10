#!/usr/bin/env bash
# Fails when files under plugins/fb-standards/ changed relative to <base> but the
# version in plugin.json did not go up. Consumers only pick up a new plugin build
# when the version changes, so an un-bumped change never ships.
#
# Usage: scripts/check-version-bump.sh [base]   (default: origin/main)
#   before a push / in a PR:  base = origin/main
#   in CI on push to main:    base = the commit before the push
set -euo pipefail

base="${1:-origin/main}"
manifest="plugins/fb-standards/.claude-plugin/plugin.json"
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if ! git rev-parse --verify --quiet "$base^{commit}" >/dev/null; then
  echo "version-bump: base '$base' not found — skipping (first push?)"
  exit 0
fi

# compare against the fork point, so commits that landed on <base> meanwhile do not count
fork="$(git merge-base "$base" HEAD)"
changed="$(git diff --name-only "$fork" HEAD -- plugins/fb-standards/)"
if [ -z "$changed" ]; then
  echo "version-bump: no plugin changes"
  exit 0
fi

old="$(git show "$fork:$manifest" 2>/dev/null | jq -r '.version // empty' || true)"
new="$(jq -r '.version' "$manifest")"
if [ -z "$old" ]; then
  echo "version-bump: no previous version — $new OK"
  exit 0
fi
if [ "$old" = "$new" ]; then
  echo "version-bump: plugins/fb-standards changed but version is still $new — bump $manifest. Changed:"
  printf '  %s\n' "$changed"
  exit 1
fi
highest="$(printf '%s\n%s\n' "$old" "$new" | sort -V | tail -1)"
if [ "$highest" != "$new" ]; then
  echo "version-bump: version went down ($old -> $new)"
  exit 1
fi
if ! grep -Eq "^## \[$(printf '%s' "$new" | sed 's/\./\\./g')\]" CHANGELOG.md 2>/dev/null; then
  echo "version-bump: $new has no '## [$new]' entry in CHANGELOG.md"
  exit 1
fi
echo "version-bump: $old -> $new OK"
