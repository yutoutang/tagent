"""Pytest configuration and fixtures for pi-coding tests."""
import asyncio
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def event_loop_policy() -> asyncio.DefaultEventLoopPolicy:
    """Event loop policy fixture."""
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """
    Create a temporary directory for testing.

    This is a wrapper around pytest's tmp_path fixture
    with a more descriptive name.
    """
    return tmp_path


@pytest.fixture
def mock_signal() -> MagicMock:
    """Create a mock abort signal."""
    signal = MagicMock()
    signal.aborted = False
    return signal


@pytest.fixture
def mock_on_update() -> MagicMock:
    """Create a mock on_update callback."""
    return MagicMock()


@pytest.fixture
def sample_text_file(tmp_path: Path) -> Path:
    """Create a sample text file for testing."""
    file_path = tmp_path / "sample.txt"
    file_path.write_text("Hello, World!\nThis is a test file.\nWith multiple lines.")
    return file_path


@pytest.fixture
def sample_code_file(tmp_path: Path) -> Path:
    """Create a sample Python file for testing."""
    content = '''"""Sample module for testing."""

def hello(name: str) -> str:
    """Say hello to someone."""
    return f"Hello, {name}!"


class SampleClass:
    """A sample class."""

    def __init__(self, value: int):
        """Initialize with value."""
        self.value = value

    def double(self) -> int:
        """Double the value."""
        return self.value * 2
'''
    file_path = tmp_path / "sample.py"
    file_path.write_text(content)
    return file_path


@pytest.fixture
def sample_directory(tmp_path: Path) -> Path:
    """Create a sample directory structure for testing."""
    base = tmp_path / "project"
    base.mkdir()

    (base / "src").mkdir()
    (base / "tests").mkdir()
    (base / "docs").mkdir()

    (base / "src" / "main.py").write_text("# Main module")
    (base / "src" / "utils.py").write_text("# Utils module")
    (base / "tests" / "test_main.py").write_text("# Test main")
    (base / "docs" / "README.md").write_text("# Documentation")

    return base
