import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

V3 = Path(__file__).resolve().parents[1]
START = b"# >>> dotfiles v3 >>>\n"
END = b"# <<< dotfiles v3 <<<\n"


@unittest.skipUnless(shutil.which("git"), "Git is required")
class GitBlockTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.config = self.home / ".gitconfig"
        self.ignore = self.home / ".gitignore"
        self.private = (b"[user]\n\tname = Example User\n\temail = private@example.invalid\n"
                        b"\tsigningkey = PLACEHOLDER_KEY\n[core]\n\teditor = private-editor")
        self.config.write_bytes(self.private)
        self.ignore.write_bytes(b"!private-pattern")
        self.env = {"HOME": str(self.home), "PATH": os.environ["PATH"],
                    "GIT_CONFIG_NOSYSTEM": "1", "XDG_CONFIG_HOME": str(self.home / ".config")}

    def configure(self, apply=True):
        result = subprocess.run(
            ["bash", "-euo", "pipefail", "-c",
             'SCRIPT_DIR=$1; APPLY=$2; source "$SCRIPT_DIR/.scripts/git.sh"; configure_git',
             "git-block-test", str(V3), "true" if apply else "false"],
            cwd=self.home, env=self.env, capture_output=True, timeout=15,
        )
        output = result.stdout + result.stderr
        for private in (b"Example User", b"private@example.invalid", b"PLACEHOLDER_KEY",
                        b"private-editor", b"private-pattern", str(self.home).encode()):
            if private in output:
                self.fail("Git updater exposed private contents or paths")
        self.assertEqual(result.returncode, 0, "Unexpected Git updater status")
        return result

    def git_config(self, *args):
        return subprocess.run(
            ["git", "config", "--global", *args], cwd=self.home, env=self.env,
            check=True, capture_output=True, text=True, timeout=10,
        ).stdout.strip()

    def test_preview_does_not_write(self):
        self.configure(apply=False)
        self.assertEqual(self.config.read_bytes(), self.private)
        self.assertEqual(self.ignore.read_bytes(), b"!private-pattern")
        self.assertEqual(set(self.home.iterdir()), {self.config, self.ignore})

    def test_shared_preferences_and_private_identity_render_with_overrides(self):
        self.configure()
        expected = {
            "user.name": "Example User", "user.email": "private@example.invalid",
            "user.signingkey": "PLACEHOLDER_KEY", "core.editor": "private-editor",
            "core.pager": "delta", "core.excludesfile": "~/.gitignore",
            "init.defaultBranch": "main", "push.default": "current",
            "push.autoSetupRemote": "true", "fetch.prune": "true",
            "rebase.autoStash": "true", "rebase.updateRefs": "true",
            "rerere.enabled": "true", "branch.sort": "-committerdate",
            "interactive.diffFilter": "delta --color-only", "delta.navigate": "true",
            "delta.side-by-side": "true", "merge.conflictstyle": "zdiff3",
            "diff.algorithm": "histogram", "diff.colorMoved": "default",
            "commit.gpgsign": "true", "commit.verbose": "true",
            "alias.cursor-commit": "commit -p",
            "url.git@bitbucket.org:.insteadOf": "https://bitbucket.org/",
            "url.git@gitlab.com:.insteadOf": "https://gitlab.com/",
        }
        for key, value in expected.items():
            with self.subTest(key=key):
                self.assertEqual(self.git_config("--get", key), value)
        self.assertEqual(self.git_config("--get-all", "core.editor"), "nano\nprivate-editor")
        self.assertEqual(self.config.read_bytes(), START + (V3 / "git/gitconfig").read_bytes() + END + self.private)
        self.assertEqual(self.ignore.read_bytes(), START + (V3 / "git/gitignore").read_bytes() + END + b"!private-pattern")
        self.assertFalse(self.config.is_symlink())
        self.assertFalse(self.ignore.is_symlink())
        self.assertNotIn(b"[include]", self.config.read_bytes())

    def test_reapply_is_byte_and_mtime_identical(self):
        self.configure()
        before = {path: (path.read_bytes(), path.stat().st_mtime_ns)
                  for path in self.home.iterdir()}
        self.configure()
        self.assertEqual({path: (path.read_bytes(), path.stat().st_mtime_ns)
                          for path in self.home.iterdir()}, before)

    def test_global_identity_write_stays_private_and_survives_reapply(self):
        self.configure()
        self.git_config("user.name", "Updated Example")
        self.assertEqual(self.git_config("--get", "user.name"), "Updated Example")
        prefix, suffix = self.config.read_bytes().split(END)
        self.assertNotIn(b"Updated Example", prefix)
        self.assertIn(b"Updated Example", suffix)
        self.configure()
        self.assertEqual(self.git_config("--get", "user.name"), "Updated Example")


if __name__ == "__main__":
    unittest.main()
