"""Tests for FindTool."""
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pi.coding.tools.find import FindTool


class TestFindTool:
    """Test cases for FindTool."""

    def test_init_default_cwd(self, tmp_path: Path) -> None:
        """Test initialization with default cwd."""
        tool = FindTool(cwd=tmp_path)
        assert tool.cwd == tmp_path

    def test_init_no_cwd(self) -> None:
        """Test initialization without cwd uses current directory."""
        tool = FindTool()
        assert tool.cwd == Path.cwd()

    def test_get_schema(self) -> None:
        """Test parameter schema."""
        tool = FindTool()
        schema = tool.get_schema()

        assert "pattern" in schema.properties
        assert "pattern" in schema.required

        assert "path" in schema.properties
        assert "path" not in schema.required

        assert "max_results" in schema.properties

    @pytest.mark.asyncio
    async def test_execute_find_by_extension(self, tmp_path: Path) -> None:
        """Test finding files by extension."""
        (tmp_path / "test1.txt").write_text("content1")
        (tmp_path / "test2.txt").write_text("content2")
        (tmp_path / "test.py").write_text("content3")

        tool = FindTool(cwd=tmp_path)
        result = await tool._execute(
            tool_call_id="test-1",
            params={"pattern": "*.txt"},
            signal=None,
            on_update=None,
        )

        assert result["details"]["totalFiles"] == 2
        assert "test1.txt" in result["content"][0]["text"]
        assert "test2.txt" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_execute_recursive_pattern(self, tmp_path: Path) -> None:
        """Test recursive pattern with **."""
        (tmp_path / "root.txt").write_text("content")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "nested.txt").write_text("content")
        (subdir / "sub.py").write_text("content")

        tool = FindTool(cwd=tmp_path)
        result = await tool._execute(
            tool_call_id="test-2",
            params={"pattern": "**/*.txt"},
            signal=None,
            on_update=None,
        )

        assert result["details"]["totalFiles"] == 2
        assert "root.txt" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_execute_find_in_subdirectory(self, tmp_path: Path) -> None:
        """Test finding files in specific subdirectory."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file1.txt").write_text("content1")
        (subdir / "file2.txt").write_text("content2")
        (tmp_path / "root.txt").write_text("content3")

        tool = FindTool(cwd=tmp_path)
        result = await tool._execute(
            tool_call_id="test-3",
            params={"pattern": "*.txt", "path": "subdir"},
            signal=None,
            on_update=None,
        )

        # Should only find files in subdir
        assert "subdir/file1.txt" in result["content"][0]["text"]
        assert "subdir/file2.txt" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_execute_no_matches(self, tmp_path: Path) -> None:
        """Test finding with no matches."""
        (tmp_path / "test.txt").write_text("content")

        tool = FindTool(cwd=tmp_path)
        result = await tool._execute(
            tool_call_id="test-4",
            params={"pattern": "*.nonexistent"},
            signal=None,
            on_update=None,
        )

        assert result["details"]["totalFiles"] == 0
        assert "No files found" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_execute_max_results_limit(self, tmp_path: Path) -> None:
        """Test max_results limit."""
        for i in range(20):
            (tmp_path / f"file{i}.txt").write_text("content")

        tool = FindTool(cwd=tmp_path)
        result = await tool._execute(
            tool_call_id="test-5",
            params={"pattern": "*.txt", "max_results": 5},
            signal=None,
            on_update=None,
        )

        assert result["details"]["resultsShown"] == 5

    @pytest.mark.asyncio
    async def test_execute_empty_pattern(self, tmp_path: Path) -> None:
        """Test empty pattern raises error."""
        tool = FindTool(cwd=tmp_path)

        with pytest.raises(ValueError, match="Pattern is required"):
            await tool._execute(
                tool_call_id="test-6",
                params={"pattern": ""},
                signal=None,
                on_update=None,
            )

    @pytest.mark.asyncio
    async def test_execute_with_abort_signal(self, tmp_path: Path) -> None:
        """Test execution with abort signal."""
        (tmp_path / "test.txt").write_text("content")

        tool = FindTool(cwd=tmp_path)
        signal = MagicMock()
        signal.aborted = True

        with pytest.raises(RuntimeError, match="Operation aborted"):
            await tool._execute(
                tool_call_id="test-7",
                params={"pattern": "*.txt"},
                signal=signal,
                on_update=None,
            )

    @pytest.mark.asyncio
    async def test_resolve_path_absolute(self, tmp_path: Path) -> None:
        """Test resolving absolute paths."""
        tool = FindTool(cwd=tmp_path)
        absolute = tmp_path / "test.txt"

        result = tool.resolve_path(str(absolute))
        assert result == absolute

    @pytest.mark.asyncio
    async def test_resolve_path_relative(self, tmp_path: Path) -> None:
        """Test resolving relative paths."""
        tool = FindTool(cwd=tmp_path)
        result = tool.resolve_path("test.txt")
        assert result == (tmp_path / "test.txt").resolve()

    @pytest.mark.asyncio
    async def test_find_with_directory_path(self, tmp_path: Path) -> None:
        """Test finding with directory path."""
        (tmp_path / "test.txt").write_text("content")

        tool = FindTool(cwd=tmp_path)
        result = await tool._execute(
            tool_call_id="test-8",
            params={"pattern": "*.txt", "path": str(tmp_path)},
            signal=None,
            on_update=None,
        )

        assert result["details"]["totalFiles"] == 1
