import os
from pathlib import Path
import shutil
import tempfile

import test_zsh_updater as zsh_updater


class BlockUpdaterTests(zsh_updater.ZshUpdaterTests):
    script = zsh_updater.SCRIPT.with_name("update-block.sh")
    body = b"# shared synthetic settings\n"
    block = zsh_updater.START + b"\n" + body + zsh_updater.END + b"\n"

    def setUp(self):
        super().setUp()
        self.body_file = self.path.parent / "body"
        self.body_file.write_bytes(self.body)
        self.updater_args = ("--block", str(self.body_file))

    def run_updater(self, *args, **kwargs):
        result = super().run_updater(*args, **kwargs)
        if self.body.rstrip(b"\n") in result.stdout + result.stderr:
            self.fail("Updater exposed the block body")
        return result

    def test_missing_file_with_prepend_is_created_privately(self):
        self.path.unlink()
        self.run_updater("--position", "prepend", "--apply")
        self.assertEqual(self.path.read_bytes(), self.block)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_append_with_existing_newline(self):
        original = self.private + b"\n"
        self.path.write_bytes(original)
        self.run_updater("--position", "append", "--apply")
        self.assertEqual(self.path.read_bytes(), original + self.block)

    def test_prepend_preserves_original_without_newline(self):
        self.run_updater("--position", "prepend", "--apply")
        self.assertEqual(self.path.read_bytes(), self.block + self.private)
        mtime = self.path.stat().st_mtime_ns
        result = self.run_updater("--position", "prepend", "--apply")
        self.assertEqual(result.stdout, b"Already up to date.\n")
        self.assertEqual(self.path.read_bytes(), self.block + self.private)
        self.assertEqual(self.path.stat().st_mtime_ns, mtime)

    def test_prepend_replaces_existing_block_in_place(self):
        prefix = b"# prefix\r\n\xff\x00\n"
        suffix = b"# suffix\r\n\xfe\x00"
        self.path.write_bytes(prefix + zsh_updater.START + b"\nold\n" + zsh_updater.END + b"\n" + suffix)
        self.run_updater("--position", "prepend", "--apply")
        self.assertEqual(self.path.read_bytes(), prefix + self.block + suffix)

    def test_body_without_trailing_newline(self):
        self.body_file.write_bytes(self.body.rstrip(b"\n"))
        self.run_updater("--apply")
        self.assertEqual(self.path.read_bytes(), self.private + b"\n" + self.block)

    def test_body_markers_are_refused_without_backups_or_changes(self):
        before = set(self.path.parent.iterdir())
        for marker in (zsh_updater.START, zsh_updater.END):
            for ending in (b"", b"\n", b"\r\n"):
                with self.subTest(marker=marker, ending=ending):
                    self.body_file.write_bytes(b"# body\n" + marker + ending)
                    self.run_updater("--apply", success=False)
                    self.assertEqual(self.path.read_bytes(), self.private)
                    self.assertEqual(set(self.path.parent.iterdir()), before)

    def test_explicit_backup_directory_keeps_private_backup_only_there(self):
        directory = self.path.parent / "backups"
        directory.mkdir()
        self.run_updater("--backup-dir", str(directory), "--apply")
        saved = list(directory.iterdir())
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0].read_bytes(), self.private)
        self.assertEqual(saved[0].stat().st_mode & 0o777, 0o600)
        self.assertEqual(list(self.path.parent.glob("*.v3-backup-*")), [])
        self.assertEqual(list(self.path.parent.glob("*.v3-update-*")), [])

    def test_late_edit_recovery_is_retained_in_explicit_backup_directory(self):
        directory = self.path.parent / "backups"
        directory.mkdir()
        edited = b"# late concurrent edit\n" + self.private
        edit = self.path.parent / "edit"
        edit.write_bytes(edited)
        self.env["MOCK_EDIT"] = str(edit)
        self.mock_mv_publication('  cat -- "$MOCK_EDIT" > "$MOCK_TARGET"')
        result = self.run_updater("--backup-dir", str(directory), "--apply", success=False)
        self.assertIn(b"Recovery warning:", result.stderr)
        self.assertEqual(self.path.read_bytes(), self.private + b"\n" + self.block)
        saved = list(directory.iterdir())
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0].read_bytes(), edited)
        self.assertEqual(saved[0].stat().st_mode & 0o777, 0o600)
        self.assertEqual(list(self.path.parent.glob("*.v3-backup-*")), [])
        self.assertEqual(list(self.path.parent.glob("*.v3-update-*")), [])

    def test_unsuitable_backup_directories_refused_before_changes(self):
        link = self.path.parent / "backup-link"
        link.symlink_to(self.path.parent, target_is_directory=True)
        for directory in (link, str(link) + "/", self.body_file,
                          self.path.parent / "missing", self.script.parent):
            with self.subTest(directory=directory):
                before = set(self.path.parent.iterdir())
                self.run_updater("--backup-dir", str(directory), "--apply", success=False)
                self.assertEqual(self.path.read_bytes(), self.private)
                self.assertEqual(set(self.path.parent.iterdir()), before)

    def test_cross_device_backup_refused_before_any_writes(self):
        directory = Path("/dev/shm")
        if not directory.is_dir() or directory.stat().st_dev == self.path.parent.stat().st_dev:
            self.skipTest("No second temporary filesystem available")
        with tempfile.TemporaryDirectory(dir=directory) as backup_dir:
            before = set(self.path.parent.iterdir())
            for args in ((), ("--apply",)):
                result = self.run_updater("--backup-dir", backup_dir, *args, success=False)
                self.assertIn(b"same filesystem", result.stderr)
                self.assertNotIn(backup_dir.encode(), result.stdout + result.stderr)
                self.assertEqual(self.path.read_bytes(), self.private)
                self.assertEqual(set(self.path.parent.iterdir()), before)
                self.assertEqual(list(Path(backup_dir).iterdir()), [])

    def test_no_copy_staging_failure_precedes_publication(self):
        directory = self.path.parent / "backups"
        directory.mkdir()
        mock = self.path.parent / "bin"
        mock.mkdir()
        wrapper = mock / "mv"
        wrapper.write_text(
            '#!/usr/bin/env bash\n'
            'if [[ " $* " == *" --exchange "* ]]; then\n'
            '  : > "$MOCK_PUBLISHED"\n'
            'elif [[ " $* " == *" --no-copy "* ]]; then\n'
            '  exit 1\n'
            'fi\n'
            'exec "$MOCK_REAL_MV" "$@"\n'
        )
        wrapper.chmod(0o700)
        published = self.path.parent / "published"
        self.env.update(PATH=str(mock) + os.pathsep + os.environ["PATH"],
                        MOCK_REAL_MV=shutil.which("mv"), MOCK_PUBLISHED=str(published))
        self.run_updater("--backup-dir", str(directory), "--apply", success=False)
        self.assertFalse(published.exists())
        self.assertEqual(self.path.read_bytes(), self.private)
        saved = list(directory.iterdir())
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0].read_bytes(), self.private)
        self.assertEqual(saved[0].stat().st_mode & 0o777, 0o600)
        self.assertEqual(list(self.path.parent.glob("*.v3-backup-*")), [])
        self.assertEqual(list(self.path.parent.glob("*.v3-update-*")), [])

    def test_invalid_arguments_refused_without_changes(self):
        before = set(self.path.parent.iterdir())
        for args in (("--position",), ("--position", "invalid"), ("--block",),
                     ("--backup-dir",), ("--block", str(self.path.parent / "missing"))):
            with self.subTest(args=args):
                self.run_updater(*args, "--apply", success=False)
                self.assertEqual(self.path.read_bytes(), self.private)
                self.assertEqual(set(self.path.parent.iterdir()), before)
