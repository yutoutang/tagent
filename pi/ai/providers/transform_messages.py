"""
Message Transformation Utilities

Transform messages for cross-provider compatibility.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional, cast

from ..types import (
    Api,
    AssistantMessage,
    Message,
    Model,
    TextContent,
    ToolCall,
    ToolResultMessage,
)


def transform_messages(
    messages: List[Message],
    model: Model,
    normalize_tool_call_id: Optional[Callable[[str, Model, AssistantMessage], str]] = None,
) -> List[Message]:
    """
    Normalize tool call ID for cross-provider compatibility.
    OpenAI Responses API generates IDs that are 450+ chars with special characters like `|`.
    Anthropic APIs require IDs matching ^[a-zA-Z0-9_-]+$ (max 64 chars).

    Args:
        messages: The messages to transform
        model: The target model
        normalize_tool_call_id: Optional function to normalize tool call IDs

    Returns:
        Transformed messages
    """
    # Build a map of original tool call IDs to normalized IDs
    tool_call_id_map: Dict[str, str] = {}

    # First pass: transform messages (thinking blocks, tool call ID normalization)
    transformed: List[Message] = []

    for msg in messages:
        # User messages pass through unchanged
        if msg.role == "user":
            transformed.append(msg)
            continue

        # Handle toolResult messages - normalize toolCallId if we have a mapping
        if msg.role == "toolResult":
            normalized_id = tool_call_id_map.get(msg.toolCallId)
            if normalized_id and normalized_id != msg.toolCallId:
                # Create a copy with normalized ID
                transformed.append(ToolResultMessage(
                    role="toolResult",
                    toolCallId=normalized_id,
                    toolName=msg.toolName,
                    content=msg.content,
                    details=msg.details,
                    isError=msg.isError,
                    timestamp=msg.timestamp,
                ))
            else:
                transformed.append(msg)
            continue

        # Assistant messages need transformation check
        if msg.role == "assistant":
            assistant_msg = cast(AssistantMessage, msg)
            is_same_model = (
                assistant_msg.provider == model.provider and
                assistant_msg.api == model.api and
                assistant_msg.model == model.id
            )

            transformed_content: List[Any] = []
            for block in assistant_msg.content:
                if block.type == "thinking":
                    # For same model: keep thinking blocks with signatures (needed for replay)
                    # even if the thinking text is empty (OpenAI encrypted reasoning)
                    if is_same_model and block.thinkingSignature:
                        transformed_content.append(block)
                        continue
                    # Skip empty thinking blocks, convert others to plain text
                    if not block.thinking or block.thinking.strip() == "":
                        continue
                    if is_same_model:
                        transformed_content.append(block)
                        continue
                    transformed_content.append(TextContent(
                        type="text",
                        text=block.thinking,
                    ))
                    continue

                if block.type == "text":
                    if is_same_model:
                        transformed_content.append(block)
                        continue
                    transformed_content.append(TextContent(
                        type="text",
                        text=block.text,
                    ))
                    continue

                if block.type == "toolCall":
                    tool_call = cast(ToolCall, block)
                    normalized_tool_call = tool_call

                    if not is_same_model and tool_call.thoughtSignature:
                        # Create copy without thoughtSignature
                        normalized_tool_call = ToolCall(
                            type="toolCall",
                            id=tool_call.id,
                            name=tool_call.name,
                            arguments=tool_call.arguments.copy(),
                        )

                    if not is_same_model and normalize_tool_call_id:
                        normalized_id = normalize_tool_call_id(tool_call.id, model, assistant_msg)
                        if normalized_id != tool_call.id:
                            tool_call_id_map[tool_call.id] = normalized_id
                            normalized_tool_call = ToolCall(
                                type="toolCall",
                                id=normalized_id,
                                name=normalized_tool_call.name,
                                arguments=normalized_tool_call.arguments.copy(),
                                thoughtSignature=normalized_tool_call.thoughtSignature,
                            )

                    transformed_content.append(normalized_tool_call)
                    continue

                transformed_content.append(block)

            transformed.append(AssistantMessage(
                role="assistant",
                content=transformed_content,
                api=assistant_msg.api,
                provider=assistant_msg.provider,
                model=assistant_msg.model,
                usage=assistant_msg.usage,
                stopReason=assistant_msg.stopReason,
                errorMessage=assistant_msg.errorMessage,
                timestamp=assistant_msg.timestamp,
            ))
            continue

        transformed.append(msg)

    # Second pass: insert synthetic empty tool results for orphaned tool calls
    # This preserves thinking signatures and satisfies API requirements
    result: List[Message] = []
    pending_tool_calls: List[ToolCall] = []
    existing_tool_result_ids: set = set()

    for i, msg in enumerate(transformed):
        if msg.role == "assistant":
            # If we have pending orphaned tool calls from a previous assistant, insert synthetic results now
            if pending_tool_calls:
                for tc in pending_tool_calls:
                    if tc.id not in existing_tool_result_ids:
                        result.append(ToolResultMessage(
                            role="toolResult",
                            toolCallId=tc.id,
                            toolName=tc.name,
                            content=[TextContent(type="text", text="No result provided")],
                            isError=True,
                            timestamp=int(time.time() * 1000),
                        ))
                pending_tool_calls = []
                existing_tool_result_ids = set()

            # Skip errored/aborted assistant messages entirely
            assistant_msg = cast(AssistantMessage, msg)
            if assistant_msg.stopReason in ("error", "aborted"):
                continue

            # Track tool calls from this assistant message
            tool_calls = [b for b in assistant_msg.content if b.type == "toolCall"]
            if tool_calls:
                pending_tool_calls = [cast(ToolCall, tc) for tc in tool_calls]
                existing_tool_result_ids = set()

            result.append(msg)

        elif msg.role == "toolResult":
            tool_result = cast(ToolResultMessage, msg)
            existing_tool_result_ids.add(tool_result.toolCallId)
            result.append(msg)

        elif msg.role == "user":
            # User message interrupts tool flow - insert synthetic results for orphaned calls
            if pending_tool_calls:
                for tc in pending_tool_calls:
                    if tc.id not in existing_tool_result_ids:
                        result.append(ToolResultMessage(
                            role="toolResult",
                            toolCallId=tc.id,
                            toolName=tc.name,
                            content=[TextContent(type="text", text="No result provided")],
                            isError=True,
                            timestamp=int(time.time() * 1000),
                        ))
                pending_tool_calls = []
                existing_tool_result_ids = set()
            result.append(msg)

        else:
            result.append(msg)

    return result
