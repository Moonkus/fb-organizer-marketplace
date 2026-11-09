"""pre-bash-secret-scan.sh and pre-file-secret-guard.sh."""
import unittest

from _harness import bash, run_hook, write

# Fake values assembled at runtime so this file never contains a literal secret.
GOCSPX = "GOCSPX-" + "a1B2c3D4e5F6g7H8i9J0kLmN"
YA29 = "ya29." + "A0ARrdaM" * 4
REFRESH = "1//0" + "gAbCdEfGhIjKlMnOpQrStUvWxYz012345"
GH_PAT = "ghp_" + "A" * 36
SECRET_KEY = "SECRET_KEY = '" + "x7#k" * 10 + "'"


class SecretScanTest(unittest.TestCase):
    def scan(self, command):
        return run_hook("pre-bash-secret-scan.sh", bash(command))

    def test_blocks_google_and_github_secrets(self):
        for secret in (GOCSPX, YA29, REFRESH, GH_PAT, SECRET_KEY):
            with self.subTest(secret=secret[:8]):
                proc = self.scan(f"echo {secret!r} > /dev/null")
                self.assertEqual(proc.returncode, 2, proc.stderr)
                self.assertIn("BLOCKED", proc.stderr)

    def test_blocks_postgres_url_with_password(self):
        proc = self.scan("psql postgres://feedback:" + "s3cr3tPass" + "@db:5432/app")
        self.assertEqual(proc.returncode, 2)

    def test_allows_benign_commands(self):
        for cmd in ("uv run pytest -q", "git status", "echo SECRET_KEY=env('SECRET_KEY')",
                    "docker compose up -d db"):
            with self.subTest(cmd=cmd):
                self.assertEqual(self.scan(cmd).returncode, 0)


class SecretFileGuardTest(unittest.TestCase):
    def guard(self, path, content=""):
        return run_hook("pre-file-secret-guard.sh", write(path, content))

    def read(self, path):
        return run_hook("pre-file-secret-guard.sh", {"tool_name": "Read", "tool_input": {"file_path": path}})

    def test_blocks_reading_protected_paths(self):
        for path in ("/app/.env", "/app/.env.prod", "/app/credentials.json", "/app/token.json",
                     "/app/config/secrets/fernet.txt", "/app/client_secret_1.json"):
            with self.subTest(path=path):
                self.assertEqual(self.read(path).returncode, 2)

    def test_allows_reading_env_example_and_fixtures(self):
        for path in ("/app/.env.example", "/app/apps/integrations/tests/fixtures/token_response.json",
                     "/app/apps/feedback/models.py"):
            with self.subTest(path=path):
                self.assertEqual(self.read(path).returncode, 0)

    def test_blocks_protected_paths(self):
        for path in ("/app/.env", "/app/.env.prod", "/app/certs/server.pem", "/app/tls.key",
                     "/app/secrets/db.txt", "/app/client_secret_123.apps.json", "/app/token.json",
                     "/app/credentials.json", "/app/deploy/secrets/key.txt"):
            with self.subTest(path=path):
                proc = self.guard(path, "x")
                self.assertEqual(proc.returncode, 2, proc.stderr)
                self.assertIn("BLOCKED (path)", proc.stderr)

    def test_allows_env_example_with_placeholders(self):
        proc = self.guard("/app/.env.example", "SECRET_KEY=replace-me\nGOOGLE_CLIENT_SECRET=<secret>\n")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_blocks_real_secret_in_allowed_file(self):
        proc = self.guard("/app/.env.example", f"GOOGLE_CLIENT_SECRET={GOCSPX}\n")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("BLOCKED (content)", proc.stderr)

    def test_allows_regular_python(self):
        proc = self.guard("/app/apps/feedback/models.py", "SECRET_KEY = env('SECRET_KEY')\n")
        self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main()
