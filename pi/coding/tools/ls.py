"""
Ls tool for pi-coding.

Converted from TypeScript core/tools/ls.ts
"""
from pathlib import Path
from typing import Any, Optional
from pi.agent.tools import BaseTool, ToolSchema, ParameterType, ParameterProperty


class LsTool(BaseTool):
    """
    Tool for listing directory contents.

    Similar to Unix 'ls' command.
    """

    name = "ls"
    label = "ls"
    description = (
        "List directory contents. "
        "Shows files and subdirectories with metadata."
    )

    def __init__(self, cwd: Optional[str | Path] = None):
        """
        Initialize the ls tool.

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
                    description="Directory path to list (default: current directory)",
                ),
                "detail": ParameterProperty(
                    type=ParameterType.BOOLEAN,
                    description="Show detailed information (size, type)",
                ),
            },
            required=[],
        )

    def resolve_path(self, path: str) -> Path:
        """Resolve a file path relative to the working directory."""
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
        """Execute the ls tool."""
        # Check for abort signal
        if signal and hasattr(signal, "aborted") and signal.aborted:
            raise RuntimeError("Operation aborted")

        path = params.get("path", ".")
        detail = params.get("detail", False)

        # Resolve path
        list_path = self.resolve_path(path)

        # Check if path exists
        if not list_path.exists():
            raise FileNotFoundError(f"Path not found: {list_path}")

        # If it's a file, just return info about it
        if list_path.is_file():
            if detail:
                size = list_path.stat().st_size
                message = f"{list_path.name} ({size} bytes, file)"
            else:
                message = list_path.name

            return {
                "content": [{"type": "text", "text": message}],
                "details": {
                    "path": str(list_path),
                    "type": "file",
                },
            }

        # List directory contents
        try:
            items = sorted(list_path.iterdir(), key=lambda p: (not p.is_dir(), p.name))

            if detail:
                lines = []
                for item in items:
                    if item.is_dir():
                        lines.append(f"{item.name}/ (directory)")
                    else:
                        size = item.stat().st_size
                        lines.append(f"{item.name} ({size} bytes)")
                message = "\n".join(lines)
            else:
                # Simple listing with / suffix for directories
                lines = []
                for item in items:
                    name = item.name
                    if item.is_dir():
                        name += "/"
                    lines.append(name)
                message = "\n".join(lines)

            # Count items
            dirs = sum(1 for item in items if item.is_dir())
            files = len(items) - dirs

            return {
                "content": [{"type": "text", "text": message}],
                "details": {
                    "path": str(list_path),
                    "directories": dirs,
                    "files": files,
                    "total": len(items),
                },
            }

        except PermissionError:
            raise PermissionError(f"Permission denied: {list_path}")


__all__ = ["LsTool"]
