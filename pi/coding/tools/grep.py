"""
Grep tool for pi-coding.

Converted from TypeScript core/tools/grep.ts
"""
import re
from pathlib import Path
from typing import Any, Optional
from pi.agent.tools import BaseTool, ToolSchema, ParameterType, ParameterProperty


class GrepTool(BaseTool):
    """
    Tool for searching file contents (grep-like).

    Searches for text patterns in files.
    """

    name = "grep"
    label = "grep"
    description = (
        "Search for text patterns in files. "
        "Supports literal string matching and basic regex patterns. "
        "Use for finding code, text, or patterns in files."
    )

    def __init__(self, cwd: Optional[str | Path] = None):
        """
        Initialize the grep tool.

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
                    description="Text pattern to search for (supports regex)",
                ),
                "path": ParameterProperty(
                    type=ParameterType.STRING,
                    description="File or directory path to search (default: current directory)",
                ),
                "recursive": ParameterProperty(
                    type=ParameterType.BOOLEAN,
                    description="Search recursively in subdirectories",
                ),
                "include": ParameterProperty(
                    type=ParameterType.STRING,
                    description="File pattern to include (e.g., '*.py')",
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
        """Execute the grep tool."""
        # Check for abort signal
        if signal and hasattr(signal, "aborted") and signal.aborted:
            raise RuntimeError("Operation aborted")

        pattern = params.get("pattern", "")
        path = params.get("path", ".")
        recursive = params.get("recursive", True)
        include = params.get("include")
        max_results = params.get("max_results", 100)

        if not pattern:
            raise ValueError("Pattern is required")

        # Resolve path
        search_path = self.resolve_path(path)

        # Compile regex pattern
        try:
            regex = re.compile(pattern)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")

        # Collect results
        results = []
        total_matches = 0

        def search_file(file_path: Path) -> list[tuple[int, str]]:
            """Search a single file and return matching lines."""
            matches = []
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                for line_num, line in enumerate(content.split("\n"), 1):
                    if regex.search(line):
                        matches.append((line_num, line.rstrip()))
            except Exception:
                pass  # Skip files that can't be read
            return matches

        def search_dir(directory: Path) -> None:
            """Recursively search directory."""
            nonlocal results, total_matches

            for item in directory.iterdir():
                if signal and hasattr(signal, "aborted") and signal.aborted:
                    return

                if item.is_file():
                    # Check include pattern
                    if include:
                        if not item.match(include):
                            continue

                    matches = search_file(item)
                    if matches:
                        total_matches += len(matches)
                        for line_num, line in matches:
                            results.append({
                                "file": str(item.relative_to(self.cwd)),
                                "line": line_num,
                                "text": line,
                            })
                            if len(results) >= max_results:
                                return

                elif item.is_dir() and recursive:
                    search_dir(item)

        # Perform search
        if search_path.is_file():
            matches = search_file(search_path)
            for line_num, line in matches:
                results.append({
                    "file": str(search_path.relative_to(self.cwd)),
                    "line": line_num,
                    "text": line,
                })
            total_matches = len(matches)
        elif search_path.is_dir():
            search_dir(search_path)

        # Format results
        if results:
            output_lines = []
            for result in results:
                output_lines.append(f"{result['file']}:{result['line']}: {result['text']}")

            message = "\n".join(output_lines)

            if total_matches > len(results):
                message += f"\n\n(Showing {len(results)} of {total_matches} matches)"

        else:
            message = f"No matches found for pattern: {pattern}"

        return {
            "content": [{"type": "text", "text": message}],
            "details": {
                "pattern": pattern,
                "matches": total_matches,
                "resultsShown": len(results),
            },
        }


__all__ = ["GrepTool"]
