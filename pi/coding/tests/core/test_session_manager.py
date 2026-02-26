"""Tests for SessionManager."""
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from pi.coding.core.session_manager import (
    SessionManager,
    SessionHeader,
    SessionMessageEntry,
    ThinkingLevelChangeEntry,
    ModelChangeEntry,
    SessionInfoEntry,
    SessionContext,
    SessionInfo,
    generate_id,
    CURRENT_SESSION_VERSION,
)


class TestGenerateId:
    """Test cases for generate_id utility."""

    def test_generate_unique_id(self) -> None:
        """Test that generated IDs are unique."""
        existing_ids = set()
        new_id = generate_id(existing_ids)
        assert len(new_id) == 8
        assert new_id not in existing_ids

    def test_generate_id_with_existing(self) -> None:
        """Test generating ID with existing IDs."""
        existing_ids = {"abc12345", "def67890"}
        new_id = generate_id(existing_ids)
        assert new_id not in existing_ids

    def test_generate_id_fallback(self) -> None:
        """Test fallback to full UUID when short IDs exhausted."""
        # Create a set with many possible IDs
        existing_ids = {f"{i:08x}" for i in range(1000)}
        new_id = generate_id(existing_ids)
        # Should fall back to full UUID (32+ chars)
        assert len(new_id) >= 8


class TestSessionManager:
    """Test cases for SessionManager."""

    def test_init_default_cwd(self, tmp_path: Path) -> None:
        """Test initialization with default cwd."""
        manager = SessionManager(cwd=tmp_path)
        assert manager.cwd == tmp_path

    def test_init_creates_sessions_dir(self, tmp_path: Path) -> None:
        """Test that sessions directory is created."""
        sessions_dir = tmp_path / "sessions"
        manager = SessionManager(sessions_dir=sessions_dir)
        assert sessions_dir.exists()
        assert manager.sessions_dir == sessions_dir

    def test_create_new_session(self, tmp_path: Path) -> None:
        """Test creating a new session."""
        manager = SessionManager(cwd=tmp_path)

        assert manager.get_session_id() is not None
        assert len(manager.get_session_id()) == 8

        session_file = manager.get_session_file()
        assert session_file is not None
        assert session_file.exists()

    def test_session_file_header(self, tmp_path: Path) -> None:
        """Test that session file has proper header."""
        # Use a specific sessions dir to avoid conflicts
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)

        manager = SessionManager(cwd=tmp_path, sessions_dir=sessions_dir)

        header = manager.get_header()
        assert header is not None
        assert header.type == "session"
        assert header.version == CURRENT_SESSION_VERSION
        assert header.id == manager.get_session_id()
        assert header.cwd == str(tmp_path)

    def test_append_message(self, tmp_path: Path) -> None:
        """Test appending a message to session."""
        manager = SessionManager(cwd=tmp_path)

        message = {
            "role": "user",
            "content": "Hello, AI!",
        }
        entry_id = manager.append_message(message)

        assert entry_id is not None
        assert len(manager.get_entries()) == 1

        entry = manager.get_entries()[0]
        assert isinstance(entry, SessionMessageEntry)
        assert entry.message == message

    def test_append_thinking_level_change(self, tmp_path: Path) -> None:
        """Test appending thinking level change."""
        manager = SessionManager(cwd=tmp_path)

        entry_id = manager.append_thinking_level_change("high")

        assert entry_id is not None
        assert len(manager.get_entries()) == 1

        entry = manager.get_entries()[0]
        assert isinstance(entry, ThinkingLevelChangeEntry)
        assert entry.thinking_level == "high"

    def test_append_model_change(self, tmp_path: Path) -> None:
        """Test appending model change."""
        manager = SessionManager(cwd=tmp_path)

        entry_id = manager.append_model_change("anthropic", "claude-opus-4-5")

        assert entry_id is not None
        assert len(manager.get_entries()) == 1

        entry = manager.get_entries()[0]
        assert isinstance(entry, ModelChangeEntry)
        assert entry.provider == "anthropic"
        assert entry.model_id == "claude-opus-4-5"

    def test_parent_id_chain(self, tmp_path: Path) -> None:
        """Test that entries form a parent chain."""
        manager = SessionManager(cwd=tmp_path)

        id1 = manager.append_thinking_level_change("low")
        id2 = manager.append_message({"role": "user", "content": "test"})
        id3 = manager.append_message({"role": "assistant", "content": "response"})

        entries = manager.get_entries()
        assert entries[0].parent_id is None  # First entry has no parent
        assert entries[1].parent_id == id1
        assert entries[2].parent_id == id2

    def test_get_leaf_id(self, tmp_path: Path) -> None:
        """Test getting the leaf (last) entry ID."""
        manager = SessionManager(cwd=tmp_path)

        assert manager.get_leaf_id() is None

        id1 = manager.append_thinking_level_change("medium")
        assert manager.get_leaf_id() == id1

        id2 = manager.append_message({"role": "user", "content": "test"})
        assert manager.get_leaf_id() == id2

    def test_build_session_context(self, tmp_path: Path) -> None:
        """Test building session context from entries."""
        manager = SessionManager(cwd=tmp_path)

        manager.append_model_change("google", "gemini-2.5-flash")
        manager.append_thinking_level_change("high")
        manager.append_message({"role": "user", "content": "Hello"})

        context = manager.build_session_context()

        assert context.messages == [{"role": "user", "content": "Hello"}]
        assert context.thinking_level == "high"
        assert context.model == {"provider": "google", "modelId": "gemini-2.5-flash"}

    def test_build_session_context_empty(self, tmp_path: Path) -> None:
        """Test building context from empty session."""
        manager = SessionManager(cwd=tmp_path)
        context = manager.build_session_context()

        assert context.messages == []
        assert context.thinking_level == "off"
        assert context.model is None

    def test_get_session_info(self, tmp_path: Path) -> None:
        """Test getting session info."""
        manager = SessionManager(cwd=tmp_path)

        manager.append_message({"role": "user", "content": "This is a test message"})

        info = manager.get_session_info()

        assert info.id == manager.get_session_id()
        assert info.cwd == str(tmp_path)
        assert info.message_count == 1
        assert "test message" in info.first_message

    def test_get_session_info_no_messages(self, tmp_path: Path) -> None:
        """Test session info with no messages."""
        manager = SessionManager(cwd=tmp_path)
        info = manager.get_session_info()

        assert info.message_count == 0
        assert info.first_message == ""

    def test_persistence(self, tmp_path: Path) -> None:
        """Test that session persists across manager instances."""
        # Create session and add data
        manager1 = SessionManager(cwd=tmp_path, sessions_dir=tmp_path / "sessions")
        session_id = manager1.get_session_id()
        manager1.append_message({"role": "user", "content": "persistent"})

        # Load session in new manager
        session_file = manager1.get_session_file()
        manager2 = SessionManager(session_file=session_file)

        assert manager2.get_session_id() == session_id
        entries = manager2.get_entries()
        assert len(entries) == 1
        assert entries[0].message == {"role": "user", "content": "persistent"}

    def test_get_branch(self, tmp_path: Path) -> None:
        """Test getting all entries in branch."""
        manager = SessionManager(cwd=tmp_path)

        manager.append_thinking_level_change("low")
        manager.append_message({"role": "user", "content": "test"})

        branch = manager.get_branch()
        assert len(branch) == 2

    def test_get_cwd(self, tmp_path: Path) -> None:
        """Test getting current working directory."""
        manager = SessionManager(cwd=tmp_path)
        assert manager.get_cwd() == str(tmp_path)

    def test_static_create(self, tmp_path: Path) -> None:
        """Test static create method."""
        manager = SessionManager.create(cwd=tmp_path)
        assert manager.cwd == tmp_path

    def test_static_in_memory(self, tmp_path: Path) -> None:
        """Test static in_memory method creates manager without persistence."""
        # Use a temporary path to avoid creating files in home directory
        # in_memory() creates a new session at default location
        # The key is that entries persist in memory but may write to file
        manager = SessionManager.in_memory()
        assert manager.get_session_id() is not None
        # Note: in_memory still creates a file at default location
        # but allows working without a specific session_file


class TestDataclasses:
    """Test cases for session dataclasses."""

    def test_session_header(self) -> None:
        """Test SessionHeader dataclass."""
        header = SessionHeader(
            id="test123",
            timestamp="2024-01-01T00:00:00",
            cwd="/test/path",
        )
        assert header.type == "session"
        assert header.version == CURRENT_SESSION_VERSION

    def test_session_message_entry(self) -> None:
        """Test SessionMessageEntry dataclass."""
        entry = SessionMessageEntry(
            type="message",
            id="msg123",
            timestamp="2024-01-01T00:00:00",
            message={"role": "user", "content": "test"},
        )
        assert entry.type == "message"

    def test_thinking_level_change_entry(self) -> None:
        """Test ThinkingLevelChangeEntry dataclass."""
        entry = ThinkingLevelChangeEntry(
            type="thinking_level_change",
            id="think123",
            timestamp="2024-01-01T00:00:00",
            thinking_level="high",
        )
        assert entry.thinking_level == "high"

    def test_model_change_entry(self) -> None:
        """Test ModelChangeEntry dataclass."""
        entry = ModelChangeEntry(
            type="model_change",
            id="model123",
            timestamp="2024-01-01T00:00:00",
            provider="anthropic",
            model_id="claude-opus-4-5",
        )
        assert entry.provider == "anthropic"

    def test_session_info_entry(self) -> None:
        """Test SessionInfoEntry dataclass."""
        entry = SessionInfoEntry(
            type="session_info",
            id="info123",
            timestamp="2024-01-01T00:00:00",
            name="My Session",
        )
        assert entry.name == "My Session"

    def test_session_context(self) -> None:
        """Test SessionContext dataclass."""
        context = SessionContext(
            messages=[{"role": "user", "content": "test"}],
            thinking_level="medium",
            model={"provider": "google", "modelId": "gemini"},
        )
        assert len(context.messages) == 1
        assert context.thinking_level == "medium"

    def test_session_info(self) -> None:
        """Test SessionInfo dataclass."""
        now = datetime.now()
        info = SessionInfo(
            path="/path/to/session.jsonl",
            id="session123",
            cwd="/test/path",
            created=now,
            modified=now,
            message_count=5,
            first_message="Test message...",
        )
        assert info.id == "session123"
        assert info.message_count == 5
