"""File argument processing for pi-coding.

Converted from TypeScript cli/file-processor.ts
"""

from pathlib import Path
from typing import Union, Optional, Any


async def process_file_args(file_args: list[str], cwd: Union[str, Path] = ".") -> list[dict]:
    """
    Process file arguments (@file notation) and convert to messages.

    Args:
        file_args: List of file paths (without @ prefix)
        cwd: Current working directory for relative paths

    Returns:
        List of message dictionaries
    """
    # TODO: Implement file processing
    # This should handle:
    # - Reading text files as content
    # - Processing images
    # - Handling frontmatter in markdown files
    return []


def read_file_content(file_path: Path) -> Optional[str]:
    """
    Read file content as string.

    Args:
        file_path: Path to file

    Returns:
        File content or None if not readable
    """
    try:
        return file_path.read_text(encoding="utf-8")
    except (IOError, UnicodeDecodeError):
        return None
