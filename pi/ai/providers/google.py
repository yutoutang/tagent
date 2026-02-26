"""
Google Generative AI Provider

Stream completions from Google's Gemini models.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Union

from ..env_api_keys import get_env_api_key
from ..models import calculate_cost
from ..types import (
    Api,
    AssistantMessage,
    Context,
    Model,
    SimpleStreamOptions,
    StopReason,
    StreamFunction,
    StreamOptions,
    TextContent,
    ThinkingBudgets,
    ThinkingContent,
    ThinkingLevel,
    Tool,
    ToolCall,
    Usage,
    UsageCost,
)
from ..utils.event_stream import AssistantMessageEventStream
from ..utils.sanitize_unicode import sanitize_surrogates
from .simple_options import build_base_options, clamp_reasoning

# Counter for generating unique tool call IDs
_tool_call_counter = 0


@dataclass
class GoogleOptions(StreamOptions):
    """Google-specific streaming options."""
    toolChoice: Optional[Literal["auto", "none", "any"]] = None
    thinking: Optional[Dict[str, Any]] = None


GoogleThinkingLevel = Literal["MINIMAL", "LOW", "MEDIUM", "HIGH"]


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


def is_gemini_3_pro_model(model: Model) -> bool:
    """Check if model is Gemini 3 Pro."""
    return "3-pro" in model.id


def is_gemini_3_flash_model(model: Model) -> bool:
    """Check if model is Gemini 3 Flash."""
    return "3-flash" in model.id


def get_gemini_3_thinking_level(
    effort: str,
    model: Model,
) -> GoogleThinkingLevel:
    """Get thinking level for Gemini 3 models."""
    if is_gemini_3_pro_model(model):
        if effort in ("minimal", "low"):
            return "LOW"
        return "HIGH"

    mapping = {
        "minimal": "MINIMAL",
        "low": "LOW",
        "medium": "MEDIUM",
        "high": "HIGH",
    }
    return mapping.get(effort, "MEDIUM")


def get_google_budget(
    model: Model,
    effort: str,
    custom_budgets: Optional[ThinkingBudgets] = None,
) -> int:
    """Get thinking budget for Google models."""
    if custom_budgets and effort in custom_budgets:
        return custom_budgets[effort]

    if "2.5-pro" in model.id:
        budgets = {
            "minimal": 128,
            "low": 2048,
            "medium": 8192,
            "high": 32768,
        }
        return budgets.get(effort, 8192)

    if "2.5-flash" in model.id:
        budgets = {
            "minimal": 128,
            "low": 2048,
            "medium": 8192,
            "high": 24576,
        }
        return budgets.get(effort, 8192)

    return -1


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


def convert_tools(tools: List[Tool]) -> List[Dict[str, Any]]:
    """Convert tools to Google's format."""
    return [{
        "functionDeclarations": [{
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
        } for tool in tools]
    }]


def convert_messages(model: Model, context: Context) -> List[Dict[str, Any]]:
    """Convert messages to Google's format."""
    contents = []

    for msg in context.messages:
        if msg.role == "user":
            if isinstance(msg.content, str):
                contents.append({
                    "role": "user",
                    "parts": [{"text": sanitize_surrogates(msg.content)}],
                })
            else:
                parts = []
                for item in msg.content:
                    if item.type == "text":
                        parts.append({"text": sanitize_surrogates(item.text)})
                    elif item.type == "image" and "image" in model.input:
                        parts.append({
                            "inlineData": {
                                "mimeType": item.mimeType,
                                "data": item.data,
                            }
                        })
                if parts:
                    contents.append({"role": "user", "parts": parts})

        elif msg.role == "assistant":
            parts = []
            for block in msg.content:
                if block.type == "text" and block.text.strip():
                    parts.append({"text": sanitize_surrogates(block.text)})
                elif block.type == "thinking" and block.thinking.strip():
                    parts.append({
                        "text": sanitize_surrogates(block.thinking),
                        "thought": True,
                        **({"thoughtSignature": block.thinkingSignature} if block.thinkingSignature else {}),
                    })
                elif block.type == "toolCall":
                    parts.append({
                        "functionCall": {
                            "name": block.name,
                            "args": block.arguments or {},
                            **({"id": block.id} if block.id else {}),
                        }
                    })
            if parts:
                contents.append({"role": "model", "parts": parts})

        elif msg.role == "toolResult":
            parts = []
            for item in msg.content:
                if item.type == "text":
                    parts.append({"text": sanitize_surrogates(item.text)})
                elif item.type == "image":
                    parts.append({
                        "inlineData": {
                            "mimeType": item.mimeType,
                            "data": item.data,
                        }
                    })
            contents.append({
                "role": "user",
                "parts": [{
                    "functionResponse": {
                        "name": msg.toolName,
                        "response": {
                            "result": parts[0].get("text", "") if parts else "",
                        }
                    }
                }],
            })

    return contents


def stream_google(
    model: Model,
    context: Context,
    options: Optional[GoogleOptions] = None,
) -> AssistantMessageEventStream:
    """
    Stream completions from Google's Gemini models.

    This is a Python implementation that requires the google-genai library.
    """
    stream = AssistantMessageEventStream()

    async def _stream():
        global _tool_call_counter
        output = AssistantMessage(
            role="assistant",
            content=[],
            api="google-generative-ai",
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
            from google import genai

            api_key = (options.get("apiKey") if options else None) or get_env_api_key(model.provider) or ""

            client = genai.Client(api_key=api_key)

            params = _build_params(model, context, options)
            if options and options.get("onPayload"):
                options["onPayload"](params)

            stream.push({"type": "start", "partial": output})

            current_block: Optional[Union[TextContent, ThinkingContent]] = None

            def block_index() -> int:
                return len(output.content) - 1

            for chunk in client.models.generate_content_stream(**params):
                candidate = chunk.candidates[0] if chunk.candidates else None
                if candidate and candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if hasattr(part, 'text') and part.text is not None:
                            is_thinking = is_thinking_part(part)

                            if (not current_block or
                                (is_thinking and current_block.type != "thinking") or
                                (not is_thinking and current_block.type != "text")):
                                if current_block:
                                    if current_block.type == "text":
                                        stream.push({
                                            "type": "text_end",
                                            "contentIndex": block_index(),
                                            "content": current_block.text,
                                            "partial": output,
                                        })
                                    else:
                                        stream.push({
                                            "type": "thinking_end",
                                            "contentIndex": block_index(),
                                            "content": current_block.thinking,
                                            "partial": output,
                                        })

                                if is_thinking:
                                    current_block = ThinkingContent(type="thinking", thinking="")
                                    output.content.append(current_block)
                                    stream.push({
                                        "type": "thinking_start",
                                        "contentIndex": block_index(),
                                        "partial": output,
                                    })
                                else:
                                    current_block = TextContent(type="text", text="")
                                    output.content.append(current_block)
                                    stream.push({
                                        "type": "text_start",
                                        "contentIndex": block_index(),
                                        "partial": output,
                                    })

                            if current_block.type == "thinking":
                                current_block.thinking += part.text
                                current_block.thinkingSignature = retain_thought_signature(
                                    current_block.thinkingSignature,
                                    getattr(part, 'thoughtSignature', None),
                                )
                                stream.push({
                                    "type": "thinking_delta",
                                    "contentIndex": block_index(),
                                    "delta": part.text,
                                    "partial": output,
                                })
                            else:
                                current_block.text += part.text
                                stream.push({
                                    "type": "text_delta",
                                    "contentIndex": block_index(),
                                    "delta": part.text,
                                    "partial": output,
                                })

                        if hasattr(part, 'function_call') and part.function_call:
                            if current_block:
                                if current_block.type == "text":
                                    stream.push({
                                        "type": "text_end",
                                        "contentIndex": block_index(),
                                        "content": current_block.text,
                                        "partial": output,
                                    })
                                else:
                                    stream.push({
                                        "type": "thinking_end",
                                        "contentIndex": block_index(),
                                        "content": current_block.thinking,
                                        "partial": output,
                                    })
                                current_block = None

                            fc = part.function_call
                            provided_id = getattr(fc, 'id', None)
                            needs_new_id = (
                                not provided_id or
                                any(b.type == "toolCall" and b.id == provided_id for b in output.content)
                            )
                            _tool_call_counter += 1
                            tool_call_id = (
                                f"{fc.name}_{int(time.time() * 1000)}_{_tool_call_counter}"
                                if needs_new_id else provided_id
                            )

                            tool_call = ToolCall(
                                type="toolCall",
                                id=tool_call_id,
                                name=fc.name or "",
                                arguments=dict(fc.args) if fc.args else {},
                            )
                            output.content.append(tool_call)
                            stream.push({
                                "type": "toolcall_start",
                                "contentIndex": block_index(),
                                "partial": output,
                            })
                            stream.push({
                                "type": "toolcall_delta",
                                "contentIndex": block_index(),
                                "delta": json.dumps(tool_call.arguments),
                                "partial": output,
                            })
                            stream.push({
                                "type": "toolcall_end",
                                "contentIndex": block_index(),
                                "toolCall": tool_call,
                                "partial": output,
                            })

                if candidate and candidate.finish_reason:
                    output.stopReason = map_stop_reason(candidate.finish_reason)
                    if any(b.type == "toolCall" for b in output.content):
                        output.stopReason = "toolUse"

                if hasattr(chunk, 'usage_metadata') and chunk.usage_metadata:
                    output.usage.input = chunk.usage_metadata.prompt_token_count or 0
                    output.usage.output = (
                        (chunk.usage_metadata.candidates_token_count or 0) +
                        (chunk.usage_metadata.thoughts_token_count or 0)
                    )
                    output.usage.cacheRead = chunk.usage_metadata.cached_content_token_count or 0
                    output.usage.cacheWrite = 0
                    output.usage.totalTokens = chunk.usage_metadata.total_token_count or 0
                    calculate_cost(model, output.usage)

            if current_block:
                if current_block.type == "text":
                    stream.push({
                        "type": "text_end",
                        "contentIndex": block_index(),
                        "content": current_block.text,
                        "partial": output,
                    })
                else:
                    stream.push({
                        "type": "thinking_end",
                        "contentIndex": block_index(),
                        "content": current_block.thinking,
                        "partial": output,
                    })

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
    options: Optional[GoogleOptions] = None,
) -> Dict[str, Any]:
    """Build parameters for Google API call."""
    contents = convert_messages(model, context)

    config: Dict[str, Any] = {}
    if options:
        if options.get("temperature") is not None:
            config["temperature"] = options["temperature"]
        if options.get("maxTokens") is not None:
            config["maxOutputTokens"] = options["maxTokens"]

    if context.systemPrompt:
        config["systemInstruction"] = sanitize_surrogates(context.systemPrompt)

    if context.tools and len(context.tools) > 0:
        config["tools"] = convert_tools(context.tools)

    if context.tools and len(context.tools) > 0 and options and options.get("toolChoice"):
        config["toolConfig"] = {
            "functionCallingConfig": {
                "mode": map_tool_choice(options["toolChoice"]),
            },
        }

    if options and options.get("thinking", {}).get("enabled") and model.reasoning:
        thinking_config: Dict[str, Any] = {"includeThoughts": True}
        if options["thinking"].get("level") is not None:
            thinking_config["thinkingLevel"] = options["thinking"]["level"]
        elif options["thinking"].get("budgetTokens") is not None:
            thinking_config["thinkingBudget"] = options["thinking"]["budgetTokens"]
        config["thinkingConfig"] = thinking_config

    return {
        "model": model.id,
        "contents": contents,
        "config": config,
    }


def stream_simple_google(
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
        return stream_google(model, context, {**base, "thinking": {"enabled": False}})

    effort = clamp_reasoning(options.get("reasoning"))

    if is_gemini_3_pro_model(model) or is_gemini_3_flash_model(model):
        return stream_google(model, context, {
            **base,
            "thinking": {
                "enabled": True,
                "level": get_gemini_3_thinking_level(effort, model),
            },
        })

    return stream_google(model, context, {
        **base,
        "thinking": {
            "enabled": True,
            "budgetTokens": get_google_budget(model, effort, options.get("thinkingBudgets") if options else None),
        },
    })


# Import json for tool call serialization
import json
