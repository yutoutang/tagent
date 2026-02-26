"""
Extension loader for discovering and loading extensions.

Converted from TypeScript core/extensions/loader.ts
"""
import importlib.util
from pathlib import Path
from typing import Any, Optional, List, Callable

from .types import (
    Extension,
    ExtensionFactory,
    ExtensionContext,
    ExtensionAPI,
    LoadExtensionsResult,
)


class ExtensionRuntime:
    """Runtime for managing extensions."""

    def __init__(self, context: ExtensionContext):
        """
        Initialize the extension runtime.

        Args:
            context: Extension context
        """
        self.context = context
        self.extensions: List[Extension] = []
        self.errors: List[str] = []

    def load_extension(self, extension: Extension) -> None:
        """Load an extension into the runtime."""
        self.extensions.append(extension)

    def get_tools(self) -> List[Any]:
        """Get all tools from loaded extensions."""
        tools = []
        for ext in self.extensions:
            tools.extend(ext.tools)
        return tools

    def get_commands(self) -> List[Any]:
        """Get all commands from loaded extensions."""
        commands = []
        for ext in self.extensions:
            commands.extend(ext.commands)
        return commands


def create_extension_runtime(context: ExtensionContext) -> ExtensionRuntime:
    """
    Create a new extension runtime.

    Args:
        context: Extension context

    Returns:
        New ExtensionRuntime instance
    """
    return ExtensionRuntime(context)


def load_extension_from_factory(
    factory: ExtensionFactory,
    context: ExtensionContext,
    api: ExtensionAPI,
) -> Optional[Extension]:
    """
    Load an extension from a factory function.

    Args:
        factory: Extension factory function
        context: Extension context
        api: Extension API

    Returns:
        Extension instance or None if loading failed
    """
    try:
        extension = factory(context, api)
        return extension
    except Exception as e:
        return None


def discover_and_load_extensions(
    extension_dirs: List[Path],
    context: ExtensionContext,
    api: ExtensionAPI,
) -> LoadExtensionsResult:
    """
    Discover and load extensions from directories.

    Args:
        extension_dirs: Directories to search for extensions
        context: Extension context
        api: Extension API

    Returns:
        LoadExtensionsResult with loaded extensions and any errors
    """
    extensions: List[Extension] = []
    errors: List[str] = []

    for ext_dir in extension_dirs:
        if not ext_dir.exists():
            continue

        for ext_path in ext_dir.iterdir():
            if ext_path.is_file() and ext_path.suffix == ".py":
                try:
                    # Load Python module
                    spec = importlib.util.spec_from_file_location(
                        ext_path.stem,
                        ext_path,
                    )
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)

                        # Look for extension factory
                        if hasattr(module, "create_extension"):
                            factory = module.create_extension
                            ext = load_extension_from_factory(factory, context, api)
                            if ext:
                                extensions.append(ext)

                except Exception as e:
                    errors.append(f"Failed to load {ext_path}: {e}")

    return LoadExtensionsResult(
        extensions=extensions,
        slash_commands=[],
        errors=errors,
    )


def load_extensions(
    sources: List[str],
    context: ExtensionContext,
    api: ExtensionAPI,
) -> LoadExtensionsResult:
    """
    Load extensions from source paths.

    Args:
        sources: List of source paths (files or directories)
        context: Extension context
        api: Extension API

    Returns:
        LoadExtensionsResult with loaded extensions and any errors
    """
    extensions: List[Extension] = []
    errors: List[str] = []

    for source in sources:
        source_path = Path(source)

        if source_path.is_file():
            # Load single file
            ext_dirs = [source_path.parent]
            result = discover_and_load_extensions(ext_dirs, context, api)
            extensions.extend(result.extensions)
            errors.extend(result.errors)
        elif source_path.is_dir():
            # Load from directory
            result = discover_and_load_extensions([source_path], context, api)
            extensions.extend(result.extensions)
            errors.extend(result.errors)

    return LoadExtensionsResult(
        extensions=extensions,
        slash_commands=[],
        errors=errors,
    )


__all__ = [
    "ExtensionRuntime",
    "create_extension_runtime",
    "load_extension_from_factory",
    "discover_and_load_extensions",
    "load_extensions",
]
