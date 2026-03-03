"""Claude Code-style interactive REPL for pi-coding.

Features:
- Clean, minimal interface
- Real-time streaming display
- Tool execution feedback with status icons
- Theme-based styling
"""
import asyncio
from pathlib import Path
from typing import Optional, Any, Callable

import typer
from rich.console import Console
from rich.prompt import Prompt
from rich.live import Live

from ...core.sdk import CreateAgentSessionOptions, create_agent_session
from ...core.model_registry import ModelRegistry
from ...core.auth_storage import AuthStorage
from ...config import get_agent_dir
from .theme import get_theme


app = typer.Typer(
    name="pi",
    help="AI-powered coding assistant",
    add_completion=True,
    no_args_is_help=True,
)


class REPL:
    """
    Read-Eval-Print Loop for interactive coding assistance.

    Claude Code-inspired UI with:
    - Clean, minimal interface
    - Real-time streaming display
    - Tool execution with status icons
    - Theme-based styling
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        thinking: Optional[str] = None,
        cwd: Optional[Path] = None,
        show_thinking: bool = True,
    ):
        """Initialize the REPL."""
        self.console = Console()
        self.cwd = cwd or Path.cwd()
        self.provider = provider or "zai"
        self.model = model or "glm-5"
        self.thinking = thinking or "medium"
        self.show_thinking = show_thinking
        self.running = True
        self.session: Any = None
        self._message_count = 0
        self.theme = get_theme()

        # Event handling state
        self._unsubscribe: Optional[Callable] = None
        self._streaming_live: Optional[Live] = None
        self._streaming_content: str = ""
        self._streaming_thinking: str = ""
        self._pending_tools: dict[str, dict] = {}
        self._response_complete: asyncio.Event = asyncio.Event()

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
                self.console.print()
                self.console.print(f"[{self.theme.colors.warning}]Interrupted. Use /exit to quit.[/]")
                continue
            except EOFError:
                break
            except Exception as e:
                self.console.print(f"[{self.theme.colors.error}]Error: {e}[/]")
                import traceback
                traceback.print_exc()

        # Cleanup
        await self._shutdown()

        return 0

    async def _shutdown(self) -> None:
        """Clean shutdown of resources."""
        if self._unsubscribe:
            self._unsubscribe()
            self._unsubscribe = None

        if self._streaming_live:
            self._streaming_live.stop()
            self._streaming_live = None

        if self.session and hasattr(self.session, 'dispose'):
            self.session.dispose()

    def _print_welcome(self) -> None:
        """Print welcome message with clean, minimal style."""
        self.console.print()
        # Simple header
        self.console.print(f"[{self.theme.colors.primary} bold]pi[/] [{self.theme.colors.text_dim}]AI Coding Assistant[/]")
        self.console.print()

        # Compact help line
        self.console.print(f"[{self.theme.colors.text_dim}]Type your message or /help for commands[/]")
        self.console.print()

    async def _create_session(self) -> None:
        """Create the agent session."""
        if self._unsubscribe:
            self._unsubscribe()
            self._unsubscribe = None

        options = CreateAgentSessionOptions(
            cwd=self.cwd,
            thinking_level=self.thinking,
        )

        result = await create_agent_session(options)
        self.session = result.session

        if result.model_fallback_message:
            self.console.print(f"[{self.theme.colors.warning}]{result.model_fallback_message}[/]")

        # Subscribe to agent events for real-time display
        self._unsubscribe = self.session.subscribe(self._handle_agent_event)

    def _handle_agent_event(self, event: dict) -> None:
        """Handle agent events for real-time display."""
        event_type = event.get("type", "")

        try:
            loop = asyncio.get_running_loop()
            if event_type == "message_start":
                loop.create_task(self._on_message_start(event))
            elif event_type == "message_update":
                loop.create_task(self._on_message_update(event))
            elif event_type == "message_end":
                loop.create_task(self._on_message_end(event))
            elif event_type == "tool_execution_start":
                loop.create_task(self._on_tool_start(event))
            elif event_type == "tool_execution_end":
                loop.create_task(self._on_tool_end(event))
            elif event_type == "agent_end":
                loop.create_task(self._on_agent_end(event))
        except RuntimeError:
            pass

    async def _on_message_start(self, event: dict) -> None:
        """Handle message streaming start."""
        message = event.get("message", {})
        if message.get("role") == "assistant":
            self._streaming_content = ""
            self._streaming_thinking = ""
            self._response_complete.clear()

            # Start live display
            self._streaming_live = Live(
                "",
                console=self.console,
                refresh_per_second=4,
            )
            self._streaming_live.start()

    async def _on_message_update(self, event: dict) -> None:
        """Handle streaming content updates."""
        message = event.get("message", {})
        if message.get("role") != "assistant":
            return

        content = message.get("content", [])
        if isinstance(content, str):
            new_text = content
        else:
            texts = []
            thinking_parts = []
            for block in content:
                # Handle both dict and dataclass content blocks
                if isinstance(block, dict):
                    block_type = block.get("type", "")
                    if block_type == "text":
                        texts.append(block.get("text", ""))
                    elif block_type == "thinking":
                        thinking_parts.append(block.get("thinking", ""))
                else:
                    # Handle dataclass objects (TextContent, ThinkingContent, etc.)
                    block_type = getattr(block, "type", "")
                    if block_type == "text":
                        texts.append(getattr(block, "text", ""))
                    elif block_type == "thinking":
                        thinking_parts.append(getattr(block, "thinking", ""))
            new_text = "".join(texts)
            new_thinking = "".join(thinking_parts)

            if new_thinking != self._streaming_thinking and self.show_thinking:
                self._streaming_thinking = new_thinking

        if new_text != self._streaming_content:
            self._streaming_content = new_text
            if self._streaming_live:
                self._streaming_live.update(self._format_streaming_content())

    def _format_streaming_content(self) -> str:
        """Format streaming content for display."""
        lines = []

        if self._streaming_thinking and self.show_thinking:
            lines.append(f"[{self.theme.colors.text_dim} italic]{self._streaming_thinking}[/]")
            lines.append("")

        if self._streaming_content:
            lines.append(self._streaming_content)

        return "\n".join(lines)

    async def _on_message_end(self, event: dict) -> None:
        """Handle message streaming end."""
        if self._streaming_live:
            self._streaming_live.stop()
            self._streaming_live = None
        self.console.print()

    async def _on_tool_start(self, event: dict) -> None:
        """Handle tool execution start."""
        tool_name = event.get("toolName", "unknown")
        tool_call_id = event.get("toolCallId", "")
        args = event.get("args", {})

        self._pending_tools[tool_call_id] = {
            "name": tool_name,
            "args": args,
            "start_time": asyncio.get_event_loop().time(),
        }

        # Minimal tool start indicator
        self.console.print(f"  [{self.theme.colors.text_dim}]{self.theme.icons.running}[/] [{self.theme.colors.accent}]{tool_name}[/]")

    async def _on_tool_end(self, event: dict) -> None:
        """Handle tool execution end."""
        tool_name = event.get("toolName", "unknown")
        tool_call_id = event.get("toolCallId", "")
        result = event.get("result", "")
        is_error = event.get("isError", False)

        # Calculate duration
        duration = None
        if tool_call_id in self._pending_tools:
            start_time = self._pending_tools[tool_call_id].get("start_time", 0)
            duration = asyncio.get_event_loop().time() - start_time
            del self._pending_tools[tool_call_id]

        # Format result
        if isinstance(result, str):
            result_str = result
        else:
            result_str = str(result)

        if len(result_str) > 200:
            result_str = result_str[:200] + "..."

        # Determine style
        color = self.theme.colors.error if is_error else self.theme.colors.success
        icon = self.theme.icons.error if is_error else self.theme.icons.success

        # Compact result display
        duration_str = f" ({duration:.2f}s)" if duration else ""
        self.console.print(f"  [{color}]{icon}[/] [{self.theme.colors.accent}]{tool_name}[/]{duration_str}")

        if result_str:
            self.console.print(f"    [{self.theme.colors.text_dim}]{result_str[:100]}[/]")
        self.console.print()

    async def _on_agent_end(self, event: dict) -> None:
        """Handle agent turn end."""
        self._response_complete.set()

    async def _get_input(self) -> str:
        """Get user input from prompt."""
        prompt_str = f"[{self.theme.colors.primary} bold]{self.theme.icons.user}[/] "

        try:
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
        """Handle a user message."""
        # Don't redisplay the input - user already sees it from prompt
        self.console.print()

        try:
            self._response_complete.clear()
            self._streaming_content = ""
            self._streaming_thinking = ""

            await self.session.prompt(message)

            try:
                await asyncio.wait_for(
                    self._response_complete.wait(),
                    timeout=300.0
                )
            except asyncio.TimeoutError:
                self.console.print(f"[{self.theme.colors.error}]Response timed out[/]")

        except Exception as e:
            self.console.print(f"[{self.theme.colors.error}]Error: {e}[/]")
            import traceback
            traceback.print_exc()

    async def _handle_command(self, command: str) -> None:
        """Handle a slash command."""
        parts = command.split(None, 1)
        cmd = parts[0][1:].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd in ("exit", "quit"):
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

        elif cmd == "clear":
            self._clear_screen()

        else:
            self.console.print(f"[{self.theme.colors.error}]Unknown command: {cmd}[/]")
            self.console.print(f"[{self.theme.colors.text_dim}]Type /help for available commands[/]")

    def _clear_screen(self) -> None:
        """Clear the screen."""
        self.console.clear()

    def _show_help(self) -> None:
        """Show help information."""
        self.console.print()
        self.console.print(f"[{self.theme.colors.primary} bold]Commands[/]")
        self.console.print()

        commands = [
            ("/model [id]", "Switch AI model", "/model claude-opus-4-5"),
            ("/thinking [level]", "Set thinking level", "/thinking high"),
            ("/models", "List all models", ""),
            ("/providers", "List providers", ""),
            ("/clear", "Clear screen", ""),
            ("/help", "Show this help", ""),
            ("/exit", "Exit", "Ctrl+D"),
        ]

        for cmd, desc, example in commands:
            self.console.print(
                f"  [{self.theme.colors.accent}]{cmd:<20}[/] "
                f"[{self.theme.colors.text_dim}]{desc}[/]"
            )

        self.console.print()
        self.console.print(f"[{self.theme.colors.text_dim}]Thinking levels: off, minimal, low, medium, high, xhigh[/]")

    async def _list_models(self) -> None:
        """List available models."""
        models = self.model_registry.list_models()

        if not models:
            self.console.print(f"[{self.theme.colors.warning}]No models found[/]")
            return

        self.console.print(f"[{self.theme.colors.primary} bold]Available Models[/]")
        self.console.print()

        for model in models[:30]:
            reasoning = f" [{self.theme.colors.accent}]thinking[/]" if model.reasoning else ""
            self.console.print(
                f"  [{self.theme.colors.text_dim}]{model.provider}[/]/"
                f"[{self.theme.colors.accent}]{model.id[:40]}[/]{reasoning}"
            )

        if len(models) > 30:
            self.console.print(f"\n[{self.theme.colors.text_dim}]+ {len(models) - 30} more models. Use /model <name> to search.[/]")

    def _list_providers(self) -> None:
        """List all providers."""
        providers = self.model_registry.list_providers()

        self.console.print(f"[{self.theme.colors.primary} bold]Providers[/]")
        self.console.print()

        for provider in sorted(providers):
            models = self.model_registry.list_models(provider)
            reasoning_count = sum(1 for m in models if m.reasoning)
            reasoning_str = f" ({reasoning_count} thinking)" if reasoning_count else ""
            self.console.print(
                f"  [{self.theme.colors.accent}]{provider}[/] "
                f"[{self.theme.colors.text_dim}]{len(models)} models{reasoning_str}[/]"
            )

    async def _set_model(self, model_spec: str) -> None:
        """Set the model."""
        if "/" in model_spec:
            provider, model_id = model_spec.split("/", 1)
        else:
            results = self.model_registry.search(model_spec)
            if results:
                model = results[0]
                provider = model.provider
                model_id = model.id
            else:
                self.console.print(f"[{self.theme.colors.error}]Model not found: {model_spec}[/]")
                return

        model = self.model_registry.find(provider, model_id)
        if model:
            self.provider = provider
            self.model = model_id

            await self._create_session()

            self.console.print(f"[{self.theme.colors.success}]{self.theme.icons.success}[/] [{self.theme.colors.accent}]{model.name}[/]")
        else:
            self.console.print(f"[{self.theme.colors.error}]Model not found: {provider}/{model_id}[/]")

    async def _show_current_model(self) -> None:
        """Show current model information."""
        model = self.model_registry.find(self.provider, self.model)
        if model:
            reasoning = f" (thinking)" if model.reasoning else ""
            self.console.print(
                f"[{self.theme.colors.accent}]{model.provider}/{model.id}[/] "
                f"[{self.theme.colors.text_dim}]{model.name}{reasoning}[/]"
            )
        else:
            self.console.print(f"[{self.theme.colors.accent}]{self.provider}/{self.model}[/]")

    async def _set_thinking(self, level: str) -> None:
        """Set thinking level."""
        valid_levels = ["off", "minimal", "low", "medium", "high", "xhigh"]

        if level not in valid_levels:
            self.console.print(f"[{self.theme.colors.error}]Invalid level. Valid: {', '.join(valid_levels)}[/]")
            return

        self.thinking = level

        await self._create_session()

        self.console.print(f"[{self.theme.colors.success}]{self.theme.icons.success}[/] [{self.theme.colors.accent}]thinking: {level}[/]")

    def _show_current_thinking(self) -> None:
        """Show current thinking level."""
        self.console.print(f"[{self.theme.colors.accent}]thinking: {self.thinking}[/]")


__all__ = ["REPL", "app"]
