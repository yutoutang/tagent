"""
Extension runner for executing extension lifecycle hooks.

Converted from TypeScript core/extensions/runner.ts
"""
from typing import Any, Callable, Optional, List, Dict

from .types import (
    Extension,
    ExtensionEvent,
    ExtensionHandler,
    ExtensionErrorListener,
)


class ExtensionRunner:
    """
    Runs extension lifecycle hooks and manages event distribution.
    """

    def __init__(self, extensions: List[Extension]):
        """
        Initialize the extension runner.

        Args:
            extensions: List of loaded extensions
        """
        self.extensions = extensions
        self._listeners: Dict[str, List[ExtensionHandler]] = {}
        self._error_listeners: List[ExtensionErrorListener] = []

    def on(self, event_type: str, handler: ExtensionHandler) -> Callable[[], None]:
        """
        Subscribe to an event type.

        Args:
            event_type: Type of event to listen for
            handler: Handler function

        Returns:
            Unsubscribe function
        """
        if event_type not in self._listeners:
            self._listeners[event_type] = []

        self._listeners[event_type].append(handler)

        def unsubscribe():
            if handler in self._listeners.get(event_type, []):
                self._listeners[event_type].remove(handler)

        return unsubscribe

    def on_error(self, listener: ExtensionErrorListener) -> Callable[[], None]:
        """
        Subscribe to extension errors.

        Args:
            listener: Error listener function

        Returns:
            Unsubscribe function
        """
        self._error_listeners.append(listener)

        def unsubscribe():
            if listener in self._error_listeners:
                self._error_listeners.remove(listener)

        return unsubscribe

    def emit(self, event: ExtensionEvent) -> None:
        """
        Emit an event to all listeners.

        Args:
            event: Event to emit
        """
        event_type = event.type
        handlers = self._listeners.get(event_type, [])

        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                for error_listener in self._error_listeners:
                    try:
                        error_listener(event.extension_name or "unknown", e)
                    except Exception:
                        pass

    async def emit_context(self, messages: List[Any]) -> List[Any]:
        """
        Emit context transformation event.

        Args:
            messages: Current message list

        Returns:
            Transformed message list
        """
        # For now, just return the messages unchanged
        # Extensions can modify this in the future
        return messages

    async def on_session_start(self, session_info: Dict[str, Any]) -> None:
        """
        Called when a session starts.

        Args:
            session_info: Information about the session
        """
        self.emit(ExtensionEvent(
            type="session_start",
            extension_name=None,
        ))

    async def on_session_end(self, session_info: Dict[str, Any]) -> None:
        """
        Called when a session ends.

        Args:
            session_info: Information about the session
        """
        self.emit(ExtensionEvent(
            type="session_end",
            extension_name=None,
        ))

    async def on_tool_call(self, tool_name: str, arguments: Dict[str, Any], tool_call_id: str) -> None:
        """
        Called when a tool is invoked.

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments
            tool_call_id: Unique tool call ID
        """
        from .types import ToolCallEvent
        self.emit(ToolCallEvent(
            type="tool_call",
            tool_name=tool_name,
            arguments=arguments,
            tool_call_id=tool_call_id,
        ))

    async def on_tool_result(
        self,
        tool_name: str,
        result: Any,
        tool_call_id: str,
        is_error: bool = False,
    ) -> None:
        """
        Called when a tool returns a result.

        Args:
            tool_name: Name of the tool
            result: Tool result
            tool_call_id: Unique tool call ID
            is_error: Whether the result is an error
        """
        from .types import ToolResultEvent
        self.emit(ToolResultEvent(
            type="tool_result",
            tool_name=tool_name,
            result=result,
            tool_call_id=tool_call_id,
            is_error=is_error,
        ))

    def dispose(self) -> None:
        """Dispose of all extensions."""
        for ext in self.extensions:
            if ext.dispose:
                try:
                    ext.dispose()
                except Exception:
                    pass

        self._listeners.clear()
        self._error_listeners.clear()


__all__ = ["ExtensionRunner"]
