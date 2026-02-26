"""Built-in tools for pi-coding."""

from .read import ReadTool
from .write import WriteTool
from .bash import BashTool
from .edit import EditTool
from .grep import GrepTool
from .find import FindTool
from .ls import LsTool


__all__ = [
    "ReadTool",
    "WriteTool",
    "BashTool",
    "EditTool",
    "GrepTool",
    "FindTool",
    "LsTool",
    "get_builtin_tools",
]


def get_builtin_tools() -> list:
    """Get all built-in tools as a list."""
    return [
        ReadTool(),
        WriteTool(),
        BashTool(),
        EditTool(),
        GrepTool(),
        FindTool(),
        LsTool(),
    ]
