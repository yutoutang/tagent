"""Tests for ReadTool."""
import asyncio
from pathlib import Path
from textwrap import dedent
from unittest.mock import AsyncMock, MagicMock

import pytest

from pi.coding.tools.read import ReadTool, DEFAULT_MAX_LINES, DEFAULT_MAX_BYTES, format_size


class TestReadTool:
    """Test cases for ReadTool."""

    def test_init_default_cwd(self, tmp_path: Path) -> None:
        """Test initialization with default cwd."""
        tool = ReadTool(cwd=tmp_path)
        assert tool.cwd == tmp_path

    def test_init_no_cwd(self) -> None:
        """Test initialization without cwd uses current directory."""
        tool = ReadTool()
        assert tool.cwd == Path.cwd()

    def test_get_schema(self) -> None:
        """Test parameter schema."""
        tool = ReadTool()
        schema = tool.get_schema()

        assert "path" in schema.properties
        assert schema.properties["path"].type.value == "string"
        assert "path" in schema.required

        assert "offset" in schema.properties
        assert schema.properties["offset"].type.value == "number"
        assert "offset" not in schema.required

        assert "limit" in schema.properties
        assert schema.properties["limit"].type.value == "number"
        assert "limit" not in schema.required

    def test_resolve_path_absolute(self, tmp_path: Path) -> None:
        """Test resolving absolute paths."""
        tool = ReadTool(cwd=tmp_path)
        absolute = tmp_path / "test.txt"

        result = tool.resolve_path(str(absolute))
        assert result == absolute

    def test_resolve_path_relative(self, tmp_path: Path) -> None:
        """Test resolving relative paths."""
        tool = ReadTool(cwd=tmp_path)
        result = tool.resolve_path("test.txt")
        assert result == (tmp_path / "test.txt").resolve()

    @pytest.mark.asyncio
    async def test_execute_read_file(self, tmp_path: Path) -> None:
        """Test reading a file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        tool = ReadTool(cwd=tmp_path)
        result = await tool._execute(
            tool_call_id="test-1",
            params={"path": "test.txt"},
            signal=None,
            on_update=None,
        )

        assert "content" in result
        assert len(result["content"]) == 1
        assert result["content"][0]["text"] == "Hello, World!"
        assert result["details"]["truncation"]["truncated"] is False

    @pytest.mark.asyncio
    async def test_execute_read_file_with_offset(self, tmp_path: Path) -> None:
        """Test reading a file with offset."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n")

        tool = ReadTool(cwd=tmp_path)
        result = await tool._execute(
            tool_call_id="test-2",
            params={"path": "test.txt", "offset": 3},
            signal=None,
            on_update=None,
        )

        assert result["content"][0]["text"] == "Line 3\nLine 4\nLine 5\n"

    @pytest.mark.asyncio
    async def test_execute_read_file_with_limit(self, tmp_path: Path) -> None:
        """Test reading a file with limit."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n")

        tool = ReadTool(cwd=tmp_path)
        result = await tool._execute(
            tool_call_id="test-3",
            params={"path": "test.txt", "limit": 2},
            signal=None,
            on_update=None,
        )

        # With limit, tool appends message about remaining content
        assert "Line 1\nLine 2" in result["content"][0]["text"]
        assert "more lines in file" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_execute_read_file_with_offset_and_limit(self, tmp_path: Path) -> None:
        """Test reading a file with offset and limit."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n")

        tool = ReadTool(cwd=tmp_path)
        result = await tool._execute(
            tool_call_id="test-4",
            params={"path": "test.txt", "offset": 2, "limit": 2},
            signal=None,
            on_update=None,
        )

        # With limit, tool appends message about remaining content
        assert "Line 2\nLine 3" in result["content"][0]["text"]
        assert "more lines in file" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_execute_file_not_found(self, tmp_path: Path) -> None:
        """Test reading a non-existent file."""
        tool = ReadTool(cwd=tmp_path)

        with pytest.raises(FileNotFoundError, match="File not found"):
            await tool._execute(
                tool_call_id="test-5",
                params={"path": "nonexistent.txt"},
                signal=None,
                on_update=None,
            )

    @pytest.mark.asyncio
    async def test_execute_path_is_directory(self, tmp_path: Path) -> None:
        """Test reading a directory raises error."""
        tool = ReadTool(cwd=tmp_path)

        with pytest.raises(ValueError, match="Path is not a file"):
            await tool._execute(
                tool_call_id="test-6",
                params={"path": str(tmp_path)},
                signal=None,
                on_update=None,
            )

    @pytest.mark.asyncio
    async def test_execute_offset_beyond_file(self, tmp_path: Path) -> None:
        """Test offset beyond file end raises error."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Line 1\nLine 2\n")

        tool = ReadTool(cwd=tmp_path)

        with pytest.raises(ValueError, match="Offset .* is beyond end of file"):
            await tool._execute(
                tool_call_id="test-7",
                params={"path": "test.txt", "offset": 10},
                signal=None,
                on_update=None,
            )

    @pytest.mark.asyncio
    async def test_truncate_content_by_lines(self, tmp_path: Path) -> None:
        """Test content truncation by line count."""
        tool = ReadTool(cwd=tmp_path)

        # Create content with more than DEFAULT_MAX_LINES lines
        lines = [f"Line {i}" for i in range(DEFAULT_MAX_LINES + 100)]
        content = "\n".join(lines)

        truncated, details = tool.truncate_content(content)

        assert details["truncated"] is True
        assert details["truncatedBy"] == "lines"
        assert details["outputLines"] == DEFAULT_MAX_LINES
        assert details["totalLines"] == len(lines)

    @pytest.mark.asyncio
    async def test_truncate_content_by_bytes(self, tmp_path: Path) -> None:
        """Test content truncation by byte size."""
        tool = ReadTool(cwd=tmp_path)

        # Create content larger than DEFAULT_MAX_BYTES
        content = "x" * (DEFAULT_MAX_BYTES + 10000)

        truncated, details = tool.truncate_content(content)

        assert details["truncated"] is True
        assert details["truncatedBy"] == "bytes"
        assert details["totalBytes"] > DEFAULT_MAX_BYTES

    def test_format_size(self) -> None:
        """Test format_size utility."""
        assert format_size(100) == "100B"
        # format_size returns float format like "2.0KB"
        assert format_size(2048) == "2.0KB"
        assert format_size(1048576) == "1.0MB"
        assert format_size(1073741824) == "1.0GB"

    @pytest.mark.asyncio
    async def test_execute_with_abort_signal(self, tmp_path: Path) -> None:
        """Test execution with abort signal."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello")

        tool = ReadTool(cwd=tmp_path)
        signal = MagicMock()
        signal.aborted = True

        with pytest.raises(RuntimeError, match="Operation aborted"):
            await tool._execute(
                tool_call_id="test-8",
                params={"path": "test.txt"},
                signal=signal,
                on_update=None,
            )


class TestReadToolIntegration:
    """Integration tests for ReadTool."""

    @pytest.mark.asyncio
    async def test_read_multiline_file(self, tmp_path: Path) -> None:
        """Test reading a file with multiple lines."""
        content = dedent("""
            First line
            Second line
            Third line
        """).strip()

        test_file = tmp_path / "multiline.txt"
        test_file.write_text(content)

        tool = ReadTool(cwd=tmp_path)
        result = await tool._execute(
            tool_call_id="int-1",
            params={"path": "multiline.txt"},
            signal=None,
            on_update=None,
        )

        assert result["content"][0]["text"] == content
        assert result["details"]["truncation"]["totalLines"] == 3

    @pytest.mark.asyncio
    async def test_read_empty_file(self, tmp_path: Path) -> None:
        """Test reading an empty file."""
        test_file = tmp_path / "empty.txt"
        test_file.write_text("")

        tool = ReadTool(cwd=tmp_path)
        result = await tool._execute(
            tool_call_id="int-2",
            params={"path": "empty.txt"},
            signal=None,
            on_update=None,
        )

        assert result["content"][0]["text"] == ""
        assert result["details"]["truncation"]["totalLines"] == 1

    @pytest.mark.asyncio
    async def test_read_unicode_file(self, tmp_path: Path) -> None:
        """Test reading a file with Unicode content."""
        content = "Hello 世界 🌍"

        test_file = tmp_path / "unicode.txt"
        test_file.write_text(content, encoding="utf-8")

        tool = ReadTool(cwd=tmp_path)
        result = await tool._execute(
            tool_call_id="int-3",
            params={"path": "unicode.txt"},
            signal=None,
            on_update=None,
        )

        assert result["content"][0]["text"] == content
