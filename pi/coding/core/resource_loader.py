"""Resource loader for pi-coding.

Converted from TypeScript core/resource-loader.ts
"""
from typing import Optional, Any
from pathlib import Path
from dataclasses import dataclass


@dataclass
class LoadExtensionsResult:
    """Result of loading extensions."""
    extensions: list[Any]  # Extension instances
    slash_commands: list[dict]  # Slash command info
    errors: list[str]  # Error messages


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

        self.cwd = Path(cwd) if cwd else Path.cwd()
        self.agent_dir = Path(agent_dir) if agent_dir else get_agent_dir()
        self.settings_manager = settings_manager

        self._extensions_result = LoadExtensionsResult(
            extensions=[],
            slash_commands=[],
            errors=[],
        )

    async def reload(self) -> None:
        """Reload all resources."""
        # TODO: Implement resource loading
        # - Load extensions from settings and project-local dirs
        # - Load skills
        # - Load themes
        # - Load prompt templates
        pass

    def get_extensions(self) -> LoadExtensionsResult:
        """
        Get the loaded extensions result.

        Returns:
            LoadExtensionsResult with extensions, slash commands, and errors
        """
        return self._extensions_result


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
        # TODO: Implement actual loading logic


__all__ = [
    "LoadExtensionsResult",
    "ResourceLoader",
    "DefaultResourceLoader",
]
