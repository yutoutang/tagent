"""Tests for LsTool."""
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pi.coding.tools.ls import LsTool


class TestLsTool:
    """Test cases for LsTool."""

    def test_init_default_cwd(self, tmp_path: Path) -> None:
        """Test initialization with default cwd."""
        tool = LsTool(cwd=tmp_path)
        assert tool.cwd == tmp_path

    def test_init_no_cwd(self) -> None:
        """Test initialization without cwd uses current directory."""
        tool = LsTool()
        assert tool.cwd == Path.cwd()

    def test_get_schema(self) -> None:
        """Test parameter schema."""
        tool = LsTool()
        schema = tool.get_schema()

        assert "path" in schema.properties
        assert "path" not in schema.required

        assert "detail" in schema.properties
        assert "detail" not in schema.required

    @pytest.mark.asyncio
    async def test_execute_list_current_directory(self, tmp_path: Path) -> None:
        """Test listing current directory."""
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.txt").write_text("content2")
        (tmp_path / "subdir").mkdir()

        tool = LsTool(cwd=tmp_path)
        result = await tool._execute(
            tool_call_id="test-1",
            params={},
            signal=None,
            on_update=None,
        )

        assert result["details"]["total"] == 3
        assert "file1.txt" in result["content"][0]["text"]
        assert "file2.txt" in result["content"][0]["text"]
        assert "subdir/" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_execute_list_with_detail(self, tmp_path: Path) -> None:
        """Test listing with detailed output."""
        (tmp_path / "file.txt").write_text("x" * 100)
        (tmp_path / "subdir").mkdir()

        tool = LsTool(cwd=tmp_path)
        result = await tool._execute(
            tool_call_id="test-2",
            params={"detail": True},
            signal=None,
            on_update=None,
        )

        content = result["content"][0]["text"]
        assert "100 bytes" in content or "(directory)" in content

    @pytest.mark.asyncio
    async def test_execute_list_specific_directory(self, tmp_path: Path) -> None:
        """Test listing a specific directory."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "nested.txt").write_text("content")

        tool = LsTool(cwd=tmp_path)
        result = await tool._execute(
            tool_call_id="test-3",
            params={"path": "subdir"},
            signal=None,
            on_update=None,
        )

        assert "nested.txt" in result["content"][0]["text"]
        assert result["details"]["total"] == 1

    @pytest.mark.asyncio
    async def test_execute_list_file(self, tmp_path: Path) -> None:
        """Test listing a single file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        tool = LsTool(cwd=tmp_path)
        result = await tool._execute(
            tool_call_id="test-4",
            params={"path": "test.txt"},
            signal=None,
            on_update=None,
        )

        assert "test.txt" in result["content"][0]["text"]
        assert result["details"]["type"] == "file"

    @pytest.mark.asyncio
    async def test_execute_list_file_with_detail(self, tmp_path: Path) -> None:
        """Test listing a single file with detail."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("x" * 500)

        tool = LsTool(cwd=tmp_path)
        result = await tool._execute(
            tool_call_id="test-5",
            params={"path": "test.txt", "detail": True},
            signal=None,
            on_update=None,
        )

        assert "500 bytes" in result["content"][0]["text"]
        assert "file" in result["content"][0]["text"].lower()

    @pytest.mark.asyncio
    async def test_execute_path_not_found(self, tmp_path: Path) -> None:
        """Test listing non-existent path."""
        tool = LsTool(cwd=tmp_path)

        with pytest.raises(FileNotFoundError, match="Path not found"):
            await tool._execute(
                tool_call_id="test-6",
                params={"path": "nonexistent"},
                signal=None,
                on_update=None,
            )

    @pytest.mark.asyncio
    async def test_execute_empty_directory(self, tmp_path: Path) -> None:
        """Test listing empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        tool = LsTool(cwd=tmp_path)
        result = await tool._execute(
            tool_call_id="test-7",
            params={"path": "empty"},
            signal=None,
            on_update=None,
        )

        assert result["details"]["total"] == 0
        assert result["details"]["files"] == 0
        assert result["details"]["directories"] == 0

    @pytest.mark.asyncio
    async def test_execute_with_abort_signal(self, tmp_path: Path) -> None:
        """Test execution with abort signal."""
        tool = LsTool(cwd=tmp_path)
        signal = MagicMock()
        signal.aborted = True

        with pytest.raises(RuntimeError, match="Operation aborted"):
            await tool._execute(
                tool_call_id="test-8",
                params={},
                signal=signal,
                on_update=None,
            )

    @pytest.mark.asyncio
    async def test_execute_sorted_output(self, tmp_path: Path) -> None:
        """Test that output is sorted (directories first, then alphabetically)."""
        (tmp_path / "z_file.txt").write_text("content")
        (tmp_path / "a_file.txt").write_text("content")
        (tmp_path / "z_dir").mkdir()
        (tmp_path / "a_dir").mkdir()

        tool = LsTool(cwd=tmp_path)
        result = await tool._execute(
            tool_call_id="test-9",
            params={},
            signal=None,
            on_update=None,
        )

        lines = result["content"][0]["text"].split("\n")
        # Directories come first, then files
        dir_indices = [i for i, line in enumerate(lines) if "a_dir/" in line or "z_dir/" in line]
        file_indices = [i for i, line in enumerate(lines) if "a_file.txt" in line or "z_file.txt" in line]

        # All directories should come before all files
        if dir_indices and file_indices:
            assert max(dir_indices) < min(file_indices)

    @pytest.mark.asyncio
    async def test_resolve_path_absolute(self, tmp_path: Path) -> None:
        """Test resolving absolute paths."""
        tool = LsTool(cwd=tmp_path)
        absolute = tmp_path / "test.txt"

        result = tool.resolve_path(str(absolute))
        assert result == absolute

    @pytest.mark.asyncio
    async def test_resolve_path_relative(self, tmp_path: Path) -> None:
        """Test resolving relative paths."""
        tool = LsTool(cwd=tmp_path)
        result = tool.resolve_path("test.txt")
        assert result == (tmp_path / "test.txt").resolve()

    @pytest.mark.asyncio
    async def test_counts_are_accurate(self, tmp_path: Path) -> None:
        """Test that file and directory counts are accurate."""
        (tmp_path / "file1.txt").write_text("content")
        (tmp_path / "file2.txt").write_text("content")
        (tmp_path / "file3.txt").write_text("content")
        (tmp_path / "dir1").mkdir()
        (tmp_path / "dir2").mkdir()

        tool = LsTool(cwd=tmp_path)
        result = await tool._execute(
            tool_call_id="test-10",
            params={},
            signal=None,
            on_update=None,
        )

        assert result["details"]["files"] == 3
        assert result["details"]["directories"] == 2
        assert result["details"]["total"] == 5
