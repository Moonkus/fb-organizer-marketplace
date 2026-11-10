#!/usr/bin/env python3
"""fb-standards — PreToolUse(Bash) guard for secret files and network egress.

Permission rules match commands by PREFIX only (`Bash(curl:*)` misses `/usr/bin/curl`, `env curl`,
`xargs curl`) and Read/Edit denies do not cover shell reads (`cat .env`). This hook closes both:

  1. SECRET FILES — refuses a command that names a protected file as a word: `.env`, `.env.*` (except
     `.env.example/.sample/.template/.dist`), `*.pem`, `*.key`, `client_secret*.json`, `credentials.json`,
     `token.json`, or anything under a `secrets/` directory. Words inside a quoted multi-word string
     (a commit message, an echo of prose) are not file references.
  2. EGRESS — refuses network tools in command position anywhere in the command: curl, wget, nc/ncat/
     netcat, scp, sftp, rsync, ssh, telnet, ftp — also behind wrappers (env, xargs, sudo, command, exec,
     nohup, time, timeout N, nice) and absolute paths. Git pushes are checked by the push guard.

Accident prevention, not a security boundary: an interpreter one-liner (`python -c "urllib…"`) or a
script file is not inspected — rules/security.md allows Python snippets only against localhost.
Exit 2 + stderr = block; exit 0 = allow. Stdlib only; run with `python3 -I -S`.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import sys

EGRESS = {"curl", "wget", "nc", "ncat", "netcat", "scp", "sftp", "rsync", "ssh", "telnet", "ftp"}
WRAPPERS = {"env", "xargs", "sudo", "command", "exec", "nohup", "time", "nice", "timeout", "then", "do",
            "else", "if", "while", "until", "!", "{"}
ENV_OK = {".env.example", ".env.sample", ".env.template", ".env.dist"}
SEPARATORS = {";", "&", "&&", "|", "||", "(", ")", "\n", "`", "$("}
MAX_PARSE = 64 * 1024


def block(reason: str) -> None:
    print("===============================", file=sys.stderr)
    print("🛑 fb-standards sensitive-command guard: BLOCKED", file=sys.stderr)
    print("===============================", file=sys.stderr)
    print(reason, file=sys.stderr)
    sys.exit(2)


def protected(word: str) -> str | None:
    """The protected pattern a single shell word names, or None."""
    word = word.strip().rstrip(",;")
    if not word or " " in word:          # a quoted multi-word string is prose, not a path
        return None
    word = word.split("=", 1)[1] if word.startswith("--") and "=" in word else word
    parts = word.replace("\\", "/").split("/")
    base = parts[-1]
    if "secrets" in parts[:-1] or (base == "secrets" and word.endswith("/")):
        return "secrets/**"
    if base in ENV_OK:
        return None
    if base == ".env" or base.startswith(".env."):
        return ".env*"
    if base.endswith(".pem"):
        return "*.pem"
    if base.endswith(".key") and len(base) > 4:
        return "*.key"
    if re.fullmatch(r"client_secret.*\.json", base):
        return "client_secret*.json"
    if base in ("credentials.json", "token.json"):
        return base
    return None


def words(cmd: str) -> list[str]:
    cmd = cmd.replace("$(", " $( ").replace("`", " ` ")
    lex = shlex.shlex(cmd, posix=True, punctuation_chars=";&|()\n")
    lex.whitespace = " \t\r"
    lex.whitespace_split = True
    return list(lex)


def command_heads(tokens: list[str]) -> list[str]:
    """The command word of each simple command, past assignments and wrappers."""
    heads, expect = [], True
    skip_value = False
    for tok in tokens:
        if tok in SEPARATORS or (tok and set(tok) <= set(";&|()\n")):
            expect = True
            continue
        if not expect:
            continue
        if skip_value:                   # the duration after `timeout`, the value after `nice -n`
            skip_value = False
            continue
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tok) or tok in WRAPPERS:
            skip_value = tok == "timeout"
            continue
        if tok.startswith("-"):          # wrapper options (`env -i`, `nice -n 5`, `xargs -0`)
            skip_value = tok in ("-n", "-u", "-s", "-k", "-I", "-P", "-L")
            continue
        heads.append(os.path.basename(tok))
        expect = False
    return heads


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        sys.exit(0)
    cmd = ((payload or {}).get("tool_input") or {}).get("command")
    if not isinstance(cmd, str) or not cmd.strip():
        sys.exit(0)
    cmd = cmd[:MAX_PARSE].replace("\\\n", " ")

    try:
        tokens = words(cmd)
    except ValueError:                   # unbalanced quotes: fall back to a plain-text scan
        tokens = re.split(r"[\s;&|()<>`'\"]+", cmd)

    for tok in tokens:
        hit = protected(tok)
        if hit:
            block(f"The command names a protected secret file ({hit}): {tok}\n"
                  "Secret files are never read, copied or printed by the agent (core rule 2). "
                  "Configuration is read by the app through django-environ; to document a variable, "
                  "edit .env.example with placeholders. If the user needs this, they can run it with `! <command>`.")

    for head in command_heads(tokens):
        if head in EGRESS:
            block(f"`{head}` is a network tool; outbound connections from the agent are refused "
                  "(core rule 2, rules/security.md). Check local HTTP through the Django test client or a "
                  "short Python snippet against localhost; library docs come from context7. If the user "
                  "needs this, they can run it with `! <command>`.")
    sys.exit(0)


if __name__ == "__main__":
    main()
