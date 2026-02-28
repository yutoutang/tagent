"""
Agent class that uses the agent-loop directly.
No transport abstraction - calls streamSimple via the loop.
"""
from typing import Any, Callable, Literal

from .message_utils import default_convert_to_llm
from .types import (
    AgentContext,
    AgentEvent,
    AgentLoopConfig,
    AgentMessage,
    AgentState,
    AgentTool,
    ThinkingLevel,
    ImageContent,
    TextContent,
    Model,
    Message,
    Usage,
    Cost,
    AssistantMessage,
)
from .agent_loop import agent_loop, agent_loop_continue
import time
import asyncio


def _get_model_attr(model: Any, attr: str, default: Any = "") -> Any:
    """Helper to get attribute from Model object or dict."""
    if model is None:
        return default
    if isinstance(model, dict):
        return model.get(attr, default)
    return getattr(model, attr, default)

class AgentOptions:
    """Options for creating an Agent."""

    def __init__(
        self,
        initial_state: dict | None = None,
        convert_to_llm: Callable | None = None,
        transform_context: Callable | None = None,
        steering_mode: Literal["all", "one-at-a-time"] = "one-at-a-time",
        follow_up_mode: Literal["all", "one-at-a-time"] = "one-at-a-time",
        stream_fn: Callable | None = None,
        session_id: str | None = None,
        get_api_key: Callable[[str], str | None | Any] | None = None,
        thinking_budgets: dict | None = None,
        transport: Literal["sse"] = "sse",
        max_retry_delay_ms: int | None = None,
    ):
        self.initial_state = initial_state
        self.convert_to_llm = convert_to_llm
        self.transform_context = transform_context
        self.steering_mode = steering_mode
        self.follow_up_mode = follow_up_mode
        self.stream_fn = stream_fn
        self.session_id = session_id
        self.get_api_key = get_api_key
        self.thinking_budgets = thinking_budgets
        self.transport = transport
        self.max_retry_delay_ms = max_retry_delay_ms


class Agent:
    """
    Agent class that manages conversation state and tool execution.
    """

    def __init__(self, opts: AgentOptions | None = None):
        if opts is None:
            opts = AgentOptions()

        # Default state todo 这里 state 初始化，提供一个函数来获取默认配置
        self._state: AgentState = {
            "systemPrompt": "",
            "model": {
                "api": "google",
                "provider": "google",
                "id": "gemini-2.5-flash-lite-preview-06-17",
            },
            "thinkingLevel": "off",
            "tools": [],
            "messages": [],
            "isStreaming": False,
            "streamMessage": None,
            "pendingToolCalls": set(),
            "error": None,
        }

        # Apply initial state if provided
        if opts.initial_state:
            for key, value in opts.initial_state.items():
                if key in self._state:
                    self._state[key] = value

        # Configuration
        self.convert_to_llm = opts.convert_to_llm or default_convert_to_llm
        self.transform_context = opts.transform_context
        self.steering_mode = opts.steering_mode or "one-at-a-time"
        self.follow_up_mode = opts.follow_up_mode or "one-at-a-time"
        self.stream_fn = opts.stream_fn or self._default_stream_fn
        self._session_id = opts.session_id
        self.get_api_key = opts.get_api_key
        self._thinking_budgets = opts.thinking_budgets
        self._transport = opts.transport or "sse"
        self._max_retry_delay_ms = opts.max_retry_delay_ms

        # Internal state
        self._listeners: set[Callable[[AgentEvent], None]] = set()
        self._abort_controller: Any = None
        self._steering_queue: list[AgentMessage] = []
        self._follow_up_queue: list[AgentMessage] = []
        self._running_prompt: Any | None = None
        self._resolve_running_prompt: Callable | None = None

    @property
    def session_id(self) -> str | None:
        """Get the current session ID used for provider caching."""
        return self._session_id

    @session_id.setter
    def session_id(self, value: str | None):
        """Set the session ID for provider caching."""
        self._session_id = value

    @property
    def thinking_budgets(self) -> dict | None:
        """Get the current thinking budgets."""
        return self._thinking_budgets

    @thinking_budgets.setter
    def thinking_budgets(self, value: dict | None):
        """Set custom thinking budgets for token-based providers."""
        self._thinking_budgets = value

    @property
    def transport(self) -> str:
        """Get the current preferred transport."""
        return self._transport

    def set_transport(self, value: Literal["sse"]):
        """Set the preferred transport."""
        self._transport = value

    @property
    def max_retry_delay_ms(self) -> int | None:
        """Get the current max retry delay in milliseconds."""
        return self._max_retry_delay_ms

    @max_retry_delay_ms.setter
    def max_retry_delay_ms(self, value: int | None):
        """Set the maximum delay to wait for server-requested retries."""
        self._max_retry_delay_ms = value

    @property
    def state(self) -> AgentState:
        """Get the current agent state."""
        return self._state

    def subscribe(self, fn: Callable[[AgentEvent], None]) -> Callable[[], None]:
        """Subscribe to agent events."""
        self._listeners.add(fn)

        def unsubscribe():
            self._listeners.discard(fn)

        return unsubscribe

    # State mutators
    def set_system_prompt(self, v: str) -> None:
        """Set the system prompt."""
        self._state["systemPrompt"] = v

    def set_model(self, m: Model) -> None:
        """Set the model."""
        self._state["model"] = m

    def set_thinking_level(self, l: ThinkingLevel) -> None:
        """Set the thinking level."""
        self._state["thinkingLevel"] = l

    def set_steering_mode(self, mode: Literal["all", "one-at-a-time"]) -> None:
        """Set the steering mode."""
        self.steering_mode = mode

    def get_steering_mode(self) -> Literal["all", "one-at-a-time"]:
        """Get the steering mode."""
        return self.steering_mode

    def set_follow_up_mode(self, mode: Literal["all", "one-at-a-time"]) -> None:
        """Set the follow-up mode."""
        self.follow_up_mode = mode

    def get_follow_up_mode(self) -> Literal["all", "one-at-a-time"]:
        """Get the follow-up mode."""
        return self.follow_up_mode

    def set_tools(self, t: list[AgentTool]) -> None:
        """Set the available tools."""
        self._state["tools"] = t

    def replace_messages(self, ms: list[AgentMessage]) -> None:
        """Replace all messages."""
        self._state["messages"] = list(ms)

    def append_message(self, m: AgentMessage) -> None:
        """Append a message."""
        self._state["messages"] = [*self._state["messages"], m]

    def steer(self, m: AgentMessage) -> None:
        """
        Queue a steering message to interrupt the agent mid-run.
        Delivered after current tool execution, skips remaining tools.
        """
        self._steering_queue.append(m)

    def follow_up(self, m: AgentMessage) -> None:
        """
        Queue a follow-up message to be processed after the agent finishes.
        Delivered only when agent has no more tool calls or steering messages.
        """
        self._follow_up_queue.append(m)

    def clear_steering_queue(self) -> None:
        """Clear the steering queue."""
        self._steering_queue = []

    def clear_follow_up_queue(self) -> None:
        """Clear the follow-up queue."""
        self._follow_up_queue = []

    def clear_all_queues(self) -> None:
        """Clear all queues."""
        self._steering_queue = []
        self._follow_up_queue = []

    def has_queued_messages(self) -> bool:
        """Check if there are queued messages."""
        return len(self._steering_queue) > 0 or len(self._follow_up_queue) > 0

    def _dequeue_steering_messages(self) -> list[AgentMessage]:
        """Dequeue steering messages based on mode."""
        if self.steering_mode == "one-at-a-time":
            if len(self._steering_queue) > 0:
                first = self._steering_queue[0]
                self._steering_queue = self._steering_queue[1:]
                return [first]
            return []

        steering = list(self._steering_queue)
        self._steering_queue = []
        return steering

    def _dequeue_follow_up_messages(self) -> list[AgentMessage]:
        """Dequeue follow-up messages based on mode."""
        if self.follow_up_mode == "one-at-a-time":
            if len(self._follow_up_queue) > 0:
                first = self._follow_up_queue[0]
                self._follow_up_queue = self._follow_up_queue[1:]
                return [first]
            return []

        follow_up = list(self._follow_up_queue)
        self._follow_up_queue = []
        return follow_up

    def clear_messages(self) -> None:
        """Clear all messages."""
        self._state["messages"] = []

    def abort(self) -> None:
        """Abort the current operation."""
        if self._abort_controller:
            # Call abort on the controller
            if hasattr(self._abort_controller, 'abort'):
                self._abort_controller.abort()

    async def wait_for_idle(self) -> None:
        """Wait for the agent to finish processing."""
        if self._running_prompt:
            await self._running_prompt
        # Return resolved promise

    def reset(self) -> None:
        """Reset the agent state."""
        self._state["messages"] = []
        self._state["isStreaming"] = False
        self._state["streamMessage"] = None
        self._state["pendingToolCalls"] = set()
        self._state["error"] = None
        self._steering_queue = []
        self._follow_up_queue = []

    async def prompt(
        self,
        input: str | AgentMessage | list[AgentMessage],
        images: list[ImageContent] | None = None,
    ) -> None:
        """Send a prompt with an AgentMessage or string."""
        if self._state["isStreaming"]:
            raise RuntimeError(
                "Agent is already processing a prompt. Use steer() or followUp() "
                "to queue messages, or wait for completion."
            )

        model = self._state.get("model")
        if not model:
            raise ValueError("No model configured")

        # Convert input to messages
        if isinstance(input, list):
            msgs = input
        elif isinstance(input, str):
            content: list[TextContent | ImageContent] = [{"type": "text", "text": input}]
            if images and len(images) > 0:
                content.extend(images)
            msgs = [{
                "role": "user",
                "content": content,
                "timestamp": int(_now()),
            }]
        else:
            msgs = [input]

        await self._run_loop(msgs)

    async def continue_(self) -> None:
        """Continue from current context (used for retries and resuming queued messages)."""
        if self._state["isStreaming"]:
            raise RuntimeError("Agent is already processing. Wait for completion before continuing.")

        messages = self._state.get("messages", [])
        if len(messages) == 0:
            raise ValueError("No messages to continue from")

        if messages[-1].get("role") == "assistant":
            queued_steering = self._dequeue_steering_messages()
            if len(queued_steering) > 0:
                await self._run_loop(queued_steering, skip_initial_steering_poll=True)
                return

            queued_follow_up = self._dequeue_follow_up_messages()
            if len(queued_follow_up) > 0:
                await self._run_loop(queued_follow_up)
                return

            raise ValueError("Cannot continue from message role: assistant")

        await self._run_loop(None)

    async def _run_loop(
        self,
        messages: list[AgentMessage] | None = None,
        skip_initial_steering_poll: bool = False,
    ) -> None:
        """Run the agent loop."""
        model = self._state.get("model")
        if not model:
            raise ValueError("No model configured")

        # Create a promise for tracking
        self._running_prompt = asyncio.create_task(self._run_loop_impl(
            messages,
            skip_initial_steering_poll,
        ))

        try:
            await self._running_prompt
        finally:
            self._running_prompt = None

    async def _run_loop_impl(
        self,
        messages: list[AgentMessage] | None,
        skip_initial_steering_poll: bool,
    ) -> None:
        """Implementation of the run loop."""
        import asyncio

        self._state["isStreaming"] = True
        self._state["streamMessage"] = None
        self._state["error"] = None

        # Create abort controller
        class AbortController:
            def __init__(self):
                self.aborted = False
                self.signal = None

            def abort(self):
                self.aborted = True

        self._abort_controller = AbortController()

        # Get model from state
        model = self._state.get("model")

        reasoning = None
        if self._state.get("thinkingLevel") != "off":
            reasoning = self._state.get("thinkingLevel")

        context: AgentContext = {
            "systemPrompt": self._state.get("systemPrompt", ""),
            "messages": list(self._state.get("messages", [])),
            "tools": self._state.get("tools", []),
        }

        config: AgentLoopConfig = {
            "model": model,
            "convertToLlm": self.convert_to_llm,
            "transformContext": self.transform_context,
            "getApiKey": self.get_api_key,
            "getSteeringMessages": self._get_steering_messages_impl(skip_initial_steering_poll),
            "getFollowUpMessages": self._get_follow_up_messages_impl,
            "reasoning": reasoning,
            "sessionId": self._session_id,
            "thinkingBudgets": self._thinking_budgets,
            "transport": self._transport,
            "maxRetryDelayMs": self._max_retry_delay_ms,
        }

        partial: AgentMessage | None = None

        try:
            stream = (
                agent_loop(
                    messages,
                    context,
                    config,
                    self._abort_controller.signal,
                    self.stream_fn,
                )
                if messages
                else agent_loop_continue(
                    context,
                    config,
                    self._abort_controller.signal,
                    self.stream_fn,
                )
            )

            async for event in stream:
                # Update internal state based on events
                event_type = event.get("type")

                if event_type == "message_start":
                    partial = event.get("message")
                    self._state["streamMessage"] = event.get("message")

                elif event_type == "message_update":
                    partial = event.get("message")
                    self._state["streamMessage"] = event.get("message")

                elif event_type == "message_end":
                    partial = None
                    self._state["streamMessage"] = None
                    self.append_message(event.get("message"))

                elif event_type == "tool_execution_start":
                    s = set(self._state.get("pendingToolCalls", set()))
                    s.add(event.get("toolCallId"))
                    self._state["pendingToolCalls"] = s

                elif event_type == "tool_execution_end":
                    s = set(self._state.get("pendingToolCalls", set()))
                    s.discard(event.get("toolCallId"))
                    self._state["pendingToolCalls"] = s

                elif event_type == "turn_end":
                    message = event.get("message", {})
                    if message.get("role") == "assistant" and message.get("errorMessage"):
                        self._state["error"] = message.get("errorMessage")

                elif event_type == "agent_end":
                    self._state["isStreaming"] = False
                    self._state["streamMessage"] = None

                # Emit to listeners
                self._emit(event)

            # Handle any remaining partial message
            if partial and partial.get("role") == "assistant" and len(partial.get("content", [])) > 0:
                only_empty = not any(
                    (c.get("type") == "thinking" and c.get("thinking", "").strip())
                    or (c.get("type") == "text" and c.get("text", "").strip())
                    or (c.get("type") == "toolCall" and c.get("name", "").strip())
                    for c in partial.get("content", [])
                )
                if not only_empty:
                    self.append_message(partial)
                else:
                    if self._abort_controller and self._abort_controller.aborted:
                        raise RuntimeError("Request was aborted")

        except Exception as err:
            error_msg: AgentMessage = {
                "role": "assistant",
                "content": [{"type": "text", "text": ""}],
                "api": _get_model_attr(model, "api"),
                "provider": _get_model_attr(model, "provider"),
                "model": _get_model_attr(model, "id"),
                "usage": {
                    "input": 0,
                    "output": 0,
                    "cacheRead": 0,
                    "cacheWrite": 0,
                    "totalTokens": 0,
                    "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "total": 0},
                },
                "stopReason": "aborted" if (self._abort_controller and self._abort_controller.aborted) else "error",
                "errorMessage": str(err),
                "timestamp": int(_now()),
            }

            self.append_message(error_msg)
            self._state["error"] = str(err)
            self._emit({"type": "agent_end", "messages": [error_msg]})

        finally:
            self._state["isStreaming"] = False
            self._state["streamMessage"] = None
            self._state["pendingToolCalls"] = set()
            self._abort_controller = None

    def _get_steering_messages_impl(self, skip_poll: bool) -> Callable:
        """Create a callback for getting steering messages."""
        skip = skip_poll

        async def callback():
            nonlocal skip
            if skip:
                skip = False
                return []
            return self._dequeue_steering_messages()

        return callback

    async def _get_follow_up_messages_impl(self) -> list[AgentMessage]:
        """Get follow-up messages."""
        return self._dequeue_follow_up_messages()

    def _emit(self, event: AgentEvent) -> None:
        """Emit an event to all listeners."""
        for listener in self._listeners:
            listener(event)

    async def _default_stream_fn(self, model: dict, context: dict, options: dict):
        """Default stream function."""
        from .event_stream import EventStream

        stream = EventStream(
            lambda e: e.get("type") in ("done", "error"),
            lambda e: e,
        )
        # Mock implementation
        stream.end({"type": "done"})
        return stream


def _now() -> float:
    """Get current timestamp in milliseconds."""
    return time.time() * 1000
