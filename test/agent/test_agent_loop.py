"""
Tests for the pi.agent agent_loop functionality.
"""
import pytest
import asyncio
from pi.agent import (
    agent_loop,
    agent_loop_continue,
    UserMessage,
    TextContent,
    AssistantMessage,
    AgentContext,
    AgentLoopConfig,
    CalculatorTool,
    EchoTool,
    BaseTool,
    ToolSchema,
    ParameterType,
    ParameterProperty,
    Model,
)


class TestAgentLoop:
    """Test agent_loop function."""

    @pytest.mark.asyncio
    async def test_agent_loop_basic_flow(self):
        """Test basic agent loop flow."""
        prompts = [
            {
                "role": "user",
                "content": [{"type": "text", "text": "Hello"}],
                "timestamp": 12345,
            }
        ]

        context: AgentContext = {
            "systemPrompt": "You are a helpful assistant.",
            "messages": [],
            "tools": [],
        }

        # Mock stream function that returns a simple assistant message
        async def mock_stream_fn(model, ctx, options):
            from pi.agent import EventStream

            stream = EventStream(
                lambda e: e.get("type") in ("done", "error"),
                lambda e: e,
            )

            # Push events
            stream.push({
                "type": "start",
                "partial": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": ""}],
                    "api": model["api"],
                    "provider": model["provider"],
                    "model": model["id"],
                    "usage": {
                        "input": 0,
                        "output": 0,
                        "cacheRead": 0,
                        "cacheWrite": 0,
                        "totalTokens": 0,
                        "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "total": 0},
                    },
                    "stopReason": "stop",
                    "timestamp": 12346,
                },
            })

            stream.push({
                "type": "text_delta",
                "delta": "Hello",
                "partial": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "Hello"}],
                    "api": model["api"],
                    "provider": model["provider"],
                    "model": model["id"],
                    "usage": {
                        "input": 0,
                        "output": 0,
                        "cacheRead": 0,
                        "cacheWrite": 0,
                        "totalTokens": 0,
                        "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "total": 0},
                    },
                    "stopReason": "stop",
                    "timestamp": 12346,
                },
            })

            stream.push({
                "type": "done",
                "reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "Hello"}],
                    "api": model["api"],
                    "provider": model["provider"],
                    "model": model["id"],
                    "usage": {
                        "input": 0,
                        "output": 5,
                        "cacheRead": 0,
                        "cacheWrite": 0,
                        "totalTokens": 5,
                        "cost": {"input": 0, "output": 0.001, "cacheRead": 0, "cacheWrite": 0, "total": 0.001},
                    },
                    "stopReason": "stop",
                    "timestamp": 12346,
                },
            })

            stream.end()
            return stream

        config: AgentLoopConfig = {
            "model": {
                "api": "test",
                "provider": "test",
                "id": "test-model",
            },
            "convertToLlm": lambda msgs: msgs,
            "transformContext": None,
            "getApiKey": None,
            "getSteeringMessages": None,
            "getFollowUpMessages": None,
        }

        stream = agent_loop(prompts, context, config, stream_fn=mock_stream_fn)

        # Collect events
        events = []
        async for event in stream:
            events.append(event)

        # Verify events
        assert events[0]["type"] == "agent_start"
        assert events[1]["type"] == "turn_start"
        assert events[-1]["type"] == "agent_end"

    @pytest.mark.asyncio
    async def test_agent_loop_with_tools(self):
        """Test agent loop with tool execution."""
        prompts = [
            {
                "role": "user",
                "content": [{"type": "text", "text": "Calculate 5 + 3"}],
                "timestamp": 12345,
            }
        ]

        context: AgentContext = {
            "systemPrompt": "You are a helpful assistant.",
            "messages": [],
            "tools": [CalculatorTool()],
        }

        async def mock_stream_fn(model, ctx, options):
            from pi.agent import EventStream

            stream = EventStream(
                lambda e: e.get("type") in ("done", "error"),
                lambda e: e,
            )

            # Return assistant message with tool call
            stream.push({
                "type": "done",
                "reason": "toolUse",
                "message": {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "I'll calculate that."},
                        {
                            "type": "toolCall",
                            "id": "call_1",
                            "name": "calculator",
                            "arguments": {"operation": "add", "a": 5, "b": 3},
                        },
                    ],
                    "api": model["api"],
                    "provider": model["provider"],
                    "model": model["id"],
                    "usage": {
                        "input": 0,
                        "output": 0,
                        "cacheRead": 0,
                        "cacheWrite": 0,
                        "totalTokens": 0,
                        "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "total": 0},
                    },
                    "stopReason": "toolUse",
                    "timestamp": 12346,
                },
            })

            stream.end()
            return stream

        config: AgentLoopConfig = {
            "model": {
                "api": "test",
                "provider": "test",
                "id": "test-model",
            },
            "convertToLlm": lambda msgs: msgs,
            "transformContext": None,
            "getApiKey": None,
            "getSteeringMessages": None,
            "getFollowUpMessages": None,
        }

        stream = agent_loop(prompts, context, config, stream_fn=mock_stream_fn)

        # Collect events
        events = []
        async for event in stream:
            events.append(event)

        # Should have tool execution events
        tool_events = [e for e in events if "tool" in e.get("type", "")]
        assert len(tool_events) > 0

    @pytest.mark.asyncio
    async def test_agent_loop_context_transformation(self):
        """Test agent loop with context transformation."""
        prompts = [
            {
                "role": "user",
                "content": [{"type": "text", "text": "Hello"}],
                "timestamp": 12345,
            }
        ]

        context: AgentContext = {
            "systemPrompt": "System prompt",
            "messages": [],
            "tools": [],
        }

        transform_called = []

        async def transform(messages, signal):
            transform_called.append(True)
            # Add a prefix to first message
            if messages:
                first = messages[0]
                return [first] + messages[1:]
            return messages

        async def mock_stream_fn(model, ctx, options):
            from pi.agent import EventStream

            stream = EventStream(
                lambda e: e.get("type") in ("done", "error"),
                lambda e: e,
            )

            stream.push({
                "type": "done",
                "reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "Hi"}],
                    "api": model["api"],
                    "provider": model["provider"],
                    "model": model["id"],
                    "usage": {
                        "input": 0,
                        "output": 0,
                        "cacheRead": 0,
                        "cacheWrite": 0,
                        "totalTokens": 0,
                        "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "total": 0},
                    },
                    "stopReason": "stop",
                    "timestamp": 12346,
                },
            })

            stream.end()
            return stream

        config: AgentLoopConfig = {
            "model": {"api": "test", "provider": "test", "id": "test-model"},
            "convertToLlm": lambda msgs: msgs,
            "transformContext": transform,
            "getApiKey": None,
            "getSteeringMessages": None,
            "getFollowUpMessages": None,
        }

        stream = agent_loop(prompts, context, config, stream_fn=mock_stream_fn)

        # Consume the stream
        async for _ in stream:
            pass

        # Transform should have been called
        assert len(transform_called) > 0


class TestAgentLoopContinue:
    """Test agent_loop_continue function."""

    @pytest.mark.asyncio
    async def test_agent_loop_continue_basic(self):
        """Test basic agent loop continue."""
        context: AgentContext = {
            "systemPrompt": "System prompt",
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": "Previous message"}],
                    "timestamp": 12345,
                }
            ],
            "tools": [],
        }

        async def mock_stream_fn(model, ctx, options):
            from pi.agent import EventStream

            stream = EventStream(
                lambda e: e.get("type") in ("done", "error"),
                lambda e: e,
            )

            stream.push({
                "type": "done",
                "reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "Response"}],
                    "api": model["api"],
                    "provider": model["provider"],
                    "model": model["id"],
                    "usage": {
                        "input": 0,
                        "output": 0,
                        "cacheRead": 0,
                        "cacheWrite": 0,
                        "totalTokens": 0,
                        "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "total": 0},
                    },
                    "stopReason": "stop",
                    "timestamp": 12346,
                },
            })

            stream.end()
            return stream

        config: AgentLoopConfig = {
            "model": {"api": "test", "provider": "test", "id": "test-model"},
            "convertToLlm": lambda msgs: msgs,
            "transformContext": None,
            "getApiKey": None,
            "getSteeringMessages": None,
            "getFollowUpMessages": None,
        }

        stream = agent_loop_continue(context, config, stream_fn=mock_stream_fn)

        # Collect events
        events = []
        async for event in stream:
            events.append(event)

        # Should have started and ended
        assert events[0]["type"] == "agent_start"
        assert events[-1]["type"] == "agent_end"

    @pytest.mark.asyncio
    async def test_agent_loop_continue_empty_context_error(self):
        """Test that continue with empty context raises error."""
        context: AgentContext = {
            "systemPrompt": "",
            "messages": [],
            "tools": [],
        }

        config: AgentLoopConfig = {
            "model": {"api": "test", "provider": "test", "id": "test-model"},
            "convertToLlm": lambda msgs: msgs,
        }

        with pytest.raises(ValueError, match="Cannot continue: no messages in context"):
            agent_loop_continue(context, config)

    @pytest.mark.asyncio
    async def test_agent_loop_continue_from_assistant_error(self):
        """Test that continue from assistant message raises error."""
        context: AgentContext = {
            "systemPrompt": "",
            "messages": [
                {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "Hi"}],
                    "api": "test",
                    "provider": "test",
                    "model": "test-model",
                    "usage": {
                        "input": 0,
                        "output": 0,
                        "cacheRead": 0,
                        "cacheWrite": 0,
                        "totalTokens": 0,
                        "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "total": 0},
                    },
                    "stopReason": "stop",
                    "timestamp": 12346,
                }
            ],
            "tools": [],
        }

        config: AgentLoopConfig = {
            "model": {"api": "test", "provider": "test", "id": "test-model"},
            "convertToLlm": lambda msgs: msgs,
        }

        with pytest.raises(ValueError, match="Cannot continue from message role: assistant"):
            agent_loop_continue(context, config)


class TestConvertToLlm:
    """Test convertToLlm functionality."""

    def test_convert_to_llm_filters_messages(self):
        """Test that convertToLlm filters correctly."""
        from pi.agent import default_convert_to_llm

        messages = [
            {
                "role": "user",
                "content": [{"type": "text", "text": "Hello"}],
                "timestamp": 12345,
            },
            {
                "role": "custom_notification",
                "content": [{"type": "text", "text": "Notification"}],
                "timestamp": 12346,
            },
            {
                "role": "assistant",
                "content": [{"type": "text", "text": "Response"}],
                "timestamp": 12347,
            },
        ]

        result = default_convert_to_llm(messages)

        # Should filter out custom message
        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "assistant"


class TestSteeringAndFollowUp:
    """Test steering and follow-up message handling."""

    @pytest.mark.asyncio
    async def test_steering_messages_integration(self):
        """Test steering messages are processed."""
        prompts = [
            {
                "role": "user",
                "content": [{"type": "text", "text": "Start"}],
                "timestamp": 12345,
            }
        ]

        steering_queue = [
            {
                "role": "user",
                "content": [{"type": "text", "text": "Steer"}],
                "timestamp": 12346,
            }
        ]

        context: AgentContext = {
            "systemPrompt": "",
            "messages": [],
            "tools": [],
        }

        async def mock_stream_fn(model, ctx, options):
            from pi.agent import EventStream

            stream = EventStream(
                lambda e: e.get("type") in ("done", "error"),
                lambda e: e,
            )

            stream.push({
                "type": "done",
                "reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "OK"}],
                    "api": model["api"],
                    "provider": model["provider"],
                    "model": model["id"],
                    "usage": {
                        "input": 0,
                        "output": 0,
                        "cacheRead": 0,
                        "cacheWrite": 0,
                        "totalTokens": 0,
                        "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "total": 0},
                    },
                    "stopReason": "stop",
                    "timestamp": 12346,
                },
            })

            stream.end()
            return stream

        steering_index = [0]

        async def get_steering():
            if steering_index[0] < len(steering_queue):
                msg = steering_queue[steering_index[0]]
                steering_index[0] += 1
                return [msg]
            return []

        config: AgentLoopConfig = {
            "model": {"api": "test", "provider": "test", "id": "test-model"},
            "convertToLlm": lambda msgs: msgs,
            "getSteeringMessages": get_steering,
            "getFollowUpMessages": None,
        }

        stream = agent_loop(prompts, context, config, stream_fn=mock_stream_fn)

        # Consume stream
        events = []
        async for event in stream:
            events.append(event)

        # Should have processed steering message
        assert steering_index[0] > 0


class TestToolExecution:
    """Test tool execution in agent loop."""

    @pytest.mark.asyncio
    async def test_tool_execution_with_validation_error(self):
        """Test tool execution with validation errors."""
        class StrictTool(BaseTool):
            name = "strict_tool"
            description = "Tool with strict validation"

            def get_schema(self) -> ToolSchema:
                return ToolSchema(
                    properties={
                        "required_param": ParameterProperty(
                            type=ParameterType.STRING,
                            description="Required parameter",
                            required=True,
                        ),
                    },
                    required=["required_param"],
                )

            async def _execute(self, tool_call_id, params, signal, on_update):
                return {
                    "content": [{"type": "text", "text": "OK"}],
                    "details": params,
                }

        tool = StrictTool()

        # Test with valid params
        result = await tool.execute("call-1", {"required_param": "value"})
        assert result["details"]["required_param"] == "value"

        # Test with invalid params (missing required)
        result = await tool.execute("call-2", {})
        # Should return error result
        assert "error" in result["content"][0]["text"].lower()

    @pytest.mark.asyncio
    async def test_tool_execution_with_signal_abort(self):
        """Test tool execution with abort signal."""
        class SlowTool(BaseTool):
            name = "slow_tool"
            description = "Tool that takes time"

            def get_schema(self) -> ToolSchema:
                return ToolSchema(properties={}, required=[])

            async def _execute(self, tool_call_id, params, signal, on_update):
                # Simulate slow operation
                for i in range(10):
                    await asyncio.sleep(0.01)
                    if signal and signal.aborted:
                        raise RuntimeError("Aborted")

                    if on_update:
                        on_update({
                            "content": [{"type": "text", "text": f"Step {i}"}],
                            "details": {"progress": i / 10},
                        })

                return {
                    "content": [{"type": "text", "text": "Done"}],
                    "details": {},
                }

        tool = SlowTool()

        # Create abort signal
        class AbortSignal:
            def __init__(self):
                self.aborted = False

        signal = AbortSignal()

        # Abort after a short delay
        async def abort_after_delay():
            await asyncio.sleep(0.03)
            signal.aborted = True

        # Run tool and abort concurrently
        task = asyncio.create_task(tool.execute("call-1", {}, signal, lambda x: None))
        await asyncio.create_task(abort_after_delay())

        result = await task

        # Should have error due to abort
        assert "error" in result["details"] or "aborted" in result["content"][0]["text"].lower()
