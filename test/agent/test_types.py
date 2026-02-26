"""
Tests for pi.agent type definitions and validation.
"""
import pytest
from pi.agent import (
    # Content types
    TextContent,
    ImageContent,
    ThinkingContent,
    ToolCall,
    ContentBlock,
    # Message types
    Usage,
    Cost,
    UserMessage,
    AssistantMessage,
    ToolResultMessage,
    Message,
    # Model types
    Model,
    ThinkingBudgets,
    # Agent types
    ThinkingLevel,
    AgentMessage,
    AgentState,
    AgentContext,
    # Event types
    AgentEvent,
    AgentStartEvent,
    AgentEndEvent,
    TurnStartEvent,
    TurnEndEvent,
    MessageStartEvent,
    MessageUpdateEvent,
    MessageEndEvent,
    ToolExecutionStartEvent,
    ToolExecutionUpdateEvent,
    ToolExecutionEndEvent,
)


class TestContentTypes:
    """Test content type definitions."""

    def test_text_content(self):
        """Test TextContent structure."""
        content: TextContent = {
            "type": "text",
            "text": "Hello, world!",
        }
        assert content["type"] == "text"
        assert content["text"] == "Hello, world!"

    def test_text_content_with_signature(self):
        """Test TextContent with optional signature."""
        content: TextContent = {
            "type": "text",
            "text": "Signed text",
            "textSignature": "sig123",
        }
        assert content["textSignature"] == "sig123"

    def test_image_content(self):
        """Test ImageContent structure."""
        content: ImageContent = {
            "type": "image",
            "image": "data:image/png;base64,iVBORw0KG...",
        }
        assert content["type"] == "image"
        assert content["image"].startswith("data:image/png")

    def test_image_content_with_mime_type(self):
        """Test ImageContent with MIME type."""
        content: ImageContent = {
            "type": "image",
            "image": "base64data",
            "mimeType": "image/jpeg",
        }
        assert content["mimeType"] == "image/jpeg"

    def test_thinking_content(self):
        """Test ThinkingContent structure."""
        content: ThinkingContent = {
            "type": "thinking",
            "thinking": "Let me think about this...",
        }
        assert content["type"] == "thinking"
        assert content["thinking"] == "Let me think about this..."

    def test_thinking_content_with_signature(self):
        """Test ThinkingContent with optional signature."""
        content: ThinkingContent = {
            "type": "thinking",
            "thinking": "Thinking process",
            "thinkingSignature": "think_sig",
        }
        assert content["thinkingSignature"] == "think_sig"

    def test_tool_call(self):
        """Test ToolCall structure."""
        tool_call: ToolCall = {
            "type": "toolCall",
            "id": "call_123",
            "name": "calculator",
            "arguments": {"operation": "add", "a": 5, "b": 3},
        }
        assert tool_call["type"] == "toolCall"
        assert tool_call["id"] == "call_123"
        assert tool_call["name"] == "calculator"
        assert tool_call["arguments"]["operation"] == "add"


class TestMessageTypes:
    """Test message type definitions."""

    def test_user_message(self):
        """Test UserMessage structure."""
        message: UserMessage = {
            "role": "user",
            "content": [
                {"type": "text", "text": "Hello!"},
            ],
            "timestamp": 1234567890,
        }
        assert message["role"] == "user"
        assert len(message["content"]) == 1
        assert message["timestamp"] == 1234567890

    def test_user_message_with_multiple_content(self):
        """Test UserMessage with multiple content blocks."""
        message: UserMessage = {
            "role": "user",
            "content": [
                {"type": "text", "text": "Check this image:"},
                {"type": "image", "image": "base64imagedata"},
            ],
            "timestamp": 1234567890,
        }
        assert len(message["content"]) == 2
        assert message["content"][0]["type"] == "text"
        assert message["content"][1]["type"] == "image"

    def test_assistant_message(self):
        """Test AssistantMessage structure."""
        message: AssistantMessage = {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "Hi there!"},
            ],
            "api": "openai",
            "provider": "openai",
            "model": "gpt-4",
            "usage": {
                "input": 10,
                "output": 20,
                "cacheRead": 0,
                "cacheWrite": 0,
                "totalTokens": 30,
                "cost": {"input": 0.001, "output": 0.002, "cacheRead": 0, "cacheWrite": 0, "total": 0.003},
            },
            "stopReason": "stop",
            "timestamp": 1234567890,
        }
        assert message["role"] == "assistant"
        assert message["model"] == "gpt-4"
        assert message["stopReason"] == "stop"
        assert message["usage"]["totalTokens"] == 30

    def test_assistant_message_with_error(self):
        """Test AssistantMessage with error."""
        message: AssistantMessage = {
            "role": "assistant",
            "content": [],
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
            "stopReason": "error",
            "errorMessage": "Something went wrong",
            "timestamp": 1234567890,
        }
        assert message["stopReason"] == "error"
        assert message["errorMessage"] == "Something went wrong"

    def test_tool_result_message(self):
        """Test ToolResultMessage structure."""
        message: ToolResultMessage = {
            "role": "toolResult",
            "toolCallId": "call_123",
            "toolName": "calculator",
            "content": [
                {"type": "text", "text": "Result: 8"},
            ],
            "details": {"operation": "add", "operands": [5, 3], "result": 8},
            "isError": False,
            "timestamp": 1234567890,
        }
        assert message["role"] == "toolResult"
        assert message["toolCallId"] == "call_123"
        assert message["isError"] is False
        assert message["details"]["result"] == 8

    def test_tool_result_message_with_error(self):
        """Test ToolResultMessage with error."""
        message: ToolResultMessage = {
            "role": "toolResult",
            "toolCallId": "call_456",
            "toolName": "failing_tool",
            "content": [
                {"type": "text", "text": "Error: Division by zero"},
            ],
            "details": {},
            "isError": True,
            "timestamp": 1234567890,
        }
        assert message["isError"] is True


class TestModelTypes:
    """Test model-related type definitions."""

    def test_model(self):
        """Test Model structure."""
        model: Model = {
            "api": "anthropic",
            "provider": "anthropic",
            "id": "claude-3-opus-20240229",
        }
        assert model["api"] == "anthropic"
        assert model["provider"] == "anthropic"
        assert model["id"] == "claude-3-opus-20240229"

    def test_thinking_budgets(self):
        """Test ThinkingBudgets structure."""
        budgets: ThinkingBudgets = {
            "minimal": 1000,
            "low": 5000,
            "medium": 10000,
            "high": 50000,
            "xhigh": 100000,
        }
        assert budgets["minimal"] == 1000
        assert budgets["xhigh"] == 100000


class TestAgentTypes:
    """Test agent-related type definitions."""

    def test_thinking_level_values(self):
        """Test ThinkingLevel literal values."""
        levels: list[ThinkingLevel] = ["off", "minimal", "low", "medium", "high", "xhigh"]
        assert "off" in levels
        assert "xhigh" in levels

    def test_agent_state(self):
        """Test AgentState structure."""
        state: AgentState = {
            "systemPrompt": "You are a helpful assistant.",
            "model": {
                "api": "test",
                "provider": "test_provider",
                "id": "test-model",
            },
            "thinkingLevel": "medium",
            "tools": [],
            "messages": [],
            "isStreaming": False,
            "streamMessage": None,
            "pendingToolCalls": set(),
            "error": None,
        }
        assert state["systemPrompt"] == "You are a helpful assistant."
        assert state["thinkingLevel"] == "medium"
        assert state["isStreaming"] is False

    def test_agent_context(self):
        """Test AgentContext structure."""
        context: AgentContext = {
            "systemPrompt": "System prompt",
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": "Hello"}],
                    "timestamp": 12345,
                },
            ],
            "tools": None,
        }
        assert len(context["messages"]) == 1
        assert context["tools"] is None


class TestEventTypes:
    """Test event type definitions."""

    def test_agent_start_event(self):
        """Test AgentStartEvent structure."""
        event: AgentStartEvent = {"type": "agent_start"}
        assert event["type"] == "agent_start"

    def test_agent_end_event(self):
        """Test AgentEndEvent structure."""
        event: AgentEndEvent = {
            "type": "agent_end",
            "messages": [
                {"role": "user", "content": [], "timestamp": 12345},
            ],
        }
        assert event["type"] == "agent_end"
        assert len(event["messages"]) == 1

    def test_turn_start_event(self):
        """Test TurnStartEvent structure."""
        event: TurnStartEvent = {"type": "turn_start"}
        assert event["type"] == "turn_start"

    def test_turn_end_event(self):
        """Test TurnEndEvent structure."""
        event: TurnEndEvent = {
            "type": "turn_end",
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "Response"}],
                "timestamp": 12345,
            },
            "toolResults": [],
        }
        assert event["type"] == "turn_end"
        assert len(event["toolResults"]) == 0

    def test_message_start_event(self):
        """Test MessageStartEvent structure."""
        event: MessageStartEvent = {
            "type": "message_start",
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": "Hello"}],
                "timestamp": 12345,
            },
        }
        assert event["type"] == "message_start"

    def test_message_update_event(self):
        """Test MessageUpdateEvent structure."""
        event: MessageUpdateEvent = {
            "type": "message_update",
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "Partial"}],
                "timestamp": 12345,
            },
            "assistantMessageEvent": {
                "type": "text_delta",
                "delta": " content",
            },
        }
        assert event["type"] == "message_update"
        assert event["assistantMessageEvent"]["type"] == "text_delta"

    def test_message_end_event(self):
        """Test MessageEndEvent structure."""
        event: MessageEndEvent = {
            "type": "message_end",
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "Complete"}],
                "timestamp": 12345,
            },
        }
        assert event["type"] == "message_end"

    def test_tool_execution_start_event(self):
        """Test ToolExecutionStartEvent structure."""
        event: ToolExecutionStartEvent = {
            "type": "tool_execution_start",
            "toolCallId": "call_123",
            "toolName": "calculator",
            "args": {"operation": "add", "a": 5, "b": 3},
        }
        assert event["type"] == "tool_execution_start"
        assert event["toolCallId"] == "call_123"

    def test_tool_execution_update_event(self):
        """Test ToolExecutionUpdateEvent structure."""
        event: ToolExecutionUpdateEvent = {
            "type": "tool_execution_update",
            "toolCallId": "call_123",
            "toolName": "progress_tool",
            "args": {"steps": 5},
            "partialResult": {
                "content": [{"type": "text", "text": "Step 1/5"}],
                "details": {"progress": 0.2},
            },
        }
        assert event["type"] == "tool_execution_update"
        assert event["partialResult"]["details"]["progress"] == 0.2

    def test_tool_execution_end_event(self):
        """Test ToolExecutionEndEvent structure."""
        event: ToolExecutionEndEvent = {
            "type": "tool_execution_end",
            "toolCallId": "call_123",
            "toolName": "calculator",
            "result": {
                "content": [{"type": "text", "text": "Result: 8"}],
                "details": {"result": 8},
            },
            "isError": False,
        }
        assert event["type"] == "tool_execution_end"
        assert event["isError"] is False


class TestStopReasons:
    """Test stop reason values."""

    def test_stop_reason_values(self):
        """Test valid stop reason values."""
        valid_reasons = ["stop", "length", "toolUse", "aborted", "error"]
        assert "stop" in valid_reasons
        assert "error" in valid_reasons
        assert "aborted" in valid_reasons


class TestComplexMessages:
    """Test complex message structures."""

    def test_message_with_thinking(self):
        """Test message with thinking content."""
        message: AssistantMessage = {
            "role": "assistant",
            "content": [
                {
                    "type": "thinking",
                    "thinking": "Let me analyze this step by step...",
                },
                {
                    "type": "text",
                    "text": "Based on my analysis...",
                },
            ],
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
            "timestamp": 12345,
        }
        assert len(message["content"]) == 2
        assert message["content"][0]["type"] == "thinking"
        assert message["content"][1]["type"] == "text"

    def test_message_with_tool_calls(self):
        """Test message with tool calls."""
        message: AssistantMessage = {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "I'll calculate that for you."},
                {
                    "type": "toolCall",
                    "id": "call_1",
                    "name": "calculator",
                    "arguments": {"operation": "add", "a": 5, "b": 3},
                },
            ],
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
            "stopReason": "toolUse",
            "timestamp": 12345,
        }
        assert len(message["content"]) == 2
        assert message["content"][1]["type"] == "toolCall"
        assert message["stopReason"] == "toolUse"
