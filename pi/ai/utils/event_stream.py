"""
Generic event stream class for async iteration.
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Callable, Generic, List, Optional, TypeVar

from ..types import AssistantMessage, AssistantMessageEvent

T = TypeVar("T")
R = TypeVar("R")


class EventStream(Generic[T, R]):
    """Generic event stream class for async iteration."""

    def __init__(
        self,
        is_complete: Callable[[T], bool],
        extract_result: Callable[[T], R],
    ):
        self._queue: List[T] = []
        self._waiting: List[asyncio.Future] = []
        self._done = False
        self._is_complete = is_complete
        self._extract_result = extract_result
        self._final_result: Optional[R] = None
        self._final_result_future: asyncio.Future[R] = asyncio.get_event_loop().create_future()

    def push(self, event: T) -> None:
        """Push an event to the stream."""
        if self._done:
            return

        if self._is_complete(event):
            self._done = True
            self._final_result = self._extract_result(event)
            if not self._final_result_future.done():
                self._final_result_future.set_result(self._final_result)

        # Deliver to waiting consumer or queue it
        if self._waiting:
            future = self._waiting.pop(0)
            future.set_result((event, False))
        else:
            self._queue.append(event)

    def end(self, result: Optional[R] = None) -> None:
        """End the stream."""
        self._done = True
        if result is not None and not self._final_result_future.done():
            self._final_result_future.set_result(result)
        # Notify all waiting consumers that we're done
        for future in self._waiting:
            future.set_result((None, True))
        self._waiting.clear()

    async def __aiter__(self) -> AsyncIterator[T]:
        """Async iterator for the stream."""
        while True:
            if self._queue:
                yield self._queue.pop(0)
            elif self._done:
                return
            else:
                future: asyncio.Future = asyncio.get_event_loop().create_future()
                self._waiting.append(future)
                try:
                    event, done = await future
                    if done:
                        return
                    yield event
                finally:
                    if future in self._waiting:
                        self._waiting.remove(future)

    async def result(self) -> R:
        """Get the final result of the stream."""
        return await self._final_result_future


class AssistantMessageEventStream(EventStream[AssistantMessageEvent, AssistantMessage]):
    """Event stream for assistant messages."""

    def __init__(self):
        def is_complete(event: AssistantMessageEvent) -> bool:
            # Handle both dict and dataclass events
            if isinstance(event, dict):
                return event.get("type") in ("done", "error")
            return hasattr(event, "type") and event.type in ("done", "error")

        def extract_result(event: AssistantMessageEvent) -> AssistantMessage:
            # Handle both dict and dataclass events
            if isinstance(event, dict):
                if event.get("type") == "done":
                    return event.get("message")
                elif event.get("type") == "error":
                    return event.get("error")
            else:
                if hasattr(event, "type") and event.type == "done":
                    return event.message
                elif hasattr(event, "type") and event.type == "error":
                    return event.error
            raise ValueError("Unexpected event type for final result")

        super().__init__(is_complete, extract_result)


def create_assistant_message_event_stream() -> AssistantMessageEventStream:
    """Factory function for AssistantMessageEventStream (for use in extensions)."""
    return AssistantMessageEventStream()
