"""subagent-start-context.sh — rules for subagents without copying them into agent bodies."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from _harness import PLUGIN, run_hook

RULES = PLUGIN / "rules"


def context(proc):
    return json.loads(proc.stdout)["hookSpecificOutput"]["additionalContext"]


def start(agent_type, **kw):
    return run_hook("subagent-start-context.sh", {"hook_event_name": "SubagentStart", "agent_type": agent_type}, **kw)


def declared_rules(agent):
    for line in (PLUGIN / "agents" / f"{agent}.md").read_text().splitlines():
        if line.startswith("rules:"):
            return [r.strip() for r in line[6:].split(",") if r.strip()]
    return []


class SubagentStartTest(unittest.TestCase):
    def test_plugin_agent_gets_core_and_its_rules_only(self):
        for agent in (p.stem for p in (PLUGIN / "agents").glob("*.md")):
            with self.subTest(agent=agent):
                proc = start(f"fb-standards:{agent}")
                self.assertEqual(proc.returncode, 0, proc.stderr)
                ctx = context(proc)
                self.assertEqual(json.loads(proc.stdout)["hookSpecificOutput"]["hookEventName"], "SubagentStart")
                self.assertIn((RULES / "core.md").read_text().strip(), ctx)
                wanted = declared_rules(agent)
                for rule in RULES.glob("*.md"):
                    if rule.stem == "core":
                        continue
                    body = rule.read_text().strip()
                    (self.assertIn if rule.stem in wanted else self.assertNotIn)(body, ctx)
                self.assertLess(len(ctx), 10000)

    def test_other_subagents_get_core_and_index(self):
        for agent in ("Explore", "Plan", "general-purpose", "other-plugin:developer"):
            with self.subTest(agent=agent):
                ctx = context(start(agent))
                self.assertIn((RULES / "core.md").read_text().strip(), ctx)
                self.assertIn(f"→ {RULES / 'django.md'}", ctx)
                self.assertNotIn((RULES / "django.md").read_text().strip(), ctx)

    def test_missing_agent_type_still_gets_core(self):
        proc = run_hook("subagent-start-context.sh", {"hook_event_name": "SubagentStart"})
        self.assertIn((RULES / "core.md").read_text().strip(), context(proc))

    def test_missing_core_fails_open_visibly(self):
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copytree(PLUGIN / "hooks", Path(tmp, "hooks"))
            Path(tmp, "rules").mkdir()
            proc = start("fb-standards:developer", plugin_root=Path(tmp))
            self.assertEqual((proc.returncode, proc.stdout), (0, ""))
            self.assertIn("NOT injected", proc.stderr)


if __name__ == "__main__":
    unittest.main()
