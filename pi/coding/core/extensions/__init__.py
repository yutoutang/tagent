"""
Extension system for lifecycle events and custom tools.

Converted from TypeScript core/extensions/index.ts
"""

from .types import (
    Extension,
    ExtensionFactory,
    ExtensionContext,
    ExtensionAPI,
    ToolDefinition,
    LoadExtensionsResult,
)
from .loader import (
    discover_and_load_extensions,
    load_extension_from_factory,
    load_extensions,
    create_extension_runtime,
)
from .runner import ExtensionRunner
from .wrapper import wrap_registered_tool, wrap_registered_tools

__all__ = [
    # Types
    "Extension",
    "ExtensionFactory",
    "ExtensionContext",
    "ExtensionAPI",
    "ToolDefinition",
    "LoadExtensionsResult",
    # Loader
    "discover_and_load_extensions",
    "load_extension_from_factory",
    "load_extensions",
    "create_extension_runtime",
    # Runner
    "ExtensionRunner",
    # Wrapper
    "wrap_registered_tool",
    "wrap_registered_tools",
]
