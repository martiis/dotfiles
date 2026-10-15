import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

V3 = Path(__file__).resolve().parents[1]
GIT_BLOCK_COMMANDS = {"delta": "git-delta", "nano": "nano"}


@unittest.skipUnless(shutil.which("stow"), "GNU Stow is required")
class SetupScriptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.home = self.base / "home"
        self.home.mkdir()
        self.zshrc = self.home / ".zshrc"
        self.original = b'export DEMO_TOKEN="synthetic-secret"\n'
        self.zshrc.write_bytes(self.original)
        self.mock = self.base / "bin"
        self.mock.mkdir()
        self.log = self.base / "external-calls"
        # Fail if a test attempts a package install or clone. Never run either.
        for name in ("sudo", "pacman", "git"):
            self.mock_command(name, 'printf "unexpected\\n" >> "$MOCK_LOG"\nexit 99\n')
        # Commands the Git block invokes; present by default so the host is irrelevant.
        for name in GIT_BLOCK_COMMANDS:
            self.mock_command(name, 'exit 0\n')
        self.env = dict(
            os.environ, HOME=str(self.home), MOCK_LOG=str(self.log),
            PATH=str(self.mock) + os.pathsep + os.environ["PATH"],
            ZSH_CUSTOM=str(self.home / ".oh-my-zsh" / "custom"),
            CDPATH=".",
        )

    def mock_command(self, name, body):
        script = self.mock / name
        script.write_text('#!/usr/bin/env bash\n' + body)
        script.chmod(0o700)

    def hide_git_block_commands(self):
        """Use a PATH where the Git block's commands do not exist at all."""
        visible = self.base / "visible-bin"
        visible.mkdir()
        hidden = set(GIT_BLOCK_COMMANDS)
        seen = set()
        for directory in os.environ["PATH"].split(os.pathsep):
            if not directory or not os.path.isdir(directory):
                continue
            for entry in os.scandir(directory):
                if entry.name in hidden or entry.name in seen:
                    continue
                if entry.is_file() and os.access(entry.path, os.X_OK):
                    seen.add(entry.name)
                    (visible / entry.name).symlink_to(entry.path)
        for name in hidden:
            (self.mock / name).unlink()
        self.env["PATH"] = str(self.mock) + os.pathsep + str(visible)
        self.env["MOCK_BIN"] = str(self.mock)

    def assert_untouched(self):
        self.assertEqual(self.zshrc.read_bytes(), self.original)
        self.assertEqual(set(self.home.iterdir()), {self.zshrc})

    def mock_package_install(self):
        self.mock_command("sudo", 'printf "sudo:%s\\n" "$*" >> "$MOCK_LOG"\n')

    def mock_clone(self, success):
        self.mock_command("git", '''printf "git:%s\\n" "$*" >> "$MOCK_LOG"
target=${@: -1}
printf 'Clone output: %s\\n' "$target"
printf 'Clone diagnostic: %s\\n' "$target" >&2
''' + ('mkdir -p -- "$target/.git"\n' if success else 'exit 1\n'))

    def run_setup(self, *args, script="install.sh", success=True, external=False):
        result = subprocess.run(
            ["bash", str(V3.relative_to(V3.parent.parent) / script), *args],
            cwd=V3.parent.parent, env=self.env, capture_output=True, timeout=15,
        )
        output = result.stdout + result.stderr
        if b"synthetic-secret" in output or str(self.home).encode() in output:
            self.fail("Setup exposed private values or paths")
        self.assertEqual(result.returncode == 0, success, "Unexpected setup status")
        if not external:
            self.assertFalse(self.log.exists(), "Attempted package installation or cloning")
        return result

    def test_relative_stage_previews_with_cdpath_do_not_write(self):
        for script in ("packages.sh", "stow.sh"):
            with self.subTest(script=script):
                self.run_setup(script=script)
                self.assertEqual(self.zshrc.read_bytes(), self.original)
                self.assertEqual(set(self.home.iterdir()), {self.zshrc})

    def test_preview_with_packages_does_not_write(self):
        result = self.run_setup("--packages")
        self.assertEqual(result.stdout.count(b"Would install Arch packages: stow"), 1)
        installs = [line for line in result.stdout.splitlines()
                    if line.startswith(b"==> Would install Arch packages:")]
        packages = set(b" ".join(installs).split())
        self.assertIn(b"alacritty", packages)
        self.assertIn(b"libpulse", packages)
        self.assertNotIn(b"ghostty", packages)
        self.assertEqual(result.stdout.count(b"Would clone TPM."), 1)
        self.assertEqual(self.zshrc.read_bytes(), self.original)
        self.assertEqual(set(self.home.iterdir()), {self.zshrc})

    def test_conflicts_stop_before_packages_or_config_writes(self):
        config = self.home / ".tmux.conf"
        config.write_bytes(b"keep existing")
        self.run_setup("--apply", "--packages", success=False)
        self.assertEqual(config.read_bytes(), b"keep existing")
        self.assertEqual(self.zshrc.read_bytes(), self.original)
        self.assertEqual(set(self.home.iterdir()), {self.zshrc, config})

    def test_invalid_zsh_markers_stop_before_linking_or_packages(self):
        self.zshrc.write_bytes(b"# >>> dotfiles v3 >>>\n")
        self.run_setup("--apply", "--packages", success=False)
        self.assertEqual(set(self.home.iterdir()), {self.zshrc})

    def test_invalid_git_markers_stop_before_linking_or_packages(self):
        for name in (".gitconfig", ".gitignore"):
            with self.subTest(name=name):
                target = self.home / name
                original = b"# >>> dotfiles v3 >>>\n"
                target.write_bytes(original)
                self.run_setup("--apply", "--packages", success=False)
                self.assertEqual(target.read_bytes(), original)
                self.assertEqual(self.zshrc.read_bytes(), self.original)
                self.assertEqual(set(self.home.iterdir()), {self.zshrc, target})
                target.unlink()

    def test_backup_directory_is_forwarded_to_all_updates(self):
        backups = self.base / "backups"
        backups.mkdir()
        config = self.home / ".gitconfig"
        ignore = self.home / ".gitignore"
        originals = {self.zshrc: self.original, config: b"# private preferences\n",
                     ignore: b"private-pattern"}
        for path, content in originals.items():
            path.write_bytes(content)
        self.run_setup("--apply", "--backup-dir", str(backups))
        self.assertEqual(len(list(backups.iterdir())), 3)
        for path, content in originals.items():
            saved = list(backups.glob(path.name + ".v3-backup-*"))
            self.assertEqual(len(saved), 1)
            self.assertEqual(saved[0].read_bytes(), content)
            self.assertEqual(saved[0].stat().st_mode & 0o777, 0o600)
        self.assertEqual(list(self.home.glob("*.v3-backup-*")), [])
        self.assertEqual(list(self.home.glob("*.v3-update-*")), [])

    def test_clone_collisions_stop_before_packages_or_config_writes(self):
        targets = (
            (self.home / ".tmux/plugins/tpm", "TPM"),
            (self.home / ".oh-my-zsh", "Oh My Zsh"),
            (self.home / ".oh-my-zsh/custom/plugins/zsh-autosuggestions", "zsh-autosuggestions"),
            (self.home / ".oh-my-zsh/custom/plugins/zsh-syntax-highlighting", "zsh-syntax-highlighting"),
        )
        for target, description in targets:
            for directory in (False, True):
                with self.subTest(target=target.relative_to(self.home), directory=directory):
                    target.parent.mkdir(parents=True, exist_ok=True)
                    omz_git = self.home / ".oh-my-zsh/.git"
                    if target.is_relative_to(self.home / ".oh-my-zsh/custom"):
                        omz_git.mkdir()
                    if directory:
                        target.mkdir()
                        preserved = target / "keep"
                    else:
                        preserved = target
                    preserved.write_bytes(b"unmanaged bytes")
                    before = set(self.home.rglob("*"))
                    result = self.run_setup("--apply", "--packages", success=False)
                    self.assertIn(f"{description} target already exists".encode(), result.stderr)
                    self.assertEqual(preserved.read_bytes(), b"unmanaged bytes")
                    self.assertEqual(self.zshrc.read_bytes(), self.original)
                    self.assertEqual(set(self.home.rglob("*")), before)
                    if directory:
                        preserved.unlink()
                        target.rmdir()
                    else:
                        target.unlink()
                    if omz_git.exists():
                        omz_git.rmdir()
                    parent = target.parent
                    while parent != self.home:
                        parent.rmdir()
                        parent = parent.parent

    def test_zsh_custom_inside_repository_stops_before_packages_or_writes(self):
        self.env["ZSH_CUSTOM"] = str(V3 / "zsh")
        self.run_setup("--apply", "--packages", success=False)
        self.assertEqual(self.zshrc.read_bytes(), self.original)
        self.assertEqual(set(self.home.iterdir()), {self.zshrc})

    def test_invalid_arguments_do_not_write_or_install(self):
        cases = (
            ("install.sh", ("--apply", "--unknown")),
            ("install.sh", ("--backup-dir",)),
            ("install.sh", ("--packages", "private-argument")),
            ("packages.sh", ("--apply", "--extra")),
            ("packages.sh", ("--packages",)),
            ("stow.sh", ("--apply", "--extra")),
            (".scripts/update-zshrc.sh", ("--apply", "--unknown")),
            (".scripts/update-zshrc.sh", ("--file",)),
        )
        for script, args in cases:
            with self.subTest(script=script, args=args):
                self.run_setup(*args, script=script, success=False)
                self.assertEqual(self.zshrc.read_bytes(), self.original)
                self.assertEqual(set(self.home.iterdir()), {self.zshrc})

    def test_existing_git_checkouts_are_untouched(self):
        targets = (
            self.home / ".tmux/plugins/tpm",
            self.home / ".oh-my-zsh",
            self.home / ".oh-my-zsh/custom/plugins/zsh-autosuggestions",
            self.home / ".oh-my-zsh/custom/plugins/zsh-syntax-highlighting",
        )
        for target in targets:
            (target / ".git").mkdir(parents=True)
            (target / ".git/HEAD").write_bytes(b"ref: refs/heads/local\n")
            (target / "local-file").write_bytes(b"local changes\n")
        before = {path: path.read_bytes() for path in self.home.rglob("*") if path.is_file()}
        entries = set(self.home.rglob("*"))
        self.mock_package_install()
        self.run_setup("--apply", script="packages.sh", external=True)
        self.assertEqual(set(self.home.rglob("*")), entries)
        self.assertEqual(
            {path: path.read_bytes() for path in self.home.rglob("*") if path.is_file()}, before,
        )
        self.assertEqual(len(self.log.read_text().splitlines()), 3)
        self.assertTrue(all(line.startswith("sudo:pacman -S --needed ")
                            for line in self.log.read_text().splitlines()))

    def test_apply_package_clones_hide_success_diagnostics(self):
        self.mock_package_install()
        self.mock_clone(success=True)
        result = self.run_setup("--apply", "--packages", external=True)
        self.assertEqual(result.stdout.count(b"Would clone TPM."), 1)
        self.assertLess(result.stdout.index(b"Would clone TPM."), result.stdout.index(b"Installing TPM."))
        calls = self.log.read_text().splitlines()
        clones = [call for call in calls if call.startswith("git:")]
        self.assertEqual(len(clones), 4)
        expected_urls = (
            "https://github.com/tmux-plugins/tpm.git",
            "https://github.com/ohmyzsh/ohmyzsh.git",
            "https://github.com/zsh-users/zsh-autosuggestions.git",
            "https://github.com/zsh-users/zsh-syntax-highlighting.git",
        )
        for call, url in zip(clones, expected_urls):
            self.assertTrue(call.startswith(f"git:clone --quiet --depth 1 -- {url} "))
        self.assertNotIn(b"Clone output:", result.stdout)
        self.assertNotIn(b"Clone diagnostic:", result.stderr)
        self.assertTrue((self.home / ".tmux/plugins/tpm/.git").is_dir())
        self.assertTrue((self.home / ".oh-my-zsh/.git").is_dir())
        self.assertEqual(self.zshrc.read_bytes().count(b"# >>> dotfiles v3 >>>"), 1)

    def test_apply_package_clones_hide_failure_diagnostics(self):
        self.mock_package_install()
        self.mock_clone(success=False)
        result = self.run_setup("--apply", "--packages", success=False, external=True)
        self.assertIn(b"Could not clone TPM", result.stderr)
        calls = self.log.read_text().splitlines()
        self.assertEqual(len([call for call in calls if call.startswith("git:")]), 1)
        self.assertEqual(self.zshrc.read_bytes(), self.original)
        self.assertEqual(set(self.home.iterdir()), {self.zshrc})
        self.assertNotIn(b"Clone output:", result.stdout)
        self.assertNotIn(b"Clone diagnostic:", result.stderr)

    def test_missing_git_block_commands_stop_before_any_write(self):
        self.hide_git_block_commands()
        for args in ((), ("--apply",)):
            with self.subTest(args=args):
                result = self.run_setup(*args, success=False)
                self.assertIn(b"needs missing packages: git-delta nano", result.stderr)
                self.assertIn(b"--allow-missing-deps", result.stderr)
                self.assert_untouched()

    def test_allow_missing_deps_writes_git_block_with_warning(self):
        self.hide_git_block_commands()
        result = self.run_setup("--apply", "--allow-missing-deps")
        self.assertIn(b"continuing because of --allow-missing-deps", result.stderr)
        self.assertTrue((self.home / ".gitconfig").read_bytes().startswith(b"# >>> dotfiles v3 >>>"))

    def test_package_preview_accepts_missing_git_block_commands(self):
        self.hide_git_block_commands()
        result = self.run_setup("--packages")
        self.assertIn(b"the package stage installs them: git-delta nano", result.stdout)
        installs = [line for line in result.stdout.splitlines()
                    if line.startswith(b"==> Would install Arch packages:")]
        packages = set(b" ".join(installs).split())
        for package in GIT_BLOCK_COMMANDS.values():
            self.assertIn(package.encode(), packages)
        self.assert_untouched()

    def run_package_stage_without_git_block_commands(self, installs):
        self.hide_git_block_commands()
        create = "".join(
            f'printf "#!/bin/sh\\n" > "$MOCK_BIN/{name}"; chmod +x "$MOCK_BIN/{name}"\n'
            for name in GIT_BLOCK_COMMANDS
        ) if installs else ""
        self.mock_command("sudo", 'printf "sudo:%s\\n" "$*" >> "$MOCK_LOG"\n' + create)
        self.mock_clone(success=True)
        return self.run_setup("--apply", "--packages", success=installs, external=True)

    def test_package_stage_provides_git_block_commands(self):
        self.run_package_stage_without_git_block_commands(installs=True)
        config = (self.home / ".gitconfig").read_bytes()
        self.assertTrue(config.startswith(b"# >>> dotfiles v3 >>>"))

    def test_git_block_commands_still_missing_after_package_stage_stop_writes(self):
        result = self.run_package_stage_without_git_block_commands(installs=False)
        self.assertIn(b"needs missing packages: git-delta nano", result.stderr)
        self.assertFalse((self.home / ".gitconfig").exists())
        self.assertFalse((self.home / ".tmux.conf").exists())
        self.assertEqual(self.zshrc.read_bytes(), self.original)

    def test_apply_and_reapply_only_touch_temporary_home(self):
        self.run_setup("--apply")
        self.assertTrue(self.zshrc.read_bytes().startswith(self.original))
        self.assertEqual(self.zshrc.read_bytes().count(b"# >>> dotfiles v3 >>>"), 1)
        self.assertEqual(
            (self.home / ".config/alacritty/alacritty.toml").resolve(),
            V3 / "alacritty/.config/alacritty/alacritty.toml",
        )
        self.assertFalse((self.home / ".tmux").is_symlink())
        self.assertFalse((self.home / ".config").is_symlink())
        before = self.zshrc.read_bytes()
        self.run_setup("--apply")
        self.assertEqual(self.zshrc.read_bytes(), before)
        self.assertEqual(len(list(self.home.glob(".zshrc.v3-backup-*"))), 1)


if __name__ == "__main__":
    unittest.main()
