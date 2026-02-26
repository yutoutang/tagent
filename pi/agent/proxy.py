"""
Proxy stream function for apps that route LLM calls through a server.
The server manages auth and proxies requests to LLM providers.
"""
from typing import Any
from .event_stream import EventStream
from .types import (
    ProxyAssistantMessageEvent,
    ProxyStreamOptions,
    AssistantMessage,
    AssistantMessageEvent,
    ToolCall,
)
import json
import asyncio


class ProxyMessageEventStream(EventStream[AssistantMessageEvent, AssistantMessage]):
    """Event stream for proxy-based assistant messages."""

    def __init__(self):
        def is_done(event: AssistantMessageEvent) -> bool:
            return event.get("type") in ("done", "error")

        def get_result(event: AssistantMessageEvent) -> AssistantMessage:
            event_type = event.get("type")
            if event_type == "done":
                return event.get("message")
            if event_type == "error":
                return event.get("error")
            raise RuntimeError("Unexpected event type")

        super().__init__(is_done, get_result)


async def stream_proxy(
    model: dict,
    context: dict,
    options: ProxyStreamOptions,
) -> ProxyMessageEventStream:
    """
    Stream function that proxies through a server instead of calling LLM providers directly.
    The server strips the partial field from delta events to reduce bandwidth.
    We reconstruct the partial message client-side.

    Use this as the `streamFn` option when creating an Agent that needs to go through a proxy.
    """
    import aiohttp

    stream = ProxyMessageEventStream()

    async def _run():
        # Initialize the partial message that we'll build up from events
        partial: AssistantMessage = {
            "role": "assistant",
            "stopReason": "stop",
            "content": [],
            "api": model.get("api"),
            "provider": model.get("provider"),
            "model": model.get("id"),
            "usage": {
                "input": 0,
                "output": 0,
                "cacheRead": 0,
                "cacheWrite": 0,
                "totalTokens": 0,
                "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "total": 0},
            },
            "timestamp": int(_now()),
        }

        signal = options.get("signal")
        reader = None

        def abort_handler():
            nonlocal reader
            if reader:
                # Cancel the reader/cconnection
                pass

        # Register abort handler if signal is available
        if signal and hasattr(signal, 'addEventListener'):
            signal.addEventListener("abort", abort_handler)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{options['proxyUrl']}/api/stream",
                    headers={
                        "Authorization": f"Bearer {options['authToken']}",
                        "Content-Type": "application/json",
                    },
                    data=json.dumps({
                        "model": model,
                        "context": context,
                        "options": {
                            "temperature": options.get("temperature"),
                            "maxTokens": options.get("maxTokens"),
                            "reasoning": options.get("reasoning"),
                        },
                    }),
                ) as response:
                    if response.status != 200:
                        error_msg = f"Proxy error: {response.status} {response.reason}"
                        try:
                            error_data = await response.json()
                            if error_data.get("error"):
                                error_msg = f"Proxy error: {error_data['error']}"
                        except:
                            pass
                        raise RuntimeError(error_msg)

                    # Read server-sent events
                    buffer = ""
                    async for line_bytes in response.content:
                        line = line_bytes.decode('utf-8')

                        if signal and signal.aborted:
                            raise RuntimeError("Request aborted by user")

                        buffer += line
                        lines = buffer.split("\n")
                        buffer = lines[-1] if lines else ""

                        for line_data in lines[:-1]:
                            if line_data.startswith("data: "):
                                data = line_data[6:].strip()
                                if data:
                                    try:
                                        proxy_event = json.loads(data)
                                        event = _process_proxy_event(proxy_event, partial)
                                        if event:
                                            stream.push(event)
                                    except json.JSONDecodeError:
                                        pass

                    if signal and signal.aborted:
                        raise RuntimeError("Request aborted by user")

            stream.end()

        except Exception as error:
            error_message = str(error) if isinstance(error, Exception) else str(error)
            reason = "aborted" if (signal and signal.aborted) else "error"
            partial["stopReason"] = reason
            partial["errorMessage"] = error_message
            stream.push({
                "type": "error",
                "reason": reason,
                "error": partial,
            })
            stream.end()

        finally:
            if signal and hasattr(signal, 'removeEventListener'):
                signal.removeEventListener("abort", abort_handler)

    asyncio.create_task(_run())
    return stream


def _process_proxy_event(
    proxy_event: ProxyAssistantMessageEvent,
    partial: AssistantMessage,
) -> AssistantMessageEvent | None:
    """Process a proxy event and update the partial message."""
    event_type = proxy_event.get("type")

    if event_type == "start":
        return {"type": "start", "partial": partial}

    elif event_type == "text_start":
        content_index = proxy_event.get("contentIndex", 0)
        partial["content"][content_index] = {"type": "text", "text": ""}
        return {
            "type": "text_start",
            "contentIndex": content_index,
            "partial": partial,
        }

    elif event_type == "text_delta":
        content_index = proxy_event.get("contentIndex", 0)
        delta = proxy_event.get("delta", "")
        content = partial["content"][content_index]
        if content.get("type") == "text":
            content["text"] = content.get("text", "") + delta
            return {
                "type": "text_delta",
                "contentIndex": content_index,
                "delta": delta,
                "partial": partial,
            }
        raise ValueError("Received text_delta for non-text content")

    elif event_type == "text_end":
        content_index = proxy_event.get("contentIndex", 0)
        content = partial["content"][content_index]
        if content.get("type") == "text":
            if proxy_event.get("contentSignature"):
                content["textSignature"] = proxy_event["contentSignature"]
            return {
                "type": "text_end",
                "contentIndex": content_index,
                "content": content.get("text", ""),
                "partial": partial,
            }
        raise ValueError("Received text_end for non-text content")

    elif event_type == "thinking_start":
        content_index = proxy_event.get("contentIndex", 0)
        partial["content"][content_index] = {"type": "thinking", "thinking": ""}
        return {
            "type": "thinking_start",
            "contentIndex": content_index,
            "partial": partial,
        }

    elif event_type == "thinking_delta":
        content_index = proxy_event.get("contentIndex", 0)
        delta = proxy_event.get("delta", "")
        content = partial["content"][content_index]
        if content.get("type") == "thinking":
            content["thinking"] = content.get("thinking", "") + delta
            return {
                "type": "thinking_delta",
                "contentIndex": content_index,
                "delta": delta,
                "partial": partial,
            }
        raise ValueError("Received thinking_delta for non-thinking content")

    elif event_type == "thinking_end":
        content_index = proxy_event.get("contentIndex", 0)
        content = partial["content"][content_index]
        if content.get("type") == "thinking":
            if proxy_event.get("contentSignature"):
                content["thinkingSignature"] = proxy_event["contentSignature"]
            return {
                "type": "thinking_end",
                "contentIndex": content_index,
                "content": content.get("thinking", ""),
                "partial": partial,
            }
        raise ValueError("Received thinking_end for non-thinking content")

    elif event_type == "toolcall_start":
        content_index = proxy_event.get("contentIndex", 0)
        partial["content"][content_index] = {
            "type": "toolCall",
            "id": proxy_event.get("id"),
            "name": proxy_event.get("toolName"),
            "arguments": {},
            "partialJson": "",
        }
        return {
            "type": "toolcall_start",
            "contentIndex": content_index,
            "partial": partial,
        }

    elif event_type == "toolcall_delta":
        content_index = proxy_event.get("contentIndex", 0)
        delta = proxy_event.get("delta", "")
        content = partial["content"][content_index]
        if content.get("type") == "toolCall":
            content["partialJson"] = content.get("partialJson", "") + delta
            # Parse streaming JSON
            try:
                content["arguments"] = _parse_streaming_json(content.get("partialJson", ""))
            except:
                content["arguments"] = {}
            # Trigger reactivity by creating new content
            partial["content"] = list(partial["content"])
            return {
                "type": "toolcall_delta",
                "contentIndex": content_index,
                "delta": delta,
                "partial": partial,
            }
        raise ValueError("Received toolcall_delta for non-toolCall content")

    elif event_type == "toolcall_end":
        content_index = proxy_event.get("contentIndex", 0)
        content = partial["content"][content_index]
        if content.get("type") == "toolCall":
            # Remove partialJson from final content
            if "partialJson" in content:
                del content["partialJson"]
            return {
                "type": "toolcall_end",
                "contentIndex": content_index,
                "toolCall": content,
                "partial": partial,
            }
        return None

    elif event_type == "done":
        partial["stopReason"] = proxy_event.get("reason")
        partial["usage"] = proxy_event.get("usage", partial.get("usage"))
        return {
            "type": "done",
            "reason": proxy_event.get("reason"),
            "message": partial,
        }

    elif event_type == "error":
        partial["stopReason"] = proxy_event.get("reason")
        partial["errorMessage"] = proxy_event.get("errorMessage")
        partial["usage"] = proxy_event.get("usage", partial.get("usage"))
        return {
            "type": "error",
            "reason": proxy_event.get("reason"),
            "error": partial,
        }

    else:
        # Unknown event type
        return None


def _parse_streaming_json(partial_json: str) -> dict:
    """
    Parse a partial JSON string.
    This is a simplified version - a real implementation would handle
    incomplete JSON more gracefully.
    """
    try:
        return json.loads(partial_json)
    except json.JSONDecodeError:
        # Return empty dict if JSON is incomplete
        return {}


def _now() -> float:
    """Get current timestamp in milliseconds."""
    import time
    return time.time() * 1000
