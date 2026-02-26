"""
Main CLI entry point for pi-coding.

Converted from TypeScript cli.ts and main.ts
"""
import sys
import asyncio
from pathlib import Path
from typing import Optional

from .cli.args import parse_args, print_help, CliArgs
from .cli.list_models import list_models
from .config import (
    APP_NAME,
    VERSION,
    get_agent_dir,
    get_sessions_dir,
)
from .core.defaults import DEFAULT_SYSTEM_PROMPT
from .modes.print_mode import PrintMode
from .modes.interactive import InteractiveMode, InteractiveModeConfig


async def main_async(args: list[str] = None) -> int:
    """
    Main async entry point.

    Args:
        args: Command-line arguments (excluding program name)

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    if args is None:
        args = sys.argv[1:]

    # Parse arguments
    parsed = parse_args(args)

    # Handle help
    if parsed.help:
        print_help()
        return 0

    # Handle version
    if parsed.version:
        print(f"{APP_NAME} v{VERSION}")
        return 0

    # Handle list models
    if parsed.list_models is not None:
        search = parsed.list_models if isinstance(parsed.list_models, str) else None
        return await list_models(search=search)

    # Ensure agent directory exists
    agent_dir = get_agent_dir()
    agent_dir.mkdir(parents=True, exist_ok=True)

    # Ensure sessions directory exists
    sessions_dir = get_sessions_dir()
    sessions_dir.mkdir(parents=True, exist_ok=True)

    if parsed.print_:
        # Run in print mode (non-interactive)
        print_mode = PrintMode(parsed)
        return await print_mode.run()
    else:
        # Interactive mode
        config = InteractiveModeConfig(
            cwd=Path.cwd(),
            provider=parsed.provider,
            model=parsed.model,
            thinking_level=parsed.thinking,
            messages=parsed.messages,
        )
        interactive_mode = InteractiveMode(config)
        return await interactive_mode.run()

    return 0


def main(args: list[str] = None) -> int:
    """
    Main entry point (sync wrapper for async main).

    Args:
        args: Command-line arguments (excluding program name)

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        return asyncio.run(main_async(args))
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
