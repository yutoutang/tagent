"""
Pi Coding - AI-powered coding CLI tool.

Converted from TypeScript @mariozechner/pi-coding-agent package.
"""

__version__ = "0.1.0"

# Core API
from .core.sdk import (
    CreateAgentSessionOptions,
    CreateAgentSessionResult,
    create_agent_session,
)
from .core.agent_session import AgentSession
from .core.session_manager import SessionManager
from .core.settings_manager import SettingsManager
from .core.auth_storage import AuthStorage
from .core.model_registry import ModelRegistry, ModelInfo

# Tools
from .tools import (
    ReadTool,
    WriteTool,
    BashTool,
    EditTool,
    GrepTool,
    FindTool,
    LsTool,
    get_builtin_tools,
)

__all__ = [
    # Version
    "__version__",
    # Core API
    "CreateAgentSessionOptions",
    "CreateAgentSessionResult",
    "create_agent_session",
    "AgentSession",
    "SessionManager",
    "SettingsManager",
    "AuthStorage",
    "ModelRegistry",
    "ModelInfo",
    # Tools
    "ReadTool",
    "WriteTool",
    "BashTool",
    "EditTool",
    "GrepTool",
    "FindTool",
    "LsTool",
    "get_builtin_tools",
]
