"""scripts/check-version-bump.sh — plugin changes require a higher version."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from _harness import REPO, git

MANIFEST = "plugins/fb-standards/.claude-plugin/plugin.json"


class VersionBumpTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        shutil.copytree(REPO / "scripts", self.repo / "scripts")
        (self.repo / MANIFEST).parent.mkdir(parents=True)
        self.set_version("0.1.0")
        (self.repo / "plugins/fb-standards/rules").mkdir()
        (self.repo / "plugins/fb-standards/rules/core.md").write_text("# Core\n")
        (self.repo / "README.md").write_text("x\n")
        (self.repo / "CHANGELOG.md").write_text("# Changelog\n\n## [0.1.0]\n")
        for cmd in (["init", "-q", "-b", "main"], ["config", "user.email", "t@example.com"],
                    ["config", "user.name", "t"], ["config", "commit.gpgsign", "false"],
                    ["add", "."], ["commit", "-q", "-m", "init"]):
            git(*cmd, cwd=str(self.repo))
        self.base = git("rev-parse", "HEAD", cwd=str(self.repo)).strip()

    def tearDown(self):
        self.tmp.cleanup()

    def set_version(self, version):
        (self.repo / MANIFEST).write_text(json.dumps({"name": "fb-standards", "version": version}))

    def commit(self, path, content):
        (self.repo / path).write_text(content)
        git("add", ".", cwd=str(self.repo))
        git("commit", "-q", "-m", "change", cwd=str(self.repo))

    def check(self, base=None):
        return subprocess.run(["bash", "scripts/check-version-bump.sh", base or self.base],
                              cwd=self.repo, capture_output=True, text=True, timeout=30)

    def test_plugin_change_without_bump_fails(self):
        self.commit("plugins/fb-standards/rules/core.md", "# Core\nmore\n")
        proc = self.check()
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("still 0.1.0", proc.stdout)

    def test_plugin_change_with_bump_passes(self):
        self.set_version("0.2.0")
        (self.repo / "CHANGELOG.md").write_text("# Changelog\n\n## [0.2.0] - 2026-11-10\n\n## [0.1.0]\n")
        self.commit("plugins/fb-standards/rules/core.md", "# Core\nmore\n")
        self.assertEqual(self.check().returncode, 0)

    def test_bump_without_changelog_entry_fails(self):
        self.set_version("0.2.0")
        self.commit("plugins/fb-standards/rules/core.md", "# Core\nmore\n")
        proc = self.check()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("CHANGELOG", proc.stdout)

    def test_version_going_down_fails(self):
        self.set_version("0.0.9")
        self.commit("plugins/fb-standards/rules/core.md", "# Core\nmore\n")
        self.assertIn("went down", self.check().stdout)

    def test_semver_compares_numerically(self):
        self.set_version("0.10.0")
        (self.repo / "CHANGELOG.md").write_text("# Changelog\n\n## [0.10.0]\n")
        self.commit("plugins/fb-standards/rules/core.md", "# Core\nmore\n")
        self.assertEqual(self.check().returncode, 0)

    def test_non_plugin_change_passes(self):
        self.commit("README.md", "y\n")
        self.assertEqual(self.check().returncode, 0)

    def test_missing_base_skips(self):
        proc = self.check("0000000000000000000000000000000000000000")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("skipping", proc.stdout)


if __name__ == "__main__":
    unittest.main()
