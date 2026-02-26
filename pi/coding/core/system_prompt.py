"""System prompt builder for pi-coding.

Converted from TypeScript core/system-prompt.ts
"""
from typing import Optional


class SystemPromptBuilder:
    """Builds system prompts with various components."""

    def __init__(self):
        """Initialize the system prompt builder."""
        self.base_prompt: Optional[str] = None
        self.appendages: list[str] = []

    def set_base(self, prompt: str) -> "SystemPromptBuilder":
        """
        Set the base system prompt.

        Args:
            prompt: Base prompt text

        Returns:
            Self for chaining
        """
        self.base_prompt = prompt
        return self

    def append(self, text: str) -> "SystemPromptBuilder":
        """
        Append text to the system prompt.

        Args:
            text: Text to append

        Returns:
            Self for chaining
        """
        self.appendages.append(text)
        return self

    def build(self) -> str:
        """
        Build the final system prompt.

        Returns:
            Complete system prompt string
        """
        parts = []

        if self.base_prompt:
            parts.append(self.base_prompt)

        if self.appendages:
            parts.extend(self.appendages)

        return "\n\n".join(parts)


__all__ = ["SystemPromptBuilder"]
