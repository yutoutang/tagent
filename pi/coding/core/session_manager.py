"""
Session manager for pi-coding.

Simplified implementation converted from TypeScript core/session-manager.ts
Handles session persistence, branching, and compaction.
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Union
from dataclasses import dataclass, field, asdict


CURRENT_SESSION_VERSION = 3


@dataclass
class SessionHeader:
    """Session header metadata."""
    type: str = "session"
    version: int = CURRENT_SESSION_VERSION
    id: str = ""
    timestamp: str = ""
    cwd: str = ""
    parent_session: Optional[str] = None


@dataclass
class SessionEntryBase:
    """Base class for session entries."""
    type: str = ""
    id: str = ""
    parent_id: Optional[str] = None
    timestamp: str = ""


@dataclass
class SessionMessageEntry(SessionEntryBase):
    """Message entry in session."""
    type: str = "message"
    message: dict[str, Any] = field(default_factory=dict)


@dataclass
class ThinkingLevelChangeEntry(SessionEntryBase):
    """Thinking level change entry."""
    type: str = "thinking_level_change"
    thinking_level: str = "off"


@dataclass
class ModelChangeEntry(SessionEntryBase):
    """Model change entry."""
    type: str = "model_change"
    provider: str = ""
    model_id: str = ""
    thinking_level: str = "off"  # Add default for consistency


@dataclass
class SessionInfoEntry(SessionEntryBase):
    """Session metadata entry (user-defined display name, etc)."""
    type: str = "session_info"
    name: Optional[str] = None


# Union type for all session entries
SessionEntry = Union[
    SessionMessageEntry,
    ThinkingLevelChangeEntry,
    ModelChangeEntry,
    SessionInfoEntry,
]


@dataclass
class SessionContext:
    """Session context for agent."""
    messages: list[dict[str, Any]] = field(default_factory=list)
    thinking_level: str = "off"
    model: Optional[dict[str, str]] = None


@dataclass
class SessionInfo:
    """Information about a session."""
    path: str
    id: str
    cwd: str
    name: Optional[str] = None
    parent_session_path: Optional[str] = None
    created: datetime = field(default_factory=datetime.now)
    modified: datetime = field(default_factory=datetime.now)
    message_count: int = 0
    first_message: str = ""


def generate_id(existing_ids: set[str]) -> str:
    """Generate a unique short ID (8 hex chars)."""
    for _ in range(100):
        new_id = uuid.uuid4().hex[:8]
        if new_id not in existing_ids:
            return new_id
    # Fallback to full UUID
    return uuid.uuid4().hex


class SessionManager:
    """
    Manages agent session persistence and retrieval.

    Sessions are stored as JSONL files with a tree structure
    supporting branching and navigation.
    """

    def __init__(
        self,
        cwd: Optional[str | Path] = None,
        sessions_dir: Optional[str | Path] = None,
        session_file: Optional[str | Path] = None,
    ):
        """
        Initialize the session manager.

        Args:
            cwd: Current working directory
            sessions_dir: Directory for session files
            session_file: Specific session file to use (creates new if None)
        """
        from ..config import get_sessions_dir

        self.cwd = Path(cwd) if cwd else Path.cwd()
        self.sessions_dir = Path(sessions_dir) if sessions_dir else get_sessions_dir()
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        # Session state
        self._session_id: Optional[str] = None
        self._session_file: Optional[Path] = None
        self._entries: list[SessionEntry] = []
        self._entry_ids: set[str] = set()

        # Load or create session
        if session_file:
            self._session_file = Path(session_file)
            self._load_session()
        else:
            self._create_new_session()

    def _create_new_session(self) -> None:
        """Create a new session."""
        self._session_id = generate_id(set())
        self._entries = []
        self._entry_ids = set()

        # Create session file
        timestamp = datetime.now().isoformat()
        header = SessionHeader(
            id=self._session_id,
            timestamp=timestamp,
            cwd=str(self.cwd),
        )

        # Generate filename from session ID
        filename = f"--{self.cwd.name}--" if self.cwd.name else "--cwd--"
        self._session_file = self.sessions_dir / filename / "session.jsonl"
        self._session_file.parent.mkdir(parents=True, exist_ok=True)

        # Write header
        self._write_entry(asdict(header))

    def _load_session(self) -> None:
        """Load existing session from file."""
        if not self._session_file or not self._session_file.exists():
            self._create_new_session()
            return

        self._entries = []
        self._entry_ids = set()

        with open(self._session_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    entry_dict = json.loads(line)
                    entry_type = entry_dict.get("type")

                    if entry_type == "session":
                        self._session_id = entry_dict.get("id", "")
                        continue

                    # Parse entry based on type
                    entry: SessionEntry
                    if entry_type == "message":
                        entry = SessionMessageEntry(**entry_dict)
                    elif entry_type == "thinking_level_change":
                        entry = ThinkingLevelChangeEntry(**entry_dict)
                    elif entry_type == "model_change":
                        entry = ModelChangeEntry(**entry_dict)
                    elif entry_type == "session_info":
                        entry = SessionInfoEntry(**entry_dict)
                    else:
                        # Unknown entry type, skip
                        continue

                    self._entries.append(entry)
                    self._entry_ids.add(entry.id)

                except json.JSONDecodeError:
                    # Skip malformed lines
                    continue

    def _write_entry(self, entry_dict: dict[str, Any]) -> None:
        """Write an entry to the session file."""
        if not self._session_file:
            return

        with open(self._session_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry_dict) + "\n")

    def get_cwd(self) -> str:
        """Get the current working directory."""
        return str(self.cwd)

    def get_session_dir(self) -> Path:
        """Get the sessions directory."""
        return self.sessions_dir

    def get_session_id(self) -> str:
        """Get the current session ID."""
        return self._session_id or ""

    def get_session_file(self) -> Optional[Path]:
        """Get the current session file path."""
        return self._session_file

    def get_leaf_id(self) -> Optional[str]:
        """Get the ID of the last entry (leaf node)."""
        if self._entries:
            return self._entries[-1].id
        return None

    def get_branch(self) -> list[SessionEntry]:
        """Get all entries in the current branch."""
        return list(self._entries)

    def get_entries(self) -> list[SessionEntry]:
        """Get all session entries."""
        return list(self._entries)

    def get_header(self) -> Optional[SessionHeader]:
        """Get the session header."""
        if self._session_file and self._session_file.exists():
            with open(self._session_file, "r", encoding="utf-8") as f:
                first_line = f.readline().strip()
                if first_line:
                    try:
                        header_dict = json.loads(first_line)
                        if header_dict.get("type") == "session":
                            return SessionHeader(**header_dict)
                    except json.JSONDecodeError:
                        pass
        return None

    def append_message(self, message: dict[str, Any]) -> str:
        """
        Append a message to the session.

        Args:
            message: AgentMessage dict

        Returns:
            Entry ID
        """
        entry_id = generate_id(self._entry_ids)
        timestamp = datetime.now().isoformat()
        parent_id = self.get_leaf_id()

        entry = SessionMessageEntry(
            type="message",
            id=entry_id,
            parent_id=parent_id,
            timestamp=timestamp,
            message=message,
        )

        self._entries.append(entry)
        self._entry_ids.add(entry_id)
        self._write_entry(asdict(entry))

        return entry_id

    def append_thinking_level_change(self, level: str) -> str:
        """
        Append a thinking level change to the session.

        Args:
            level: New thinking level

        Returns:
            Entry ID
        """
        entry_id = generate_id(self._entry_ids)
        timestamp = datetime.now().isoformat()
        parent_id = self.get_leaf_id()

        entry = ThinkingLevelChangeEntry(
            type="thinking_level_change",
            id=entry_id,
            parent_id=parent_id,
            timestamp=timestamp,
            thinking_level=level,
        )

        self._entries.append(entry)
        self._entry_ids.add(entry_id)
        self._write_entry(asdict(entry))

        return entry_id

    def append_model_change(self, provider: str, model_id: str) -> str:
        """
        Append a model change to the session.

        Args:
            provider: Model provider
            model_id: Model ID

        Returns:
            Entry ID
        """
        entry_id = generate_id(self._entry_ids)
        timestamp = datetime.now().isoformat()
        parent_id = self.get_leaf_id()

        entry = ModelChangeEntry(
            type="model_change",
            id=entry_id,
            parent_id=parent_id,
            timestamp=timestamp,
            provider=provider,
            model_id=model_id,
        )

        self._entries.append(entry)
        self._entry_ids.add(entry_id)
        self._write_entry(asdict(entry))

        return entry_id

    def build_session_context(self) -> SessionContext:
        """
        Build the session context from entries.

        Walks from leaf to root, collecting messages and settings.
        """
        messages: list[dict[str, Any]] = []
        thinking_level = "off"
        model: Optional[dict[str, str]] = None

        for entry in self._entries:
            if entry.type == "message":
                messages.append(entry.message)
            elif entry.type == "thinking_level_change":
                thinking_level = entry.thinking_level
            elif entry.type == "model_change":
                model = {"provider": entry.provider, "modelId": entry.model_id}

        return SessionContext(
            messages=messages,
            thinking_level=thinking_level,
            model=model,
        )

    def get_session_info(self) -> SessionInfo:
        """Get information about the current session."""
        header = self.get_header()
        message_count = sum(1 for e in self._entries if e.type == "message")

        first_message = ""
        for entry in self._entries:
            if entry.type == "message":
                msg = entry.message
                if isinstance(msg, dict):
                    role = msg.get("role", "")
                    content = msg.get("content", "")
                    if role == "user" and isinstance(content, str):
                        first_message = content[:100]
                        break
                    elif role == "user" and isinstance(content, list):
                        for block in content:
                            if block.get("type") == "text":
                                first_message = block.get("text", "")[:100]
                                break

        return SessionInfo(
            path=str(self._session_file) if self._session_file else "",
            id=self._session_id or "",
            cwd=self.get_cwd(),
            created=datetime.fromisoformat(header.timestamp) if header else datetime.now(),
            modified=datetime.now(),
            message_count=message_count,
            first_message=first_message,
        )

    @staticmethod
    def create(cwd: Optional[str | Path] = None) -> "SessionManager":
        """
        Create a new session manager.

        Args:
            cwd: Current working directory

        Returns:
            New SessionManager instance
        """
        return SessionManager(cwd=cwd)

    @staticmethod
    def in_memory() -> "SessionManager":
        """Create an in-memory session manager (no persistence)."""
        return SessionManager(session_file=None)


__all__ = [
    "CURRENT_SESSION_VERSION",
    "SessionHeader",
    "SessionEntryBase",
    "SessionMessageEntry",
    "ThinkingLevelChangeEntry",
    "ModelChangeEntry",
    "SessionInfoEntry",
    "SessionEntry",
    "SessionContext",
    "SessionInfo",
    "generate_id",
    "SessionManager",
]
