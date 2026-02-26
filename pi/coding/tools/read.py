"""
Read tool for pi-coding.

Converted from TypeScript core/tools/read.ts
"""
import os
from pathlib import Path
from typing import Any, Optional
from pi.agent.tools import BaseTool, ToolSchema, ParameterType, ParameterProperty


# Constants for truncation
DEFAULT_MAX_LINES = 1000
DEFAULT_MAX_BYTES = 30 * 1024  # 30 KB


class ReadTool(BaseTool):
    """
    Tool for reading file contents.

    Supports text files with truncation for large files.
    """

    name = "read"
    label = "read"
    description = (
        f"Read the contents of a file. Supports text files. "
        f"Output is truncated to {DEFAULT_MAX_LINES} lines or {DEFAULT_MAX_BYTES // 1024}KB "
        f"(whichever is hit first). Use offset/limit for large files."
    )

    def __init__(self, cwd: Optional[str | Path] = None):
        """
        Initialize the read tool.

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
                    description="Path to the file to read (relative or absolute)",
                ),
                "offset": ParameterProperty(
                    type=ParameterType.NUMBER,
                    description="Line number to start reading from (1-indexed)",
                ),
                "limit": ParameterProperty(
                    type=ParameterType.NUMBER,
                    description="Maximum number of lines to read",
                ),
            },
            required=["path"],
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

    def truncate_content(
        self,
        content: str,
        offset: int = 0,
    ) -> tuple[str, dict[str, Any]]:
        """
        Truncate content if it exceeds limits.

        Args:
            content: Content to truncate
            offset: Starting line number (for display)

        Returns:
            Tuple of (truncated_content, truncation_details)
        """
        lines = content.split("\n")
        total_lines = len(lines)

        # Check if content exceeds byte limit
        content_bytes = len(content.encode("utf-8"))

        truncated = False
        truncated_by = None
        output_lines = total_lines

        if content_bytes > DEFAULT_MAX_BYTES:
            # Truncate by bytes
            truncated_bytes = 0
            result_lines = []
            for line in lines:
                line_bytes = len(line.encode("utf-8")) + 1  # +1 for newline
                if truncated_bytes + line_bytes > DEFAULT_MAX_BYTES:
                    break
                result_lines.append(line)
                truncated_bytes += line_bytes

            content = "\n".join(result_lines)
            truncated = True
            truncated_by = "bytes"
            output_lines = len(result_lines)
        elif total_lines > DEFAULT_MAX_LINES:
            # Truncate by lines
            content = "\n".join(lines[:DEFAULT_MAX_LINES])
            truncated = True
            truncated_by = "lines"
            output_lines = DEFAULT_MAX_LINES

        details: dict[str, Any] = {
            "truncated": truncated,
            "totalLines": total_lines,
            "outputLines": output_lines,
            "totalBytes": content_bytes,
        }

        if truncated:
            details["truncatedBy"] = truncated_by

        return content, details

    async def _execute(
        self,
        tool_call_id: str,
        params: dict[str, Any],
        signal: Any,
        on_update: Any,
    ) -> dict[str, Any]:
        """
        Execute the read tool.

        Args:
            tool_call_id: ID of the tool call
            params: Tool parameters (path, offset, limit)
            signal: Optional abort signal
            on_update: Optional progress callback

        Returns:
            Dict with content list and details
        """
        # Check for abort signal
        if signal and hasattr(signal, "aborted") and signal.aborted:
            raise RuntimeError("Operation aborted")

        path = params.get("path", "")
        offset = params.get("offset")
        limit = params.get("limit")

        # Resolve path
        absolute_path = self.resolve_path(path)

        # Check if file exists and is readable
        if not absolute_path.exists():
            raise FileNotFoundError(f"File not found: {absolute_path}")

        if not absolute_path.is_file():
            raise ValueError(f"Path is not a file: {absolute_path}")

        # Read file content
        try:
            content_text = absolute_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Try with error handling
            content_text = absolute_path.read_text(encoding="utf-8", errors="replace")

        # Split into lines
        all_lines = content_text.split("\n")
        total_lines = len(all_lines)

        # Apply offset if specified (1-indexed to 0-indexed)
        start_line = 0
        if offset is not None:
            start_line = max(0, offset - 1)
            if start_line >= total_lines:
                raise ValueError(
                    f"Offset {offset} is beyond end of file ({total_lines} lines total)"
                )

        # Apply limit if specified
        if limit is not None:
            end_line = min(start_line + limit, total_lines)
            selected_content = "\n".join(all_lines[start_line:end_line])
        else:
            selected_content = "\n".join(all_lines[start_line:])

        # Apply truncation
        truncated_content, truncation_details = self.truncate_content(
            selected_content,
            start_line,
        )

        # Build output message
        output_lines = truncation_details["outputLines"]
        start_display = start_line + 1
        end_display = start_display + output_lines - 1

        if truncation_details["truncated"]:
            if truncation_details["truncatedBy"] == "lines":
                truncated_content += (
                    f"\n\n[Showing lines {start_display}-{end_display} of {total_lines}. "
                    f"Use offset={end_display + 1} to continue.]"
                )
            else:
                truncated_content += (
                    f"\n\n[Showing lines {start_display}-{end_display} of {total_lines} "
                    f"({DEFAULT_MAX_BYTES // 1024}KB limit). "
                    f"Use offset={end_display + 1} to continue.]"
                )
        elif limit is not None and start_line + limit < total_lines:
            # User specified limit, there's more content
            remaining = total_lines - (start_line + limit)
            truncated_content += (
                f"\n\n[{remaining} more lines in file. "
                f"Use offset={start_line + limit + 1} to continue.]"
            )

        return {
            "content": [{"type": "text", "text": truncated_content}],
            "details": {"truncation": truncation_details},
        }


def format_size(size: int) -> str:
    """Format byte size to human readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


__all__ = ["ReadTool", "DEFAULT_MAX_LINES", "DEFAULT_MAX_BYTES", "format_size"]
