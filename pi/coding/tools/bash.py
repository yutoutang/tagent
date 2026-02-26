"""
Bash tool for pi-coding.

Converted from TypeScript core/tools/bash.ts
"""
import asyncio
import shlex
from pathlib import Path
from typing import Any, Optional
from pi.agent.tools import BaseTool, ToolSchema, ParameterType, ParameterProperty


class BashTool(BaseTool):
    """
    Tool for executing bash commands.

    Executes shell commands and returns stdout/stderr.
    """

    name = "bash"
    label = "bash"
    description = (
        "Execute a bash command in the shell. "
        "Returns stdout and stderr. Use for testing, building, git operations, etc."
    )

    def __init__(self, cwd: Optional[str | Path] = None):
        """
        Initialize the bash tool.

        Args:
            cwd: Working directory for command execution
        """
        self.cwd = Path(cwd) if cwd else Path.cwd()
        super().__init__()

    def get_schema(self) -> ToolSchema:
        """Get parameter schema."""
        return ToolSchema(
            properties={
                "command": ParameterProperty(
                    type=ParameterType.STRING,
                    description="Bash command to execute",
                ),
            },
            required=["command"],
        )

    async def _execute(
        self,
        tool_call_id: str,
        params: dict[str, Any],
        signal: Any,
        on_update: Any,
    ) -> dict[str, Any]:
        """
        Execute the bash tool.

        Args:
            tool_call_id: ID of the tool call
            params: Tool parameters (command)
            signal: Optional abort signal
            on_update: Optional progress callback

        Returns:
            Dict with content list and details
        """
        command = params.get("command", "")

        if not command:
            raise ValueError("Command is required")

        # Check for abort signal
        if signal and hasattr(signal, "aborted") and signal.aborted:
            raise RuntimeError("Operation aborted")

        try:
            # Execute command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.cwd,
            )

            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=300,  # 5 minute timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise RuntimeError(f"Command timed out after 5 minutes: {command}")

            stdout_text = stdout.decode("utf-8", errors="replace")
            stderr_text = stderr.decode("utf-8", errors="replace")
            exit_code = process.returncode or 0

            # Build response
            output_parts = []
            if stdout_text:
                output_parts.append(f"Output:\n{stdout_text}")
            if stderr_text:
                output_parts.append(f"Error:\n{stderr_text}")

            message = "\n".join(output_parts) if output_parts else f"Command completed with exit code {exit_code}"

            return {
                "content": [{"type": "text", "text": message}],
                "details": {
                    "exitCode": exit_code,
                    "stdout": stdout_text,
                    "stderr": stderr_text,
                },
            }

        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"Error executing command: {str(e)}"}],
                "details": {
                    "exitCode": -1,
                    "error": str(e),
                },
            }


__all__ = ["BashTool"]
