"""
GitHub Copilot Headers

Utilities for building GitHub Copilot dynamic headers.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any, Dict, List, Optional

from ..types import ImageContent, Message, TextContent


def has_copilot_vision_input(messages: List[Message]) -> bool:
    """Check if any message contains image content."""
    for msg in messages:
        if msg.role == "user":
            if isinstance(msg.content, list):
                for item in msg.content:
                    if item.type == "image":
                        return True
    return False


def build_copilot_dynamic_headers(
    messages: List[Message],
    has_images: bool = False,
) -> Dict[str, str]:
    """Build dynamic headers for GitHub Copilot requests."""
    # Calculate content hash for cache optimization
    content_hash = _calculate_content_hash(messages)

    headers = {
        "x-github-client-version": "copilot-cli/1.0.0",
        "x-request-id": _generate_request_id(),
    }

    if content_hash:
        headers["x-content-hash"] = content_hash

    if has_images:
        headers["x-copilot-vision"] = "enabled"

    return headers


def _calculate_content_hash(messages: List[Message]) -> Optional[str]:
    """Calculate a hash of message content for caching."""
    try:
        content_parts = []
        for msg in messages:
            if isinstance(msg.content, str):
                content_parts.append(msg.content)
            elif isinstance(msg.content, list):
                for item in msg.content:
                    if item.type == "text":
                        content_parts.append(item.text)

        if content_parts:
            combined = "\n".join(content_parts)
            return hashlib.sha256(combined.encode()).hexdigest()[:16]
    except Exception:
        pass

    return None


def _generate_request_id() -> str:
    """Generate a unique request ID."""
    import uuid
    return str(uuid.uuid4())
