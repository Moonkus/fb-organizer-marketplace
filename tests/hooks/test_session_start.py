"""session-start-context.sh."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from _harness import PLUGIN, run_hook

RULES = PLUGIN / "rules"


def context(proc):
    return json.loads(proc.stdout)["hookSpecificOutput"]["additionalContext"]


class SessionStartTest(unittest.TestCase):
    def test_pins_core_and_indexes_topic_rules(self):
        proc = run_hook("session-start-context.sh", {})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        ctx = context(proc)
        self.assertIn((RULES / "core.md").read_text().strip(), ctx)
        for rule in RULES.glob("*.md"):
            if rule.name != "core.md":
                title = rule.read_text().splitlines()[0][2:]
                self.assertIn(f"- {title} → {rule}", ctx)

    def test_full_mode_inlines_rule_bodies(self):
        ctx = context(run_hook("session-start-context.sh", {}, env={"FB_STANDARDS_INJECT_FULL": "1"}))
        self.assertIn((RULES / "security.md").read_text().strip(), ctx)
        self.assertNotIn(f"→ {RULES / 'security.md'}", ctx)

    def test_missing_core_warns_visibly_but_fails_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copytree(PLUGIN / "hooks", Path(tmp, "hooks"))
            Path(tmp, "rules").mkdir()
            proc = run_hook("session-start-context.sh", {}, plugin_root=Path(tmp))
            self.assertEqual(proc.returncode, 0)
            self.assertIn("NOT injected", proc.stderr)
            self.assertIn("NOT injected", context(proc))


if __name__ == "__main__":
    unittest.main()
