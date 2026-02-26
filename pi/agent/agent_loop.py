"""
Agent loop that works with AgentMessage throughout.
Transforms to Message[] only at the LLM call boundary.
"""
import dataclasses
from typing import Any, Callable

from .event_stream import EventStream
from .message_utils import default_convert_to_llm
from .types import (
    AgentContext,
    AgentEvent,
    AgentLoopConfig,
    AgentMessage,
    AgentTool,
    AgentToolResult,
    AssistantMessage,
    ToolCall,
    Message,
)
from .tools import BaseTool, ToolExecutor
from ..ai import stream, Context, Model, ToolResultMessage
from ..ai.stream import sample_stream


# todo 下面的函数都需要优化
def _to_dict(obj: Any) -> Any:
    """Safely convert dataclass to dict, or return as-is if already a dict."""
    if dataclasses.is_dataclass(obj):
        return dataclasses.asdict(obj)
    return obj


def _convert_tools(tools: list[Any] | None) -> list[Any] | None:
    """Convert tools to LLM-compatible format."""
    if not tools:
        return None

    from .tools import BaseTool
    from ..ai.types import Tool

    converted = []
    for tool in tools:
        if isinstance(tool, BaseTool):
            tool_dict = tool.to_dict()
            converted.append(Tool(
                name=tool_dict["name"],
                description=tool_dict["description"],
                parameters=tool_dict["parameters"],
            ))
        elif isinstance(tool, dict):
            converted.append(Tool(
                name=tool["name"],
                description=tool["description"],
                parameters=tool.get("parameters", {}),
            ))
        elif isinstance(tool, Tool):
            converted.append(tool)
        else:
            raise TypeError(f"Unsupported tool type: {type(tool)}")

    return converted


def agent_loop(
    prompts: list[AgentMessage],
    context: AgentContext,
    config: AgentLoopConfig,
    signal: Any = None,
    stream_fn: Any = None,
) -> EventStream[AgentEvent, list[AgentMessage]]:
    """
    Start an agent loop with a new prompt message.
    The prompt is added to the context and events are emitted for it.
    """
    stream = _create_agent_stream()

    async def _run():
        new_messages: list[AgentMessage] = list(prompts)
        current_context: AgentContext = {
            **context,
            "messages": [*context["messages"], *prompts],
        }

        stream.push({"type": "agent_start"})
        stream.push({"type": "turn_start"})
        for prompt in prompts:
            stream.push({"type": "message_start", "message": prompt})
            stream.push({"type": "message_end", "message": prompt})

        await _run_loop(
            current_context,
            new_messages,
            config,
            signal,
            stream,
            stream_fn,
        )

    asyncio.create_task(_run())
    return stream


def agent_loop_continue(
    context: AgentContext,
    config: AgentLoopConfig,
    signal: Any = None,
    stream_fn: Any = None,
) -> EventStream[AgentEvent, list[AgentMessage]]:
    """
    Continue an agent loop from the current context without adding a new message.
    Used for retries - context already has user message or tool results.

    **Important:** The last message in context must convert to a `user` or `toolResult` message
    via `convertToLlm`. If it doesn't, the LLM provider will reject the request.
    """
    if len(context["messages"]) == 0:
        raise ValueError("Cannot continue: no messages in context")

    if context["messages"][-1]["role"] == "assistant":
        raise ValueError("Cannot continue from message role: assistant")

    stream = _create_agent_stream()

    async def _run():
        new_messages: list[AgentMessage] = []
        current_context: AgentContext = {**context}

        stream.push({"type": "agent_start"})
        stream.push({"type": "turn_start"})

        await _run_loop(
            current_context,
            new_messages,
            config,
            signal,
            stream,
            stream_fn,
        )

    asyncio.create_task(_run())
    return stream


def _create_agent_stream() -> EventStream[AgentEvent, list[AgentMessage]]:
    def is_done(event: AgentEvent) -> bool:
        return event["type"] == "agent_end"

    def get_result(event: AgentEvent) -> list[AgentMessage]:
        if event["type"] == "agent_end":
            return event["messages"]
        raise RuntimeError("Expected agent_end event")

    return EventStream[AgentEvent, list[AgentMessage]](is_done, get_result)


async def _run_loop(
    current_context: AgentContext,
    new_messages: list[AgentMessage],
    config: AgentLoopConfig,
    signal: Any,
    stream: EventStream[AgentEvent, list[AgentMessage]],
    stream_fn: Any,
) -> None:
    """Main loop logic shared by agent_loop and agent_loop_continue."""
    import asyncio

    first_turn = True
    # Check for steering messages at start (user may have typed while waiting)
    get_steering = config.get("getSteeringMessages")
    pending_messages: list[AgentMessage] = (
        await get_steering_messages()
        if get_steering
        else []
    )

    # Outer loop: continues when queued follow-up messages arrive after agent would stop
    while True:
        has_more_tool_calls = True
        steering_after_tools: list[AgentMessage] | None = None

        # Inner loop: process tool calls and steering messages
        while has_more_tool_calls or len(pending_messages) > 0:
            if not first_turn:
                stream.push({"type": "turn_start"})
            else:
                first_turn = False

            # Process pending messages (inject before next assistant response)
            if len(pending_messages) > 0:
                for message in pending_messages:
                    stream.push({"type": "message_start", "message": message})
                    stream.push({"type": "message_end", "message": message})
                    current_context["messages"].append(message)
                    new_messages.append(message)
                pending_messages = []

            # Stream assistant response
            message = await _stream_assistant_response(
                current_context,
                config,
                signal,
                stream,
                stream_fn,
            )
            new_messages.append(message)

            stop_reason = message.stopReason
            if stop_reason in ("error", "aborted"):
                stream.push({
                    "type": "turn_end",
                    "message": message,
                    "toolResults": [],
                })
                stream.push({"type": "agent_end", "messages": new_messages})
                stream.end(new_messages)
                return

            # Check for tool calls
            tool_calls = [
                c for c in (message.content or [])
                if c.type == "toolCall"
            ]
            has_more_tool_calls = len(tool_calls) > 0

            tool_results: list[ToolResultMessage] = []
            if has_more_tool_calls:
                tool_execution = await _execute_tool_calls(
                    current_context.get("tools"),
                    message,
                    signal,
                    stream,
                    config.get("getSteeringMessages"),
                )
                tool_results.extend(tool_execution["toolResults"])
                steering_after_tools = tool_execution.get("steeringMessages")

                for result in tool_results:
                    current_context["messages"].append(result)
                    new_messages.append(result)

            stream.push({
                "type": "turn_end",
                "message": message,
                "toolResults": tool_results,
            })

            # Get steering messages after turn completes
            if steering_after_tools and len(steering_after_tools) > 0:
                pending_messages = steering_after_tools
                steering_after_tools = None
            else:
                get_steering = config.get("getSteeringMessages")
                pending_messages = (
                    await get_steering_messages()
                    if get_steering
                    else []
                )

        # Agent would stop here. Check for follow-up messages.
        get_follow_up = config.get("getFollowUpMessages")
        follow_up_messages = (
            await get_follow_up_messages()
            if get_follow_up
            else []
        )
        if len(follow_up_messages) > 0:
            # Set as pending so inner loop processes them
            pending_messages = follow_up_messages
            continue

        # No more messages, exit
        break

    stream.push({"type": "agent_end", "messages": new_messages})
    stream.end(new_messages)


async def _stream_assistant_response(
    context: AgentContext,
    config: AgentLoopConfig,
    signal: Any,
    stream: EventStream[AgentEvent, list[AgentMessage]],
    stream_fn: Any,
) -> AssistantMessage:
    """
    Stream an assistant response from the LLM.
    This is where AgentMessage[] gets transformed to Message[] for the LLM.
    """
    # Apply context transform if configured (AgentMessage[] → AgentMessage[])
    messages = context["messages"]
    transform_context = config.get("transformContext")
    if transform_context:
        messages = await transform_context(messages, signal)

    # Convert to LLM-compatible messages (AgentMessage[] → Message[])
    # todo 这种写法堆栈报错无法抛出
    convert_to_llm = config["convertToLlm"]
    llm_messages = default_convert_to_llm(messages)

    # Convert tools to LLM-compatible format
    tools = _convert_tools(context.get("tools"))

    # Build LLM context
    llm_context = Context(systemPrompt=context["systemPrompt"], messages=llm_messages, tools=tools)

    # todo 测试完后还原
    stream_function = stream_fn or _default_stream_fn

    # Resolve API key (important for expiring tokens)
    get_api_key = config.get("getApiKey")
    resolved_api_key = get_api_key
    if get_api_key:
        resolved_api_key = get_api_key(config["model"]["provider"])

    # todo 请求模型的位置
    response = await sample_stream(
        config["model"],
        llm_context,
        {
            **config,
            "apiKey": resolved_api_key or config.get("apiKey"),
            "signal": signal,
        },
    )

    partial_message: AssistantMessage | None = None
    added_partial = False

    async for event in response:
        event_type = event.get("type")

        if event_type == "start":
            partial_message = event.get("partial")
            context["messages"].append(partial_message)
            added_partial = True
            stream.push({
                "type": "message_start",
                "message": _to_dict(partial_message),
            })

        elif event_type in (
            "text_start", "text_delta", "text_end",
            "thinking_start", "thinking_delta", "thinking_end",
            "toolcall_start", "toolcall_delta", "toolcall_end",
        ):
            if partial_message:
                partial_message = event.get("partial")
                context["messages"][-1] = partial_message
                stream.push({
                    "type": "message_update",
                    "assistantMessageEvent": event,
                    "message": _to_dict(partial_message),
                })

        elif event_type in ("done", "error"):
            final_message = await response.result()
            if added_partial:
                context["messages"][-1] = final_message
            else:
                context["messages"].append(final_message)
            if not added_partial:
                stream.push({"type": "message_start", "message": _to_dict(final_message)})
            stream.push({"type": "message_end", "message": final_message})
            return final_message

    return await response.result()


async def _execute_tool_calls(
    tools: list[Any] | None,  # Can be BaseTool instances or AgentTool dicts
    assistant_message: AssistantMessage,
    signal: Any,
    stream: EventStream[AgentEvent, list[AgentMessage]],
    get_steering_messages: Callable[[], Any] | None = None,
) -> dict:
    """Execute tool calls from an assistant message."""
    tool_calls = [
        c for c in (assistant_message.content or [])
        if c.type == "toolCall"
    ]
    results: list[ToolResultMessage] = []
    steering_messages: list[AgentMessage] | None = None

    for index, tool_call in enumerate(tool_calls):
        tool = None
        if tools:
            for t in tools:
                # Handle both BaseTool objects and dicts
                tool_name = t.name if hasattr(t, 'name') else t.get("name")
                if tool_name == tool_call.name:
                    tool = t
                    break

        stream.push({
            "type": "tool_execution_start",
            "toolCallId": tool_call.id,
            "toolName": tool_call.name,
            "args": tool_call.arguments,
        })

        result: AgentToolResult
        is_error = False

        try:
            if not tool:
                raise ValueError(f"Tool {tool_call.name} not found")

            # Validate arguments (simplified - would use full validation in real implementation)
            validated_args = tool_call.arguments or {}

            # Execute tool (this would call the tool's execute method)
            result = await _execute_tool(
                tool,
                tool_call.id,
                validated_args,
                signal,
                lambda partial: stream.push({
                    "type": "tool_execution_update",
                    "toolCallId": tool_call.id,
                    "toolName": tool_call.name,
                    "args": tool_call.arguments,
                    "partialResult": partial,
                }),
            )
        except Exception as e:
            result = {
                "content": [{"type": "text", "text": str(e)}],
                "details": {},
            }
            is_error = True

        stream.push({
            "type": "tool_execution_end",
            "toolCallId": tool_call.id,
            "toolName": tool_call.name,
            "result": result,
            "isError": is_error,
        })

        # Convert result dict to proper content format
        content_list = result.get("content", [])
        if isinstance(content_list, list):
            # Ensure content blocks are in correct format
            converted_content = []
            for item in content_list:
                if isinstance(item, dict):
                    item_type = item.get("type", "text")
                    if item_type == "text":
                        from ..ai.types import TextContent
                        converted_content.append(TextContent(type="text", text=item.get("text", "")))
                    else:
                        converted_content.append(item)
                else:
                    converted_content.append(item)
            content_list = converted_content

        tool_result_message = ToolResultMessage(
            role="toolResult",
            toolCallId=tool_call.id,
            toolName=tool_call.name,
            content=content_list,
            details=result.get("details"),
            isError=is_error,
            timestamp=int(_now()),
        )

        results.append(tool_result_message)
        stream.push({"type": "message_start", "message": tool_result_message})
        stream.push({"type": "message_end", "message": tool_result_message})

        # Check for steering messages - skip remaining tools if user interrupted
        if get_steering_messages:
            steering = await get_steering_messages()
            if steering and len(steering) > 0:
                steering_messages = steering
                remaining_calls = tool_calls[index + 1:]
                for skipped in remaining_calls:
                    results.append(_skip_tool_call(skipped, stream))
                break

    return {"toolResults": results, "steeringMessages": steering_messages}


def _skip_tool_call(
    tool_call: ToolCall,
    stream: EventStream[AgentEvent, list[AgentMessage]],
) -> ToolResultMessage:
    """Create a skipped tool result message."""
    result: AgentToolResult = {
        "content": [{"type": "text", "text": "Skipped due to queued user message."}],
        "details": {},
    }

    stream.push({
        "type": "tool_execution_start",
        "toolCallId": tool_call.id,
        "toolName": tool_call.name,
        "args": tool_call.arguments,
    })
    stream.push({
        "type": "tool_execution_end",
        "toolCallId": tool_call.id,
        "toolName": tool_call.name,
        "result": result,
        "isError": True,
    })

    # Convert result dict to proper content format
    content_list = result.get("content", [])
    if isinstance(content_list, list):
        converted_content = []
        for item in content_list:
            if isinstance(item, dict):
                from ..ai.types import TextContent
                converted_content.append(TextContent(type="text", text=item.get("text", "")))
            else:
                converted_content.append(item)
        content_list = converted_content

    tool_result_message = ToolResultMessage(
        role="toolResult",
        toolCallId=tool_call.id,
        toolName=tool_call.name,
        content=content_list,
        details={},
        isError=True,
        timestamp=int(_now()),
    )

    stream.push({"type": "message_start", "message": tool_result_message})
    stream.push({"type": "message_end", "message": tool_result_message})

    return tool_result_message


async def _execute_tool(
    tool: Any,  # Can be BaseTool instance or AgentTool dict
    tool_call_id: str,
    params: dict,
    signal: Any,
    on_update: Callable,
) -> AgentToolResult:
    """Execute a single tool with the given parameters."""
    # Check if tool is a BaseTool instance or has execute method
    if isinstance(tool, BaseTool):
        # Use the BaseTool's execute method (with validation)
        return await tool.execute(tool_call_id, params, signal, on_update)
    elif isinstance(tool, dict) and "execute" in tool:
        # Tool is a dict with execute function (backward compatibility)
        execute_fn = tool["execute"]
        if callable(execute_fn):
            return await execute_fn(tool_call_id, params, signal, on_update)
        else:
            raise ValueError(f"Tool execute method is not callable")
    else:
        raise ValueError(f"Invalid tool format: {type(tool)}")


async def _default_stream_fn(model: dict, context: dict, options: dict):
    """Default stream function - should be replaced with actual implementation."""
    return stream


async def get_steering_messages() -> list[AgentMessage]:
    """Get steering messages - placeholder."""
    return []


async def get_follow_up_messages() -> list[AgentMessage]:
    """Get follow-up messages - placeholder."""
    return []


def _now() -> float:
    """Get current timestamp in milliseconds."""
    import time
    return time.time() * 1000


# Import asyncio at module level
import asyncio
