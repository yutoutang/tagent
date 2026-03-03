"""Prompt templates for pi-coding.

Converted from TypeScript core/prompt-templates.ts
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List
import re


@dataclass
class PromptTemplate:
    """A prompt template definition."""
    name: str
    description: str
    content: str
    path: Optional[Path] = None
    variables: Optional[List[str]] = None

    def render(self, **kwargs) -> str:
        """
        Render the template with the given variables.

        Args:
            **kwargs: Variable values to substitute

        Returns:
            Rendered template string
        """
        if not self.variables:
            return self.content

        result = self.content
        for var in self.variables:
            pattern = r"\{\{\s*" + re.escape(var) + r"\s*\}\}"
            value = str(kwargs.get(var, ""))
            result = re.sub(pattern, value, result)

        return result


class PromptTemplates:
    """Manages prompt templates."""

    def __init__(self, directories: Optional[List[Path]] = None):
        """
        Initialize the prompt templates manager.

        Args:
            directories: List of directories to search for templates
        """
        self.directories = directories or []
        self._templates: dict[str, PromptTemplate] = {}
        self._loaded = False

    def add_directory(self, directory: Path) -> None:
        """
        Add a directory to search for templates.

        Args:
            directory: Directory path to add
        """
        if directory not in self.directories:
            self.directories.append(directory)

    def load_templates(self) -> List[PromptTemplate]:
        """
        Load all templates from configured directories.

        Returns:
            List of loaded templates
        """
        self._templates.clear()

        for directory in self.directories:
            if not directory.exists():
                continue

            for file_path in directory.glob("*.md"):
                template = self._load_template_file(file_path)
                if template:
                    self._templates[template.name] = template

        self._loaded = True
        return list(self._templates.values())

    def _load_template_file(self, file_path: Path) -> Optional[PromptTemplate]:
        """
        Load a template from a markdown file.

        The file format is:
        ---
        name: template-name
        description: Template description
        variables: var1, var2
        ---
        Template content here...

        Args:
            file_path: Path to the template file

        Returns:
            PromptTemplate or None if invalid
        """
        try:
            content = file_path.read_text(encoding="utf-8")

            # Parse front matter
            name = file_path.stem  # Default to filename without extension
            description = ""
            variables = None

            # Check for front matter
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    front_matter = parts[1].strip()
                    template_content = parts[2].strip()

                    # Parse front matter
                    for line in front_matter.split("\n"):
                        if ":" in line:
                            key, value = line.split(":", 1)
                            key = key.strip().lower()
                            value = value.strip()

                            if key == "name":
                                name = value
                            elif key == "description":
                                description = value
                            elif key == "variables":
                                variables = [v.strip() for v in value.split(",") if v.strip()]

                    content = template_content

            # Extract variables from content if not specified
            if variables is None:
                var_pattern = r"\{\{\s*(\w+)\s*\}\}"
                found_vars = re.findall(var_pattern, content)
                variables = list(set(found_vars)) if found_vars else None

            return PromptTemplate(
                name=name,
                description=description,
                content=content,
                path=file_path,
                variables=variables,
            )

        except Exception:
            return None

    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """
        Get a template by name.

        Args:
            name: Template name

        Returns:
            PromptTemplate or None if not found
        """
        if not self._loaded:
            self.load_templates()

        return self._templates.get(name)

    def has_template(self, name: str) -> bool:
        """
        Check if a template exists.

        Args:
            name: Template name

        Returns:
            True if template exists
        """
        if not self._loaded:
            self.load_templates()

        return name in self._templates


# Default prompt templates instance
_default_templates: Optional[PromptTemplates] = None


def get_prompt_templates() -> PromptTemplates:
    """
    Get the default prompt templates instance.

    Returns:
        PromptTemplates instance
    """
    global _default_templates

    if _default_templates is None:
        from ..resources import PROMPTS_DIR
        _default_templates = PromptTemplates(directories=[PROMPTS_DIR])
        _default_templates.load_templates()

    return _default_templates


def load_prompt_template(name: str) -> Optional[str]:
    """
    Load a prompt template by name.

    Args:
        name: Template name

    Returns:
        Template content or None if not found
    """
    templates = get_prompt_templates()
    template = templates.get_template(name)
    return template.content if template else None


__all__ = [
    "PromptTemplate",
    "PromptTemplates",
    "get_prompt_templates",
    "load_prompt_template",
]
