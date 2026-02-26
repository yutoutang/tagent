"""
Print mode for pi-coding.

Non-interactive mode that processes prompts and exits.
Converted from TypeScript modes/print-mode.ts
"""
from typing import Any, Optional
from pathlib import Path

from ..core.sdk import CreateAgentSessionOptions, create_agent_session
from ..cli.args import CliArgs
from ..config import get_agent_dir


class PrintMode:
    """
    Non-interactive mode for processing prompts.

    Runs the agent, prints results, and exits.
    """

    def __init__(
        self,
        args: CliArgs,
        cwd: Optional[str | Path] = None,
    ):
        """
        Initialize print mode.

        Args:
            args: Parsed CLI arguments
            cwd: Working directory
        """
        self.args = args
        self.cwd = Path(cwd) if cwd else Path.cwd()

    async def run(self) -> int:
        """
        Run the agent in print mode.

        Returns:
            Exit code (0 for success, non-zero for error)
        """
        from ..core.defaults import DEFAULT_SYSTEM_PROMPT

        # Build session options
        options = CreateAgentSessionOptions(
            cwd=self.cwd,
        )

        # Apply CLI overrides
        if self.args.provider or self.args.model:
            # Model specification from CLI
            provider = self.args.provider or "google"
            model_id = self.args.model or "gemini-2.5-flash-lite-preview-06-17"
            options.model = {
                "provider": provider,
                "id": model_id,
            }

        if self.args.thinking:
            options.thinking_level = self.args.thinking

        # Create session
        try:
            result = await create_agent_session(options)
            session = result.session

            # Print any warning message
            if result.model_fallback_message:
                print(f"Note: {result.model_fallback_message}")

            # Process messages
            for message_text in self.args.messages:
                await session.prompt(message_text)

            # Wait for completion
            await session.wait_for_idle()

            # Print final messages
            for message in session.state.get("messages", []):
                self._print_message(message)

            return 0

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error: {e}")
            return 1

    def _print_message(self, message: dict[str, Any]) -> None:
        """Print a message to stdout."""
        role = message.get("role", "")
        content = message.get("content", "")

        if role == "assistant":
            if isinstance(content, str):
                print(content)
            elif isinstance(content, list):
                for block in content:
                    if block.get("type") == "text":
                        print(block.get("text", ""))
                    elif block.get("type") == "thinking":
                        print(f"[Thinking: {block.get('thinking', '')}]")


__all__ = ["PrintMode"]
