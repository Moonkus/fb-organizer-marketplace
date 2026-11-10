"""Shared helpers for hook tests: run a hook script with a JSON payload on stdin."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PLUGIN = REPO / "plugins" / "fb-standards"
HOOKS = PLUGIN / "hooks"


def run_hook(script: str, payload: dict, env: dict | None = None,
             plugin_root: Path | None = None, cwd: str | None = None) -> subprocess.CompletedProcess:
    path = HOOKS / script
    cmd = ["python3", "-I", "-S", str(path)] if script.endswith(".py") else [str(path)]
    full_env = {**os.environ, "CLAUDE_PLUGIN_ROOT": str(plugin_root or PLUGIN), **(env or {})}
    full_env.pop("CLAUDE_PROJECT_DIR", None)
    return subprocess.run(cmd, input=json.dumps(payload), capture_output=True, text=True,
                          env=full_env, cwd=cwd, timeout=60)


def bash(command: str, cwd: str | None = None, **extra) -> dict:
    payload = {"tool_name": "Bash", "tool_input": {"command": command}, **extra}
    if cwd:
        payload["cwd"] = cwd
    return payload


def write(file_path: str, content: str = "") -> dict:
    return {"tool_name": "Write", "tool_input": {"file_path": file_path, "content": content}}


def decision(proc: subprocess.CompletedProcess) -> str | None:
    """permissionDecision from a JSON-emitting hook, or None when it printed nothing."""
    out = proc.stdout.strip()
    if not out:
        return None
    return json.loads(out)["hookSpecificOutput"]["permissionDecision"]


def git(*args: str, cwd: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


def make_repo(origin_url: str, branch: str = "main") -> tempfile.TemporaryDirectory:
    """A throwaway repo with one commit, an `origin` remote, on `branch`."""
    tmp = tempfile.TemporaryDirectory()
    d = tmp.name
    git("init", "-q", "-b", "main", cwd=d)
    git("config", "user.email", "t@example.com", cwd=d)
    git("config", "user.name", "t", cwd=d)
    git("config", "commit.gpgsign", "false", cwd=d)
    Path(d, "README").write_text("x\n")
    git("add", "README", cwd=d)
    git("commit", "-q", "-m", "init", cwd=d)
    git("remote", "add", "origin", origin_url, cwd=d)
    if branch != "main":
        git("checkout", "-q", "-b", branch, cwd=d)
    return tmp
