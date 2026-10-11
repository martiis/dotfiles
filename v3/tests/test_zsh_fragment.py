from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

FRAGMENT = Path(__file__).resolve().parents[1] / "zsh" / ".config" / "zsh" / "v3.zsh"
ZSH = shutil.which("zsh")
NAMES = ("ls", "lt", "cat", "..", "...", "....")


@unittest.skipUnless(ZSH, "Zsh is required")
class ZshFragmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.zdotdir = self.home / "zdotdir"
        self.zdotdir.mkdir()
        self.bin = self.home / "bin"
        self.bin.mkdir()
        for directory in (self.home, self.zdotdir):
            (directory / ".zshrc").write_text('print -r -- "unexpected startup file"\n')
        self.env = {
            "HOME": str(self.home), "ZDOTDIR": str(self.zdotdir),
            "PATH": str(self.bin), "TERM": "dumb",
        }

    def mock_optional_commands(self):
        for name in ("eza", "bat"):
            executable = self.bin / name
            executable.write_text(f'#!/bin/sh\nprintf "%s\\n" "{name}" "$@"\n')
            executable.chmod(0o700)

    def run_fragment(self, before="", after="", interactive=True):
        command = [ZSH, "-d", "-f"]
        if interactive:
            command.append("-i")
        result = subprocess.run(
            [*command, "-c", before + '\nsource "$1"\n' + after, "fragment-test", str(FRAGMENT)],
            cwd=self.home, env=self.env, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        return result.stdout.splitlines()

    def test_existing_aliases_stay_effective(self):
        self.mock_optional_commands()
        before = "\n".join(f"alias {name}='print -r -- alias:{name}'" for name in NAMES)
        after = "\n".join(f'eval "{name}"' for name in NAMES)
        self.assertEqual(self.run_fragment(before, after), [f"alias:{name}" for name in NAMES])

    def test_existing_functions_stay_effective(self):
        self.mock_optional_commands()
        before = "\n".join(f"functions[{name}]='print -r -- function:{name}'" for name in NAMES)
        after = "\n".join(f'eval "{name}"' for name in NAMES)
        self.assertEqual(self.run_fragment(before, after), [f"function:{name}" for name in NAMES])

    def test_missing_defaults_are_added_with_optional_commands(self):
        self.mock_optional_commands()
        self.assertEqual(
            self.run_fragment(after='eval ls\neval lt\neval "cat sample.txt"'),
            ["eza", "-lh", "--group-directories-first", "--icons=auto",
             "eza", "--tree", "--level=2", "--long", "--icons", "--git",
             "bat", "sample.txt"],
        )
        nested = self.home / "one" / "two" / "three"
        nested.mkdir(parents=True)
        for name, destination in zip(NAMES[3:], (nested.parent, nested.parent.parent, self.home)):
            with self.subTest(alias=name):
                self.assertEqual(
                    self.run_fragment(after=f'cd "{nested}"\neval "{name}"\npwd'),
                    [str(destination)],
                )

    def test_optional_defaults_are_absent_without_commands(self):
        self.assertEqual(
            self.run_fragment(after='print -r -- $+aliases[ls] $+aliases[lt] $+aliases[cat]'),
            ["0 0 0"],
        )

    def test_optional_private_overrides_are_sourced(self):
        (self.home / ".zshrc.local").write_text("alias ls='print -r -- private-override'\n")
        self.mock_optional_commands()
        self.assertEqual(self.run_fragment(after="eval ls"), ["private-override"])

    def test_noninteractive_shell_does_not_load_fragment_or_private_overrides(self):
        (self.home / ".zshrc.local").write_text('print -r -- "unexpected private override"\n')
        self.mock_optional_commands()
        self.assertEqual(
            self.run_fragment(
                after='print -r -- $+aliases[ls] $+aliases[lt] $+aliases[cat] '
                      '$+aliases[..] $+aliases[...] $+aliases[....]',
                interactive=False,
            ),
            ["0 0 0 0 0 0"],
        )


if __name__ == "__main__":
    unittest.main()
