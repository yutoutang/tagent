"""Event bus for pi-coding.

Converted from TypeScript core/event-bus.ts
"""
from typing import Any, Callable, TypeVar, Generic
from dataclasses import dataclass
from collections import defaultdict


T = TypeVar("T")


@dataclass
class Event:
    """Base event class."""
    type: str


class EventBus:
    """Simple event bus for pub/sub messaging."""

    def __init__(self):
        """Initialize the event bus."""
        self._listeners: dict[str, list[Callable]] = defaultdict(list)

    def on(self, event_type: str, callback: Callable) -> Callable[[], None]:
        """
        Subscribe to events of a given type.

        Args:
            event_type: Type of event to listen for
            callback: Function to call when event is emitted

        Returns:
            Unsubscribe function
        """
        self._listeners[event_type].append(callback)

        def unsubscribe():
            if callback in self._listeners[event_type]:
                self._listeners[event_type].remove(callback)

        return unsubscribe

    def emit(self, event: Event) -> None:
        """
        Emit an event to all listeners.

        Args:
            event: Event to emit
        """
        for callback in self._listeners.get(event.type, []):
            try:
                callback(event)
            except Exception:
                # Log but don't propagate to avoid breaking other listeners
                pass

    def clear(self) -> None:
        """Clear all event listeners."""
        self._listeners.clear()


__all__ = ["Event", "EventBus"]
