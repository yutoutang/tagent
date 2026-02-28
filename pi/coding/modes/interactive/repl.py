"""Typer-based interactive REPL for pi-coding.

Provides a clean, simple REPL interface with:
- Command history and autocomplete
- Rich output formatting
- Slash commands for model management
- Clean message display
"""
import asyncio
import sys
from pathlib import Path
from typing import Optional, Any

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.live import Live
from rich.table import Table
from rich.text import Text

from ...core.sdk import CreateAgentSessionOptions, create_agent_session
from ...core.model_registry import ModelRegistry
from ...core.auth_storage import AuthStorage
from ...config import get_agent_dir


app = typer.Typer(
    name="pi",
    help="AI-powered coding assistant",
    add_completion=True,
    no_args_is_help=True,
)


class REPL:
    """
    Read-Eval-Print Loop for interactive coding assistance.

    Features:
    - Command history (up/down arrows)
    - Slash commands (/model, /thinking, /exit, /help)
    - Rich formatted output
    - Streaming response display
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        thinking: Optional[str] = None,
        cwd: Optional[Path] = None,
    ):
        """Initialize the REPL."""
        self.console = Console()
        self.cwd = cwd or Path.cwd()
        self.provider = provider or "zai"
        self.model = model or "glm-5"
        self.thinking = thinking or "medium"
        self.running = True
        self.session: Any = None
        self._message_count = 0

        # Model registry
        agent_dir = get_agent_dir()
        self.model_registry = ModelRegistry(
            auth_storage=AuthStorage.create(agent_dir / "auth.json"),
            models_path=agent_dir / "models.json",
        )

    async def start(self) -> int:
        """Start the REPL loop."""
        # Print welcome message
        self._print_welcome()

        # Create agent session
        await self._create_session()

        # Main REPL loop
        while self.running:
            try:
                # Get user input
                user_input = await self._get_input()

                if not user_input:
                    continue

                # Handle commands
                if user_input.startswith("/"):
                    await self._handle_command(user_input)
                else:
                    await self._handle_message(user_input)

                self._message_count += 1

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Interrupted. Use /exit to quit.[/yellow]")
                continue
            except EOFError:
                break
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/red]")
                import traceback
                traceback.print_exc()

        # Cleanup
        if self.session:
            await self.session.close()

        return 0

    def _print_welcome(self) -> None:
        """Print welcome message."""
        self.console.print()
        self.console.print(Panel(
            "[bold cyan]🤖 pi - AI Coding Assistant[/bold cyan]",
            border_style="cyan",
        ))
        self.console.print()

        # Show commands
        commands_table = Table(show_header=False, box=None, padding=(0, 2))
        commands_table.add_column("Command", style="cyan")
        commands_table.add_column("Description")

        commands_table.add_row("/model [provider/id]", "Switch AI model")
        commands_table.add_row("/thinking [level]", "Set thinking level")
        commands_table.add_row("/models", "List all models")
        commands_table.add_row("/providers", "List providers")
        commands_table.add_row("/help", "Show this help")
        commands_table.add_row("/exit or Ctrl+D", "Exit")

        self.console.print(Panel(
            commands_table,
            title="[bold]Commands[/bold]",
            border_style="dim",
        ))

        # Show current config
        config_table = Table(show_header=False, box=None, padding=(0, 2))
        config_table.add_column("Setting", style="cyan")
        config_table.add_column("Value", style="green")

        config_table.add_row("Provider", self.provider)
        config_table.add_row("Model", self.model)
        config_table.add_row("Thinking", self.thinking)

        self.console.print(Panel(
            config_table,
            title="[bold]Current Config[/bold]",
            border_style="dim",
        ))
        self.console.print()

    async def _create_session(self) -> None:
        """Create the agent session."""
        # todo
        options = CreateAgentSessionOptions(
            cwd=self.cwd,
            thinking_level=self.thinking,
        )

        result = await create_agent_session(options)
        self.session = result.session

        if result.model_fallback_message:
            self.console.print(f"[yellow]{result.model_fallback_message}[/yellow]")

    async def _get_input(self) -> str:
        """Get user input from prompt."""
        prompt_str = f"[bold cyan]>>>[/bold cyan] "

        try:
            # Use rich Prompt for input
            user_input = Prompt.ask(
                prompt_str,
                console=self.console,
                default="",
                show_default=False,
            )
            return user_input.strip()
        except (EOFError, KeyboardInterrupt):
            self.running = False
            return ""

    async def _handle_message(self, message: str) -> None:
        """
        Handle a user message.

        Args:
            message: The user's message
        """
        # Display user message
        self.console.print(Panel(
            message,
            title="[bold cyan]You[/bold cyan]",
            border_style="cyan",
            padding=(0, 1),
        ))

        # Show thinking indicator
        with self.console.status("[bold yellow]Thinking...[/bold yellow]", spinner="dots"):
            try:
                # Send to agent
                await self.session.prompt(message)
                await self.session.wait_for_idle()

                # Display response
                await self._display_response()

            except Exception as e:
                self.console.print(f"[red]Error: {e}[/red]")

    async def _display_response(self) -> None:
        """Display the agent's response."""
        messages = self.session.state.get("messages", [])

        # Get new messages (last one should be the response)
        for msg in messages[-1:]:
            if msg.get("role") == "assistant":
                content = msg.get("content", "")

                if isinstance(content, str):
                    # Simple text response
                    self.console.print()
                    self.console.print(Panel(
                        Markdown(content),
                        title="[bold green]Assistant[/bold green]",
                        border_style="green",
                        padding=(0, 1),
                    ))
                elif isinstance(content, list):
                    # Structured response with blocks
                    self.console.print()
                    for block in content:
                        if block.get("type") == "text":
                            self.console.print(Panel(
                                Markdown(block.get("text", "")),
                                title="[bold green]Assistant[/bold green]",
                                border_style="green",
                                padding=(0, 1),
                            ))
                        elif block.get("type") == "thinking":
                            thinking_text = block.get("thinking", "")
                            if thinking_text:
                                self.console.print(Panel(
                                    f"[dim]{thinking_text}[/dim]",
                                    title="[bold yellow]Thinking[/bold yellow]",
                                    border_style="yellow",
                                    padding=(0, 1),
                                ))

        self.console.print()

    async def _handle_command(self, command: str) -> None:
        """
        Handle a slash command.

        Args:
            command: The command string (with leading slash)
        """
        parts = command.split(None, 1)
        cmd = parts[0][1:].lower()  # Remove leading slash
        args = parts[1] if len(parts) > 1 else ""

        if cmd == "exit" or cmd == "quit":
            self.running = False

        elif cmd == "help":
            self._show_help()

        elif cmd == "models":
            await self._list_models()

        elif cmd == "providers":
            self._list_providers()

        elif cmd == "model":
            if args:
                await self._set_model(args)
            else:
                await self._show_current_model()

        elif cmd == "thinking":
            if args:
                await self._set_thinking(args)
            else:
                self._show_current_thinking()

        else:
            self.console.print(f"[red]Unknown command: {cmd}[/red]")
            self.console.print("Type /help for available commands")

    def _show_help(self) -> None:
        """Show help information."""
        help_text = """
## Available Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/model [provider/id]` | Switch AI model | `/model anthropic/claude-opus-4-5` |
| `/thinking [level]` | Set thinking level | `/thinking high` |
| `/models` | List all models | `/models` |
| `/providers` | List all providers | `/providers` |
| `/help` | Show this help | `/help` |
| `/exit` | Exit the REPL | `/exit` |

**Thinking levels:** off, minimal, low, medium, high, xhigh

**Keyboard shortcuts:**
- `Ctrl+C` - Interrupt current request
- `Ctrl+D` - Exit
- Up/Down arrows - Command history
"""
        self.console.print(Markdown(help_text))

    async def _list_models(self) -> None:
        """List available models."""
        models = self.model_registry.list_models()

        if not models:
            self.console.print("[yellow]No models found[/yellow]")
            return

        table = Table(title="Available Models")
        table.add_column("Provider", style="cyan")
        table.add_column("Model", style="green")
        table.add_column("Name", style="white")
        table.add_column("Reasoning", style="yellow")

        # Show first 50 models
        for model in models[:50]:
            table.add_row(
                model.provider,
                Text(model.id[:40], overflow="ellipsis"),
                Text(model.name[:30], overflow="ellipsis"),
                "✓" if model.reasoning else "✗",
            )

        if len(models) > 50:
            self.console.print(f"\n[dim]... and {len(models) - 50} more models[/dim]")

        self.console.print(table)
        self.console.print(f"\n[bold]Total: {len(models)} models from {len(self.model_registry.list_providers())} providers[/bold]")

    def _list_providers(self) -> None:
        """List all providers."""
        providers = self.model_registry.list_providers()

        table = Table(title="Available Providers")
        table.add_column("Provider", style="cyan")
        table.add_column("Models", style="green")
        table.add_column("Reasoning", style="yellow")

        for provider in sorted(providers):
            models = self.model_registry.list_models(provider)
            reasoning_count = sum(1 for m in models if m.reasoning)
            table.add_row(
                provider,
                str(len(models)),
                str(reasoning_count),
            )

        self.console.print(table)

    async def _set_model(self, model_spec: str) -> None:
        """
        Set the model.

        Args:
            model_spec: Model specification (provider/id or just id)
        """
        if "/" in model_spec:
            provider, model_id = model_spec.split("/", 1)
        else:
            # Search for model
            results = self.model_registry.search(model_spec)
            if results:
                model = results[0]
                provider = model.provider
                model_id = model.id
            else:
                self.console.print(f"[red]Model not found: {model_spec}[/red]")
                return

        # Verify model exists
        model = self.model_registry.find(provider, model_id)
        if model:
            self.provider = provider
            self.model = model_id

            # Recreate session with new model
            await self._create_session()

            self.console.print(f"[green]✓ Switched to {model.name}[/green]")
        else:
            self.console.print(f"[red]Model not found: {provider}/{model_id}[/red]")

    async def _show_current_model(self) -> None:
        """Show current model information."""
        model = self.model_registry.find(self.provider, self.model)
        if model:
            info = f"""
## Current Model

- **Provider:** {model.provider}
- **Model:** {model.id}
- **Name:** {model.name}
- **API:** {model.api}
- **Reasoning:** {'Yes' if model.reasoning else 'No'}
"""
            self.console.print(Markdown(info))
        else:
            self.console.print(f"[cyan]Provider:[/cyan] {self.provider}")
            self.console.print(f"[cyan]Model:[/cyan] {self.model}")

    async def _set_thinking(self, level: str) -> None:
        """
        Set thinking level.

        Args:
            level: Thinking level (off, minimal, low, medium, high, xhigh)
        """
        valid_levels = ["off", "minimal", "low", "medium", "high", "xhigh"]

        if level not in valid_levels:
            self.console.print(f"[red]Invalid thinking level. Valid: {', '.join(valid_levels)}[/red]")
            return

        self.thinking = level

        # Recreate session
        await self._create_session()

        self.console.print(f"[green]✓ Thinking level set to {level}[/green]")

    def _show_current_thinking(self) -> None:
        """Show current thinking level."""
        self.console.print(f"[cyan]Thinking level:[/cyan] {self.thinking}")


__all__ = ["REPL", "app"]
