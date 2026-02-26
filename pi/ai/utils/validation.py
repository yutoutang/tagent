"""
Tool validation utilities.
"""

from __future__ import annotations

import copy
import json
from typing import Any, Dict, List, Optional

try:
    import jsonschema
    from jsonschema import validate, ValidationError as JsonSchemaValidationError
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

from ..types import Tool, ToolCall


def validate_tool_call(tools: List[Tool], tool_call: ToolCall) -> Any:
    """
    Finds a tool by name and validates the tool call arguments against its schema.

    Args:
        tools: Array of tool definitions
        toolCall: The tool call from the LLM

    Returns:
        The validated arguments

    Raises:
        ValueError: If tool is not found or validation fails
    """
    tool = next((t for t in tools if t.name == tool_call.name), None)
    if not tool:
        raise ValueError(f'Tool "{tool_call.name}" not found')
    return validate_tool_arguments(tool, tool_call)


def validate_tool_arguments(tool: Tool, tool_call: ToolCall) -> Any:
    """
    Validates tool call arguments against the tool's JSON Schema.

    Args:
        tool: The tool definition with JSON Schema
        toolCall: The tool call from the LLM

    Returns:
        The validated (and potentially coerced) arguments

    Raises:
        ValueError: With formatted message if validation fails
    """
    if not HAS_JSONSCHEMA:
        # Without jsonschema, trust the LLM's output without validation
        return tool_call.arguments

    try:
        # Clone arguments so validation can safely mutate for type coercion
        args = copy.deepcopy(tool_call.arguments)

        # Validate against the schema
        jsonschema.validate(args, tool.parameters)
        return args
    except JsonSchemaValidationError as e:
        # Format validation errors nicely
        path = (
            ".".join(str(p) for p in e.absolute_path)
            if e.absolute_path
            else "root"
        )
        error_msg = f"  - {path}: {e.message}"

        full_error_msg = (
            f'Validation failed for tool "{tool_call.name}":\n{error_msg}\n\n'
            f"Received arguments:\n{json.dumps(tool_call.arguments, indent=2)}"
        )

        raise ValueError(full_error_msg)
