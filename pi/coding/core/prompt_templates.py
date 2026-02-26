"""Prompt templates for pi-coding.

Converted from TypeScript core/prompt-templates.ts
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class PromptTemplate:
    """A prompt template definition."""
    name: str
    description: str
    content: str
    path: Optional[Path] = None
    variables: Optional[list[str]] = None


class PromptTemplates:
    """Manages prompt templates."""

    def __init__(self, directories: Optional[list[Path]] = None):
        """
        Initialize the prompt templates manager.

        Args:
            directories: List of directories to search for templates
        """
        self.directories = directories or []

    def load_templates(self) -> list[PromptTemplate]:
        """
        Load all templates from configured directories.

        Returns:
            List of loaded templates
        """
        # TODO: Implement template loading
        return []

    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """
        Get a template by name.

        Args:
            name: Template name

        Returns:
            PromptTemplate or None if not found
        """
        # TODO: Implement template lookup
        return None


__all__ = ["PromptTemplate", "PromptTemplates"]
