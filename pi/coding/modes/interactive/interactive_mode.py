"""Interactive mode for pi-coding using typer REPL."""
import asyncio
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from .repl import REPL


@dataclass
class InteractiveModeConfig:
    """Configuration for interactive mode."""
    cwd: Optional[Path] = None
    session_file: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    thinking_level: Optional[str] = None
    messages: Optional[list[str]] = None


class InteractiveMode:
    """
    Interactive mode using typer-based REPL.

    Provides a clean, simple REPL interface with:
    - Command history and autocomplete
    - Rich formatted output
    - Slash commands
    - No complex TUI framework
    """

    def __init__(self, config: InteractiveModeConfig):
        """
        Initialize interactive mode.

        Args:
            config: Configuration options
        """
        self.config = config
        self.cwd = config.cwd or Path.cwd()

    async def run(self) -> int:
        """
        Run the interactive REPL.

        Returns:
            Exit code (0 for success, non-zero for error)
        """
        repl = REPL(
            provider=self.config.provider,
            model=self.config.model,
            thinking=self.config.thinking_level,
            cwd=self.cwd,
        )

        # Process initial messages if provided
        if self.config.messages:
            for message in self.config.messages:
                if message.strip():
                    await repl._handle_message(message)

        # Start the REPL loop
        return await repl.start()


__all__ = ["InteractiveMode", "InteractiveModeConfig"]
