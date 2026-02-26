"""
Extension system types.

Converted from TypeScript core/extensions/types.ts
"""
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, List, Dict, Union, Protocol, runtime_checkable


@dataclass
class ToolDefinition:
    """Definition of a tool that can be registered by extensions."""
    name: str
    description: str
    parameters: Dict[str, Any]
    execute: Callable[..., Any]
    label: Optional[str] = None


@dataclass
class RegisteredTool:
    """A registered tool with metadata."""
    name: str
    description: str
    parameters: Dict[str, Any]
    execute: Callable[..., Any]
    label: str
    from_extension: Optional[str] = None


@dataclass
class RegisteredCommand:
    """A registered command with metadata."""
    name: str
    description: str
    handler: Callable[..., Any]
    from_extension: Optional[str] = None


@dataclass
class ExtensionFlag:
    """A CLI flag registered by an extension."""
    name: str
    type: str  # "boolean" or "string"
    description: Optional[str] = None


@dataclass
class ExtensionShortcut:
    """A keyboard shortcut registered by an extension."""
    key: str
    description: str
    action: Callable[[], Any]


@dataclass
class ExtensionContext:
    """Context provided to extension factories."""
    cwd: str
    agent_dir: str
    session_manager: Any  # SessionManager
    model_registry: Any  # ModelRegistry
    settings_manager: Any  # SettingsManager


@dataclass
class ExtensionAPI:
    """API available to extensions."""
    # Tool registration
    register_tool: Callable[[ToolDefinition], None]
    unregister_tool: Callable[[str], None]

    # Command registration
    register_command: Callable[[str, str, Callable], None]
    unregister_command: Callable[[str], None]

    # Event subscription
    on: Callable[[str, Callable], Callable[[], None]]

    # Utility functions
    log: Callable[[str], None]
    notify: Callable[[str, str], None]  # message, type


@runtime_checkable
class ExtensionFactory(Protocol):
    """Protocol for extension factory functions."""

    def __call__(
        self,
        context: ExtensionContext,
        api: ExtensionAPI,
    ) -> "Extension":
        """Create an extension instance."""
        ...


@dataclass
class Extension:
    """An extension instance."""
    name: str
    version: str
    description: Optional[str] = None
    tools: List[RegisteredTool] = field(default_factory=list)
    commands: List[RegisteredCommand] = field(default_factory=list)
    flags: List[ExtensionFlag] = field(default_factory=list)
    shortcuts: List[ExtensionShortcut] = field(default_factory=list)
    dispose: Optional[Callable[[], None]] = None


@dataclass
class LoadExtensionsResult:
    """Result from loading extensions."""
    extensions: List[Extension]
    slash_commands: List[Dict[str, Any]]
    errors: List[str]


# Event types
@dataclass
class ExtensionEvent:
    """Base event for extension system."""
    type: str = ""
    extension_name: Optional[str] = None


@dataclass
class ToolCallEvent:
    """Event when a tool is called."""
    type: str = "tool_call"
    tool_name: str = ""
    arguments: Dict[str, Any] = field(default_factory=dict)
    tool_call_id: str = ""
    extension_name: Optional[str] = None


@dataclass
class ToolResultEvent:
    """Event when a tool returns a result."""
    type: str = "tool_result"
    tool_name: str = ""
    result: Any = None
    tool_call_id: str = ""
    is_error: bool = False
    extension_name: Optional[str] = None


# Type aliases
ExtensionHandler = Callable[[ExtensionEvent], Any]
ExtensionErrorListener = Callable[[str, Exception], None]


__all__ = [
    "ToolDefinition",
    "RegisteredTool",
    "RegisteredCommand",
    "ExtensionFlag",
    "ExtensionShortcut",
    "ExtensionContext",
    "ExtensionAPI",
    "ExtensionFactory",
    "Extension",
    "LoadExtensionsResult",
    "ExtensionEvent",
    "ToolCallEvent",
    "ToolResultEvent",
    "ExtensionHandler",
    "ExtensionErrorListener",
]
