import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

try:
    import tomllib
except ImportError:
    tomllib = None

V3 = Path(__file__).resolve().parents[1]


class PackageTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("stow"), "GNU Stow is required")
    def test_packages_link_only_into_temporary_home_and_can_be_unlinked(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            env = dict(os.environ, HOME=directory)
            command = ["stow", "--no-folding", "-d", str(V3), "-t", str(target)]
            packages = ["alacritty", "zsh", "tmux"]
            subprocess.run(command + packages, env=env, check=True, capture_output=True)
            expected = {
                ".config/alacritty/alacritty.toml": "alacritty",
                ".config/alacritty/theme/gruvbox-dark.toml": "alacritty",
                ".config/xdg-terminals.list": "alacritty",
                ".config/gnome-xdg-terminals.list": "alacritty",
                ".config/zsh/v3.zsh": "zsh",
                ".tmux.conf": "tmux",
                ".tmux/scripts/rename-window.sh": "tmux",
                ".tmux/scripts/ram_progress.sh": "tmux",
            }
            for relative, package in expected.items():
                self.assertEqual((target / relative).resolve(), V3 / package / relative)
            self.assertFalse((target / ".tmux").is_symlink())
            self.assertFalse((target / ".config").is_symlink())
            self.assertFalse((target / ".config/alacritty").is_symlink())
            self.assertFalse((target / ".config/alacritty/theme").is_symlink())
            self.assertFalse((target / ".zshrc").exists())
            self.assertFalse((target / ".gitconfig").exists())
            self.assertFalse((target / ".gitignore").exists())
            subprocess.run(command + ["-D"] + packages, env=env, check=True, capture_output=True)
            for relative in expected:
                self.assertFalse((target / relative).exists())
                self.assertFalse((target / relative).is_symlink())

    @unittest.skipIf(tomllib is None, "Python 3.11+ is required for TOML validation")
    def test_alacritty_config_imports_bundled_theme_and_uses_external_audio(self):
        directory = V3 / "alacritty/.config/alacritty"
        config = tomllib.loads((directory / "alacritty.toml").read_text())
        self.assertEqual(config["general"]["import"], ["theme/gruvbox-dark.toml"])
        theme = tomllib.loads((directory / config["general"]["import"][0]).read_text())
        self.assertEqual(theme["colors"]["primary"]["background"], "#282828")
        self.assertEqual(config["env"]["TERM"], "xterm-256color")
        self.assertEqual(config["bell"]["command"]["program"], "paplay")
        for name in ("xdg-terminals.list", "gnome-xdg-terminals.list"):
            self.assertEqual((directory.parent / name).read_text(), "Alacritty.desktop\n")

    @unittest.skipUnless(shutil.which("tmux"), "tmux is required")
    def test_tmux_config_loads_in_isolated_server_without_plugins(self):
        with tempfile.TemporaryDirectory() as directory:
            env = dict(os.environ, HOME=directory, TMUX="")
            socket = str(Path(directory) / "tmux.sock")
            command = ["tmux", "-S", socket]
            def run(*args):
                return subprocess.run(
                    command + list(args), env=env, check=True,
                    capture_output=True, text=True, timeout=10,
                ).stdout.strip()
            try:
                run("-f", str(V3 / "tmux" / ".tmux.conf"), "new-session", "-d", "-s", "v3check")
                self.assertEqual(run("show-options", "-gv", "prefix"), "C-s")
                self.assertEqual(run("show-options", "-gv", "status"), "2")
                self.assertEqual(run("show-options", "-gv", "mouse"), "on")
                self.assertNotIn(".tmux.conf:", run("show-messages"))
            finally:
                subprocess.run(command + ["kill-server"], env=env, capture_output=True)

    def test_no_copied_zshrc_or_absolute_home_paths(self):
        self.assertFalse((V3 / "zsh" / ".zshrc").exists())
        for path in V3.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                if b"/" + b"home/" in path.read_bytes():
                    self.fail(f"Absolute home path in {path.relative_to(V3)}")


if __name__ == "__main__":
    unittest.main()
