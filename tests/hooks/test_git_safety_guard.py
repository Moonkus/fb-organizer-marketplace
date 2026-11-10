"""pre-bash-git-safety-guard.py — ask on discard, refuse ref-less stash, read-only subagents."""
import unittest

from _harness import bash, decision, run_hook


def guard(command, **extra):
    return run_hook("pre-bash-git-safety-guard.py", bash(command, cwd="/tmp", **extra))


class GitSafetyGuardTest(unittest.TestCase):
    def test_asks_before_discarding_work(self):
        for cmd in ("git reset --hard", "git checkout -- .", "git restore apps/", "git clean -fd",
                    "git branch -D old", "git stash clear", "cd /tmp && git reset --hard HEAD~1"):
            with self.subTest(cmd=cmd):
                self.assertEqual(decision(guard(cmd)), "ask")

    def test_refuses_stash_without_ref(self):
        for cmd in ("git stash pop", "git stash apply", "git stash drop"):
            with self.subTest(cmd=cmd):
                self.assertEqual(decision(guard(cmd)), "deny")

    def test_passes_safe_commands(self):
        for cmd in ("git status", "git diff", "git log --oneline", "git restore --staged apps/x.py",
                    "git reset --keep HEAD~1", "git commit -m 'reset --hard docs'"):
            with self.subTest(cmd=cmd):
                proc = guard(cmd)
                self.assertEqual(proc.returncode, 0)
                self.assertIsNone(decision(proc), proc.stdout)

    def test_subagent_cannot_write_shared_tree(self):
        proc = guard("git commit -m x", agent_id="a1", agent_type="fb-standards:developer")
        self.assertEqual(decision(proc), "deny")

    def test_subagent_may_read(self):
        proc = guard("git status", agent_id="a1", agent_type="fb-standards:developer")
        self.assertIsNone(decision(proc))

    def test_subagent_may_write_own_worktree(self):
        payload_cwd = "/repo/.claude/worktrees/dev-1"
        proc = run_hook("pre-bash-git-safety-guard.py",
                        bash("git commit -m x", cwd=payload_cwd, agent_id="a1",
                             agent_type="fb-standards:developer"))
        self.assertIsNone(decision(proc))


if __name__ == "__main__":
    unittest.main()
