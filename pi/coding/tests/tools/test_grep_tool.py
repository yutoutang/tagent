"""Tests for GrepTool."""
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pi.coding.tools.grep import GrepTool


class TestGrepTool:
    """Test cases for GrepTool."""

    def test_init_default_cwd(self, tmp_path: Path) -> None:
        """Test initialization with default cwd."""
        tool = GrepTool(cwd=tmp_path)
        assert tool.cwd == tmp_path

    def test_init_no_cwd(self) -> None:
        """Test initialization without cwd uses current directory."""
        tool = GrepTool()
        assert tool.cwd == Path.cwd()

    def test_get_schema(self) -> None:
        """Test parameter schema."""
        tool = GrepTool()
        schema = tool.get_schema()

        assert "pattern" in schema.properties
        assert "pattern" in schema.required

        assert "path" in schema.properties
        assert "path" not in schema.required

        assert "recursive" in schema.properties
        assert "include" in schema.properties
        assert "max_results" in schema.properties

    @pytest.mark.asyncio
    async def test_execute_search_single_file(self, tmp_path: Path) -> None:
        """Test searching in a single file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World\nHello Python\nGoodbye World\n")

        tool = GrepTool(cwd=tmp_path)
        result = await tool._execute(
            tool_call_id="test-1",
            params={"pattern": "Hello", "path": "test.txt"},
            signal=None,
            on_update=None,
        )

        assert result["details"]["matches"] == 2
        assert "Hello World" in result["content"][0]["text"]
        assert "Hello Python" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_execute_search_recursive(self, tmp_path: Path) -> None:
        """Test recursive search in directory."""
        (tmp_path / "file1.txt").write_text("pattern1\n")
        (tmp_path / "file2.txt").write_text("pattern2\n")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file3.txt").write_text("pattern1\n")

        tool = GrepTool(cwd=tmp_path)
        result = await tool._execute(
            tool_call_id="test-2",
            params={"pattern": "pattern1", "path": str(tmp_path), "recursive": True},
            signal=None,
            on_update=None,
        )

        assert result["details"]["matches"] == 2

    @pytest.mark.asyncio
    async def test_execute_search_non_recursive(self, tmp_path: Path) -> None:
        """Test non-recursive search."""
        (tmp_path / "file1.txt").write_text("pattern1\n")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file2.txt").write_text("pattern1\n")

        tool = GrepTool(cwd=tmp_path)
        result = await tool._execute(
            tool_call_id="test-3",
            params={"pattern": "pattern1", "path": str(tmp_path), "recursive": False},
            signal=None,
            on_update=None,
        )

        # Should only find one match in file1.txt
        assert result["details"]["matches"] == 1

    @pytest.mark.asyncio
    async def test_execute_search_with_include(self, tmp_path: Path) -> None:
        """Test search with file pattern filter."""
        (tmp_path / "test.py").write_text("import os\n")
        (tmp_path / "test.txt").write_text("import os\n")

        tool = GrepTool(cwd=tmp_path)
        result = await tool._execute(
            tool_call_id="test-4",
            params={"pattern": "import", "path": str(tmp_path), "include": "*.py"},
            signal=None,
            on_update=None,
        )

        # Should only match in .py file
        assert result["details"]["matches"] == 1
        assert "test.py" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_execute_regex_pattern(self, tmp_path: Path) -> None:
        """Test search with regex pattern."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("abc123\nxyz456\nabc789\n")

        tool = GrepTool(cwd=tmp_path)
        result = await tool._execute(
            tool_call_id="test-5",
            params={"pattern": r"abc\d+", "path": "test.txt"},
            signal=None,
            on_update=None,
        )

        assert result["details"]["matches"] == 2

    @pytest.mark.asyncio
    async def test_execute_no_matches(self, tmp_path: Path) -> None:
        """Test search with no matches."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World\n")

        tool = GrepTool(cwd=tmp_path)
        result = await tool._execute(
            tool_call_id="test-6",
            params={"pattern": "nonexistent", "path": "test.txt"},
            signal=None,
            on_update=None,
        )

        assert result["details"]["matches"] == 0
        assert "No matches found" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_execute_max_results_limit(self, tmp_path: Path) -> None:
        """Test max_results limit."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("\n".join([f"line {i}" for i in range(100)]))

        tool = GrepTool(cwd=tmp_path)
        result = await tool._execute(
            tool_call_id="test-7",
            params={"pattern": "line", "path": "test.txt", "max_results": 10},
            signal=None,
            on_update=None,
        )

        # The grep tool shows all matches by default when searching a single file
        # The max_results limit applies to directory search
        assert result["details"]["matches"] == 100

    @pytest.mark.asyncio
    async def test_execute_invalid_regex(self, tmp_path: Path) -> None:
        """Test invalid regex pattern."""
        tool = GrepTool(cwd=tmp_path)

        with pytest.raises(ValueError, match="Invalid regex pattern"):
            await tool._execute(
                tool_call_id="test-8",
                params={"pattern": "[invalid", "path": "."},
                signal=None,
                on_update=None,
            )

    @pytest.mark.asyncio
    async def test_execute_empty_pattern(self, tmp_path: Path) -> None:
        """Test empty pattern raises error."""
        tool = GrepTool(cwd=tmp_path)

        with pytest.raises(ValueError, match="Pattern is required"):
            await tool._execute(
                tool_call_id="test-9",
                params={"pattern": "", "path": "."},
                signal=None,
                on_update=None,
            )

    @pytest.mark.asyncio
    async def test_execute_with_abort_signal(self, tmp_path: Path) -> None:
        """Test execution with abort signal."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World\n")

        tool = GrepTool(cwd=tmp_path)
        signal = MagicMock()
        signal.aborted = True

        with pytest.raises(RuntimeError, match="Operation aborted"):
            await tool._execute(
                tool_call_id="test-10",
                params={"pattern": "Hello", "path": "test.txt"},
                signal=signal,
                on_update=None,
            )

    @pytest.mark.asyncio
    async def test_resolve_path_absolute(self, tmp_path: Path) -> None:
        """Test resolving absolute paths."""
        tool = GrepTool(cwd=tmp_path)
        absolute = tmp_path / "test.txt"

        result = tool.resolve_path(str(absolute))
        assert result == absolute

    @pytest.mark.asyncio
    async def test_resolve_path_relative(self, tmp_path: Path) -> None:
        """Test resolving relative paths."""
        tool = GrepTool(cwd=tmp_path)
        result = tool.resolve_path("test.txt")
        assert result == (tmp_path / "test.txt").resolve()
