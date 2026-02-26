"""
Find tool for pi-coding.

Converted from TypeScript core/tools/find.ts
"""
from pathlib import Path
from typing import Any, Optional
from pi.agent.tools import BaseTool, ToolSchema, ParameterType, ParameterProperty
import fnmatch


class FindTool(BaseTool):
    """
    Tool for finding files by pattern.

    Similar to Unix 'find' command.
    """

    name = "find"
    label = "find"
    description = (
        "Find files by glob pattern. "
        "Supports wildcards like *.py, **/*.ts, etc. "
        "Use for locating files in the codebase."
    )

    def __init__(self, cwd: Optional[str | Path] = None):
        """
        Initialize the find tool.

        Args:
            cwd: Working directory for relative paths
        """
        self.cwd = Path(cwd) if cwd else Path.cwd()
        super().__init__()

    def get_schema(self) -> ToolSchema:
        """Get parameter schema."""
        return ToolSchema(
            properties={
                "pattern": ParameterProperty(
                    type=ParameterType.STRING,
                    description="Glob pattern to match files (e.g., '*.py', '**/*.ts')",
                ),
                "path": ParameterProperty(
                    type=ParameterType.STRING,
                    description="Directory path to search (default: current directory)",
                ),
                "max_results": ParameterProperty(
                    type=ParameterType.NUMBER,
                    description="Maximum number of results to return (default: 100)",
                ),
            },
            required=["pattern"],
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
        """Execute the find tool."""
        # Check for abort signal
        if signal and hasattr(signal, "aborted") and signal.aborted:
            raise RuntimeError("Operation aborted")

        pattern = params.get("pattern", "")
        path = params.get("path", ".")
        max_results = params.get("max_results", 100)

        if not pattern:
            raise ValueError("Pattern is required")

        # Resolve path
        search_path = self.resolve_path(path)

        # Find matching files
        results = []

        def find_files(directory: Path, pattern: str) -> list[Path]:
            """Find files matching pattern."""
            matches = []

            # Handle recursive patterns (*/)
            if "**" in pattern:
                for item in directory.rglob(pattern.replace("**/", "")):
                    if item.is_file():
                        matches.append(item)
            else:
                # Non-recursive: only search immediate directory
                for item in directory.glob(pattern):
                    if item.is_file():
                        matches.append(item)

                # Also try matching in subdirectories for patterns like *.py
                for item in directory.iterdir():
                    if item.is_dir():
                        for sub_item in item.glob(pattern):
                            if sub_item.is_file():
                                matches.append(sub_item)

            return matches

        try:
            matched_files = find_files(search_path, pattern)

            # Convert to relative paths and limit results
            for file_path in matched_files:
                if signal and hasattr(signal, "aborted") and signal.aborted:
                    break

                try:
                    rel_path = file_path.relative_to(self.cwd)
                    results.append(str(rel_path))
                except ValueError:
                    # File is not relative to cwd, use absolute path
                    results.append(str(file_path))

                if len(results) >= max_results:
                    break

        except Exception as e:
            raise ValueError(f"Error searching for files: {e}")

        # Format results
        total_files = len(matched_files)

        if results:
            message = "\n".join(results)

            if total_files > len(results):
                message += f"\n\n(Showing {len(results)} of {total_files} files)"

        else:
            message = f"No files found matching pattern: {pattern}"

        return {
            "content": [{"type": "text", "text": message}],
            "details": {
                "pattern": pattern,
                "totalFiles": total_files,
                "resultsShown": len(results),
            },
        }


__all__ = ["FindTool"]
