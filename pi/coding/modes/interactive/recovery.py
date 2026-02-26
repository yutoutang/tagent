"""Crash recovery and session restoration utilities."""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CrashRecovery:
    """
    Handles crash recovery and session restoration.

    Provides functionality to:
    - Save session state periodically
    - Detect crashes from previous runs
    - Restore sessions after crashes
    - Clean up stale crash markers
    """

    CRASH_MARKER_FILE = ".crash_marker"
    BACKUP_SUFFIX = ".backup"

    def __init__(self, sessions_dir: Path):
        """
        Initialize crash recovery.

        Args:
            sessions_dir: Directory containing session files
        """
        self.sessions_dir = sessions_dir
        self.crash_marker = sessions_dir / self.CRASH_MARKER_FILE

    def mark_session_start(self) -> None:
        """Mark the start of a session for crash detection."""
        try:
            with open(self.crash_marker, "w") as f:
                json.dump({
                    "start_time": datetime.now().isoformat(),
                    "pid": self._get_pid(),
                }, f)
        except IOError as e:
            logger.warning(f"Could not write crash marker: {e}")

    def mark_session_end(self) -> None:
        """Mark the end of a session (normal shutdown)."""
        try:
            if self.crash_marker.exists():
                self.crash_marker.unlink()
        except IOError as e:
            logger.warning(f"Could not remove crash marker: {e}")

    def detect_crash(self) -> bool:
        """
        Detect if the previous session crashed.

        Returns:
            True if crash marker exists
        """
        return self.crash_marker.exists()

    def get_crash_info(self) -> Optional[dict]:
        """
        Get information about the previous crash.

        Returns:
            Crash info dict or None if no crash detected
        """
        if not self.detect_crash():
            return None

        try:
            with open(self.crash_marker) as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            logger.warning(f"Could not read crash marker: {e}")
            return None

    def get_recoverable_sessions(self) -> list[Path]:
        """
        Get list of sessions that can be recovered.

        Returns:
            List of session file paths
        """
        sessions = []

        for session_file in self.sessions_dir.glob("**/session.jsonl"):
            # Check if there's a backup
            backup_file = session_file.with_suffix(self.BACKUP_SUFFIX)

            if backup_file.exists():
                sessions.append(backup_file)
            elif session_file.exists():
                sessions.append(session_file)

        return sessions

    def backup_session(self, session_file: Path) -> None:
        """
        Create a backup of a session file.

        Args:
            session_file: Path to the session file
        """
        backup_file = session_file.with_suffix(self.BACKUP_SUFFIX)

        try:
            if session_file.exists():
                import shutil
                shutil.copy2(session_file, backup_file)
                logger.debug(f"Backed up session to {backup_file}")
        except (IOError, shutil.Error) as e:
            logger.warning(f"Could not backup session: {e}")

    def restore_session(self, backup_file: Path) -> Optional[Path]:
        """
        Restore a session from backup.

        Args:
            backup_file: Path to the backup file

        Returns:
            Path to the restored session file or None
        """
        if not backup_file.exists():
            return None

        # Remove .backup suffix to get original path
        session_file = backup_file.with_suffix("")

        try:
            import shutil
            shutil.copy2(backup_file, session_file)
            logger.info(f"Restored session from {backup_file}")
            return session_file
        except (IOError, shutil.Error) as e:
            logger.error(f"Could not restore session: {e}")
            return None

    def cleanup_old_backups(self, days: int = 7) -> int:
        """
        Clean up old backup files.

        Args:
            days: Age in days after which to delete backups

        Returns:
            Number of backups cleaned up
        """
        import time

        count = 0
        cutoff = time.time() - (days * 86400)

        for backup_file in self.sessions_dir.glob(f"**/*{self.BACKUP_SUFFIX}"):
            try:
                if backup_file.stat().st_mtime < cutoff:
                    backup_file.unlink()
                    count += 1
                    logger.debug(f"Cleaned up old backup: {backup_file}")
            except IOError as e:
                logger.warning(f"Could not delete backup {backup_file}: {e}")

        return count

    @staticmethod
    def _get_pid() -> int:
        """Get the current process ID."""
        import os
        return os.getpid()


class SessionCheckpoint:
    """
    Periodic session checkpointing for crash recovery.

    Saves session state at regular intervals to minimize data loss.
    """

    def __init__(self, session_file: Path, interval_seconds: int = 60):
        """
        Initialize session checkpointing.

        Args:
            session_file: Path to the session file
            interval_seconds: Checkpoint interval in seconds
        """
        self.session_file = session_file
        self.interval = interval_seconds
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._last_position = 0

    async def start(self) -> None:
        """Start periodic checkpointing."""
        self._running = True
        self._task = asyncio.create_task(self._checkpoint_loop())

    async def stop(self) -> None:
        """Stop periodic checkpointing."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _checkpoint_loop(self) -> None:
        """Main checkpoint loop."""
        import asyncio

        while self._running:
            await asyncio.sleep(self.interval)
            if self._running:
                await self._create_checkpoint()

    async def _create_checkpoint(self) -> None:
        """Create a checkpoint of the current session state."""
        recovery = CrashRecovery(self.session_file.parent)
        recovery.backup_session(self.session_file)


def setup_crash_recovery(sessions_dir: Path) -> CrashRecovery:
    """
    Set up crash recovery for a sessions directory.

    Args:
        sessions_dir: Directory containing session files

    Returns:
        CrashRecovery instance
    """
    recovery = CrashRecovery(sessions_dir)

    # Clean up old backups on startup
    recovery.cleanup_old_backups()

    return recovery


__all__ = [
    "CrashRecovery",
    "SessionCheckpoint",
    "setup_crash_recovery",
]
