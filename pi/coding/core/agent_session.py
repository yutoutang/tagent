"""
Agent session for pi-coding.

Wraps pi.agent.Agent with session management.
"""
from typing import Any, Optional
from pathlib import Path
from dataclasses import dataclass

from pi.agent import Agent, AgentOptions
from pi.agent.types import AgentMessage, ThinkingLevel
from .session_manager import SessionManager
from ..tools import get_builtin_tools


@dataclass
class SessionConfig:
    """Configuration for an agent session."""
    model: dict[str, Any]
    thinking_level: ThinkingLevel = "medium"
    tools: Optional[list[Any]] = None
    system_prompt: Optional[str] = None
    cwd: Optional[str | Path] = None


class AgentSession:
    """
    Manages an agent session with persistence.

    Combines pi.agent.Agent with SessionManager for
    persistent agent conversations.
    """

    def __init__(
        self,
        agent: Agent,
        session_manager: SessionManager,
        settings_manager: Optional[Any] = None,  # SettingsManager
        cwd: Optional[str | Path] = None,
        scoped_models: Optional[list[dict[str, Any]]] = None,
        resource_loader: Optional[Any] = None,
        custom_tools: Optional[list[Any]] = None,
        model_registry: Optional[Any] = None,
        initial_active_tool_names: Optional[list[str]] = None,
    ):
        """
        Initialize the agent session.

        Args:
            agent: The Agent instance
            session_manager: SessionManager for persistence
            settings_manager: Optional SettingsManager
            cwd: Working directory
            scoped_models: Models available for cycling
            resource_loader: ResourceLoader for extensions
            custom_tools: Custom tools to register
            model_registry: ModelRegistry instance
            initial_active_tool_names: Initially active tool names
        """
        self.agent = agent
        self.session_manager = session_manager
        self.settings_manager = settings_manager
        self.cwd = Path(cwd) if cwd else Path.cwd()
        self.scoped_models = scoped_models or []
        self.resource_loader = resource_loader
        self.custom_tools = custom_tools or []
        self.model_registry = model_registry
        self.initial_active_tool_names = initial_active_tool_names or [
            "read", "bash", "edit", "write"
        ]

    @property
    def state(self) -> dict[str, Any]:
        """Get the agent's current state."""
        return self.agent.state

    def subscribe(self, callback) -> Any:
        """Subscribe to agent events."""
        return self.agent.subscribe(callback)

    async def prompt(
        self,
        input: str | AgentMessage | list[AgentMessage],
    ) -> None:
        """
        Send a prompt to the agent.

        Args:
            input: Prompt text, message, or list of messages
        """
        await self.agent.prompt(input)

    async def continue_(self) -> None:
        """Continue from current context (used for retries)."""
        await self.agent.continue_()

    def abort(self) -> None:
        """Abort the current operation."""
        self.agent.abort()

    async def wait_for_idle(self) -> None:
        """Wait for the agent to finish processing."""
        await self.agent.wait_for_idle()

    def reset(self) -> None:
        """Reset the agent state."""
        self.agent.reset()

    # State mutators (delegated to agent)

    def set_system_prompt(self, prompt: str) -> None:
        """Set the system prompt."""
        self.agent.set_system_prompt(prompt)

    def set_model(self, model: dict[str, Any]) -> None:
        """Set the model."""
        self.agent.set_model(model)

    def set_thinking_level(self, level: ThinkingLevel) -> None:
        """Set the thinking level."""
        self.agent.set_thinking_level(level)

    def set_tools(self, tools: list[Any]) -> None:
        """Set the available tools."""
        self.agent.set_tools(tools)

    def replace_messages(self, messages: list[AgentMessage]) -> None:
        """Replace all messages."""
        self.agent.replace_messages(messages)

    def append_message(self, message: AgentMessage) -> None:
        """Append a message."""
        self.agent.append_message(message)

    def steer(self, message: AgentMessage) -> None:
        """Queue a steering message."""
        self.agent.steer(message)

    def follow_up(self, message: AgentMessage) -> None:
        """Queue a follow-up message."""
        self.agent.follow_up(message)

    def clear_steering_queue(self) -> None:
        """Clear the steering queue."""
        self.agent.clear_steering_queue()

    def clear_follow_up_queue(self) -> None:
        """Clear the follow-up queue."""
        self.agent.clear_follow_up_queue()

    def clear_all_queues(self) -> None:
        """Clear all queues."""
        self.agent.clear_all_queues()

    def has_queued_messages(self) -> bool:
        """Check if there are queued messages."""
        return self.agent.has_queued_messages()

    def set_steering_mode(self, mode: str) -> None:
        """Set the steering mode."""
        self.agent.set_steering_mode(mode)

    def get_steering_mode(self) -> str:
        """Get the steering mode."""
        return self.agent.get_steering_mode()

    def set_follow_up_mode(self, mode: str) -> None:
        """Set the follow-up mode."""
        self.agent.set_follow_up_mode(mode)

    def get_follow_up_mode(self) -> str:
        """Get the follow-up mode."""
        return self.agent.get_follow_up_mode()

    @property
    def session_id(self) -> Optional[str]:
        """Get the session ID."""
        return self.agent.session_id

    @session_id.setter
    def session_id(self, value: Optional[str]) -> None:
        """Set the session ID."""
        self.agent.session_id = value

    @property
    def thinking_budgets(self) -> Optional[dict[str, int]]:
        """Get the thinking budgets."""
        return self.agent.thinking_budgets

    @thinking_budgets.setter
    def thinking_budgets(self, value: Optional[dict[str, int]]) -> None:
        """Set the thinking budgets."""
        self.agent.thinking_budgets = value

    @property
    def transport(self) -> str:
        """Get the transport mode."""
        return self.agent.transport

    def set_transport(self, value: str) -> None:
        """Set the transport mode."""
        self.agent.set_transport(value)

    @property
    def max_retry_delay_ms(self) -> Optional[int]:
        """Get the max retry delay."""
        return self.agent.max_retry_delay_ms

    @max_retry_delay_ms.setter
    def max_retry_delay_ms(self, value: Optional[int]) -> None:
        """Set the max retry delay."""
        self.agent.max_retry_delay_ms = value


__all__ = [
    "SessionConfig",
    "AgentSession",
]
