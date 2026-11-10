#!/usr/bin/env python3
"""Validate fb-standards content — the checks `claude plugin validate` does not do.

- agents/*.md         frontmatter name (== file name), description, tools, model;
                      every `mcp__…` tool named in the body is listed in `tools:`;
                      every name in `rules:` is a rules/*.md file, and core.md + those rules fit the
                      SubagentStart additionalContext limit (CONTEXT_BUDGET characters)
- skills/*/SKILL.md   frontmatter name (== directory), description; no skill dir without SKILL.md
- rules/*.md          first line `# Title` (the SessionStart index uses it), ≤ MAX_RULE_LINES;
                      rules/core.md exists and is ≤ MAX_CORE_LINES (it is injected every session)
- every `fb-standards:<name>` in agents/skills/rules names an existing agent or skill

Stdlib only. Prints one line per problem; exit 1 if any.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "fb-standards"
MAX_RULE_LINES = 80
MAX_CORE_LINES = 40
CONTEXT_BUDGET = 9700  # Claude Code caps hook additionalContext at 10 000 characters
MODELS = {"opus", "sonnet", "haiku", "inherit"}
REF = re.compile(r"fb-standards:([a-z0-9-]+)")
MCP = re.compile(r"mcp__[A-Za-z0-9_-]+")


def split_frontmatter(path: Path) -> tuple[dict[str, str] | None, str]:
    """(frontmatter as flat key/value, body); frontmatter is None when absent or unterminated."""
    lines = path.read_text().splitlines()
    if not lines or lines[0] != "---":
        return None, "\n".join(lines)
    fm: dict[str, str] = {}
    for i, line in enumerate(lines[1:], start=1):
        if line == "---":
            return fm, "\n".join(lines[i + 1:])
        if ":" in line and not line.startswith((" ", "\t")):
            key, _, value = line.partition(":")
            fm[key.strip()] = value.strip()
    return None, ""


def rel(path: Path) -> Path:
    return path.relative_to(ROOT)


def main() -> int:
    problems: list[str] = []
    agents = {p.stem for p in (PLUGIN / "agents").glob("*.md")}
    skills = {p.parent.name for p in (PLUGIN / "skills").glob("*/SKILL.md")}

    core_file = PLUGIN / "rules" / "core.md"
    core_text = core_file.read_text() if core_file.exists() else ""
    for agent in sorted((PLUGIN / "agents").glob("*.md")):
        fm, body = split_frontmatter(agent)
        if fm is None:
            problems.append(f"{rel(agent)}: missing or unterminated frontmatter")
            continue
        for key in ("name", "description", "tools", "model"):
            if not fm.get(key):
                problems.append(f"{rel(agent)}: frontmatter `{key}` is missing or empty")
        if fm.get("name") and fm["name"] != agent.stem:
            problems.append(f"{rel(agent)}: name `{fm['name']}` != file name `{agent.stem}`")
        if fm.get("model") and fm["model"] not in MODELS:
            problems.append(f"{rel(agent)}: model `{fm['model']}` not in {sorted(MODELS)}")
        wanted = [r.strip() for r in fm.get("rules", "").split(",") if r.strip()]
        size = len(core_text) + 100
        for r in wanted:
            rule = PLUGIN / "rules" / f"{r}.md"
            if not rule.exists() or r == "core":
                problems.append(f"{rel(agent)}: rules lists `{r}`, which is not a topic rule in rules/")
            else:
                size += len(rule.read_text()) + 10
        if size > CONTEXT_BUDGET:
            problems.append(f"{rel(agent)}: core + rules = {size} chars > {CONTEXT_BUDGET} "
                            "(SubagentStart context limit); trim the rules or the list")
        tools = {t.strip() for t in fm.get("tools", "").split(",")}
        for tool in sorted(set(MCP.findall(body)) - tools):
            problems.append(f"{rel(agent)}: body uses {tool} but it is not in tools:")

    for skill in sorted((PLUGIN / "skills").glob("*/SKILL.md")):
        fm, _ = split_frontmatter(skill)
        if fm is None:
            problems.append(f"{rel(skill)}: missing or unterminated frontmatter")
            continue
        for key in ("name", "description"):
            if not fm.get(key):
                problems.append(f"{rel(skill)}: frontmatter `{key}` is missing or empty")
        if fm.get("name") and fm["name"] != skill.parent.name:
            problems.append(f"{rel(skill)}: name `{fm['name']}` != directory `{skill.parent.name}`")
    for d in sorted((PLUGIN / "skills").iterdir()):
        if d.is_dir() and not (d / "SKILL.md").exists():
            problems.append(f"{rel(d)}: skill directory without SKILL.md")

    for rule in sorted((PLUGIN / "rules").glob("*.md")):
        lines = rule.read_text().splitlines()
        if not lines or not lines[0].startswith("# "):
            problems.append(f"{rel(rule)}: first line must be a `# Title` (the SessionStart index uses it)")
        if len(lines) > MAX_RULE_LINES:
            problems.append(f"{rel(rule)}: {len(lines)} lines > {MAX_RULE_LINES}; split it")
    core = PLUGIN / "rules" / "core.md"
    if not core.exists():
        problems.append(f"{rel(core)} is missing (SessionStart pins it)")
    elif len(core.read_text().splitlines()) > MAX_CORE_LINES:
        problems.append(f"{rel(core)} exceeds {MAX_CORE_LINES} lines (it is injected every session)")

    sources = [*(PLUGIN / "agents").glob("*.md"), *(PLUGIN / "skills").glob("*/SKILL.md"),
               *(PLUGIN / "rules").glob("*.md")]
    for src in sorted(sources):
        for name in sorted(set(REF.findall(src.read_text()))):
            if name not in agents and name not in skills:
                problems.append(f"{rel(src)}: references fb-standards:{name}, which does not exist")

    for p in problems:
        print(p)
    if not problems:
        print(f"validate: OK ({len(agents)} agents, {len(skills)} skills)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
