"""Tests for WriteTool."""
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pi.coding.tools.write import WriteTool


class TestWriteTool:
    """Test cases for WriteTool."""

    def test_init_default_cwd(self, tmp_path: Path) -> None:
        """Test initialization with default cwd."""
        tool = WriteTool(cwd=tmp_path)
        assert tool.cwd == tmp_path

    def test_init_no_cwd(self) -> None:
        """Test initialization without cwd uses current directory."""
        tool = WriteTool()
        assert tool.cwd == Path.cwd()

    def test_get_schema(self) -> None:
        """Test parameter schema."""
        tool = WriteTool()
        schema = tool.get_schema()

        assert "path" in schema.properties
        assert schema.properties["path"].type.value == "string"
        assert "path" in schema.required

        assert "content" in schema.properties
        assert schema.properties["content"].type.value == "string"
        assert "content" in schema.required

    def test_resolve_path_absolute(self, tmp_path: Path) -> None:
        """Test resolving absolute paths."""
        tool = WriteTool(cwd=tmp_path)
        absolute = tmp_path / "test.txt"

        result = tool.resolve_path(str(absolute))
        assert result == absolute

    def test_resolve_path_relative(self, tmp_path: Path) -> None:
        """Test resolving relative paths."""
        tool = WriteTool(cwd=tmp_path)
        result = tool.resolve_path("test.txt")
        assert result == (tmp_path / "test.txt").resolve()

    @pytest.mark.asyncio
    async def test_execute_create_new_file(self, tmp_path: Path) -> None:
        """Test creating a new file."""
        tool = WriteTool(cwd=tmp_path)

        result = await tool._execute(
            tool_call_id="test-1",
            params={"path": "new.txt", "content": "Hello, World!"},
            signal=None,
            on_update=None,
        )

        test_file = tmp_path / "new.txt"
        assert test_file.exists()
        assert test_file.read_text() == "Hello, World!"

        assert result["content"][0]["text"] == f"Created new file: {test_file}"
        assert result["details"]["existed"] is False
        assert result["details"]["size"] == 13
        assert result["details"]["lines"] == 1

    @pytest.mark.asyncio
    async def test_execute_overwrite_existing_file(self, tmp_path: Path) -> None:
        """Test overwriting an existing file."""
        test_file = tmp_path / "existing.txt"
        test_file.write_text("Old content")

        tool = WriteTool(cwd=tmp_path)

        result = await tool._execute(
            tool_call_id="test-2",
            params={"path": "existing.txt", "content": "New content"},
            signal=None,
            on_update=None,
        )

        assert test_file.read_text() == "New content"

        assert result["content"][0]["text"] == f"Overwrote existing file: {test_file}"
        assert result["details"]["existed"] is True

    @pytest.mark.asyncio
    async def test_execute_create_nested_directories(self, tmp_path: Path) -> None:
        """Test creating file with nested directories."""
        tool = WriteTool(cwd=tmp_path)

        result = await tool._execute(
            tool_call_id="test-3",
            params={"path": "nested/dir/file.txt", "content": "content"},
            signal=None,
            on_update=None,
        )

        test_file = tmp_path / "nested" / "dir" / "file.txt"
        assert test_file.exists()
        assert test_file.read_text() == "content"

    @pytest.mark.asyncio
    async def test_execute_multiline_content(self, tmp_path: Path) -> None:
        """Test writing multiline content."""
        tool = WriteTool(cwd=tmp_path)

        content = "Line 1\nLine 2\nLine 3\n"
        result = await tool._execute(
            tool_call_id="test-4",
            params={"path": "multiline.txt", "content": content},
            signal=None,
            on_update=None,
        )

        assert result["details"]["lines"] == 4  # 3 lines + 1 for trailing newline count

    @pytest.mark.asyncio
    async def test_execute_empty_content(self, tmp_path: Path) -> None:
        """Test writing empty content."""
        tool = WriteTool(cwd=tmp_path)

        result = await tool._execute(
            tool_call_id="test-5",
            params={"path": "empty.txt", "content": ""},
            signal=None,
            on_update=None,
        )

        test_file = tmp_path / "empty.txt"
        assert test_file.read_text() == ""
        assert result["details"]["size"] == 0

    @pytest.mark.asyncio
    async def test_execute_unicode_content(self, tmp_path: Path) -> None:
        """Test writing Unicode content."""
        tool = WriteTool(cwd=tmp_path)

        content = "Hello 世界 🌍"
        result = await tool._execute(
            tool_call_id="test-6",
            params={"path": "unicode.txt", "content": content},
            signal=None,
            on_update=None,
        )

        test_file = tmp_path / "unicode.txt"
        assert test_file.read_text(encoding="utf-8") == content

    @pytest.mark.asyncio
    async def test_execute_with_abort_signal(self, tmp_path: Path) -> None:
        """Test execution with abort signal."""
        tool = WriteTool(cwd=tmp_path)
        signal = MagicMock()
        signal.aborted = True

        with pytest.raises(RuntimeError, match="Operation aborted"):
            await tool._execute(
                tool_call_id="test-7",
                params={"path": "test.txt", "content": "content"},
                signal=signal,
                on_update=None,
            )

    @pytest.mark.asyncio
    async def test_file_size_tracking(self, tmp_path: Path) -> None:
        """Test that file size is correctly tracked."""
        tool = WriteTool(cwd=tmp_path)

        content = "x" * 1000
        result = await tool._execute(
            tool_call_id="test-8",
            params={"path": "size_test.txt", "content": content},
            signal=None,
            on_update=None,
        )

        assert result["details"]["size"] == 1000
