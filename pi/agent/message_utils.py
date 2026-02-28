"""
Message conversion utilities for agent system.
"""
import dataclasses
from typing import Any, Union

from ..ai.types import (
    UserMessage as AiUserMessage,
    AssistantMessage as AiAssistantMessage,
    ToolResultMessage as AiToolResultMessage,
    TextContent as AiTextContent,
    ThinkingContent as AiThinkingContent,
    ToolCall as AiToolCall,
    ImageContent as AiImageContent,
    Usage as AiUsage,
    UsageCost as AiUsageCost,
)
from .types import AgentMessage


def dicts_to_agent_messages(messages: list[dict[str, Any]]) -> list[AgentMessage]:
    """
    Convert a list of dictionaries to AgentMessage dataclass instances.

    Args:
        messages: List of message dictionaries with role, content, and optional timestamp

    Returns:
        List of AgentMessage (pi.ai.types dataclass instances)

    Example:
        >>> messages = [
        ...     {
        ...         "role": "user",
        ...         "content": [{"type": "text", "text": "计算 1 + 1"}],
        ...         "timestamp": 12345,
        ...     }
        ... ]
        >>> agent_messages = dicts_to_agent_messages(messages)
    """
    import time

    converted = []
    for msg in messages:
        role = msg.get("role")
        if not role:
            raise ValueError(f"Message missing required field 'role': {msg}")

        timestamp = msg.get("timestamp", int(time.time() * 1000))

        if role == "user":
            content = msg.get("content", "")
            # Convert string content or list content
            if isinstance(content, str):
                pass  # Use string directly
            elif isinstance(content, list):
                content = _convert_content_blocks(content)
            else:
                raise ValueError(f"User content must be string or list, got {type(content)}")

            converted.append(AiUserMessage(
                role="user",
                content=content,
                timestamp=timestamp,
            ))

        elif role == "assistant":
            content = msg.get("content", [])
            if isinstance(content, list):
                content = _convert_content_blocks(content)

            # Handle usage
            usage = msg.get("usage")
            if usage:
                usage = _convert_usage(usage) if isinstance(usage, dict) else usage
            else:
                usage = AiUsage()

            converted.append(AiAssistantMessage(
                role="assistant",
                content=content,
                api=msg.get("api", ""),
                provider=msg.get("provider", ""),
                model=msg.get("model", ""),
                usage=usage,
                stopReason=msg.get("stopReason", "stop"),
                errorMessage=msg.get("errorMessage"),
                timestamp=timestamp,
            ))

        elif role == "toolResult":
            content = msg.get("content", [])
            if isinstance(content, list):
                content = _convert_content_blocks(content)

            converted.append(AiToolResultMessage(
                role="toolResult",
                toolCallId=msg.get("toolCallId", ""),
                toolName=msg.get("toolName", ""),
                content=content,
                details=msg.get("details"),
                isError=msg.get("isError", False),
                timestamp=timestamp,
            ))

        else:
            raise ValueError(f"Unknown message role: {role}")

    return converted


def _convert_content_blocks(content: list) -> list:
    """Convert content blocks from dict to dataclass as needed."""
    converted = []
    for item in content:
        if dataclasses.is_dataclass(item):
            converted.append(item)
        elif isinstance(item, dict):
            item_type = item.get("type")
            if item_type == "text":
                converted.append(AiTextContent(
                    type="text",
                    text=item.get("text", ""),
                    textSignature=item.get("textSignature"),
                ))
            elif item_type == "thinking":
                converted.append(AiThinkingContent(
                    type="thinking",
                    thinking=item.get("thinking", ""),
                    thinkingSignature=item.get("thinkingSignature"),
                ))
            elif item_type == "toolCall":
                converted.append(AiToolCall(
                    type="toolCall",
                    id=item.get("id", ""),
                    name=item.get("name", ""),
                    arguments=item.get("arguments", {}),
                    thoughtSignature=item.get("thoughtSignature"),
                ))
            elif item_type == "image":
                converted.append(AiImageContent(
                    type="image",
                    data=item.get("data", ""),
                    mimeType=item.get("mimeType", "image/png"),
                ))
            else:
                converted.append(item)
        else:
            converted.append(item)
    return converted


def _convert_usage(usage: dict) -> AiUsage:
    """Convert usage dict to Usage dataclass."""
    cost_dict = usage.get("cost", {})
    cost = AiUsageCost(
        input=cost_dict.get("input", 0.0),
        output=cost_dict.get("output", 0.0),
        cacheRead=cost_dict.get("cacheRead", 0.0),
        cacheWrite=cost_dict.get("cacheWrite", 0.0),
        total=cost_dict.get("total", 0.0),
    )

    return AiUsage(
        input=usage.get("input", 0),
        output=usage.get("output", 0),
        cacheRead=usage.get("cacheRead", 0),
        cacheWrite=usage.get("cacheWrite", 0),
        totalTokens=usage.get("totalTokens", 0),
        cost=cost,
    )


def create_user_message(text: str, timestamp: int | None = None) -> AiUserMessage:
    """
    Create a user message dataclass from plain text.

    Args:
        text: The text content
        timestamp: Optional timestamp in milliseconds

    Returns:
        UserMessage dataclass instance
    """
    import time

    return AiUserMessage(
        role="user",
        content=text,
        timestamp=timestamp or int(time.time() * 1000),
    )


def create_user_message_from_content(
    content: list[dict[str, Any] | Any],
    timestamp: int | None = None,
) -> AiUserMessage:
    """
    Create a user message dataclass from content blocks.

    Args:
        content: List of content blocks (dicts or dataclasses)
        timestamp: Optional timestamp in milliseconds

    Returns:
        UserMessage dataclass instance
    """
    import time

    converted_content = _convert_content_blocks(content)

    return AiUserMessage(
        role="user",
        content=converted_content,
        timestamp=timestamp or int(time.time() * 1000),
    )


def default_convert_to_llm(messages: list[AgentMessage]) -> list:
    """
    Convert AgentMessage list to Message list for LLM consumption.

    Handles:
    - Dataclass objects (pi.ai.types.Message) - pass through
    - Dict objects - convert to dataclass
    - Mixed content blocks (dict vs dataclass)
    """
    from ..ai.types import Message

    result = []
    for msg in messages:
        # If it's already a pi.ai.types message (dataclass), use it directly
        if dataclasses.is_dataclass(msg) and isinstance(msg, Message):
            result.append(msg)
        # For dict input, convert to dataclass
        elif isinstance(msg, dict):
            converted = dicts_to_agent_messages([msg])
            if converted:
                result.append(converted[0])
        else:
            raise TypeError(f"Unsupported message type: {type(msg)}")

    return result


# Re-export for convenience
__all__ = [
    "dicts_to_agent_messages",
    "create_user_message",
    "create_user_message_from_content",
    "default_convert_to_llm",
    "get_msg_attr"
]
