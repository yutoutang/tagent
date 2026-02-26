"""
TypeBox Helpers

Helper functions for creating JSON Schema compatible with various providers.
In Python, we use plain dictionaries for JSON Schema instead of TypeBox.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypeVar, Union

T = TypeVar("T")


def string_enum(
    values: List[str],
    description: Optional[str] = None,
    default: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Creates a string enum schema compatible with Google's API and other providers
    that don't support anyOf/const patterns.

    Args:
        values: List of allowed string values
        description: Optional description for the schema
        default: Optional default value

    Returns:
        A JSON Schema dictionary

    Example:
        operation_schema = string_enum(
            ["add", "subtract", "multiply", "divide"],
            description="The operation to perform"
        )
    """
    schema: Dict[str, Any] = {
        "type": "string",
        "enum": values,
    }

    if description:
        schema["description"] = description

    if default:
        schema["default"] = default

    return schema


def object_schema(
    properties: Dict[str, Dict[str, Any]],
    required: Optional[List[str]] = None,
    description: Optional[str] = None,
    additional_properties: bool = False,
) -> Dict[str, Any]:
    """
    Creates an object schema.

    Args:
        properties: Dictionary of property name to property schema
        required: List of required property names
        description: Optional description for the schema
        additional_properties: Whether to allow additional properties

    Returns:
        A JSON Schema dictionary
    """
    schema: Dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": additional_properties,
    }

    if required:
        schema["required"] = required

    if description:
        schema["description"] = description

    return schema


def array_schema(
    items: Dict[str, Any],
    description: Optional[str] = None,
    min_items: Optional[int] = None,
    max_items: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Creates an array schema.

    Args:
        items: Schema for array items
        description: Optional description for the schema
        min_items: Minimum number of items
        max_items: Maximum number of items

    Returns:
        A JSON Schema dictionary
    """
    schema: Dict[str, Any] = {
        "type": "array",
        "items": items,
    }

    if description:
        schema["description"] = description

    if min_items is not None:
        schema["minItems"] = min_items

    if max_items is not None:
        schema["maxItems"] = max_items

    return schema


def string_schema(
    description: Optional[str] = None,
    default: Optional[str] = None,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    pattern: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Creates a string schema.

    Args:
        description: Optional description for the schema
        default: Optional default value
        min_length: Minimum string length
        max_length: Maximum string length
        pattern: Regex pattern for validation

    Returns:
        A JSON Schema dictionary
    """
    schema: Dict[str, Any] = {"type": "string"}

    if description:
        schema["description"] = description

    if default:
        schema["default"] = default

    if min_length is not None:
        schema["minLength"] = min_length

    if max_length is not None:
        schema["maxLength"] = max_length

    if pattern:
        schema["pattern"] = pattern

    return schema


def number_schema(
    description: Optional[str] = None,
    default: Optional[Union[int, float]] = None,
    minimum: Optional[Union[int, float]] = None,
    maximum: Optional[Union[int, float]] = None,
    integer: bool = False,
) -> Dict[str, Any]:
    """
    Creates a number schema.

    Args:
        description: Optional description for the schema
        default: Optional default value
        minimum: Minimum value
        maximum: Maximum value
        integer: Whether the number must be an integer

    Returns:
        A JSON Schema dictionary
    """
    schema: Dict[str, Any] = {"type": "integer" if integer else "number"}

    if description:
        schema["description"] = description

    if default is not None:
        schema["default"] = default

    if minimum is not None:
        schema["minimum"] = minimum

    if maximum is not None:
        schema["maximum"] = maximum

    return schema


def boolean_schema(
    description: Optional[str] = None,
    default: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Creates a boolean schema.

    Args:
        description: Optional description for the schema
        default: Optional default value

    Returns:
        A JSON Schema dictionary
    """
    schema: Dict[str, Any] = {"type": "boolean"}

    if description:
        schema["description"] = description

    if default is not None:
        schema["default"] = default

    return schema


def optional(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mark a schema as optional (for documentation purposes).
    In JSON Schema, optionality is determined by the 'required' array in the parent object.

    Args:
        schema: The schema to mark as optional

    Returns:
        The same schema (this is just for documentation/clarity)
    """
    return schema


def nullable(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Make a schema nullable (allow null values).

    Args:
        schema: The schema to make nullable

    Returns:
        A schema that allows null values
    """
    return {
        "anyOf": [schema, {"type": "null"}],
    }
