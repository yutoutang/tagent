"""
Settings manager for pi-coding.

Converted from TypeScript core/settings-manager.ts
"""
import json
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field

from ..config import get_settings_path
from pi.agent.types import ThinkingLevel


@dataclass
class RetrySettings:
    """Retry settings."""
    max_delay_ms: int = 30000


@dataclass
class ThinkingBudgets:
    """Thinking budgets for token-based providers."""
    minimal: int = 1000
    low: int = 5000
    medium: int = 10000
    high: int = 20000
    xhigh: int = 60000


@dataclass
class Settings:
    """User settings."""
    # Model settings todo 这里的 provider 不一定正确
    default_provider: str = "zai"
    default_model: str = "glm-5"
    default_thinking_level: ThinkingLevel = "medium"

    # Behavior settings
    steering_mode: str = "one-at-a-time"
    follow_up_mode: str = "one-at-a-time"
    transport: str = "sse"

    # Retry settings
    retry_settings: RetrySettings = field(default_factory=RetrySettings)

    # Thinking budgets
    thinking_budgets: ThinkingBudgets = field(default_factory=ThinkingBudgets)

    # Feature flags
    block_images: bool = False
    quiet_startup: bool = True
    auto_compaction: bool = True
    auto_compaction_threshold: int = 10
    max_history_entries: int = 100

    # UI settings
    theme: str = "default"

    # Extensions
    enabled_extensions: list[str] = field(default_factory=list)
    enabled_skills: list[str] = field(default_factory=list)
    enabled_prompt_templates: list[str] = field(default_factory=list)
    enabled_themes: list[str] = field(default_factory=list)


class SettingsManager:
    """
    Manages user settings.

    Loads settings from ~/.pi/agent/settings.json with support for
    project-local overrides.
    """

    def __init__(
        self,
        cwd: Optional[str | Path] = None,
        agent_dir: Optional[str | Path] = None,
    ):
        """
        Initialize the settings manager.

        Args:
            cwd: Current working directory (for project-local settings)
            agent_dir: Agent configuration directory
        """
        self.cwd = Path(cwd) if cwd else Path.cwd()
        self.agent_dir = Path(agent_dir) if agent_dir else get_settings_path().parent

        # Settings paths
        self.global_settings_path = get_settings_path()
        self.local_settings_path = self.cwd / ".pi" / "settings.json"

        # Load settings
        self._settings = self._load_settings()

    def _load_settings(self) -> Settings:
        """Load settings from files."""
        settings = Settings()  # Start with defaults

        # Load global settings
        if self.global_settings_path.exists():
            try:
                with open(self.global_settings_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._apply_settings(settings, data)
            except (json.JSONDecodeError, IOError):
                pass

        # Load local (project) settings
        if self.local_settings_path.exists():
            try:
                with open(self.local_settings_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._apply_settings(settings, data)
            except (json.JSONDecodeError, IOError):
                pass

        return settings

    def _apply_settings(self, settings: Settings, data: dict[str, Any]) -> None:
        """Apply settings from dict to Settings object."""
        for key, value in data.items():
            if hasattr(settings, key):
                # Handle nested objects
                if key == "retry_settings" and isinstance(value, dict):
                    settings.retry_settings = RetrySettings(**value)
                elif key == "thinking_budgets" and isinstance(value, dict):
                    settings.thinking_budgets = ThinkingBudgets(**value)
                else:
                    setattr(settings, key, value)

    def _save_global_settings(self) -> None:
        """Save global settings to file."""
        self.global_settings_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "defaultProvider": self._settings.default_provider,
            "defaultModel": self._settings.default_model,
            "defaultThinkingLevel": self._settings.default_thinking_level,
            "steeringMode": self._settings.steering_mode,
            "followUpMode": self._settings.follow_up_mode,
            "transport": self._settings.transport,
            "retrySettings": {
                "maxDelayMs": self._settings.retry_settings.max_delay_ms,
            },
            "thinkingBudgets": {
                "minimal": self._settings.thinking_budgets.minimal,
                "low": self._settings.thinking_budgets.low,
                "medium": self._settings.thinking_budgets.medium,
                "high": self._settings.thinking_budgets.high,
                "xhigh": self._settings.thinking_budgets.xhigh,
            },
            "blockImages": self._settings.block_images,
            "quietStartup": self._settings.quiet_startup,
            "autoCompaction": self._settings.auto_compaction,
            "autoCompactionThreshold": self._settings.auto_compaction_threshold,
            "maxHistoryEntries": self._settings.max_history_entries,
            "theme": self._settings.theme,
            "enabledExtensions": self._settings.enabled_extensions,
            "enabledSkills": self._settings.enabled_skills,
            "enabledPromptTemplates": self._settings.enabled_prompt_templates,
            "enabledThemes": self._settings.enabled_themes,
        }

        with open(self.global_settings_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    # Getters

    def get_default_provider(self) -> str:
        """Get the default provider."""
        return self._settings.default_provider

    def get_default_model(self) -> str:
        """Get the default model ID."""
        return self._settings.default_model

    def get_default_thinking_level(self) -> ThinkingLevel:
        """Get the default thinking level."""
        return self._settings.default_thinking_level

    def get_steering_mode(self) -> str:
        """Get the steering mode."""
        return self._settings.steering_mode

    def get_follow_up_mode(self) -> str:
        """Get the follow-up mode."""
        return self._settings.follow_up_mode

    def get_transport(self) -> str:
        """Get the transport mode."""
        return self._settings.transport

    def get_retry_settings(self) -> RetrySettings:
        """Get the retry settings."""
        return self._settings.retry_settings

    def get_thinking_budgets(self) -> ThinkingBudgets:
        """Get the thinking budgets."""
        return self._settings.thinking_budgets

    def get_block_images(self) -> bool:
        """Get the block images setting."""
        return self._settings.block_images

    def get_quiet_startup(self) -> bool:
        """Get the quiet startup setting."""
        return self._settings.quiet_startup

    def get_auto_compaction(self) -> bool:
        """Get the auto compaction setting."""
        return self._settings.auto_compaction

    def get_auto_compaction_threshold(self) -> int:
        """Get the auto compaction threshold."""
        return self._settings.auto_compaction_threshold

    def get_max_history_entries(self) -> int:
        """Get the max history entries setting."""
        return self._settings.max_history_entries

    def get_theme(self) -> str:
        """Get the theme setting."""
        return self._settings.theme

    # Setters

    def set_default_provider(self, provider: str) -> None:
        """Set the default provider."""
        self._settings.default_provider = provider
        self._save_global_settings()

    def set_default_model(self, model: str) -> None:
        """Set the default model ID."""
        self._settings.default_model = model
        self._save_global_settings()

    def set_default_thinking_level(self, level: ThinkingLevel) -> None:
        """Set the default thinking level."""
        self._settings.default_thinking_level = level
        self._save_global_settings()

    @staticmethod
    def create(
        cwd: Optional[str | Path] = None,
        agent_dir: Optional[str | Path] = None,
    ) -> "SettingsManager":
        """
        Create a SettingsManager instance.

        Args:
            cwd: Current working directory
            agent_dir: Agent configuration directory

        Returns:
            New SettingsManager instance
        """
        return SettingsManager(cwd, agent_dir)


__all__ = [
    "RetrySettings",
    "ThinkingBudgets",
    "Settings",
    "SettingsManager",
]
