"""
Tests for the pi.agent Agent class.
"""
import pytest
import asyncio
from pi.agent import (
    Agent,
    AgentOptions,
    ThinkingLevel,
    UserMessage,
    TextContent,
    ImageContent,
    AssistantMessage,
    CalculatorTool,
    EchoTool,
    NoOpTool,
    BaseTool,
    ToolSchema,
    ParameterType,
    ParameterProperty,
)


class TestAgentCreation:
    """Test Agent creation and initialization."""

    def test_agent_creation_with_default_state(self):
        """Test creating an agent with default state."""
        agent = Agent()
        assert agent.state["systemPrompt"] == ""
        assert agent.state["thinkingLevel"] == "off"
        assert agent.state["isStreaming"] is False
        assert agent.state["messages"] == []
        assert agent.state["pendingToolCalls"] == set()
        assert agent.state["error"] is None

    def test_agent_creation_with_initial_state(self, sample_model):
        """Test creating an agent with initial state."""
        agent = Agent(AgentOptions(
            initial_state={
                "systemPrompt": "You are a helpful assistant.",
                "model": sample_model,
                "thinkingLevel": "medium",
                "tools": [],
                "messages": [],
                "isStreaming": False,
                "streamMessage": None,
                "pendingToolCalls": set(),
                "error": None,
            }
        ))
        assert agent.state["systemPrompt"] == "You are a helpful assistant."
        assert agent.state["thinkingLevel"] == "medium"
        assert agent.state["model"]["id"] == "test-model"

    def test_agent_mode_options(self):
        """Test steering and follow-up mode options."""
        agent = Agent(AgentOptions(
            steering_mode="all",
            follow_up_mode="one-at-a-time",
        ))
        assert agent.get_steering_mode() == "all"
        assert agent.get_follow_up_mode() == "one-at-a-time"


class TestAgentStateManagement:
    """Test Agent state management methods."""

    def test_set_system_prompt(self, sample_agent):
        """Test setting system prompt."""
        sample_agent.set_system_prompt("New system prompt")
        assert sample_agent.state["systemPrompt"] == "New system prompt"

    def test_set_thinking_level(self, sample_agent):
        """Test setting thinking level."""
        sample_agent.set_thinking_level("high")
        assert sample_agent.state["thinkingLevel"] == "high"

    def test_set_model(self, sample_agent, sample_model):
        """Test setting model."""
        new_model = {
            "api": "openai",
            "provider": "openai",
            "id": "gpt-4",
        }
        sample_agent.set_model(new_model)
        assert sample_agent.state["model"]["id"] == "gpt-4"

    def test_set_tools(self, sample_agent):
        """Test setting tools."""
        tools = [CalculatorTool(), EchoTool()]
        sample_agent.set_tools(tools)
        assert len(sample_agent.state["tools"]) == 2
        assert sample_agent.state["tools"][0].name == "calculator"

    def test_replace_messages(self, sample_agent):
        """Test replacing all messages."""
        messages = [
            {
                "role": "user",
                "content": [{"type": "text", "text": "Hello"}],
                "timestamp": 12345,
            },
            {
                "role": "assistant",
                "content": [{"type": "text", "text": "Hi there!"}],
                "timestamp": 12346,
            },
        ]
        sample_agent.replace_messages(messages)
        assert len(sample_agent.state["messages"]) == 2
        assert sample_agent.state["messages"][0]["role"] == "user"

    def test_append_message(self, sample_agent, sample_user_message):
        """Test appending a single message."""
        sample_agent.append_message(sample_user_message)
        assert len(sample_agent.state["messages"]) == 1
        assert sample_agent.state["messages"][0]["role"] == "user"

    def test_clear_messages(self, sample_agent, sample_user_message):
        """Test clearing all messages."""
        sample_agent.append_message(sample_user_message)
        sample_agent.clear_messages()
        assert len(sample_agent.state["messages"]) == 0


class TestAgentQueues:
    """Test Agent steering and follow-up queue management."""

    def test_steer_queue(self, sample_agent, sample_user_message):
        """Test steering queue."""
        sample_agent.steer(sample_user_message)
        assert sample_agent.has_queued_messages() is True

        messages = sample_agent._dequeue_steering_messages()
        assert len(messages) == 1
        assert sample_agent.has_queued_messages() is False

    def test_follow_up_queue(self, sample_agent, sample_user_message):
        """Test follow-up queue."""
        sample_agent.follow_up(sample_user_message)
        assert sample_agent.has_queued_messages() is True

        messages = sample_agent._dequeue_follow_up_messages()
        assert len(messages) == 1

    def test_one_at_a_time_mode(self, sample_agent):
        """Test one-at-a-time queue mode."""
        sample_agent.set_steering_mode("one-at-a-time")

        msg1 = {
            "role": "user",
            "content": [{"type": "text", "text": "First"}],
            "timestamp": 1,
        }
        msg2 = {
            "role": "user",
            "content": [{"type": "text", "text": "Second"}],
            "timestamp": 2,
        }
        msg3 = {
            "role": "user",
            "content": [{"type": "text", "text": "Third"}],
            "timestamp": 3,
        }

        sample_agent.steer(msg1)
        sample_agent.steer(msg2)
        sample_agent.steer(msg3)

        # Should get only one message at a time
        messages = sample_agent._dequeue_steering_messages()
        assert len(messages) == 1
        assert messages[0]["content"][0]["text"] == "First"

        # Get the next one
        messages = sample_agent._dequeue_steering_messages()
        assert len(messages) == 1
        assert messages[0]["content"][0]["text"] == "Second"

    def test_all_mode(self, sample_agent):
        """Test 'all' queue mode."""
        sample_agent.set_steering_mode("all")

        msg1 = {
            "role": "user",
            "content": [{"type": "text", "text": "First"}],
            "timestamp": 1,
        }
        msg2 = {
            "role": "user",
            "content": [{"type": "text", "text": "Second"}],
            "timestamp": 2,
        }

        sample_agent.steer(msg1)
        sample_agent.steer(msg2)

        # Should get all messages at once
        messages = sample_agent._dequeue_steering_messages()
        assert len(messages) == 2

    def test_clear_queues(self, sample_agent, sample_user_message):
        """Test clearing all queues."""
        sample_agent.steer(sample_user_message)
        sample_agent.follow_up(sample_user_message)
        assert sample_agent.has_queued_messages() is True

        sample_agent.clear_all_queues()
        assert sample_agent.has_queued_messages() is False


class TestAgentProperties:
    """Test Agent property getters and setters."""

    def test_session_id(self, sample_agent):
        """Test session ID property."""
        assert sample_agent.session_id is None
        sample_agent.session_id = "test-session-123"
        assert sample_agent.session_id == "test-session-123"

    def test_thinking_budgets(self, sample_agent):
        """Test thinking budgets property."""
        assert sample_agent.thinking_budgets is None
        budgets = {
            "minimal": 1000,
            "low": 5000,
            "medium": 10000,
            "high": 50000,
            "xhigh": 100000,
        }
        sample_agent.thinking_budgets = budgets
        assert sample_agent.thinking_budgets == budgets

    def test_transport(self, sample_agent):
        """Test transport property."""
        assert sample_agent.transport == "sse"
        sample_agent.set_transport("sse")
        assert sample_agent.transport == "sse"

    def test_max_retry_delay_ms(self, sample_agent):
        """Test max retry delay property."""
        assert sample_agent.max_retry_delay_ms is None
        sample_agent.max_retry_delay_ms = 60000
        assert sample_agent.max_retry_delay_ms == 60000


class TestAgentEventSubscription:
    """Test Agent event subscription system."""

    def test_subscribe_and_unsubscribe(self, sample_agent):
        """Test subscribing to and unsubscribing from events."""
        events = []

        def listener(event):
            events.append(event)

        unsubscribe = sample_agent.subscribe(listener)

        # Emit a test event
        sample_agent._emit({"type": "test_event"})
        assert len(events) == 1

        # Unsubscribe and emit again
        unsubscribe()
        sample_agent._emit({"type": "test_event_2"})
        assert len(events) == 1  # Should not have increased

    def test_multiple_listeners(self, sample_agent):
        """Test multiple event listeners."""
        events1 = []
        events2 = []

        def listener1(event):
            events1.append(event)

        def listener2(event):
            events2.append(event)

        sample_agent.subscribe(listener1)
        sample_agent.subscribe(listener2)

        sample_agent._emit({"type": "test_event"})
        assert len(events1) == 1
        assert len(events2) == 1


class TestAgentReset:
    """Test Agent reset functionality."""

    def test_reset(self, sample_agent, sample_user_message):
        """Test resetting agent state."""
        # Add some state
        sample_agent.append_message(sample_user_message)
        sample_agent.steer(sample_user_message)
        sample_agent.state["error"] = "Test error"
        sample_agent.state["isStreaming"] = True
        sample_agent.state["pendingToolCalls"].add("tool-1")

        # Reset
        sample_agent.reset()

        # Check state is cleared
        assert len(sample_agent.state["messages"]) == 0
        assert sample_agent.state["isStreaming"] is False
        assert sample_agent.state["streamMessage"] is None
        assert len(sample_agent.state["pendingToolCalls"]) == 0
        assert sample_agent.state["error"] is None
        assert sample_agent.has_queued_messages() is False


class TestAgentAbort:
    """Test Agent abort functionality."""

    def test_abort(self, sample_agent):
        """Test aborting current operation."""
        # Should not raise any errors
        sample_agent.abort()


class TestAgentWaitForIdle:
    """Test Agent wait for idle functionality."""

    @pytest.mark.asyncio
    async def test_wait_for_idle_when_not_running(self, sample_agent):
        """Test waiting for idle when agent is not running."""
        # Should complete immediately
        await sample_agent.wait_for_idle()


class TestConvertToLlm:
    """Test convertToLlm functionality."""

    def test_default_convert_to_llm(self):
        """Test default convertToLlm function."""
        from pi.agent import default_convert_to_llm

        messages = [
            {
                "role": "user",
                "content": [{"type": "text", "text": "Hello"}],
                "timestamp": 12345,
            },
            {
                "role": "assistant",
                "content": [{"type": "text", "text": "Hi"}],
                "timestamp": 12346,
            },
            {
                "role": "custom",
                "content": [{"type": "text", "text": "Custom message"}],
                "timestamp": 12347,
            },
        ]

        result = default_convert_to_llm(messages)
        # Should filter out custom messages
        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "assistant"


class TestCustomToolIntegration:
    """Test integrating custom tools with Agent."""

    @pytest.mark.asyncio
    async def test_agent_with_custom_tool(self, sample_agent):
        """Test agent with a custom tool."""

        class UppercaseTool(BaseTool):
            name = "uppercase"
            description = "Convert text to uppercase"

            def get_schema(self) -> ToolSchema:
                return ToolSchema(
                    properties={
                        "text": ParameterProperty(
                            type=ParameterType.STRING,
                            description="Text to convert",
                            required=True,
                        ),
                    },
                    required=["text"],
                )

            async def _execute(self, tool_call_id, params, signal, on_update):
                text = params["text"]
                return {
                    "content": [{"type": "text", "text": text.upper()}],
                    "details": {"original": text, "uppercase": text.upper()},
                }

        tool = UppercaseTool()
        sample_agent.set_tools([tool])

        result = await tool.execute("call-1", {"text": "hello"})
        assert result["content"][0]["text"] == "HELLO"
        assert result["details"]["uppercase"] == "HELLO"


class TestErrorHandling:
    """Test Agent error handling."""

    def test_error_state(self, sample_agent):
        """Test error state management."""
        assert sample_agent.state["error"] is None

        # Simulate setting an error
        sample_agent.state["error"] = "Test error"
        assert sample_agent.state["error"] == "Test error"

    @pytest.mark.asyncio
    async def test_tool_error_handling(self):
        """Test error handling in tool execution."""

        class ErrorTool(BaseTool):
            name = "error_tool"
            description = "Tool that raises errors"

            def get_schema(self) -> ToolSchema:
                return ToolSchema(properties={}, required=[])

            async def _execute(self, tool_call_id, params, signal, on_update):
                raise ValueError("Intentional error")

        tool = ErrorTool()
        result = await tool.execute("call-1", {})

        # Tool should return error as result, not raise
        assert "error" in result["details"]
        assert result["details"]["error_type"] == "ValueError"
