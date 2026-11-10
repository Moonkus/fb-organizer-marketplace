"""pre-bash-commit-scan.sh and user-prompt-secret-scan.sh."""
import json
import unittest
from pathlib import Path

from _harness import bash, git, make_repo, run_hook

GOCSPX = "GOCSPX-" + "a1B2c3D4e5F6g7H8i9J0kLmN"


class CommitScanTest(unittest.TestCase):
    def setUp(self):
        self.tmp = make_repo("git@github.com:Moonkus/fb-organizer.git")
        self.repo = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def stage(self, name, content):
        path = Path(self.repo, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        git("add", "-f", name, cwd=self.repo)

    def commit(self, command):
        return run_hook("pre-bash-commit-scan.sh", bash(command, cwd=self.repo))

    def test_blocks_commit_with_secret_or_forbidden_file(self):
        self.stage("apps/x.py", f"KEY = '{GOCSPX}'\n")
        proc = self.commit('git commit -m "add x"')
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("Google OAuth client secret", proc.stderr)

    def test_blocks_dump_even_when_chained(self):
        self.stage("db.dump", "tiny\n")
        proc = self.commit('cd . && git commit -m "backup"')
        self.assertEqual(proc.returncode, 2)
        self.assertIn("DATABASE DUMP", proc.stderr)

    def test_allows_clean_commit(self):
        self.stage("apps/x.py", "KEY = env('KEY')\n")
        self.assertEqual(self.commit('git commit -m "fix -a flag handling"').returncode, 0)

    def test_refuses_commit_all(self):
        for cmd in ("git commit -a -m x", "git commit -am x", "git commit --all -m x", "git commit -sam x"):
            with self.subTest(cmd=cmd):
                proc = self.commit(cmd)
                self.assertEqual(proc.returncode, 2)
                self.assertIn("git add <path>", proc.stderr)

    def test_ignores_non_commit_and_prose(self):
        for cmd in ("git status", "git log --oneline -3", "echo git commit later", "grep -r commit docs/"):
            with self.subTest(cmd=cmd):
                self.assertEqual(self.commit(cmd).returncode, 0)

    def test_empty_payload_passes(self):
        self.assertEqual(run_hook("pre-bash-commit-scan.sh", {}).returncode, 0)


class PromptSecretScanTest(unittest.TestCase):
    def prompt(self, text):
        return run_hook("user-prompt-secret-scan.sh", {"hook_event_name": "UserPromptSubmit", "prompt": text})

    def test_blocks_prompt_with_secret(self):
        proc = self.prompt(f"here is the client secret {GOCSPX}, configure it")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("NOT sent", proc.stderr)

    def test_allows_ordinary_prompts(self):
        for text in ("закоміть зміни", "set GOOGLE_CLIENT_SECRET in .env.example to <secret>", "review apps/feedback"):
            with self.subTest(text=text):
                self.assertEqual(self.prompt(text).returncode, 0)

    def test_empty_payload_passes(self):
        self.assertEqual(run_hook("user-prompt-secret-scan.sh", {}).returncode, 0)


if __name__ == "__main__":
    unittest.main()
