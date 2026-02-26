"""
Tool wrapper for extensions.

Converted from TypeScript core/extensions/wrapper.ts
"""
from typing import Any, Callable, Optional

from .types import RegisteredTool, ToolDefinition
from .runner import ExtensionRunner


def wrap_registered_tool(
    tool: RegisteredTool,
    runner: Optional[ExtensionRunner] = None,
) -> RegisteredTool:
    """
    Wrap a registered tool with extension event emission.

    Args:
        tool: The registered tool to wrap
        runner: Optional extension runner for event emission

    Returns:
        Wrapped tool
    """
    if not runner:
        return tool

    original_execute = tool.execute

    async def wrapped_execute(
        tool_call_id: str,
        params: dict,
        signal: Any = None,
        on_update: Any = None,
    ) -> Any:
        # Emit tool call event
        await runner.on_tool_call(tool.name, params, tool_call_id)

        try:
            result = await original_execute(tool_call_id, params, signal, on_update)

            # Emit tool result event
            await runner.on_tool_result(tool.name, result, tool_call_id, is_error=False)

            return result

        except Exception as e:
            # Emit tool result event with error
            await runner.on_tool_result(tool.name, str(e), tool_call_id, is_error=True)
            raise

    # Create a new tool with wrapped execute
    return RegisteredTool(
        name=tool.name,
        description=tool.description,
        parameters=tool.parameters,
        execute=wrapped_execute,
        label=tool.label,
        from_extension=tool.from_extension,
    )


def wrap_registered_tools(
    tools: list[RegisteredTool],
    runner: Optional[ExtensionRunner] = None,
) -> list[RegisteredTool]:
    """
    Wrap multiple registered tools with extension event emission.

    Args:
        tools: List of registered tools to wrap
        runner: Optional extension runner for event emission

    Returns:
        List of wrapped tools
    """
    if not runner:
        return tools

    return [wrap_registered_tool(tool, runner) for tool in tools]


def wrap_tool_with_extensions(
    tool: Any,
    runner: Optional[ExtensionRunner] = None,
) -> Any:
    """
    Wrap any tool object with extension event emission.

    Args:
        tool: Tool object with execute method
        runner: Optional extension runner for event emission

    Returns:
        Wrapped tool
    """
    if not runner:
        return tool

    if not hasattr(tool, "execute"):
        return tool

    original_execute = tool.execute

    async def wrapped_execute(
        tool_call_id: str,
        params: dict,
        signal: Any = None,
        on_update: Any = None,
    ) -> Any:
        tool_name = getattr(tool, "name", "unknown")

        # Emit tool call event
        await runner.on_tool_call(tool_name, params, tool_call_id)

        try:
            result = await original_execute(tool_call_id, params, signal, on_update)

            # Emit tool result event
            await runner.on_tool_result(tool_name, result, tool_call_id, is_error=False)

            return result

        except Exception as e:
            # Emit tool result event with error
            await runner.on_tool_result(tool_name, str(e), tool_call_id, is_error=True)
            raise

    # Replace the execute method
    tool.execute = wrapped_execute
    return tool


def wrap_tools_with_extensions(
    tools: list[Any],
    runner: Optional[ExtensionRunner] = None,
) -> list[Any]:
    """
    Wrap multiple tools with extension event emission.

    Args:
        tools: List of tool objects
        runner: Optional extension runner for event emission

    Returns:
        List of wrapped tools
    """
    if not runner:
        return tools

    return [wrap_tool_with_extensions(tool, runner) for tool in tools]


__all__ = [
    "wrap_registered_tool",
    "wrap_registered_tools",
    "wrap_tool_with_extensions",
    "wrap_tools_with_extensions",
]
