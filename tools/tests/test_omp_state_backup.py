import fcntl
import os
import runpy
import sqlite3
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / ".local" / "bin" / "omp-state-backup"


class OmpStateBackupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.agent_dir = self.root / "agent"
        self.backup_dir = self.root / "backups"
        self.agent_dir.mkdir()
        for name in ("agent.db", "models.db", "history.db"):
            self.create_database(self.agent_dir / name)

    def create_database(self, path: Path) -> None:
        with sqlite3.connect(path) as connection:
            connection.execute("CREATE TABLE records (value TEXT NOT NULL)")
            connection.execute("INSERT INTO records (value) VALUES (?)", (path.name,))

    def run_backup(
        self,
        keep: int = 48,
        agent_dir: Path | None = None,
        backup_dir: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        selected_agent_dir = self.agent_dir if agent_dir is None else agent_dir
        selected_backup_dir = self.backup_dir if backup_dir is None else backup_dir
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--agent-dir",
                str(selected_agent_dir),
                "--backup-dir",
                str(selected_backup_dir),
                "--keep",
                str(keep),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

    def successful_snapshot(self, result: subprocess.CompletedProcess[str]) -> Path:
        self.assertEqual(result.returncode, 0, result.stderr)
        snapshot = Path(result.stdout.strip())
        self.assertTrue(snapshot.is_dir())
        return snapshot

    def snapshot_names(self) -> set[str]:
        if not self.backup_dir.exists():
            return set()
        return {
            entry.name
            for entry in self.backup_dir.iterdir()
            if entry.is_dir() and not entry.is_symlink() and entry.name.startswith("snapshot-")
        }

    def file_mode(self, path: Path) -> int:
        return stat.S_IMODE(path.stat().st_mode)

    def test_copies_committed_wal_data_and_retains_snapshot_contents(self) -> None:
        (self.agent_dir / "config.yml").write_text("name: primary\n", encoding="utf-8")
        (self.agent_dir / "models.yml").write_text("models: []\n", encoding="utf-8")
        (self.agent_dir / "keybindings.yml").write_text("keys: {}\n", encoding="utf-8")
        connection = sqlite3.connect(self.agent_dir / "agent.db")
        self.addCleanup(connection.close)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("INSERT INTO records (value) VALUES (?)", ("committed in wal",))
        connection.commit()
        self.assertTrue((self.agent_dir / "agent.db-wal").exists())
        snapshot = self.successful_snapshot(self.run_backup())
        self.assertFalse((snapshot / "agent.db-wal").exists())
        self.assertFalse((snapshot / "agent.db-shm").exists())
        with sqlite3.connect(snapshot / "agent.db") as copied_database:
            rows = copied_database.execute("SELECT value FROM records ORDER BY rowid").fetchall()
        self.assertIn(("committed in wal",), rows)
        for name in ("models.db", "history.db"):
            with sqlite3.connect(snapshot / name) as copied_database:
                rows = copied_database.execute("SELECT value FROM records ORDER BY rowid").fetchall()
            self.assertEqual(rows, [(name,)])
        self.assertEqual((snapshot / "config.yml").read_text(encoding="utf-8"), "name: primary\n")
        self.assertEqual((snapshot / "models.yml").read_text(encoding="utf-8"), "models: []\n")
        self.assertEqual((snapshot / "keybindings.yml").read_text(encoding="utf-8"), "keys: {}\n")

    def test_corruption_failure_preserves_existing_snapshots(self) -> None:
        self.successful_snapshot(self.run_backup())
        snapshots_before = self.snapshot_names()
        (self.agent_dir / "models.db").write_bytes(b"not a sqlite database")
        failed_result = self.run_backup()
        self.assertEqual(failed_result.returncode, 1)
        self.assertIn("models.db", failed_result.stderr)
        self.assertEqual(self.snapshot_names(), snapshots_before)

    def test_fsync_failure_before_publication_preserves_existing_snapshots(self) -> None:
        self.successful_snapshot(self.run_backup())
        snapshots_before = self.snapshot_names()
        backup_module = runpy.run_path(str(SCRIPT), run_name="omp_state_backup")
        original_fsync = os.fsync
        staging_sync_failed = False

        def fail_staging_sync(file_descriptor: int) -> None:
            nonlocal staging_sync_failed
            if stat.S_ISDIR(os.fstat(file_descriptor).st_mode) and not staging_sync_failed:
                staging_sync_failed = True
                raise OSError("injected staging sync failure")
            original_fsync(file_descriptor)

        with mock.patch.object(backup_module["os"], "fsync", side_effect=fail_staging_sync):
            with self.assertRaisesRegex(OSError, "injected staging sync failure"):
                backup_module["create_snapshot"](self.agent_dir, self.backup_dir, 48)
        self.assertTrue(staging_sync_failed)
        self.assertEqual(self.snapshot_names(), snapshots_before)
        self.assertFalse(any(entry.name.startswith(".omp-state-backup-") for entry in self.backup_dir.iterdir()))

    def test_rejects_a_concurrent_backup(self) -> None:
        self.backup_dir.mkdir()
        lock_path = self.backup_dir / ".omp-state-backup.lock"
        with lock_path.open("w", encoding="utf-8") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = self.run_backup()
        self.assertEqual(result.returncode, 1)
        self.assertIn("already running", result.stderr)

    def test_rejects_nested_agent_and_backup_directories(self) -> None:
        backup_inside_agent = self.agent_dir / "backups"
        inside_result = self.run_backup(backup_dir=backup_inside_agent)
        self.assertEqual(inside_result.returncode, 1)
        self.assertIn("inside the agent directory", inside_result.stderr)
        agent_inside_backup = self.backup_dir / "agent"
        agent_inside_backup.mkdir(parents=True)
        for name in ("agent.db", "models.db", "history.db"):
            self.create_database(agent_inside_backup / name)
        enclosing_result = self.run_backup(agent_dir=agent_inside_backup)
        self.assertEqual(enclosing_result.returncode, 1)
        self.assertIn("inside the backup directory", enclosing_result.stderr)

    def test_retention_only_removes_matching_snapshot_directories(self) -> None:
        self.backup_dir.mkdir()
        oldest = self.backup_dir / "snapshot-20000101T000000000000Z"
        retained = self.backup_dir / "snapshot-20010101T000000000000Z"
        unrelated = self.backup_dir / "notes"
        symlink = self.backup_dir / "snapshot-20020101T000000000000Z"
        oldest.mkdir()
        retained.mkdir()
        unrelated.mkdir()
        symlink.symlink_to(unrelated, target_is_directory=True)
        snapshot = self.successful_snapshot(self.run_backup(keep=2))
        self.assertFalse(oldest.exists())
        self.assertTrue(retained.is_dir())
        self.assertTrue(unrelated.is_dir())
        self.assertTrue(symlink.is_symlink())
        self.assertTrue(snapshot.is_dir())

    def test_sets_owner_only_permissions(self) -> None:
        (self.agent_dir / "config.yml").write_text("name: primary\n", encoding="utf-8")
        snapshot = self.successful_snapshot(self.run_backup())
        self.assertEqual(self.file_mode(self.backup_dir), 0o700)
        self.assertEqual(self.file_mode(snapshot), 0o700)
        self.assertEqual(self.file_mode(self.backup_dir / ".omp-state-backup.lock"), 0o600)
        for name in ("agent.db", "models.db", "history.db", "config.yml"):
            self.assertEqual(self.file_mode(snapshot / name), 0o600)


if __name__ == "__main__":
    unittest.main()
