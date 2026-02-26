"""
Google Shared Utilities

Shared utilities for Google providers.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..types import StopReason


def map_stop_reason(reason: str) -> StopReason:
    """Map Google stop reason to our StopReason type."""
    mapping = {
        "STOP": "stop",
        "MAX_TOKENS": "length",
        "SAFETY": "error",
        "RECITATION": "error",
        "BLOCKLIST": "error",
        "PROHIBITED_CONTENT": "error",
        "SPII": "error",
        "MALFORMED_FUNCTION_CALL": "error",
        "IMAGE_SAFETY": "error",
        "FINISH_REASON_UNSPECIFIED": "stop",
    }
    return mapping.get(reason, "stop")


def map_tool_choice(choice: str) -> str:
    """Map tool choice to Google's format."""
    mapping = {
        "auto": "AUTO",
        "none": "NONE",
        "any": "ANY",
    }
    return mapping.get(choice, "AUTO")


def is_thinking_part(part: Dict[str, Any]) -> bool:
    """Check if a part is a thinking part."""
    return part.get("thought") is True or part.get("thoughtSignature") is not None


def retain_thought_signature(
    current: Optional[str],
    new: Optional[str],
) -> Optional[str]:
    """Retain thought signature."""
    if new:
        return new
    return current
