"""Typer-based CLI entry point for pi-coding."""
import asyncio
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from .modes.interactive.repl import REPL
from .modes.print_mode import PrintMode
from .cli.args import parse_args


console = Console()


# Define typer app
app = typer.Typer(
    name="pi",
    help="🤖 AI-powered coding assistant",
    add_completion=True,
    no_args_is_help=True,
)


@app.command()
def interactive(
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="AI provider"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model ID"),
    thinking: Optional[str] = typer.Option(None, "--thinking", "-t", help="Thinking level"),
):
    """
    Start interactive REPL mode.

    This is the default mode when no arguments are provided.
    """
    async def run_repl():
        repl = REPL(
            provider=provider,
            model=model,
            thinking=thinking,
            cwd=Path.cwd(),
        )
        return await repl.start()

    sys.exit(asyncio.run(run_repl()))


@app.command()
def chat(
    message: list[str] = typer.Argument(None, help="Messages to send"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="AI provider"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model ID"),
    thinking: Optional[str] = typer.Option(None, "--thinking", "-t", help="Thinking level"),
):
    """
    Send a message and get a response (one-shot mode).

    Example:
        pi chat "Write a Python function"
    """
    if not message:
        console.print("[red]Error: No message provided[/red]")
        console.print("Usage: pi chat \"your message\"")
        raise typer.Exit(1)

    # Combine multiple message arguments
    combined_message = " ".join(message)

    # Use print mode for one-shot
    from .cli.args import CliArgs
    args = CliArgs(
        provider=provider,
        model=model,
        thinking=thinking,
        messages=[combined_message],
        print_=True,
    )

    print_mode = PrintMode(args)
    sys.exit(asyncio.run(print_mode.run()))


def main(args: list[str] = None) -> int:
    """
    Main entry point.

    This function routes to the appropriate mode based on arguments.
    """
    if args is None:
        args = sys.argv[1:]

    # If no arguments, start interactive mode
    if not args:
        try:
            repl = REPL()
            return asyncio.run(repl.start())
        except KeyboardInterrupt:
            console.print("\n[yellow]Goodbye![/yellow]")
            return 0
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return 1

    # Parse arguments to determine mode
    try:
        parsed = parse_args(args)

        # Handle special flags
        if parsed.help:
            from .cli.args import print_help
            print_help()
            return 0

        if parsed.version:
            from .config import APP_NAME, VERSION
            console.print(f"{APP_NAME} v{VERSION}")
            return 0

        # Check for print mode or messages
        if parsed.print_ or parsed.messages:
            print_mode = PrintMode(parsed)
            return asyncio.run(print_mode.run())

        # Otherwise, start interactive mode
        repl = REPL(
            provider=parsed.provider,
            model=parsed.model,
            thinking=parsed.thinking,
            cwd=Path.cwd(),
        )

        # Process initial messages if provided
        if parsed.messages:
            for msg in parsed.messages:
                asyncio.run(repl._handle_message(msg))

        return asyncio.run(repl.start())

    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye![/yellow]")
        return 0
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
