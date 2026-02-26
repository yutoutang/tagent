"""
Event stream implementation for async agent events.
"""
from typing import TypeVar, Generic, Callable, Awaitable, Any
from asyncio import Queue, QueueEmpty
import asyncio


TEvent = TypeVar("TEvent")
TResult = TypeVar("TResult")


class EventStream(Generic[TEvent, TResult]):
    """
    Async event stream that collects events and produces a final result.
    """

    def __init__(
        self,
        is_done: Callable[[TEvent], bool],
        get_result: Callable[[TEvent], TResult],
    ):
        self._queue: Queue[TEvent] = Queue()
        self._is_done = is_done
        self._get_result = get_result
        self._finished = False
        self._result: TResult | None = None

    def push(self, event: TEvent) -> None:
        """Push an event to the stream."""
        self._queue.put_nowait(event)

    def end(self, result: TResult) -> None:
        """Mark the stream as finished with a result."""
        self._finished = True
        self._result = result

    def __aiter__(self):
        return self

    async def __anext__(self) -> TEvent:
        """Iterate over events until the stream is finished."""
        while True:
            # Check if we have events in the queue
            try:
                event = self._queue.get_nowait()
                # Return the event first, then check if done
                # This allows the done event to be consumed by the iterator
                return event
            except QueueEmpty:
                pass

            # Check if stream is finished
            if self._finished:
                raise StopAsyncIteration

            # Wait a bit for new events
            await asyncio.sleep(0.01)

    async def result(self) -> TResult:
        """Get the final result of the stream."""
        while not self._finished:
            await asyncio.sleep(0.01)
        if self._result is None:
            raise RuntimeError("Stream finished without result")
        return self._result
