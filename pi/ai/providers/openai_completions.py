"""
OpenAI Completions API Provider

Stream completions from OpenAI and compatible APIs.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Union, cast

from ..env_api_keys import get_env_api_key
from ..models import calculate_cost, supports_xhigh
from ..types import (
    AssistantMessage,
    Context,
    Message,
    Model,
    OpenAICompletionsCompat,
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
from .simple_options import build_base_options, clamp_reasoning
from .transform_messages import transform_messages


@dataclass
class OpenAICompletionsOptions(StreamOptions):
    """OpenAI Completions-specific streaming options."""
    toolChoice: Optional[Union[Literal["auto", "none", "required"], Dict[str, str]]] = None
    reasoningEffort: Optional[Literal["minimal", "low", "medium", "high", "xhigh"]] = None


def normalize_mistral_tool_id(id: str) -> str:
    """Normalize tool call ID for Mistral (exactly 9 alphanumeric chars)."""
    normalized = re.sub(r'[^a-zA-Z0-9]', '', id)
    if len(normalized) < 9:
        normalized += 'ABCDEFGHI'[:9 - len(normalized)]
    return normalized[:9]


def has_tool_history(messages: List[Message]) -> bool:
    """Check if conversation messages contain tool calls or tool results."""
    for msg in messages:
        if msg.role == "toolResult":
            return True
        if msg.role == "assistant":
            if any(block.type == "toolCall" for block in msg.content):
                return True
    return False


def map_stop_reason(reason: Optional[str]) -> StopReason:
    """Map OpenAI stop reason to our StopReason type."""
    if reason is None:
        return "stop"
    mapping = {
        "stop": "stop",
        "length": "length",
        "function_call": "toolUse",
        "tool_calls": "toolUse",
        "content_filter": "error",
    }
    if reason in mapping:
        return mapping[reason]
    raise ValueError(f"Unhandled stop reason: {reason}")


def detect_compat(model: Model) -> Dict[str, Any]:
    """Detect compatibility settings from provider and baseUrl."""
    provider = model.provider
    base_url = model.baseUrl

    is_zai = provider == "zai" or "api.z.ai" in base_url
    is_non_standard = (
            provider == "cerebras" or "cerebras.ai" in base_url or
            provider == "xai" or "api.x.ai" in base_url or
            provider == "mistral" or "mistral.ai" in base_url or
            "chutes.ai" in base_url or
            "deepseek.com" in base_url or
            is_zai or
            provider == "opencode" or
            "opencode.ai" in base_url
    )
    use_max_tokens = provider == "mistral" or "mistral.ai" in base_url or "chutes.ai" in base_url
    is_grok = provider == "xai" or "api.x.ai" in base_url
    is_mistral = provider == "mistral" or "mistral.ai" in base_url

    return {
        "supportsStore": not is_non_standard,
        "supportsDeveloperRole": not is_non_standard,
        "supportsReasoningEffort": not is_grok and not is_zai,
        "supportsUsageInStreaming": True,
        "maxTokensField": "max_tokens" if use_max_tokens else "max_completion_tokens",
        "requiresToolResultName": is_mistral,
        "requiresAssistantAfterToolResult": False,
        "requiresThinkingAsText": is_mistral,
        "requiresMistralToolIds": is_mistral,
        "thinkingFormat": "zai" if is_zai else "openai",
        "supportsStrictMode": not is_non_standard,
    }


def get_compat(model: Model) -> Dict[str, Any]:
    """Get resolved compatibility settings for a model."""
    detected = detect_compat(model)
    if not model.compat:
        return detected

    compat = model.compat
    return {
        "supportsStore": compat.get("supportsStore", detected["supportsStore"]),
        "supportsDeveloperRole": compat.get("supportsDeveloperRole", detected["supportsDeveloperRole"]),
        "supportsReasoningEffort": compat.get("supportsReasoningEffort", detected["supportsReasoningEffort"]),
        "supportsUsageInStreaming": compat.get("supportsUsageInStreaming", detected["supportsUsageInStreaming"]),
        "maxTokensField": compat.get("maxTokensField", detected["maxTokensField"]),
        "requiresToolResultName": compat.get("requiresToolResultName", detected["requiresToolResultName"]),
        "requiresAssistantAfterToolResult": compat.get("requiresAssistantAfterToolResult",
                                                       detected["requiresAssistantAfterToolResult"]),
        "requiresThinkingAsText": compat.get("requiresThinkingAsText", detected["requiresThinkingAsText"]),
        "requiresMistralToolIds": compat.get("requiresMistralToolIds", detected["requiresMistralToolIds"]),
        "thinkingFormat": compat.get("thinkingFormat", detected["thinkingFormat"]),
        "supportsStrictMode": compat.get("supportsStrictMode", detected["supportsStrictMode"]),
    }


def convert_tools(tools: List[Tool], compat: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert tools to OpenAI API format."""
    result = []
    for tool in tools:
        tool_def = {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }
        if compat.get("supportsStrictMode", True):
            tool_def["function"]["strict"] = False
        result.append(tool_def)
    return result


def convert_messages(
        model: Model,
        context: Context,
        compat: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Convert messages to OpenAI API format."""
    params = []

    def normalize_tool_call_id(id: str) -> str:
        if compat.get("requiresMistralToolIds"):
            return normalize_mistral_tool_id(id)
        if "|" in id:
            call_id = id.split("|")[0]
            return re.sub(r'[^a-zA-Z0-9_-]', '_', call_id)[:40]
        if model.provider == "openai":
            return id[:40] if len(id) > 40 else id
        return id

    transformed = transform_messages(context.messages, model, normalize_tool_call_id)

    if context.systemPrompt:
        use_developer_role = model.reasoning and compat.get("supportsDeveloperRole")
        role = "developer" if use_developer_role else "system"
        params.append({"role": role, "content": sanitize_surrogates(context.systemPrompt)})

    last_role = None

    for i, msg in enumerate(transformed):
        if compat.get("requiresAssistantAfterToolResult") and last_role == "toolResult" and msg.role == "user":
            params.append({"role": "assistant", "content": "I have processed the tool results."})

        if msg.role == "user":
            if isinstance(msg.content, str):
                params.append({"role": "user", "content": sanitize_surrogates(msg.content)})
            else:
                content = []
                for item in msg.content:
                    if item.type == "text":
                        content.append({"type": "text", "text": sanitize_surrogates(item.text)})
                    elif item.type == "image" and "image" in model.input:
                        content.append({
                            "type": "image_url",
                            "image_url": {"url": f"data:{item.mimeType};base64,{item.data}"},
                        })
                if content:
                    params.append({"role": "user", "content": content})
            last_role = "user"

        elif msg.role == "assistant":
            assistant_msg: Dict[str, Any] = {
                "role": "assistant",
                "content": "" if compat.get("requiresAssistantAfterToolResult") else None,
            }

            text_blocks = [b for b in msg.content if b.type == "text" and b.text.strip()]
            if text_blocks:
                if model.provider == "github-copilot":
                    assistant_msg["content"] = "".join(sanitize_surrogates(b.text) for b in text_blocks)
                else:
                    assistant_msg["content"] = [{"type": "text", "text": sanitize_surrogates(b.text)} for b in
                                                text_blocks]

            tool_calls = [b for b in msg.content if b.type == "toolCall"]
            if tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
                    }
                    for tc in tool_calls
                ]

            has_content = bool(assistant_msg.get("content")) or bool(assistant_msg.get("tool_calls"))
            if has_content:
                params.append(assistant_msg)
            last_role = "assistant"

        elif msg.role == "toolResult":
            text_result = "\n".join(
                c.text for c in msg.content if c.type == "text"
            )
            tool_result_msg: Dict[str, Any] = {
                "role": "tool",
                "content": sanitize_surrogates(text_result or "(see attached image)"),
                "tool_call_id": msg.toolCallId,
            }
            if compat.get("requiresToolResultName") and msg.toolName:
                tool_result_msg["name"] = msg.toolName
            params.append(tool_result_msg)
            last_role = "toolResult"

    return params


def stream_openai_completions(
        model: Model,
        context: Context,
        options: Optional[OpenAICompletionsOptions] = None,
) -> AssistantMessageEventStream:
    """
    Stream completions from OpenAI and compatible APIs.

    This is a Python implementation that requires the openai library.
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
            import openai

            api_key = (options.get("apiKey") if options else None) or get_env_api_key(model.provider) or ""

            client = openai.OpenAI(
                api_key=api_key,
                base_url=model.baseUrl,
            )

            compat = get_compat(model)
            params = _build_params(model, context, options, compat)
            if options and options.get("onPayload"):
                options["onPayload"](params)

            stream.push({"type": "start", "partial": output})

            current_block: Optional[Union[TextContent, ThinkingContent, ToolCall]] = None
            partial_args = ""

            def finish_current_block():
                nonlocal current_block, partial_args
                if current_block:
                    if current_block.type == "text":
                        stream.push({
                            "type": "text_end",
                            "contentIndex": len(output.content) - 1,
                            "content": current_block.text,
                            "partial": output,
                        })
                    elif current_block.type == "thinking":
                        stream.push({
                            "type": "thinking_end",
                            "contentIndex": len(output.content) - 1,
                            "content": current_block.thinking,
                            "partial": output,
                        })
                    elif current_block.type == "toolCall":
                        current_block.arguments = parse_streaming_json(partial_args)
                        stream.push({
                            "type": "toolcall_end",
                            "contentIndex": len(output.content) - 1,
                            "toolCall": current_block,
                            "partial": output,
                        })
                current_block = None
                partial_args = ""

            response = client.chat.completions.create(**params)
            for chunk in response:
                # 适配 reasoning_content
                if chunk.usage:
                    cached_tokens = getattr(chunk.usage.prompt_tokens_details, 'cached_tokens', 0) or 0
                    reasoning_tokens = getattr(chunk.usage.completion_tokens_details, 'reasoning_tokens', 0) or 0
                    input_tokens = (chunk.usage.prompt_tokens or 0) - cached_tokens
                    output_tokens = (chunk.usage.completion_tokens or 0) + reasoning_tokens

                    output.usage.input = input_tokens
                    output.usage.output = output_tokens
                    output.usage.cacheRead = cached_tokens
                    output.usage.cacheWrite = 0
                    output.usage.totalTokens = input_tokens + output_tokens + cached_tokens
                    calculate_cost(model, output.usage)

                choice = chunk.choices[0] if chunk.choices else None
                if not choice:
                    continue

                if choice.finish_reason:
                    output.stopReason = map_stop_reason(choice.finish_reason)

                if choice.delta:
                    # Handle text content
                    if choice.delta.content:
                        if not current_block or current_block.type != "text":
                            finish_current_block()
                            current_block = TextContent(type="text", text="")
                            output.content.append(current_block)
                            stream.push({
                                "type": "text_start",
                                "contentIndex": len(output.content) - 1,
                                "partial": output,
                            })

                        if current_block.type == "text":
                            current_block.text += choice.delta.content
                            stream.push({
                                "type": "text_delta",
                                "contentIndex": len(output.content) - 1,
                                "delta": choice.delta.content,
                                "partial": output,
                            })

                    # Handle tool calls
                    if choice.delta.tool_calls:
                        for tool_call in choice.delta.tool_calls:
                            if (not current_block or current_block.type != "toolCall" or
                                    (tool_call.id and current_block.id != tool_call.id)):
                                finish_current_block()
                                current_block = ToolCall(
                                    type="toolCall",
                                    id=tool_call.id or "",
                                    name=tool_call.function.name if tool_call.function else "",
                                    arguments={},
                                )
                                output.content.append(current_block)
                                stream.push({
                                    "type": "toolcall_start",
                                    "contentIndex": len(output.content) - 1,
                                    "partial": output,
                                })

                            if current_block.type == "toolCall":
                                if tool_call.id:
                                    current_block.id = tool_call.id
                                if tool_call.function and tool_call.function.name:
                                    current_block.name = tool_call.function.name
                                if tool_call.function and tool_call.function.arguments:
                                    partial_args += tool_call.function.arguments
                                    current_block.arguments = parse_streaming_json(partial_args)
                                    stream.push({
                                        "type": "toolcall_delta",
                                        "contentIndex": len(output.content) - 1,
                                        "delta": tool_call.function.arguments,
                                        "partial": output,
                                    })

            finish_current_block()
            stream.push({"type": "done", "reason": output.stopReason, "message": output})
            stream.end()

        except Exception as error:
            output.stopReason = "error"
            output.errorMessage = str(error)
            stream.push({"type": "error", "reason": output.stopReason, "error": output})
            stream.end()

    asyncio.create_task(_stream())
    return stream


def _build_params(
        model: Model,
        context: Context,
        options: Optional[OpenAICompletionsOptions],
        compat: Dict[str, Any],
) -> Dict[str, Any]:
    """Build parameters for OpenAI API call."""
    messages = convert_messages(model, context, compat)

    params: Dict[str, Any] = {
        "model": model.id,
        "messages": messages,
        "stream": True,
    }

    if compat.get("supportsUsageInStreaming", True):
        params["stream_options"] = {"include_usage": True}

    if compat.get("supportsStore"):
        params["store"] = False

    if options and options.get("maxTokens"):
        if compat.get("maxTokensField") == "max_tokens":
            params["max_tokens"] = options["maxTokens"]
        else:
            params["max_completion_tokens"] = options["maxTokens"]

    if options and options.get("temperature") is not None:
        params["temperature"] = options["temperature"]

    if context.tools and len(context.tools) > 0:
        params["tools"] = convert_tools(context.tools, compat)
    elif has_tool_history(context.messages):
        params["tools"] = []

    if options and options.get("toolChoice"):
        params["tool_choice"] = options["toolChoice"]

    # Only add reasoning-related parameters if reasoningEffort is explicitly provided
    # This avoids sending unsupported parameters to providers that don't support them
    reasoning_effort = options.get("reasoningEffort") if options else None
    if reasoning_effort:
        if compat.get("thinkingFormat") == "zai" and model.reasoning:
            params["thinking"] = {"type": "enabled"}
        elif model.reasoning and compat.get("supportsReasoningEffort"):
            params["reasoning_effort"] = reasoning_effort

    return params


def stream_simple_openai_completions(
        model: Model,
        context: Context,
        options: Optional[SimpleStreamOptions] = None,
) -> AssistantMessageEventStream:
    """Stream with simplified options."""
    api_key = (options.get("apiKey") if options else None) or get_env_api_key(model.provider)
    if not api_key:
        raise ValueError(f"No API key for provider: {model.provider}")

    base = build_base_options(model, options, api_key)
    reasoning_effort = (
        options.get("reasoning") if options and supports_xhigh(model)
        else clamp_reasoning(options.get("reasoning") if options else None)
    )
    tool_choice = options.get("toolChoice") if options else None

    # Only include reasoningEffort if it's not None
    stream_options = {**base}
    if reasoning_effort is not None:
        stream_options["reasoningEffort"] = reasoning_effort
    if tool_choice is not None:
        stream_options["toolChoice"] = tool_choice

    return stream_openai_completions(model, context, stream_options)
