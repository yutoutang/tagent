"""Message utilities for pi-coding.

Converted from TypeScript core/messages.ts
"""
from typing import Any, Union, List
from pi.ai.types import UserMessage, Message
from pi.agent.types import AgentMessage
from pi.agent.message_utils import create_user_message as _create_user_message


def create_user_message(
    text: str,
    timestamp: int | None = None,
) -> UserMessage:
    """
    Create a user message from plain text.

    Args:
        text: The text content
        timestamp: Optional timestamp in milliseconds

    Returns:
        UserMessage dataclass instance
    """
    return _create_user_message(text, timestamp)


def dicts_to_agent_messages(messages: list[dict[str, Any]]) -> list[AgentMessage]:
    """
    Convert a list of dictionaries to AgentMessage instances.

    Args:
        messages: List of message dictionaries

    Returns:
        List of AgentMessage (pi.ai.types dataclass instances)
    """
    from pi.agent.message_utils import dicts_to_agent_messages as _convert
    return _convert(messages)


def convertToLlm(messages: List[AgentMessage]) -> List[Message]:
    """
    Convert AgentMessage list to Message list for LLM consumption.

    Args:
        messages: List of AgentMessage

    Returns:
        List of Message (for LLM)
    """
    from pi.agent.message_utils import default_convert_to_llm
    return default_convert_to_llm(messages)


__all__ = [
    "create_user_message",
    "dicts_to_agent_messages",
    "convertToLlm",
]
