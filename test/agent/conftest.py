"""
Pytest configuration and shared fixtures for pi.agent tests.
"""
import pytest
import asyncio
from typing import Any

from pi.agent import (
    Agent,
    AgentOptions,
    UserMessage,
    TextContent,
    Model,
)


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_model() -> Model:
    """Sample model for testing."""
    return {
        "api": "test",
        "provider": "test_provider",
        "id": "test-model",
    }


@pytest.fixture
def sample_agent(sample_model: Model) -> Agent:
    """Sample agent for testing."""
    return Agent(AgentOptions(
        initial_state={
            "systemPrompt": "You are a helpful assistant.",
            "model": sample_model,
            "thinkingLevel": "off",
            "tools": [],
            "messages": [],
            "isStreaming": False,
            "streamMessage": None,
            "pendingToolCalls": set(),
            "error": None,
        }
    ))


@pytest.fixture
def sample_user_message() -> UserMessage:
    """Sample user message for testing."""
    return {
        "role": "user",
        "content": [{"type": "text", "text": "Hello, agent!"}],
        "timestamp": 1234567890,
    }


class MockStream:
    """Mock stream for testing."""

    def __init__(self, events: list[dict] | None = None):
        self.events = events or []
        self.index = 0
        self._finished = False
        self._result = None

    def push(self, event: dict):
        """Push an event to the stream."""
        self.events.append(event)

    def end(self, result: Any = None):
        """End the stream with a result."""
        self._finished = True
        self._result = result

    def __aiter__(self):
        return self

    async def __anext__(self):
        """Iterate over events."""
        if self.index < len(self.events):
            event = self.events[self.index]
            self.index += 1
            return event
        raise StopAsyncIteration

    async def result(self):
        """Get the final result."""
        while not self._finished:
            await asyncio.sleep(0.01)
        return self._result


@pytest.fixture
def mock_stream():
    """Mock stream fixture."""
    return MockStream


class AbortSignal:
    """Mock abort signal for testing."""

    def __init__(self):
        self.aborted = False

    def abort(self):
        """Abort the signal."""
        self.aborted = True


@pytest.fixture
def abort_signal():
    """Abort signal fixture."""
    return AbortSignal
