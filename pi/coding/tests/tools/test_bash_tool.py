"""Tests for BashTool."""
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

import pytest

from pi.coding.tools.bash import BashTool


class TestBashTool:
    """Test cases for BashTool."""

    def test_init_default_cwd(self, tmp_path: Path) -> None:
        """Test initialization with default cwd."""
        tool = BashTool(cwd=tmp_path)
        assert tool.cwd == tmp_path

    def test_init_no_cwd(self) -> None:
        """Test initialization without cwd uses current directory."""
        tool = BashTool()
        assert tool.cwd == Path.cwd()

    def test_get_schema(self) -> None:
        """Test parameter schema."""
        tool = BashTool()
        schema = tool.get_schema()

        assert "command" in schema.properties
        assert "command" in schema.required

    @pytest.mark.asyncio
    async def test_execute_simple_command(self, tmp_path: Path) -> None:
        """Test executing a simple command."""
        tool = BashTool(cwd=tmp_path)
        result = await tool._execute(
            tool_call_id="test-1",
            params={"command": "echo 'Hello, World!'"},
            signal=None,
            on_update=None,
        )

        assert result["details"]["exitCode"] == 0
        assert "Hello, World!" in result["details"]["stdout"]
        assert result["details"]["stderr"] == ""

    @pytest.mark.asyncio
    async def test_execute_command_with_stderr(self, tmp_path: Path) -> None:
        """Test command that produces stderr."""
        tool = BashTool(cwd=tmp_path)

        # ls on non-existent directory produces stderr
        result = await tool._execute(
            tool_call_id="test-2",
            params={"command": "ls /nonexistent_directory_12345 2>&1"},
            signal=None,
            on_update=None,
        )

        assert "exitCode" in result["details"]
        assert result["content"][0]["type"] == "text"

    @pytest.mark.asyncio
    async def test_execute_empty_command(self, tmp_path: Path) -> None:
        """Test empty command raises error."""
        tool = BashTool(cwd=tmp_path)

        with pytest.raises(ValueError, match="Command is required"):
            await tool._execute(
                tool_call_id="test-3",
                params={"command": ""},
                signal=None,
                on_update=None,
            )

    @pytest.mark.asyncio
    async def test_execute_with_abort_signal(self, tmp_path: Path) -> None:
        """Test execution with abort signal."""
        tool = BashTool(cwd=tmp_path)
        signal = MagicMock()
        signal.aborted = True

        with pytest.raises(RuntimeError, match="Operation aborted"):
            await tool._execute(
                tool_call_id="test-4",
                params={"command": "echo test"},
                signal=signal,
                on_update=None,
            )

    @pytest.mark.asyncio
    async def test_execute_working_directory(self, tmp_path: Path) -> None:
        """Test command executes in correct working directory."""
        tool = BashTool(cwd=tmp_path)

        # Create a file in tmp_path
        (tmp_path / "test_file.txt").write_text("test")

        # List files in cwd
        result = await tool._execute(
            tool_call_id="test-5",
            params={"command": "ls"},
            signal=None,
            on_update=None,
        )

        assert "test_file.txt" in result["details"]["stdout"]

    @pytest.mark.asyncio
    async def test_execute_command_with_pipe(self, tmp_path: Path) -> None:
        """Test command with pipe."""
        tool = BashTool(cwd=tmp_path)
        result = await tool._execute(
            tool_call_id="test-6",
            params={"command": "echo 'hello world' | grep hello"},
            signal=None,
            on_update=None,
        )

        assert result["details"]["exitCode"] == 0
        assert "hello" in result["details"]["stdout"]

    @pytest.mark.asyncio
    async def test_execute_multiline_output(self, tmp_path: Path) -> None:
        """Test command with multiline output."""
        tool = BashTool(cwd=tmp_path)
        result = await tool._execute(
            tool_call_id="test-7",
            params={"command": "echo 'line1\\nline2\\nline3'"},
            signal=None,
            on_update=None,
        )

        assert result["details"]["exitCode"] == 0
        content = result["content"][0]["text"]
        assert "line1" in content or "line2" in content

    @pytest.mark.asyncio
    async def test_execute_non_zero_exit_code(self, tmp_path: Path) -> None:
        """Test command that returns non-zero exit code."""
        tool = BashTool(cwd=tmp_path)
        result = await tool._execute(
            tool_call_id="test-8",
            params={"command": "exit 42"},
            signal=None,
            on_update=None,
        )

        assert result["details"]["exitCode"] == 42

    @pytest.mark.asyncio
    async def test_execute_command_with_env_var(self, tmp_path: Path) -> None:
        """Test command with environment variable."""
        tool = BashTool(cwd=tmp_path)
        result = await tool._execute(
            tool_call_id="test-9",
            params={"command": "echo $HOME"},
            signal=None,
            on_update=None,
        )

        assert result["details"]["exitCode"] == 0
        assert len(result["details"]["stdout"]) > 0
