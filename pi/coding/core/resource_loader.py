"""Resource loader for pi-coding.

Converted from TypeScript core/resource-loader.ts
"""
from typing import Optional, Any, List
from pathlib import Path
from dataclasses import dataclass, field

from .prompt_templates import PromptTemplates, PromptTemplate


@dataclass
class LoadExtensionsResult:
    """Result of loading extensions."""
    extensions: List[Any] = field(default_factory=list)  # Extension instances
    slash_commands: List[dict] = field(default_factory=list)  # Slash command info
    errors: List[str] = field(default_factory=list)  # Error messages


@dataclass
class LoadResourcesResult:
    """Result of loading all resources."""
    extensions: LoadExtensionsResult = field(default_factory=LoadExtensionsResult)
    prompt_templates: List[PromptTemplate] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class ResourceLoader:
    """Loads resources like extensions, skills, themes, etc."""

    def __init__(
        self,
        cwd: Optional[str | Path] = None,
        agent_dir: Optional[str | Path] = None,
        settings_manager: Optional[Any] = None,  # SettingsManager
    ):
        """
        Initialize the resource loader.

        Args:
            cwd: Current working directory
            agent_dir: Agent configuration directory
            settings_manager: Optional settings manager instance
        """
        from ..config import get_agent_dir
        from ..resources import PROMPTS_DIR

        self.cwd = Path(cwd) if cwd else Path.cwd()
        self.agent_dir = Path(agent_dir) if agent_dir else get_agent_dir()
        self.settings_manager = settings_manager
        self.prompts_dir = PROMPTS_DIR

        self._extensions_result = LoadExtensionsResult()
        self._prompt_templates: PromptTemplates = PromptTemplates()
        self._loaded = False

    async def reload(self) -> None:
        """Reload all resources."""
        # Load prompt templates from built-in and user directories
        self._load_prompt_templates()

        # TODO: Implement other resource loading
        # - Load extensions from settings and project-local dirs
        # - Load skills
        # - Load themes

        self._loaded = True

    def _load_prompt_templates(self) -> None:
        """Load prompt templates from configured directories."""
        # Clear existing templates
        self._prompt_templates = PromptTemplates()

        # Add built-in prompts directory
        if self.prompts_dir.exists():
            self._prompt_templates.add_directory(self.prompts_dir)

        # Add user prompts directory
        user_prompts_dir = self.agent_dir / "prompts"
        if user_prompts_dir.exists():
            self._prompt_templates.add_directory(user_prompts_dir)

        # Add project-local prompts directory
        project_prompts_dir = self.cwd / ".pi" / "prompts"
        if project_prompts_dir.exists():
            self._prompt_templates.add_directory(project_prompts_dir)

        # Load all templates
        self._prompt_templates.load_templates()

    def get_extensions(self) -> LoadExtensionsResult:
        """
        Get the loaded extensions result.

        Returns:
            LoadExtensionsResult with extensions, slash commands, and errors
        """
        return self._extensions_result

    def get_prompt_templates(self) -> PromptTemplates:
        """
        Get the loaded prompt templates.

        Returns:
            PromptTemplates instance
        """
        if not self._loaded:
            self._prompt_templates.load_templates()
        return self._prompt_templates

    def get_prompt_template(self, name: str) -> Optional[PromptTemplate]:
        """
        Get a specific prompt template by name.

        Args:
            name: Template name

        Returns:
            PromptTemplate or None if not found
        """
        return self.get_prompt_templates().get_template(name)


class DefaultResourceLoader(ResourceLoader):
    """Default implementation of ResourceLoader."""

    def __init__(self, options: dict[str, Any]):
        """
        Initialize the default resource loader.

        Args:
            options: Dict with keys: cwd, agentDir, settingsManager
        """
        super().__init__(
            cwd=options.get("cwd"),
            agent_dir=options.get("agentDir"),
            settings_manager=options.get("settingsManager"),
        )

    async def reload(self) -> None:
        """Reload all resources from settings."""
        await super().reload()
        # Additional loading logic for default loader
        # TODO: Implement extension loading based on settings


__all__ = [
    "LoadExtensionsResult",
    "LoadResourcesResult",
    "ResourceLoader",
    "DefaultResourceLoader",
]
