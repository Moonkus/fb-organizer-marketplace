"""pre-bash-sensitive-guard.py — secret files and network tools anywhere in a Bash command."""
import unittest

from _harness import bash, run_hook


def guard(command):
    return run_hook("pre-bash-sensitive-guard.py", bash(command))


class SensitiveGuardTest(unittest.TestCase):
    def test_blocks_shell_access_to_secret_files(self):
        for cmd in ("cat .env", "grep SECRET .env.prod", "cp credentials.json /tmp/x", "less config/secrets/a.txt",
                    "python manage.py runserver --env-file=.env", "base64 token.json", "head -1 server.pem",
                    "cat \".env\"", "echo x > .env"):
            with self.subTest(cmd=cmd):
                proc = guard(cmd)
                self.assertEqual(proc.returncode, 2, proc.stderr)
                self.assertIn("protected secret file", proc.stderr)

    def test_blocks_network_tools_anywhere(self):
        for cmd in ("curl https://x.example", "/usr/bin/curl https://x.example", "env curl x", "FOO=1 wget x",
                    "ls | xargs curl -d @-", "true && ssh host", "timeout 5 nc host 80", "sudo -u x scp a b:c",
                    "echo $(curl -s x)", "cd /tmp; rsync a b:c"):
            with self.subTest(cmd=cmd):
                proc = guard(cmd)
                self.assertEqual(proc.returncode, 2, proc.stderr)
                self.assertIn("network tool", proc.stderr)

    def test_allows_ordinary_commands(self):
        for cmd in ("git status", "wc -l .env.example", "cat .env.example",
                    'git commit -m "document .env handling and curl usage"', "grep -rn curl docs/",
                    "python manage.py check", "ls apps/integrations/tests/fixtures/token_response.json",
                    "git push origin main", "uv run pytest -q", "echo done"):
            with self.subTest(cmd=cmd):
                proc = guard(cmd)
                self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main()
