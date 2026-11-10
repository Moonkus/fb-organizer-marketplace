"""plugins/fb-standards/scripts/scan-changes.sh — staged-diff and range scans."""
import subprocess
import unittest
from pathlib import Path

from _harness import PLUGIN, git, make_repo

SCRIPT = PLUGIN / "scripts" / "scan-changes.sh"
GOCSPX = "GOCSPX-" + "a1B2c3D4e5F6g7H8i9J0kLmN"


def scan(repo, *args):
    return subprocess.run(["bash", str(SCRIPT), *args], cwd=repo, capture_output=True, text=True, timeout=30)


class ScanStagedTest(unittest.TestCase):
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

    def test_clean_staged_diff(self):
        self.stage("apps/x.py", "SECRET_KEY = env('SECRET_KEY')\n")
        proc = scan(self.repo)
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_secret_in_staged_diff(self):
        self.stage("apps/settings_local.py", f"CLIENT_SECRET = '{GOCSPX}'\n")
        proc = scan(self.repo)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("Google OAuth client secret", proc.stdout)

    def test_forbidden_files(self):
        for name in (".env", "certs/server.pem", "client_secret_1.json", "credentials.json", "token.json",
                     "secrets/x.txt"):
            with self.subTest(name=name):
                self.stage(name, "placeholder\n")
                self.assertIn(f"FORBIDDEN FILE: {name}", scan(self.repo).stdout)
                git("rm", "-q", "--cached", name, cwd=self.repo)

    def test_database_dumps(self):
        for name in ("db.dump", "backups/2026-11-09.sql.gz", "prod.backup"):
            with self.subTest(name=name):
                self.stage(name, "tiny\n")
                self.assertIn(f"DATABASE DUMP: {name}", scan(self.repo).stdout)
                git("rm", "-q", "--cached", name, cwd=self.repo)

    def test_large_file(self):
        with open(Path(self.repo, "big.bin"), "wb") as f:
            f.truncate(11 * 1024 * 1024)
        git("add", "big.bin", cwd=self.repo)
        self.assertIn("LARGE FILE: big.bin", scan(self.repo).stdout)

    def test_env_example_allowed(self):
        self.stage(".env.example", "SECRET_KEY=replace-me\n")
        self.assertEqual(scan(self.repo).returncode, 0)

    def test_range_mode_catches_committed_secret(self):
        git("checkout", "-q", "-b", "feature/x", cwd=self.repo)
        self.stage("apps/y.py", f"TOKEN = '{GOCSPX}'\n")
        git("commit", "-q", "-m", "add y", cwd=self.repo)
        proc = scan(self.repo, "main")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("SECRET PATTERN", proc.stdout)

    def test_unknown_base_is_an_error(self):
        self.assertEqual(scan(self.repo, "no-such-ref").returncode, 2)


if __name__ == "__main__":
    unittest.main()
