"""
Edit tool for pi-coding.

Converted from TypeScript core/tools/edit.ts
"""
from pathlib import Path
from typing import Any, Optional
from pi.agent.tools import BaseTool, ToolSchema, ParameterType, ParameterProperty


class EditTool(BaseTool):
    """
    Tool for editing files with find/replace.

    Performs targeted edits to file contents.
    """

    name = "edit"
    label = "edit"
    description = (
        "Edit a file by finding and replacing text. "
        "Supports literal string replacement. "
        "Be specific with the search text to avoid unintended replacements."
    )

    def __init__(self, cwd: Optional[str | Path] = None):
        """
        Initialize the edit tool.

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
                    description="Path to the file to edit (relative or absolute)",
                ),
                "search": ParameterProperty(
                    type=ParameterType.STRING,
                    description="Text to search for (exact match)",
                ),
                "replace": ParameterProperty(
                    type=ParameterType.STRING,
                    description="Replacement text",
                ),
            },
            required=["path", "search", "replace"],
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
        """Execute the edit tool."""
        # Check for abort signal
        if signal and hasattr(signal, "aborted") and signal.aborted:
            raise RuntimeError("Operation aborted")

        path = params.get("path", "")
        search_text = params.get("search", "")
        replace_text = params.get("replace", "")

        # Resolve path
        absolute_path = self.resolve_path(path)

        # Check if file exists
        if not absolute_path.exists():
            raise FileNotFoundError(f"File not found: {absolute_path}")

        # Read file content
        content = absolute_path.read_text(encoding="utf-8")

        # Find and replace
        if search_text not in content:
            return {
                "content": [{"type": "text", "text": f"Search text not found in file: {path}"}],
                "details": {
                    "found": False,
                    "replacements": 0,
                },
            }

        # Count occurrences
        count = content.count(search_text)

        # Perform replacement
        new_content = content.replace(search_text, replace_text)

        # Write back
        absolute_path.write_text(new_content, encoding="utf-8")

        return {
            "content": [{"type": "text", "text": f"Replaced {count} occurrence(s) in {path}"}],
            "details": {
                "found": True,
                "replacements": count,
                "path": str(absolute_path),
            },
        }


__all__ = ["EditTool"]
