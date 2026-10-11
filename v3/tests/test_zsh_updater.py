from pathlib import Path
import fcntl
import os
import shutil
import stat
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / ".scripts" / "update-zshrc.sh"
START = b"# >>> dotfiles v3 >>>"
END = b"# <<< dotfiles v3 <<<"
BLOCK = (
    START + b"\n"
    b"# Portable additions; existing settings remain untouched.\n"
    b'if [[ -r "$HOME/.config/zsh/v3.zsh" ]]; then\n'
    b'  source "$HOME/.config/zsh/v3.zsh"\n'
    b"fi\n" + END + b"\n"
)


class ZshUpdaterTests(unittest.TestCase):
    script = SCRIPT
    block = BLOCK
    updater_args = ()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / ".zshrc"
        # Synthetic private data only, never the host config.
        self.private = b'export DEMO_TOKEN="synthetic-secret"\nexport DEMO_PATH="/private/example"'
        self.path.write_bytes(self.private)
        os.chmod(self.path, 0o640)
        self.env = dict(os.environ, HOME=str(self.path.parent), CDPATH=".")

    def edit_target_on_tool_call(self, tool, edited):
        mock = self.path.parent / "bin"
        mock.mkdir()
        edit = self.path.parent / "edit"
        edit.write_bytes(edited)
        wrapper = mock / tool
        wrapper.write_text(
            '#!/usr/bin/env bash\n'
            'set -euo pipefail\n'
            'if [[ ! -e "$MOCK_CHANGED" ]]; then\n'
            '  cat -- "$MOCK_EDIT" > "$MOCK_TARGET"\n'
            '  : > "$MOCK_CHANGED"\n'
            'fi\n'
            'exec "$MOCK_REAL_TOOL" "$@"\n'
        )
        wrapper.chmod(0o700)
        self.env.update(
            PATH=str(mock) + os.pathsep + os.environ["PATH"],
            MOCK_REAL_TOOL=shutil.which(tool), MOCK_EDIT=str(edit),
            MOCK_TARGET=str(self.path), MOCK_CHANGED=str(self.path.parent / "changed"),
        )

    def mock_mv_publication(self, action, exchange=True):
        mock = self.path.parent / "bin"
        mock.mkdir()
        wrapper = mock / "mv"
        option = "--exchange" if exchange else "--update=none-fail"
        wrapper.write_text(
            '#!/usr/bin/env bash\n'
            'set -euo pipefail\n'
            f'if [[ " $* " == *" {option} "* ]]; then\n'
            + action + '\n'
            'fi\n'
            'exec "$MOCK_REAL_MV" "$@"\n'
        )
        wrapper.chmod(0o700)
        self.env.update(
            PATH=str(mock) + os.pathsep + os.environ["PATH"],
            MOCK_REAL_MV=shutil.which("mv"), MOCK_TARGET=str(self.path),
        )

    def run_updater(self, *args, target=None, success=True):
        repository = self.script.parents[2]
        result = subprocess.run(
            ["bash", str(self.script.relative_to(repository)), "--file",
             str(target or self.path), *self.updater_args, *args],
            cwd=repository, env=self.env, capture_output=True, timeout=15,
        )
        # Never include file contents in assertion diagnostics.
        output = result.stdout + result.stderr
        if b"synthetic-secret" in output or b"/private/example" in output:
            self.fail("Updater exposed private contents")
        if str(target or self.path).encode() in output or str(self.path.parent).encode() in output:
            self.fail("Updater exposed the target path")
        self.assertEqual(result.returncode == 0, success, "Unexpected updater status")
        return result

    def test_preview_does_not_write_or_expose_contents(self):
        self.run_updater()
        self.assertEqual(self.path.read_bytes(), self.private)
        self.assertEqual(list(self.path.parent.glob("*.v3-backup-*")), [])
        self.assertEqual(list(self.path.parent.glob("*.v3-update-*")), [])

    def test_apply_preserves_private_data_and_makes_private_backup(self):
        self.run_updater("--apply")
        self.assertEqual(self.path.read_bytes(), self.private + b"\n" + self.block)
        backups = list(self.path.parent.glob(".zshrc.v3-backup-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), self.private)
        self.assertEqual(stat.S_IMODE(backups[0].stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o640)
        self.assertEqual(list(self.path.parent.glob("*.v3-update-*")), [])

    def test_edit_before_snapshot_preserves_new_surrounding_bytes(self):
        original = self.private + b"\n" + START + b"\nold\n" + END + b"\nafter"
        self.path.write_bytes(original)
        prefix = b"# concurrent edit before snapshot\n" + self.private + b"\n"
        suffix = b"after\n# concurrent suffix without final newline"
        edited = prefix + START + b"\nold\n" + END + b"\n" + suffix
        self.edit_target_on_tool_call("mktemp", edited)

        self.run_updater("--apply")

        self.assertEqual(self.path.read_bytes(), prefix + self.block + suffix)
        backups = list(self.path.parent.glob(".zshrc.v3-backup-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), edited)
        self.assertEqual(list(self.path.parent.glob("*.v3-update-*")), [])

    def test_edit_after_snapshot_is_refused(self):
        original = self.private + b"\n" + START + b"\nold\n" + END + b"\nafter"
        self.path.write_bytes(original)
        edited = b"# concurrent edit after snapshot\n" + original
        self.edit_target_on_tool_call("grep", edited)

        result = self.run_updater("--apply", success=False)

        self.assertIn(b"Target changed during the update; refusing to replace it.", result.stderr)
        self.assertEqual(self.path.read_bytes(), edited)
        backups = list(self.path.parent.glob(".zshrc.v3-backup-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), original)
        self.assertEqual(list(self.path.parent.glob("*.v3-update-*")), [])

    def test_edit_immediately_before_exchange_is_saved_in_private_backup(self):
        edited = b"# late concurrent edit\n" + self.private
        edit = self.path.parent / "edit"
        edit.write_bytes(edited)
        self.env["MOCK_EDIT"] = str(edit)
        self.mock_mv_publication('  cat -- "$MOCK_EDIT" > "$MOCK_TARGET"')

        result = self.run_updater("--apply", success=False)

        self.assertIn(b"Recovery warning:", result.stderr)
        self.assertEqual(self.path.read_bytes(), self.private + b"\n" + self.block)
        backups = list(self.path.parent.glob(".zshrc.v3-backup-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), edited)
        self.assertEqual(stat.S_IMODE(backups[0].stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o640)
        self.assertEqual(list(self.path.parent.glob("*.v3-update-*")), [])

    def test_target_appearing_immediately_before_publication_is_not_clobbered(self):
        self.path.unlink()
        self.mock_mv_publication('  printf "concurrent creation" > "$MOCK_TARGET"', exchange=False)

        self.run_updater("--apply", success=False)

        self.assertEqual(self.path.read_bytes(), b"concurrent creation")
        self.assertEqual(list(self.path.parent.glob("*.v3-backup-*")), [])
        self.assertEqual(list(self.path.parent.glob("*.v3-update-*")), [])

    def test_apply_lock_collision_refuses_without_writes(self):
        before = set(self.path.parent.iterdir())
        lock_fd = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = self.run_updater("--apply", success=False)
            self.assertIn(b"Another updater is applying changes", result.stderr)
            self.assertEqual(self.path.read_bytes(), self.private)
            self.assertEqual(set(self.path.parent.iterdir()), before)
            self.run_updater()
            self.assertEqual(set(self.path.parent.iterdir()), before)
        finally:
            os.close(lock_fd)
        self.run_updater("--apply")

    def assert_displaced_data_survives_publication_failure(self, action):
        edited = b"# late edit before failed publication\n" + self.private
        edit = self.path.parent / "edit"
        edit.write_bytes(edited)
        self.env["MOCK_EDIT"] = str(edit)
        self.mock_mv_publication(
            '  cat -- "$MOCK_EDIT" > "$MOCK_TARGET"\n'
            '  "$MOCK_REAL_MV" "$@"\n' + action
        )

        result = self.run_updater("--apply", success=False)

        self.assertIn(b"Recovery warning:", result.stderr)
        self.assertEqual(self.path.read_bytes(), self.private + b"\n" + self.block)
        backups = list(self.path.parent.glob(".zshrc.v3-backup-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), edited)
        self.assertEqual(stat.S_IMODE(backups[0].stat().st_mode), 0o600)
        self.assertEqual(list(self.path.parent.glob("*.v3-update-*")), [])

    def test_failure_after_exchange_retains_displaced_data(self):
        self.assert_displaced_data_survives_publication_failure('  exit 1')

    def test_interruption_after_exchange_retains_displaced_data(self):
        self.assert_displaced_data_survives_publication_failure('  kill -TERM "$PPID"\n  exit 0')

    def test_missing_mv_capability_refuses_without_writes(self):
        self.mock_mv_publication('  exit 1')
        wrapper = self.path.parent / "bin" / "mv"
        wrapper.write_text('#!/usr/bin/env bash\nprintf "unsupported mv\\n"\n')
        before = set(self.path.parent.iterdir())

        result = self.run_updater("--apply", success=False)

        self.assertIn(b"GNU mv with atomic publication and flock are required", result.stderr)
        self.assertEqual(self.path.read_bytes(), self.private)
        self.assertEqual(set(self.path.parent.iterdir()), before)
        self.run_updater()

    def test_unavailable_flock_refuses_without_writes(self):
        mock = self.path.parent / "bin"
        mock.mkdir()
        wrapper = mock / "flock"
        wrapper.write_text('#!/usr/bin/env bash\nexit 127\n')
        wrapper.chmod(0o700)
        self.env["PATH"] = str(mock) + os.pathsep + os.environ["PATH"]
        before = set(self.path.parent.iterdir())

        self.run_updater("--apply", success=False)

        self.assertEqual(self.path.read_bytes(), self.private)
        self.assertEqual(set(self.path.parent.iterdir()), before)
        self.run_updater()

    def test_repeated_apply_is_noop(self):
        self.run_updater("--apply")
        before = self.path.read_bytes()
        mtime = self.path.stat().st_mtime_ns
        result = self.run_updater("--apply")
        self.assertEqual(result.stdout, b"Already up to date.\n")
        self.assertEqual(self.path.stat().st_mtime_ns, mtime)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(len(list(self.path.parent.glob(".zshrc.v3-backup-*"))), 1)

    def test_managed_block_replacement_preserves_surrounding_bytes(self):
        self.path.write_bytes(b"before\n" + START + b"\nold\n" + END + b"\nafter")
        self.run_updater("--apply")
        self.assertEqual(self.path.read_bytes(), b"before\n" + self.block + b"after")

    def test_crlf_and_non_ascii_bytes_outside_block_are_preserved(self):
        before = "# prieš\r\n".encode()
        after = "# po\r\n".encode()
        self.path.write_bytes(before + START + b"\r\nold\r\n" + END + b"\r\n" + after)
        self.run_updater("--apply")
        self.assertEqual(self.path.read_bytes(), before + self.block + after)

    def test_end_marker_without_final_newline(self):
        self.path.write_bytes(START + b"\nold\n" + END)
        self.run_updater("--apply")
        self.assertEqual(self.path.read_bytes(), self.block)

    def test_invalid_markers_do_not_write_or_backup(self):
        for original in (
            START, END, START + b"\n" + START + b"\n" + END,
            END + b"\n" + START,
        ):
            with self.subTest(case=original):
                self.path.write_bytes(original)
                self.run_updater("--apply", success=False)
                self.assertEqual(self.path.read_bytes(), original)
                self.assertEqual(list(self.path.parent.glob("*.v3-backup-*")), [])

    def test_symlink_is_refused(self):
        link = self.path.parent / "link"
        link.symlink_to(self.path)
        self.run_updater("--apply", target=link, success=False)
        self.assertEqual(self.path.read_bytes(), self.private)

    def test_repository_target_is_refused(self):
        target = self.script.parent / ".zshrc"
        self.run_updater("--apply", target=target, success=False)
        self.assertFalse(target.exists())

    def test_target_inside_repository_via_parent_symlink_is_refused(self):
        link = self.path.parent / "checkout"
        link.symlink_to(self.script.parent, target_is_directory=True)
        self.run_updater("--apply", target=link / ".zshrc", success=False)

    def test_missing_file_is_created_privately(self):
        self.path.unlink()
        self.run_updater("--apply")
        self.assertEqual(self.path.read_bytes(), self.block)
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)

    def test_invalid_target_diagnostics_do_not_expose_paths(self):
        self.run_updater("--apply", target=self.path.parent / "missing" / "file", success=False)
        self.run_updater("--apply", target=self.path.parent, success=False)


if __name__ == "__main__":
    unittest.main()
