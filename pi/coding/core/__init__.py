"""Core module for pi-coding."""

from .sdk import (
    CreateAgentSessionOptions,
    CreateAgentSessionResult,
    create_agent_session,
)
from .agent_session import AgentSession
from .session_manager import SessionManager
from .settings_manager import SettingsManager, Settings
from .auth_storage import AuthStorage
from .model_registry import ModelRegistry, ModelInfo
from .model_resolver import resolve_model, ModelConfig
from .defaults import get_default_config_dir, get_default_settings, DEFAULT_SYSTEM_PROMPT
from .messages import create_user_message, dicts_to_agent_messages
from .bash_executor import BashExecutor
from .event_bus import EventBus
from .resource_loader import ResourceLoader
from .prompt_templates import PromptTemplates
from .system_prompt import SystemPromptBuilder
from ..tools import get_builtin_tools

__all__ = [
    # SDK
    "CreateAgentSessionOptions",
    "CreateAgentSessionResult",
    "create_agent_session",
    # Agent Session
    "AgentSession",
    # Session Management
    "SessionManager",
    # Settings
    "SettingsManager",
    "Settings",
    # Auth
    "AuthStorage",
    # Models
    "ModelRegistry",
    "ModelInfo",
    "resolve_model",
    "ModelConfig",
    # Defaults
    "get_default_config_dir",
    "get_default_settings",
    "DEFAULT_SYSTEM_PROMPT",
    # Messages
    "create_user_message",
    "dicts_to_agent_messages",
    # Execution
    "BashExecutor",
    # Events
    "EventBus",
    # Resources
    "ResourceLoader",
    # Prompts
    "PromptTemplates",
    "SystemPromptBuilder",
    # Tools
    "get_builtin_tools",
]
