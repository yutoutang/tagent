"""
JSON parsing utilities for streaming responses.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional, TypeVar, cast

T = TypeVar("T")


def _parse_partial_json(partial_json: str) -> Any:
    """
    Parse potentially incomplete JSON.
    This is a simplified implementation - for production use,
    consider using a library like partial-json.
    """
    partial_json = partial_json.strip()
    if not partial_json:
        return {}

    # Try standard parsing first
    try:
        return json.loads(partial_json)
    except json.JSONDecodeError:
        pass

    # Handle incomplete objects
    if partial_json.startswith("{"):
        # Count brackets to see if object is complete
        open_braces = partial_json.count("{")
        close_braces = partial_json.count("}")
        if open_braces > close_braces:
            # Add missing closing braces
            partial_json += "}" * (open_braces - close_braces)

        # Handle trailing commas
        partial_json = re.sub(r',\s*}', '}', partial_json)
        partial_json = re.sub(r',\s*]', ']', partial_json)

        # Handle incomplete string values
        # Find strings that are opened but not closed
        partial_json = re.sub(r':\s*"[^"]*$', ': ""', partial_json)
        partial_json = re.sub(r':\s*"[^"]*,', ': "",', partial_json)

        try:
            return json.loads(partial_json)
        except json.JSONDecodeError:
            pass

    # Handle incomplete arrays
    if partial_json.startswith("["):
        open_brackets = partial_json.count("[")
        close_brackets = partial_json.count("]")
        if open_brackets > close_brackets:
            partial_json += "]" * (open_brackets - close_brackets)

        partial_json = re.sub(r',\s*]', ']', partial_json)

        try:
            return json.loads(partial_json)
        except json.JSONDecodeError:
            pass

    # If all parsing fails, return empty object
    return {}


def parse_streaming_json(partial_json: Optional[str]) -> Any:
    """
    Attempts to parse potentially incomplete JSON during streaming.
    Always returns a valid object, even if the JSON is incomplete.

    Args:
        partial_json: The partial JSON string from streaming

    Returns:
        Parsed object or empty object if parsing fails
    """
    if not partial_json or partial_json.strip() == "":
        return {}

    # Try standard parsing first (fastest for complete JSON)
    try:
        return json.loads(partial_json)
    except json.JSONDecodeError:
        # Try partial JSON parsing
        try:
            result = _parse_partial_json(partial_json)
            return result if result is not None else {}
        except Exception:
            # If all parsing fails, return empty object
            return {}
