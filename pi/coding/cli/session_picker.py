"""Session picker for pi-coding.

Converted from TypeScript cli/session-picker.ts
"""

from typing import Optional, Any
from dataclasses import dataclass


@dataclass
class SessionInfo:
    """Information about a session."""
    path: str
    label: str
    timestamp: int
    message_count: int
    model: Optional[str] = None


class SessionPicker:
    """Interactive session picker UI."""

    def __init__(self, sessions_dir: str):
        """
        Initialize the session picker.

        Args:
            sessions_dir: Directory containing session files
        """
        self.sessions_dir = sessions_dir

    async def pick_session(self) -> Optional[SessionInfo]:
        """
        Show interactive session picker.

        Returns:
            Selected session info or None if cancelled
        """
        # TODO: Implement interactive session picker
        # This requires TUI components
        return None

    def list_sessions(self) -> list[SessionInfo]:
        """
        List all available sessions.

        Returns:
            List of session info
        """
        # TODO: Implement session listing
        return []
