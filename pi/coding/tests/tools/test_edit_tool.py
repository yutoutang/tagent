"""Tests for EditTool."""
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pi.coding.tools.edit import EditTool


class TestEditTool:
    """Test cases for EditTool."""

    def test_init_default_cwd(self, tmp_path: Path) -> None:
        """Test initialization with default cwd."""
        tool = EditTool(cwd=tmp_path)
        assert tool.cwd == tmp_path

    def test_init_no_cwd(self) -> None:
        """Test initialization without cwd uses current directory."""
        tool = EditTool()
        assert tool.cwd == Path.cwd()

    def test_get_schema(self) -> None:
        """Test parameter schema."""
        tool = EditTool()
        schema = tool.get_schema()

        assert "path" in schema.properties
        assert "path" in schema.required

        assert "search" in schema.properties
        assert "search" in schema.required

        assert "replace" in schema.properties
        assert "replace" in schema.required

    @pytest.mark.asyncio
    async def test_execute_single_replacement(self, tmp_path: Path) -> None:
        """Test single text replacement."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        tool = EditTool(cwd=tmp_path)
        result = await tool._execute(
            tool_call_id="test-1",
            params={"path": "test.txt", "search": "World", "replace": "Python"},
            signal=None,
            on_update=None,
        )

        assert test_file.read_text() == "Hello, Python!"
        assert result["details"]["found"] is True
        assert result["details"]["replacements"] == 1

    @pytest.mark.asyncio
    async def test_execute_multiple_replacements(self, tmp_path: Path) -> None:
        """Test multiple text replacements."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("cat cat cat")

        tool = EditTool(cwd=tmp_path)
        result = await tool._execute(
            tool_call_id="test-2",
            params={"path": "test.txt", "search": "cat", "replace": "dog"},
            signal=None,
            on_update=None,
        )

        assert test_file.read_text() == "dog dog dog"
        assert result["details"]["replacements"] == 3

    @pytest.mark.asyncio
    async def test_execute_search_not_found(self, tmp_path: Path) -> None:
        """Test when search text is not found."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        tool = EditTool(cwd=tmp_path)
        result = await tool._execute(
            tool_call_id="test-3",
            params={"path": "test.txt", "search": "Goodbye", "replace": "Hello"},
            signal=None,
            on_update=None,
        )

        assert test_file.read_text() == "Hello, World!"  # Unchanged
        assert result["details"]["found"] is False
        assert result["details"]["replacements"] == 0

    @pytest.mark.asyncio
    async def test_execute_file_not_found(self, tmp_path: Path) -> None:
        """Test editing a non-existent file."""
        tool = EditTool(cwd=tmp_path)

        with pytest.raises(FileNotFoundError, match="File not found"):
            await tool._execute(
                tool_call_id="test-4",
                params={"path": "nonexistent.txt", "search": "x", "replace": "y"},
                signal=None,
                on_update=None,
            )

    @pytest.mark.asyncio
    async def test_execute_multiline_search(self, tmp_path: Path) -> None:
        """Test multiline search and replace."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Line 1\nLine 2\nLine 3\n")

        tool = EditTool(cwd=tmp_path)
        result = await tool._execute(
            tool_call_id="test-5",
            params={"path": "test.txt", "search": "Line 2\n", "replace": "Replaced Line\n"},
            signal=None,
            on_update=None,
        )

        assert test_file.read_text() == "Line 1\nReplaced Line\nLine 3\n"
        assert result["details"]["replacements"] == 1

    @pytest.mark.asyncio
    async def test_execute_empty_search(self, tmp_path: Path) -> None:
        """Test with empty search string."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello")

        tool = EditTool(cwd=tmp_path)
        result = await tool._execute(
            tool_call_id="test-6",
            params={"path": "test.txt", "search": "", "replace": "X"},
            signal=None,
            on_update=None,
        )

        # Empty search should match at every position
        assert result["details"]["replacements"] > 0

    @pytest.mark.asyncio
    async def test_execute_unicode_search(self, tmp_path: Path) -> None:
        """Test search with Unicode characters."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello 世界")

        tool = EditTool(cwd=tmp_path)
        result = await tool._execute(
            tool_call_id="test-7",
            params={"path": "test.txt", "search": "世界", "replace": "World"},
            signal=None,
            on_update=None,
        )

        assert test_file.read_text() == "Hello World"
        assert result["details"]["replacements"] == 1

    @pytest.mark.asyncio
    async def test_execute_with_abort_signal(self, tmp_path: Path) -> None:
        """Test execution with abort signal."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello")

        tool = EditTool(cwd=tmp_path)
        signal = MagicMock()
        signal.aborted = True

        with pytest.raises(RuntimeError, match="Operation aborted"):
            await tool._execute(
                tool_call_id="test-8",
                params={"path": "test.txt", "search": "Hello", "replace": "Goodbye"},
                signal=signal,
                on_update=None,
            )

    @pytest.mark.asyncio
    async def test_resolve_path_absolute(self, tmp_path: Path) -> None:
        """Test resolving absolute paths."""
        tool = EditTool(cwd=tmp_path)
        absolute = tmp_path / "test.txt"

        result = tool.resolve_path(str(absolute))
        assert result == absolute

    @pytest.mark.asyncio
    async def test_resolve_path_relative(self, tmp_path: Path) -> None:
        """Test resolving relative paths."""
        tool = EditTool(cwd=tmp_path)
        result = tool.resolve_path("test.txt")
        assert result == (tmp_path / "test.txt").resolve()
