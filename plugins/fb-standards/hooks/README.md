# Hooks

Wired by `hooks.json`. Behaviour, failure modes and path resolution: [`docs/ARCHITECTURE.md`](../../../docs/ARCHITECTURE.md#hooks).
Each guard documents its known residuals in its header. Tests: `tests/hooks/` at the repo root.

Prerequisites on every machine: `jq` (guards fail closed without it), `bash`, `python3` 3.9+.
