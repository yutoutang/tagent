"""
Anthropic API Provider

Stream completions from Anthropic's Claude models.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Literal, Optional, Union, cast

from ..env_api_keys import get_env_api_key
from ..models import calculate_cost
from ..types import (
    Api,
    AssistantMessage,
    CacheRetention,
    Context,
    ImageContent,
    Message,
    Model,
    SimpleStreamOptions,
    StopReason,
    StreamFunction,
    StreamOptions,
    TextContent,
    ThinkingContent,
    Tool,
    ToolCall,
    ToolResultMessage,
    Usage,
    UsageCost,
)
from ..utils.event_stream import AssistantMessageEventStream
from ..utils.json_parse import parse_streaming_json
from ..utils.sanitize_unicode import sanitize_surrogates
from .simple_options import adjust_max_tokens_for_thinking, build_base_options, clamp_reasoning
from .transform_messages import transform_messages

# Claude Code tool names for stealth mode
CLAUDE_CODE_TOOLS = [
    "Read", "Write", "Edit", "Bash", "Grep", "Glob",
    "AskUserQuestion", "EnterPlanMode", "ExitPlanMode", "KillShell",
    "NotebookEdit", "Skill", "Task", "TaskOutput", "TodoWrite",
    "WebFetch", "WebSearch",
]

CC_TOOL_LOOKUP = {t.lower(): t for t in CLAUDE_CODE_TOOLS}


def to_claude_code_name(name: str) -> str:
    """Convert tool name to Claude Code canonical casing."""
    return CC_TOOL_LOOKUP.get(name.lower(), name)


def from_claude_code_name(name: str, tools: Optional[List[Tool]] = None) -> str:
    """Convert Claude Code name back to original tool name."""
    if tools:
        lower_name = name.lower()
        for tool in tools:
            if tool.name.lower() == lower_name:
                return tool.name
    return name


AnthropicEffort = Literal["low", "medium", "high", "max"]


@dataclass
class AnthropicOptions(StreamOptions):
    """Anthropic-specific streaming options."""
    thinkingEnabled: Optional[bool] = None
    thinkingBudgetTokens: Optional[int] = None
    effort: Optional[AnthropicEffort] = None
    interleavedThinking: Optional[bool] = None
    toolChoice: Optional[Union[Literal["auto", "any", "none"], Dict[str, str]]] = None


def resolve_cache_retention(cache_retention: Optional[CacheRetention] = None) -> CacheRetention:
    """Resolve cache retention preference."""
    import os
    if cache_retention:
        return cache_retention
    if os.environ.get("PI_CACHE_RETENTION") == "long":
        return "long"
    return "short"


def get_cache_control(
    base_url: str,
    cache_retention: Optional[CacheRetention] = None,
) -> Dict[str, Any]:
    """Get cache control settings for Anthropic API."""
    retention = resolve_cache_retention(cache_retention)
    if retention == "none":
        return {"retention": retention}
    ttl = "1h" if retention == "long" and "api.anthropic.com" in base_url else None
    return {
        "retention": retention,
        "cacheControl": {"type": "ephemeral", **({"ttl": ttl} if ttl else {})},
    }


def normalize_tool_call_id(id: str) -> str:
    """Normalize tool call ID to match Anthropic's required pattern."""
    import re
    return re.sub(r'[^a-zA-Z0-9_-]', '_', id)[:64]


def is_oauth_token(api_key: str) -> bool:
    """Check if the API key is an OAuth token."""
    return "sk-ant-oat" in api_key


def supports_adaptive_thinking(model_id: str) -> bool:
    """Check if a model supports adaptive thinking (Opus 4.6+)."""
    return "opus-4-6" in model_id or "opus-4.6" in model_id


def map_thinking_level_to_effort(level: Optional[str]) -> AnthropicEffort:
    """Map ThinkingLevel to Anthropic effort levels."""
    mapping = {
        "minimal": "low",
        "low": "low",
        "medium": "medium",
        "high": "high",
        "xhigh": "max",
    }
    return mapping.get(level or "high", "high")


def map_stop_reason(reason: str) -> StopReason:
    """Map Anthropic stop reason to our StopReason type."""
    mapping = {
        "end_turn": "stop",
        "max_tokens": "length",
        "tool_use": "toolUse",
        "refusal": "error",
        "pause_turn": "stop",
        "stop_sequence": "stop",
        "sensitive": "error",
    }
    if reason in mapping:
        return mapping[reason]
    raise ValueError(f"Unhandled stop reason: {reason}")


def convert_content_blocks(
    content: List[Union[TextContent, ImageContent]]
) -> Union[str, List[Dict[str, Any]]]:
    """Convert content blocks to Anthropic API format."""
    has_images = any(c.type == "image" for c in content)
    if not has_images:
        return sanitize_surrogates("".join(c.text for c in content if c.type == "text"))

    blocks = []
    for block in content:
        if block.type == "text":
            blocks.append({
                "type": "text",
                "text": sanitize_surrogates(block.text),
            })
        else:
            blocks.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": block.mimeType,
                    "data": block.data,
                },
            })

    # If only images, add placeholder text
    if not any(b["type"] == "text" for b in blocks):
        blocks.insert(0, {"type": "text", "text": "(see attached image)"})

    return blocks


def stream_anthropic(
    model: Model,
    context: Context,
    options: Optional[AnthropicOptions] = None,
) -> AssistantMessageEventStream:
    """
    Stream completions from Anthropic's Claude models.

    This is a Python implementation that requires the anthropic library.
    """
    stream = AssistantMessageEventStream()

    async def _stream():
        output = AssistantMessage(
            role="assistant",
            content=[],
            api=model.api,
            provider=model.provider,
            model=model.id,
            usage=Usage(
                input=0,
                output=0,
                cacheRead=0,
                cacheWrite=0,
                totalTokens=0,
                cost=UsageCost(),
            ),
            stopReason="stop",
            timestamp=int(time.time() * 1000),
        )

        try:
            # Import anthropic here to allow module to load without it
            import anthropic

            api_key = options.get("apiKey") if options else None
            api_key = api_key or get_env_api_key(model.provider) or ""

            # Create client
            client = anthropic.Anthropic(
                api_key=api_key,
                base_url=model.baseUrl,
            )

            # Build params
            params = _build_params(model, context, is_oauth_token(api_key), options)
            if options and options.get("onPayload"):
                options["onPayload"](params)

            stream.push({"type": "start", "partial": output})

            # Stream response
            with client.messages.stream(**params) as anthropic_stream:
                for event in anthropic_stream:
                    if event.type == "message_start":
                        usage = event.message.usage
                        output.usage.input = usage.input_tokens or 0
                        output.usage.output = usage.output_tokens or 0
                        output.usage.cacheRead = usage.cache_read_input_tokens or 0
                        output.usage.cacheWrite = usage.cache_creation_input_tokens or 0
                        output.usage.totalTokens = (
                            output.usage.input +
                            output.usage.output +
                            output.usage.cacheRead +
                            output.usage.cacheWrite
                        )
                        calculate_cost(model, output.usage)

                    elif event.type == "content_block_start":
                        index = event.index
                        block = event.content_block
                        if block.type == "text":
                            new_block = TextContent(type="text", text="")
                            output.content.append(new_block)
                            stream.push({
                                "type": "text_start",
                                "contentIndex": len(output.content) - 1,
                                "partial": output,
                            })
                        elif block.type == "thinking":
                            new_block = ThinkingContent(type="thinking", thinking="")
                            output.content.append(new_block)
                            stream.push({
                                "type": "thinking_start",
                                "contentIndex": len(output.content) - 1,
                                "partial": output,
                            })
                        elif block.type == "tool_use":
                            new_block = ToolCall(
                                type="toolCall",
                                id=block.id,
                                name=block.name,
                                arguments=block.input or {},
                            )
                            output.content.append(new_block)
                            stream.push({
                                "type": "toolcall_start",
                                "contentIndex": len(output.content) - 1,
                                "partial": output,
                            })

                    elif event.type == "content_block_delta":
                        index = event.index
                        delta = event.delta
                        if delta.type == "text_delta":
                            if index < len(output.content):
                                block = output.content[index]
                                if block.type == "text":
                                    block.text += delta.text
                                    stream.push({
                                        "type": "text_delta",
                                        "contentIndex": index,
                                        "delta": delta.text,
                                        "partial": output,
                                    })
                        elif delta.type == "thinking_delta":
                            if index < len(output.content):
                                block = output.content[index]
                                if block.type == "thinking":
                                    block.thinking += delta.thinking
                                    stream.push({
                                        "type": "thinking_delta",
                                        "contentIndex": index,
                                        "delta": delta.thinking,
                                        "partial": output,
                                    })
                        elif delta.type == "input_json_delta":
                            if index < len(output.content):
                                block = output.content[index]
                                if block.type == "toolCall":
                                    block.arguments = parse_streaming_json(delta.partial_json)

                    elif event.type == "message_delta":
                        if event.delta.stop_reason:
                            output.stopReason = map_stop_reason(event.delta.stop_reason)
                        if event.usage:
                            if event.usage.input_tokens is not None:
                                output.usage.input = event.usage.input_tokens
                            if event.usage.output_tokens is not None:
                                output.usage.output = event.usage.output_tokens
                            if event.usage.cache_read_input_tokens is not None:
                                output.usage.cacheRead = event.usage.cache_read_input_tokens
                            if event.usage.cache_creation_input_tokens is not None:
                                output.usage.cacheWrite = event.usage.cache_creation_input_tokens
                            output.usage.totalTokens = (
                                output.usage.input +
                                output.usage.output +
                                output.usage.cacheRead +
                                output.usage.cacheWrite
                            )
                            calculate_cost(model, output.usage)

            stream.push({"type": "done", "reason": output.stopReason, "message": output})
            stream.end()

        except Exception as error:
            output.stopReason = "error"
            output.errorMessage = str(error)
            stream.push({"type": "error", "reason": output.stopReason, "error": output})
            stream.end()

    # Run the async function
    asyncio.create_task(_stream())
    return stream


def _build_params(
    model: Model,
    context: Context,
    is_oauth_token: bool,
    options: Optional[AnthropicOptions] = None,
) -> Dict[str, Any]:
    """Build parameters for Anthropic API call."""
    cache_control = get_cache_control(
        model.baseUrl,
        options.get("cacheRetention") if options else None
    ).get("cacheControl")

    params = {
        "model": model.id,
        "messages": _convert_messages(context.messages, model, is_oauth_token, cache_control),
        "max_tokens": (options.get("maxTokens") if options else None) or model.maxTokens // 3,
    }

    if is_oauth_token:
        params["system"] = [{"type": "text", "text": "You are Claude Code, Anthropic's official CLI for Claude."}]
        if context.systemPrompt:
            params["system"].append({
                "type": "text",
                "text": sanitize_surrogates(context.systemPrompt),
            })
    elif context.systemPrompt:
        params["system"] = [{
            "type": "text",
            "text": sanitize_surrogates(context.systemPrompt),
        }]

    if options and options.get("temperature") is not None:
        params["temperature"] = options["temperature"]

    if context.tools:
        params["tools"] = _convert_tools(context.tools, is_oauth_token)

    if options and options.get("thinkingEnabled") and model.reasoning:
        if supports_adaptive_thinking(model.id):
            params["thinking"] = {"type": "adaptive"}
            if options.get("effort"):
                params["output_config"] = {"effort": options["effort"]}
        else:
            params["thinking"] = {
                "type": "enabled",
                "budget_tokens": options.get("thinkingBudgetTokens") or 1024,
            }

    return params


def _convert_messages(
    messages: List[Message],
    model: Model,
    is_oauth_token: bool,
    cache_control: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Convert messages to Anthropic API format."""
    transformed = transform_messages(messages, model, normalize_tool_call_id)
    params = []

    for msg in transformed:
        if msg.role == "user":
            if isinstance(msg.content, str):
                if msg.content.strip():
                    params.append({"role": "user", "content": sanitize_surrogates(msg.content)})
            else:
                blocks = []
                for item in msg.content:
                    if item.type == "text":
                        blocks.append({"type": "text", "text": sanitize_surrogates(item.text)})
                    elif item.type == "image" and "image" in model.input:
                        blocks.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": item.mimeType,
                                "data": item.data,
                            },
                        })
                if blocks:
                    params.append({"role": "user", "content": blocks})

        elif msg.role == "assistant":
            blocks = []
            for block in msg.content:
                if block.type == "text" and block.text.strip():
                    blocks.append({"type": "text", "text": sanitize_surrogates(block.text)})
                elif block.type == "thinking" and block.thinking.strip():
                    if block.thinkingSignature:
                        blocks.append({
                            "type": "thinking",
                            "thinking": sanitize_surrogates(block.thinking),
                            "signature": block.thinkingSignature,
                        })
                    else:
                        blocks.append({"type": "text", "text": sanitize_surrogates(block.thinking)})
                elif block.type == "toolCall":
                    blocks.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": to_claude_code_name(block.name) if is_oauth_token else block.name,
                        "input": block.arguments or {},
                    })
            if blocks:
                params.append({"role": "assistant", "content": blocks})

        elif msg.role == "toolResult":
            params.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": msg.toolCallId,
                    "content": convert_content_blocks(msg.content),
                    "is_error": msg.isError,
                }],
            })

    return params


def _convert_tools(tools: List[Tool], is_oauth_token: bool) -> List[Dict[str, Any]]:
    """Convert tools to Anthropic API format."""
    return [
        {
            "name": to_claude_code_name(tool.name) if is_oauth_token else tool.name,
            "description": tool.description,
            "input_schema": {
                "type": "object",
                "properties": tool.parameters.get("properties", {}),
                "required": tool.parameters.get("required", []),
            },
        }
        for tool in tools
    ]


def stream_simple_anthropic(
    model: Model,
    context: Context,
    options: Optional[SimpleStreamOptions] = None,
) -> AssistantMessageEventStream:
    """Stream with simplified options."""
    api_key = (options.get("apiKey") if options else None) or get_env_api_key(model.provider)
    if not api_key:
        raise ValueError(f"No API key for provider: {model.provider}")

    base = build_base_options(model, options, api_key)
    if not options or not options.get("reasoning"):
        return stream_anthropic(model, context, {**base, "thinkingEnabled": False})

    if supports_adaptive_thinking(model.id):
        effort = map_thinking_level_to_effort(options.get("reasoning"))
        return stream_anthropic(model, context, {**base, "thinkingEnabled": True, "effort": effort})

    adjusted = adjust_max_tokens_for_thinking(
        base.get("maxTokens") or 0,
        model.maxTokens,
        options.get("reasoning"),
        options.get("thinkingBudgets") if options else None,
    )

    return stream_anthropic(model, context, {
        **base,
        "maxTokens": adjusted["maxTokens"],
        "thinkingEnabled": True,
        "thinkingBudgetTokens": adjusted["thinkingBudget"],
    })
