#!/usr/bin/env python3
"""fb-standards — PreToolUse(Bash) guard for git commands that destroy uncommitted work.

Policies (rules/git.md):

  1. STASH REF    `git stash pop|apply|drop|branch` with no explicit ref acts on whatever is on top —
                  possibly another session's or agent's WIP. Refused. With a ref, an entry recorded on another
                  branch is asked about: the ref is right only if the entry is yours.
  2. STASH PAIR   a stash that creates an entry and a later one that consumes it in the same command:
                  `git stash push` succeeds without creating anything on a clean tree, so whatever joins
                  them, the consume can take another session's entry. Refused — separate calls, check between.
  3. DISCARD      `reset --hard`, `checkout -- <paths>` / `checkout .` / `-f`, `switch -f`, a working-tree
                  `restore`, `clean -f`, `branch -D`, `stash clear`, `worktree remove -f` discard work that
                  exists nowhere else. The person is asked every time.
  4. DELEGATED    a subagent of a draft-only plugin (DRAFT_ONLY_PLUGINS) never changes repository state in a
                  shared tree: git is read-only for it, and it asks the session that dispatched it instead.
                  A subagent working in an isolated `.claude/worktrees/` tree owns that tree and is exempt.

A command that cannot be tokenised (an unmatched quote) and mentions one of the discard verbs is asked about
rather than guessed at. Anything else passes: the goal is to prevent accidents, not to be a security
boundary, so a command this hook does not understand to be one of the above is never blocked.

Read through: backslash-newline continuations, redirections (`2>&1`, `>/dev/null`), wrappers with arguments
(`timeout 10`, `env -i X=1`, `nice -n 5`, `sudo -u x`, `xargs -0`), `eval '<script>'`, `sh -c '<script>'`,
`$( … )` and backtick bodies, and a literal `cd <dir>` earlier in the command. Not followed (known limits):
aliases and shell functions, `cd` to a computed path, scripts in files.
"""
from __future__ import annotations

import json
from typing import Optional, TypedDict
import os
import re
import shlex
import shutil
import subprocess
import sys

DRAFT_ONLY_PLUGINS = {"fb-standards"}
ISOLATED_TREE = "/.claude/worktrees/"
MAX_PARSE = 64 * 1024
UNKNOWN_DIR = "$unknown"  # a directory the hook cannot resolve; never counts as the agent's isolated tree

STASH_CONSUME = {"pop", "apply", "drop", "branch"}
STASH_CREATE = {"push", "save", "store", ""}
STASH_ACTIONS = STASH_CONSUME | {"push", "save", "store", "list", "show", "clear", "create"}
STASH_REF = re.compile(r"^(stash@\{\d+\}|stash\^\{/.+\}|\d+|[0-9a-f]{7,40})$")
READ_ONLY = {
    "status", "diff", "log", "show", "blame", "ls-files", "ls-tree", "ls-remote", "rev-parse", "rev-list",
    "cat-file", "describe", "grep", "shortlog", "fetch", "merge-base", "name-rev", "for-each-ref", "show-ref",
    "symbolic-ref", "var", "help", "version", "check-ignore", "check-attr", "check-ref-format",
    "count-objects", "cherry", "range-diff", "show-branch", "whatchanged", "merge-tree", "archive",
}
# only flags that switch `git branch` into list mode; display options (-v, --color, --sort, --format, …) do not,
# and `git branch -v <name>` creates a branch (checked against git 2.54)
BRANCH_LISTING = {"-a", "--all", "-r", "--remotes", "--list", "-l", "--show-current", "--contains",
                  "--no-contains", "--merged", "--no-merged", "--points-at"}
BRANCH_VALUE_OPTS = {"--format", "--sort", "--column", "--contains", "--no-contains", "--merged", "--no-merged",
                     "--points-at"}
GIT_OPTS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--config-env"}
PREFIX_WORDS = {"command", "exec", "time", "nohup", "do", "then", "else", "elif", "if", "while", "until", "{",
                "}", "!"}
# wrappers that take options (and, for timeout, a duration) before the command they run
WRAPPER_VALUE_OPTS = {
    "env": {"-u", "--unset", "-C", "--chdir", "-S", "--split-string"},
    "timeout": {"-s", "--signal", "-k", "--kill-after"},
    "nice": {"-n", "--adjustment"},
    "sudo": {"-u", "-g", "-C", "-D", "-h", "-p", "-r", "-t", "-U"},
    "xargs": {"-I", "-n", "-P", "-L", "-s", "-E", "-d", "-a"},
}
SHELLS = {"sh", "bash", "zsh", "dash"}
DISCARD_VERBS = r"\bgit\b.*\b(stash|reset|checkout|switch|restore|clean|branch|worktree)\b"


class Payload(TypedDict, total=False):
    tool_name: str
    tool_input: dict
    cwd: str
    agent_id: str
    agent_type: str


def emit(decision: str, reason: str) -> None:
    if decision == "ask":
        reason += " Where nobody can answer this prompt, tell the person; they can run it with `! <command>`."
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": decision,
        "permissionDecisionReason": "fb-standards git-safety guard: " + reason,
    }}))
    sys.exit(0)


def unquoted(line: str, pos: int) -> bool:
    before = line[:pos]
    return before.count('"') % 2 == 0 and before.count("'") % 2 == 0


def strip_heredocs(cmd: str) -> str:
    """Drop heredoc bodies: text fed to a command is data, not a git invocation."""
    out, delims = [], []
    for line in cmd.split("\n"):
        if delims:
            if line.strip() == delims[0]:
                delims.pop(0)
            continue
        out.append(line)
        for m in re.finditer(r"(?<!<)<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1", line):
            if unquoted(line, m.start()):
                delims.append(m.group(2))
    return "\n".join(out)


def strip_redirections(cmd: str) -> str:
    """Drop unquoted redirections (`2>&1`, `>/dev/null`, `&>log`, `<in`) — they are not arguments. Heredoc
    operators (`<<`, `<<<`) stay."""
    out, i, n, single, double = [], 0, len(cmd), False, False
    while i < n:
        c = cmd[i]
        if c == "\\" and not single:
            out.append(cmd[i:i + 2])
            i += 2
            continue
        if c == "'" and not double:
            single = not single
        elif c == '"' and not single:
            double = not double
        if not single and not double:
            m = re.match(r"(\d*|&)(>>?|<)(?!<)(&\d+|&-)?", cmd[i:])
            prev = cmd[i - 1] if i else " "
            if m and m.group(2) and (m.group(1) or prev in " \t;|&(") and not cmd.startswith("<<", i) \
                    and not (cmd[i] == "<" and i and cmd[i - 1] == "<"):
                j = i + m.end()
                if not m.group(3):
                    while j < n and cmd[j] in " \t":
                        j += 1
                    while j < n and cmd[j] not in " \t\n;|&()<>":
                        j += 1
                out.append(" ")
                i = j
                continue
        out.append(c)
        i += 1
    return "".join(out)


def tokenize(cmd: str) -> list[str]:
    lex = shlex.shlex(cmd, posix=True, punctuation_chars=";&|()\n")
    lex.whitespace = " \t\r"
    lex.whitespace_split = True
    return list(lex)


def segments(tokens: list[str]) -> list[tuple[list[str], str]]:
    """Split into (words, separator-before) pairs."""
    segs, cur, sep = [], [], ""
    for tok in tokens:
        if tok and set(tok) <= set(";&|()\n"):
            # a newline after `&&` / `||` / `|` continues the list: it is layout, not a separator
            op = tok.replace("\n", "")
            if cur:
                segs.append((cur, sep))
                cur = []
                sep = op or "\n"
            elif op or not sep:
                sep = op or "\n"
            continue
        cur.append(tok)
    if cur:
        segs.append((cur, sep))
    return segs


def skip_prefix(words: list[str]) -> int:
    """Index of the command word, past assignments, reserved words and wrappers with their arguments."""
    i = 0
    while i < len(words):
        w = words[i]
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", w) or w in PREFIX_WORDS:
            i += 1
        elif os.path.basename(w) in WRAPPER_VALUE_OPTS:
            value_opts = WRAPPER_VALUE_OPTS[os.path.basename(w)]
            i += 1
            while i < len(words) and words[i].startswith("-") and words[i] != "--":
                i += 2 if words[i] in value_opts else 1
            if i < len(words) and words[i] == "--":
                i += 1
            if os.path.basename(w) == "timeout" and i < len(words):
                i += 1  # the duration
        else:
            break
    return i


def substitutions(cmd: str) -> list[str]:
    """Bodies of `$( … )` and backtick substitutions that the shell would execute (not inside single quotes)."""
    bodies, i, n, single, double = [], 0, len(cmd), False, False
    while i < n:
        c = cmd[i]
        if c == "\\" and not single:
            i += 2
            continue
        if c == "'" and not double:
            single = not single
        elif c == '"' and not single:
            double = not double
        elif not single and c == "`":
            j = cmd.find("`", i + 1)
            if j < 0:
                break
            bodies.append(cmd[i + 1:j])
            i = j
        elif not single and cmd.startswith("$(", i) and not cmd.startswith("$((", i):
            depth, j = 1, i + 2
            while j < n and depth:
                depth += {"(": 1, ")": -1}.get(cmd[j], 0)
                j += 1
            bodies.append(cmd[i + 2:j - 1])
            i = j - 1
        i += 1
    return bodies


def parse(cmd: str, depth: int = 0) -> list[tuple[list[str], str]]:
    """Segments of the command, with `sh -c '<script>'`, `eval`, `$( … )` and backtick scripts expanded."""
    out = []
    cmd = strip_heredocs(cmd.replace("\\\n", " "))
    if depth < 2:
        for inner in substitutions(cmd):
            out.extend(parse(inner, depth + 1))
    for words, sep in segments(tokenize(strip_redirections(cmd))):
        i = skip_prefix(words)
        script = None
        if depth < 2 and i < len(words) and words[i] == "eval":
            script = " ".join(words[i + 1:])
        elif depth < 2 and i < len(words) and os.path.basename(words[i]) in SHELLS:
            rest = words[i + 1:]
            for j, w in enumerate(rest[:-1]):
                if w.startswith("-") and not w.startswith("--") and "c" in w:
                    script = rest[j + 1]
                    break
        if script is None:
            out.append((words, sep))
            continue
        inner = parse(script, depth + 1)
        if inner:
            inner[0] = (inner[0][0], sep)
        out.extend(inner)
    return out


def git_call(words: list[str]) -> tuple[str, list[str], str | None] | None:
    """Return (subcommand, args, -C dir) when the segment runs git, else None."""
    i = skip_prefix(words)
    if i >= len(words) or not (words[i] == "git" or words[i].endswith("/git")):
        return None
    i += 1
    cdir = None
    while i < len(words) and words[i].startswith("-"):
        opt = words[i]
        if opt == "-C" and i + 1 < len(words):
            cdir = words[i + 1]
        elif opt.split("=")[0] in {"--git-dir", "--work-tree"}:
            cdir = "$repository-override"
        i += 2 if opt in GIT_OPTS_WITH_VALUE else 1
    if i >= len(words):
        return None
    return words[i], words[i + 1:], cdir


def stash_action(args: list[str]) -> tuple[str, list[str]]:
    """The stash sub-action and its arguments; flags may come before it (`git stash -u pop`)."""
    for i, a in enumerate(args):
        if a == "--":
            break
        if not a.startswith("-"):
            if a in STASH_ACTIONS:
                return a, args[:i] + args[i + 1:]
            break
    return "", args


def short_flags(args: list[str]) -> str:
    return "".join(a[1:] for a in args if a.startswith("-") and not a.startswith("--"))


def discard_reason(sub: str, args: list[str]) -> str | None:
    flags = [a for a in args if a.startswith("-")]
    short = short_flags(args)
    if sub == "reset" and "--hard" in args:
        return "`git reset --hard` discards every uncommitted change in the tree"
    if sub == "checkout" and ("--" in args or "." in args or "f" in short or "--force" in args):
        return "`git checkout -- <paths>` / `-f` overwrites uncommitted changes"
    if sub == "switch" and ("f" in short or "--force" in args or "--discard-changes" in args):
        return "`git switch --discard-changes` / `-f` throws away uncommitted changes"
    index_only = [f for f in flags if not f.startswith("--source") and f != "-s"]
    if sub == "restore" and not (index_only and set(index_only) <= {"--staged", "-S"}):
        return "`git restore` of the working tree overwrites uncommitted changes"
    if sub == "clean" and ("f" in short or "--force" in args) and not ("n" in short or "--dry-run" in args):
        return "`git clean -f` deletes untracked files that may exist nowhere else"
    if sub == "branch" and ("D" in short or (("d" in short or "--delete" in args)
                                             and ("f" in short or "--force" in args))):
        return "`git branch -D` deletes a branch whether or not its commits are merged"
    if sub == "stash" and args[:1] == ["clear"]:
        return "`git stash clear` drops every stash, including other sessions' WIP"
    if sub == "worktree" and args[:1] == ["remove"] and ("f" in short or "--force" in args):
        return "`git worktree remove --force` deletes a worktree with uncommitted changes"
    return None


def read_only(sub: str, args: list[str]) -> bool:
    if sub in READ_ONLY:
        return True
    pos = [a for a in args if not a.startswith("-")]
    if sub == "stash":
        return stash_action(args)[0] in {"list", "show", "create"}
    if sub == "branch":
        names, skip = [], False
        for a in args:
            if skip:
                skip = False
            elif a in BRANCH_VALUE_OPTS:
                skip = True
            elif not a.startswith("-"):
                names.append(a)
        return not names or any(a.split("=")[0] in BRANCH_LISTING for a in args)
    if sub == "tag":
        return not pos or any(a in {"-l", "--list", "--contains", "--points-at", "-n"} for a in args)
    if sub == "config":
        writes = {"--unset", "--unset-all", "--add", "--replace-all", "--remove-section", "--rename-section",
                  "--edit", "-e"}
        return any(a.startswith("--get") or a in {"--list", "-l"} for a in args) or (
            len(pos) == 1 and not writes.intersection(args))
    if sub == "remote":
        return not pos or pos[0] in {"show", "get-url"}
    if sub == "reflog":
        return not pos or pos[0] == "show"
    if sub == "worktree":
        return pos[:1] == ["list"]
    if sub == "notes":
        return not pos or pos[0] in {"list", "show"}
    if sub == "submodule":
        return pos[:1] == ["status"]
    if sub == "apply":
        return "--check" in args or "--stat" in args
    return False


def git_bin() -> str:
    for cand in ("/usr/bin/git", shutil.which("git") or ""):
        if cand and os.access(cand, os.X_OK):
            return cand
    return "git"


def stash_owner_mismatch(ref: str, cwd: str) -> str | None:
    """The branch a stash entry was recorded on when it is not the current branch; None when it matches or
    when git cannot tell (the check then stays out of the way)."""
    if not ref.startswith("stash@"):
        return None
    try:
        def run(*a: str) -> str:
            return subprocess.run([git_bin(), "-C", cwd, *a], capture_output=True, text=True,
                                  timeout=3).stdout
        cur = run("branch", "--show-current").strip()
        entries = run("stash", "list", "--format=%gd%x00%gs").splitlines()
    except (OSError, subprocess.SubprocessError):
        return None
    for line in entries:
        name, _, subject = line.partition("\x00")
        if name == ref:
            m = re.match(r"^(?:WIP on|On) ([^:]+):", subject)
            if m and cur and m.group(1) not in (cur, "(no branch)"):
                return m.group(1)
            return None
    return None


def isolated(cwd: str) -> bool:
    """True for a subagent's own `.claude/worktrees/<name>` tree, not for a session started inside one."""
    i = cwd.find(ISOLATED_TREE)
    if i < 0:
        return False
    tree = cwd[: i + len(ISOLATED_TREE)] + cwd[i + len(ISOLATED_TREE):].split("/")[0]
    project = os.environ.get("CLAUDE_PROJECT_DIR", "")
    return not (project and (project == tree or project.startswith(tree + "/")))


def main() -> None:
    try:
        payload: Payload = json.load(sys.stdin)
    except (ValueError, OSError):
        sys.exit(0)
    if not isinstance(payload, dict) or payload.get("tool_name") != "Bash":
        sys.exit(0)
    tool_input = payload.get("tool_input")
    cmd = tool_input.get("command") if isinstance(tool_input, dict) else None
    if not isinstance(cmd, str) or not re.search(r"\bgit\b", cmd):
        sys.exit(0)
    cwd = str(payload.get("cwd") or os.getcwd())
    # agent_type alone also marks a main session started with --agent; only agent_id marks a subagent
    agent = str(payload.get("agent_type") or "") if payload.get("agent_id") else ""

    if len(cmd) > MAX_PARSE:
        if re.search(DISCARD_VERBS, cmd):
            emit("ask", "the command is too long to read reliably and mentions a git verb that can discard "
                        "work. Confirm it is safe.")
        sys.exit(0)
    try:
        segs = parse(cmd)
    except Exception:  # a command the parser cannot read is asked about if it can discard work, else passed
        if re.search(DISCARD_VERBS, cmd):
            emit("ask", "the command cannot be read reliably (unmatched quote or unusual syntax), so which git "
                        "operation it runs is unclear. Fix the quoting, or confirm it is safe.")
        sys.exit(0)

    calls = []
    here: Optional[str] = None  # where a literal `cd` earlier in the command moved to (None: still in cwd)
    for pos, (words, _) in enumerate(segs):
        i = skip_prefix(words)
        if i < len(words) and words[i] == "cd":
            target = words[i + 1] if i + 1 < len(words) else "~"
            if here == UNKNOWN_DIR or re.search(r"[$`]|^~", target):
                here = UNKNOWN_DIR
            else:
                here = os.path.join(here, target) if here else target
            continue
        call = git_call(words)
        if not call:
            continue
        sub, args, cdir = call
        if here == UNKNOWN_DIR and not (cdir and os.path.isabs(cdir)):
            cdir = UNKNOWN_DIR
        elif here:
            cdir = os.path.join(here, cdir) if cdir else here
        calls.append((sub, args, cdir, pos))

    plugin, _, role = agent.rpartition(":")
    if plugin in DRAFT_ONLY_PLUGINS:
        for sub, args, cdir, _ in calls:
            # the exemption belongs to the tree the call acts on: `git -C <shared tree>` from an isolated
            # worktree still writes the shared tree
            target = os.path.normpath(os.path.join(cwd, cdir)) if cdir else cwd
            literal = not (cdir and re.search(r"[$`]|^~", cdir))
            if not (literal and isolated(target)) and not read_only(sub, args):
                emit("deny", f"`git {sub}` changes repository state, and git is read-only for a delegated "
                             f"agent ({role}) in a shared tree. If you need a baseline, a revert or a cleanup, "
                             "stop and tell the session that dispatched you what you need and why — it decides, "
                             "and runs baselines in a separate worktree, never in this tree.")

    created_at = None
    for sub, args, cdir, pos in calls:
        if sub != "stash":
            continue
        action, rest = stash_action(args)
        if action in STASH_CONSUME:
            refs = [a for a in rest if not a.startswith("-")]
            if action == "branch":
                if len(refs) < 2 or not STASH_REF.match(refs[-1]):
                    emit("deny", "`git stash branch` needs a branch name and an explicit ref — without the ref it "
                                 "takes the top entry, which may belong to another session or agent. Check `git stash list`, "
                                 "then run `git stash branch <new-branch> stash@{N}` with the entry that is yours.")
                refs = refs[1:]
            refs = [r for r in refs if STASH_REF.match(r)] or refs
            if not refs or not STASH_REF.match(refs[-1]):
                emit("deny", f"`git stash {action}` without an explicit ref acts on the top entry, which may be "
                             "another session's or agent's WIP. Run `git stash push -m <unique-tag>` as its own call, check "
                             "`git stash list` shows your tag at stash@{0}, then run "
                             f"`git stash {action} stash@{{0}}` as a separate call. Prefer a worktree for "
                             "baselines.")
            if created_at is not None:
                emit("deny", "a `git stash` that creates an entry and a later one that consumes it run in one "
                             "command — `git stash push` succeeds without creating anything on a clean tree, so "
                             "the consume can take another session's entry. Run them as separate calls and check "
                             "`git stash list` in between.")
            if not (cdir and re.search(r"[$`]|^~", cdir)):
                ref = f"stash@{{{refs[-1]}}}" if refs[-1].isdigit() else refs[-1]
                owner = stash_owner_mismatch(ref, os.path.join(cwd, cdir) if cdir else cwd)
                if owner:
                    emit("ask", f"{ref} was recorded on branch `{owner}`, not the current one — it is "
                                "probably another session's work. Confirm it is the entry you mean.")
        elif action in STASH_CREATE:
            created_at = pos

    for sub, args, _, _ in calls:
        reason = discard_reason(sub, args)
        if reason:
            emit("ask", reason + ". Snapshot first (`git stash create` + record the SHA, or "
                                  "`git diff > <file>`), restore only the paths you must, and confirm.")
    sys.exit(0)


if __name__ == "__main__":
    main()
