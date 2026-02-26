"""
Write tool for pi-coding.

Converted from TypeScript core/tools/write.ts
"""
from pathlib import Path
from typing import Any, Optional
from pi.agent.tools import BaseTool, ToolSchema, ParameterType, ParameterProperty


class WriteTool(BaseTool):
    """
    Tool for writing file contents.

    Creates new files or overwrites existing ones.
    """

    name = "write"
    label = "write"
    description = (
        "Write content to a file. Creates the file if it doesn't exist, "
        "or overwrites it if it does. Use with caution as this cannot be undone."
    )

    def __init__(self, cwd: Optional[str | Path] = None):
        """
        Initialize the write tool.

        Args:
            cwd: Working directory for relative paths
        """
        self.cwd = Path(cwd) if cwd else Path.cwd()
        super().__init__()

    def get_schema(self) -> ToolSchema:
        """Get parameter schema."""
        return ToolSchema(
            properties={
                "path": ParameterProperty(
                    type=ParameterType.STRING,
                    description="Path to the file to write (relative or absolute)",
                ),
                "content": ParameterProperty(
                    type=ParameterType.STRING,
                    description="Content to write to the file",
                ),
            },
            required=["path", "content"],
        )

    def resolve_path(self, path: str) -> Path:
        """
        Resolve a file path relative to the working directory.

        Args:
            path: File path (relative or absolute)

        Returns:
            Resolved absolute path
        """
        path_obj = Path(path)
        if path_obj.is_absolute():
            return path_obj
        return (self.cwd / path_obj).resolve()

    async def _execute(
        self,
        tool_call_id: str,
        params: dict[str, Any],
        signal: Any,
        on_update: Any,
    ) -> dict[str, Any]:
        """
        Execute the write tool.

        Args:
            tool_call_id: ID of the tool call
            params: Tool parameters (path, content)
            signal: Optional abort signal
            on_update: Optional progress callback

        Returns:
            Dict with content list and details
        """
        # Check for abort signal
        if signal and hasattr(signal, "aborted") and signal.aborted:
            raise RuntimeError("Operation aborted")

        path = params.get("path", "")
        content = params.get("content", "")

        # Resolve path
        absolute_path = self.resolve_path(path)

        # Create parent directories if they don't exist
        absolute_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if file exists (for reporting)
        file_existed = absolute_path.exists()

        # Write content
        absolute_path.write_text(content, encoding="utf-8")

        # Build response message
        if file_existed:
            message = f"Overwrote existing file: {absolute_path}"
        else:
            message = f"Created new file: {absolute_path}"

        # Get file size
        file_size = absolute_path.stat().st_size
        line_count = len(content.split("\n"))

        return {
            "content": [{"type": "text", "text": message}],
            "details": {
                "path": str(absolute_path),
                "size": file_size,
                "lines": line_count,
                "existed": file_existed,
            },
        }


__all__ = ["WriteTool"]
