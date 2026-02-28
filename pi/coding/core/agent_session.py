"""
Agent session for pi-coding.

Wraps pi.agent.Agent with session management.
"""
import asyncio
from typing import Any, Optional, Callable, Literal, Union
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

from pi.agent import Agent, AgentOptions
from pi.agent.types import AgentMessage, ThinkingLevel
from pi.ai.types import UserMessage, Model, TextContent, ImageContent
from .session_manager import SessionManager, SessionInfoEntry
from ..tools import get_builtin_tools


from .prompt_templates import PromptTemplate


@dataclass
class SessionConfig:
    """Configuration for an agent session."""
    model: Model
    thinking_level: ThinkingLevel = "medium"
    tools: Optional[list[Any]] = None
    system_prompt: Optional[str] = None
    cwd: Optional[str | Path] = None


@dataclass
class SessionStats:
    """Session statistics."""
    session_file: Optional[str]
    session_id: str
    user_messages: int
    assistant_messages: int
    tool_calls: int
    tool_results: int
    total_messages: int
    tokens: dict[str, int]
    cost: float


@dataclass
class ContextUsage:
    """Context usage information."""
    tokens: Optional[int]
    context_window: int
    percent: Optional[float]


@dataclass
class ModelCycleResult:
    """Result from cycling models."""
    model: Model
    thinking_level: str
    is_scoped: bool


@dataclass
class PromptOptions:
    """Options for AgentSession.prompt()."""
    expand_prompt_templates: bool = True
    images: Optional[list[dict]] = None
    streaming_behavior: Optional[Literal["steer", "followUp"]] = None
    source: str = "interactive"


class AgentSession:
    """
    Manages an agent session with persistence.

    Combines pi.agent.Agent with SessionManager for
    persistent agent conversations.
    """

    # Standard thinking levels
    _THINKING_LEVELS: list[ThinkingLevel] = ["off", "minimal", "low", "medium", "high"]
    _THINKING_LEVELS_WITH_XHIGH: list[ThinkingLevel] = ["off", "minimal", "low", "medium", "high", "xhigh"]

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

        # Event listeners
        self._event_listeners: list[Callable] = []
        self._unsubscribe_agent: Optional[Callable] = None

        # Tool registries
        self._tool_registry: dict[str, Any] = {}
        self._base_tool_registry: dict[str, Any] = {}

        # Queue tracking
        self._steering_messages: list[str] = []
        self._follow_up_messages: list[str] = []

        # Pending next turn messages
        self._pending_next_turn_messages: list[dict] = []

        # Bash execution state
        self._bash_abort_controller: Optional[Any] = None
        self._pending_bash_messages: list[dict] = []

        # Retry state
        self._retry_abort_controller: Optional[Any] = None
        self._retry_attempt: int = 0
        self._retry_promise: Optional[asyncio.Future] = None
        self._retry_resolve: Optional[Callable] = None

        # Compaction state
        self._compaction_abort_controller: Optional[Any] = None
        self._auto_compaction_abort_controller: Optional[Any] = None

        # Branch summarization state
        self._branch_summary_abort_controller: Optional[Any] = None

        # Extension system
        self._extension_runner: Optional[Any] = None
        self._extension_ui_context: Optional[Any] = None
        self._extension_command_context_actions: Optional[Any] = None
        self._extension_shutdown_handler: Optional[Any] = None
        self._extension_error_listener: Optional[Any] = None
        self._extension_error_unsubscriber: Optional[Any] = None

        # Turn tracking for extensions
        self._turn_index: int = 0

        # Base system prompt (without extension appends)
        self._base_system_prompt: str = ""

        # Last assistant message for auto-compaction
        self._last_assistant_message: Optional[dict] = None

        # Subscribe to agent events
        self._subscribe_to_agent()

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def state(self) -> dict[str, Any]:
        """Get the agent's current state."""
        return self.agent.state

    @property
    def model(self) -> Optional[Model]:
        """Get the current model."""
        m = self.state.get("model")
        if m is None:
            return None
        # If already a Model object, return it
        if isinstance(m, Model):
            return m
        # Otherwise convert dict to Model object
        if isinstance(m, dict):
            from pi.ai.types import ModelCost
            cost_dict = m.get("cost", {})
            return Model(
                id=m.get("id", ""),
                name=m.get("name", ""),
                api=m.get("api", ""),
                provider=m.get("provider", ""),
                baseUrl=m.get("baseUrl", ""),
                reasoning=m.get("reasoning", False),
                input=m.get("input", ["text"]),
                cost=ModelCost(
                    input=cost_dict.get("input", 0.0),
                    output=cost_dict.get("output", 0.0),
                    cacheRead=cost_dict.get("cacheRead", 0.0),
                    cacheWrite=cost_dict.get("cacheWrite", 0.0),
                ),
                contextWindow=m.get("contextWindow", 0),
                maxTokens=m.get("maxTokens", 0),
            )
        return None

    @property
    def thinking_level(self) -> Optional[ThinkingLevel]:
        """Get the current thinking level."""
        return self.state.get("thinkingLevel")

    @property
    def is_streaming(self) -> bool:
        """Whether the agent is currently streaming."""
        return self.state.get("isStreaming", False)

    @property
    def messages(self) -> list[AgentMessage]:
        """Get all messages from the agent state."""
        return self.state.get("messages", [])

    @property
    def prompt_templates(self) -> list[dict]:
        """Get available prompt templates from resource loader."""
        if self.resource_loader:
            return self.resource_loader.get_prompt_templates()
        return []

    @property
    def session_file(self) -> Optional[str]:
        """Get the current session file path."""
        sf = self.session_manager.get_session_file()
        return str(sf) if sf else None

    @property
    def session_name(self) -> Optional[str]:
        """Get the current session display name."""
        for entry in reversed(self.session_manager.get_entries()):
                if entry.type == "session_info":
                    info_entry = entry
                    if isinstance(info_entry, SessionInfoEntry):
                        return info_entry.name
        return None

    # =========================================================================
    # Prompt System
    # =========================================================================

    async def prompt(self, text: str, options: Optional[PromptOptions] = None) -> None:
        """
        Send a prompt to the agent with full processing.

        Args:
            text: The prompt text
            options: Optional prompt options
        """
        options = options or PromptOptions()
        expand_templates = options.expand_prompt_templates

        # Handle extension commands first (execute immediately, even during streaming)
        if expand_templates and text.startswith("/"):
            handled = await self._try_execute_extension_command(text)
            if handled:
                return

        # Emit input event for extension interception
        current_text = text
        current_images = options.images

        if self._extension_runner and hasattr(self._extension_runner, 'emit_input'):
            input_result = await self._extension_runner.emit_input(
                current_text,
                current_images,
                options.source or "interactive",
            )
            if input_result.get("action") == "handled":
                return
            if input_result.get("action") == "transform":
                current_text = input_result.get("text", current_text)
                current_images = input_result.get("images", current_images)

        # Expand skill commands and prompt templates
        expanded_text = current_text
        if expand_templates:
            expanded_text = self._expand_skill_command(expanded_text)
            expanded_text = self._expand_prompt_template(expanded_text)

        # If streaming, queue via steer() or followUp()
        if self.is_streaming:
            if not options.streaming_behavior:
                raise ValueError(
                    "Agent is already processing. Specify streaming_behavior ('steer' or 'followUp') to queue the message."
                )
            if options.streaming_behavior == "followUp":
                await self._queue_follow_up(expanded_text, current_images)
            else:
                await self._queue_steer(expanded_text, current_images)
            return

        # Flush any pending bash messages before the new prompt
        self._flush_pending_bash_messages()

        # Validate model
        if not self.model:
            raise ValueError("No model selected. Use /login or /model to select a model.")

        # Validate API key
        if self.model_registry:
            api_key = self.model_registry.get_api_key(self.model)
            if not api_key:
                is_oauth = self.model_registry.is_using_oauth(self.model)
                if is_oauth:
                    raise ValueError(
                        f'Authentication failed for "{self.model.provider}". '
                        f'Credentials may have expired. Run /login to re-authenticate.'
                    )
                raise ValueError(
                    f'No API key found for {self.model.provider}. Use /login to set an API key.'
                )

        # Check if we need to compact before sending
        last_assistant = self._find_last_assistant_message()
        if last_assistant:
            await self._check_compaction(last_assistant, skip_aborted_check=False)

        # Build messages array
        messages: list = []

        # Add user message
        user_content: list[TextContent | ImageContent] = [TextContent(type="text", text=expanded_text)]
        if current_images:
            for img in current_images:
                if isinstance(img, dict):
                    user_content.append(ImageContent(
                        type="image",
                        data=img.get("data", ""),
                        mimeType=img.get("mimeType", ""),
                    ))
                elif isinstance(img, ImageContent):
                    user_content.append(img)
        messages.append(UserMessage(
            role="user",
            content=user_content,
            timestamp=int(datetime.now().timestamp() * 1000),
        ))

        # Inject any pending "nextTurn" messages
        for msg in self._pending_next_turn_messages:
            messages.append(msg)
        self._pending_next_turn_messages = []

        # Emit before_agent_start extension event
        if self._extension_runner and hasattr(self._extension_runner, 'emit_before_agent_start'):
            result = await self._extension_runner.emit_before_agent_start(
                expanded_text,
                current_images,
                self._base_system_prompt,
            )
            # Add custom messages from extensions
            if result and result.get("messages"):
                for msg in result["messages"]:
                    messages.append({
                        "role": "custom",
                        "customType": msg.get("customType"),
                        "content": msg.get("content"),
                        "display": msg.get("display"),
                        "details": msg.get("details"),
                        "timestamp": int(datetime.now().timestamp() * 1000),
                    })
            # Apply extension-modified system prompt
            if result and result.get("systemPrompt"):
                self.agent.set_system_prompt(result["systemPrompt"])
            else:
                self.agent.set_system_prompt(self._base_system_prompt)

        # Send to agent
        await self.agent.prompt(messages)
        await self._wait_for_retry()

    def _expand_skill_command(self, text: str) -> str:
        """
        Expand skill commands (/skill:name args) to full content.

        Args:
            text: The input text

        Returns:
            Expanded text or original if not a skill command
        """
        if not text.startswith("/skill:"):
            return text

        space_index = text.find(" ")
        skill_name = text[7:space_index] if space_index != -1 else text[7:]
        args = text[space_index + 1:].strip() if space_index != -1 else ""

        # Get skill from resource loader
        if not self.resource_loader:
            return text

        skills = self.resource_loader.get_skills()
        skill = None
        for s in skills.get("skills", []):
            if s.get("name") == skill_name:
                skill = s
                break

        if not skill:
            return text  # Unknown skill, pass through

        try:
            skill_path = Path(skill.get("filePath", ""))
            content = skill_path.read_text(encoding="utf-8")

            # Strip frontmatter (content between --- markers)
            if content.startswith("---"):
                end_fm = content.find("---", 3)
                if end_fm != -1:
                    content = content[end_fm + 3:].strip()

            body = content.strip()
            skill_block = f'<skill name="{skill.get("name")}" location="{skill.get("filePath")}">\nReferences are relative to {skill.get("baseDir")}.\n\n{body}\n</skill>'
            return f"{skill_block}\n\n{args}" if args else skill_block
        except Exception:
            return text  # Return original on error

    def _expand_prompt_template(self, text: str) -> str:
        """
        Expand prompt template references.

        Args:
            text: The input text

        Returns:
            Expanded text or original if not a template reference
        """
        if not text.startswith("/"):
            return text

        templates = self.prompt_templates
        if not templates:
            return text

        space_index = text.find(" ")
        template_name = text[1:space_index] if space_index != -1 else text[1:]
        args_string = text[space_index + 1:] if space_index != -1 else ""

        for template in templates:
            if template.get("name") == template_name:
                content = template.get("content", "")
                # Simple variable substitution
                if args_string:
                    args = self._parse_command_args(args_string)
                    content = self._substitute_args(content, args)
                return content

        return text

    def _parse_command_args(self, args_string: str) -> dict[str, str]:
        """Parse command line arguments into a dictionary."""
        args: dict[str, str] = {}
        if not args_string:
            return args

        # Simple key=value parsing
        for part in args_string.split():
            if "=" in part:
                key, value = part.split("=", 1)
                args[key] = value

        return args

    def _substitute_args(self, content: str, args: dict[str, str]) -> str:
        """Substitute {{variable}} placeholders with args."""
        result = content
        for key, value in args.items():
            result = result.replace("{{" + key + "}}", value)
        return result

    async def _queue_steer(self, text: str, images: Optional[list[dict]] = None) -> None:
        """Queue a steering message to interrupt the agent."""
        self._steering_messages.append(text)

        user_content: list[TextContent | ImageContent] = [TextContent(type="text", text=text)]
        if images:
            for img in images:
                if isinstance(img, dict):
                    user_content.append(ImageContent(
                        type="image",
                        data=img.get("data", ""),
                        mimeType=img.get("mimeType", ""),
                    ))
                elif isinstance(img, ImageContent):
                    user_content.append(img)

        await self.agent.steer(UserMessage(
            role="user",
            content=user_content,
            timestamp=int(datetime.now().timestamp() * 1000),
        ))

    async def _queue_follow_up(self, text: str, images: Optional[list[dict]] = None) -> None:
        """Queue a follow-up message to be processed after agent finishes."""
        self._follow_up_messages.append(text)

        user_content: list[TextContent | ImageContent] = [TextContent(type="text", text=text)]
        if images:
            for img in images:
                if isinstance(img, dict):
                    user_content.append(ImageContent(
                        type="image",
                        data=img.get("data", ""),
                        mimeType=img.get("mimeType", ""),
                    ))
                elif isinstance(img, ImageContent):
                    user_content.append(img)

        await self.agent.follow_up(UserMessage(
            role="user",
            content=user_content,
            timestamp=int(datetime.now().timestamp() * 1000),
        ))

    async def _try_execute_extension_command(self, text: str) -> bool:
        """
        Try to execute an extension command.

        Args:
            text: Command text (starting with /)

        Returns:
            True if command was found and executed
        """
        if not self._extension_runner:
            return False

        # Parse command name and args
        space_index = text.find(" ")
        command_name = text[1:space_index] if space_index != -1 else text[1:]
        args = text[space_index + 1:] if space_index != -1 else ""

        command = None
        if hasattr(self._extension_runner, 'get_command'):
            command = self._extension_runner.get_command(command_name)

        if not command:
            return False

        # Get command context
        if hasattr(self._extension_runner, 'create_command_context'):
            ctx = self._extension_runner.create_command_context()
        else:
            ctx = {}

        try:
            handler = command.get("handler") or command
            if asyncio.iscoroutinefunction(handler):
                await handler(args, ctx)
            else:
                handler(args, ctx)
            return True
        except Exception:
            return True  # Command was found but failed

    def _find_last_assistant_message(self) -> Optional[dict]:
        """Find the last assistant message in agent state."""
        messages = self.state.get("messages", [])
        for i in range(len(messages) - 1, -1, -1):
            msg = messages[i]
            if msg.get("role") == "assistant":
                return msg
        return None

    async def _check_compaction(self, assistant_message: dict, skip_aborted_check: bool = True) -> None:
        """Check if compaction is needed and run it."""
        # TODO: Implement auto-compaction check
        pass

    def _flush_pending_bash_messages(self) -> None:
        """Flush pending bash messages to agent state."""
        if not self._pending_bash_messages:
            return

        for msg in self._pending_bash_messages:
            self.agent.append_message(msg)
        self._pending_bash_messages = []

    async def _wait_for_retry(self) -> None:
        """Wait for any in-progress retry to complete."""
        if self._retry_promise:
            await self._retry_promise

    # =========================================================================
    # Agent Methods (delegated)
    # =========================================================================

    async def continue_(self) -> None:
        """Continue from current context (used for retries)."""
        await self.agent.continue_()

    def abort(self) -> None:
        """Abort the current operation."""
        self.abort_retry()
        self.agent.abort()

    async def wait_for_idle(self) -> None:
        """Wait for the agent to finish processing."""
        await self.agent.wait_for_idle()

    def reset(self) -> None:
        """Reset the agent state."""
        self.agent.reset()

    def set_system_prompt(self, prompt: str) -> None:
        """Set the system prompt."""
        self.agent.set_system_prompt(prompt)

    def set_model(self, model: dict[str, Any]) -> None:
        """Set the model."""
        self.agent.set_model(model)

    def set_tools(self, tools: list[Any]) -> None:
        """Set the available tools."""
        self.agent.set_tools(tools)

    def replace_messages(self, messages: list[AgentMessage]) -> None:
        """Replace all messages."""
        self.agent.replace_messages(messages)

    def append_message(self, message: AgentMessage) -> None:
        """Append a message."""
        self.agent.append_message(message)

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

    def _subscribe_to_agent(self) -> None:
        """Subscribe to agent events."""
        if self._unsubscribe_agent is None:
            self._unsubscribe_agent = self.agent.subscribe(self._handle_agent_event)

    def _handle_agent_event(self, event: Any) -> None:
        """Handle agent events and emit to listeners."""
        # When a user message starts, check if it's from either queue and remove it
        if event.get("type") == "message_start" and event.get("message", {}).get("role") == "user":
            message_text = self._get_user_message_text(event.get("message", {}))
            if message_text:
                # Check steering queue first
                if message_text in self._steering_messages:
                    self._steering_messages.remove(message_text)
                elif message_text in self._follow_up_messages:
                    self._follow_up_messages.remove(message_text)

        # Emit to all listeners
        for listener in self._event_listeners:
            listener(event)

    def _get_user_message_text(self, message: dict) -> str:
        """Extract text content from a user message."""
        if message.get("role") != "user":
            return ""
        content = message.get("content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(b.get("text", "") for b in content if b.get("type") == "text")
        return ""

    def subscribe(self, callback: Callable) -> Callable:
        """
        Subscribe to agent events.

        Returns an unsubscribe function.
        """
        self._event_listeners.append(callback)

        def unsubscribe() -> None:
            if callback in self._event_listeners:
                self._event_listeners.remove(callback)

        return unsubscribe

    # =========================================================================
    # Session Control (Phase 1)
    # =========================================================================

    async def new_session(
        self,
        parent_session: Optional[str] = None,
        setup: Optional[Callable] = None,
    ) -> bool:
        """Start a new session, optionally with parent tracking."""
        if self._unsubscribe_agent:
            self._unsubscribe_agent()
            self._unsubscribe_agent = None

        await self.abort()
        self.agent.reset()

        self.session_manager._create_new_session()
        self.agent.session_id = self.session_manager.get_session_id()

        self.session_manager.append_thinking_level_change(
            self.thinking_level or "medium"
        )

        if setup:
            await setup(self.session_manager)
            session_context = self.session_manager.build_session_context()
            self.agent.replace_messages(session_context.messages)

        self._subscribe_to_agent()
        return True

    async def switch_session(self, session_path: str) -> bool:
        """Switch to a different session file."""
        if self._unsubscribe_agent:
            self._unsubscribe_agent()
            self._unsubscribe_agent = None

        await self.abort()

        self.session_manager._session_file = Path(session_path)
        self.session_manager._load_session()
        self.agent.session_id = self.session_manager.get_session_id()

        session_context = self.session_manager.build_session_context()
        self.agent.replace_messages(session_context.messages)

        self._subscribe_to_agent()
        return True

    def set_session_name(self, name: str) -> None:
        """Set a display name for the current session."""
        from .session_manager import generate_id
        new_id = generate_id(self.session_manager._entry_ids)
        timestamp = datetime.now().isoformat()
        parent_id = self.session_manager.get_leaf_id()

        entry = SessionInfoEntry(
            type="session_info",
            id=new_id,
            parent_id=parent_id,
            timestamp=timestamp,
            name=name,
        )

        self.session_manager._entries.append(entry)
        self.session_manager._entry_ids.add(new_id)

        import json
        from dataclasses import asdict
        if self.session_manager._session_file:
            with open(self.session_manager._session_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(entry)) + "\n")

    async def reload(self) -> None:
        """Reload settings and extensions."""
        if self.settings_manager:
            self.settings_manager._settings = self.settings_manager._load_settings()

    def dispose(self) -> None:
        """Remove all listeners and disconnect from agent."""
        if self._unsubscribe_agent:
            self._unsubscribe_agent()
            self._unsubscribe_agent = None
        self._event_listeners = []

    def get_session_stats(self) -> SessionStats:
        """Get session statistics."""
        state = self.state
        messages = state.get("messages", [])

        user_messages = sum(1 for m in messages if m.get("role") == "user")
        assistant_messages = sum(1 for m in messages if m.get("role") == "assistant")
        tool_results = sum(1 for m in messages if m.get("role") == "toolResult")

        tool_calls = 0
        total_input = 0
        total_output = 0
        total_cache_read = 0
        total_cache_write = 0
        total_cost = 0.0

        for message in messages:
            if message.get("role") == "assistant":
                content = message.get("content", [])
                if isinstance(content, list):
                    tool_calls += sum(1 for c in content if c.get("type") == "toolCall")

                usage = message.get("usage", {})
                total_input += usage.get("input", 0)
                total_output += usage.get("output", 0)
                total_cache_read += usage.get("cacheRead", 0)
                total_cache_write += usage.get("cacheWrite", 0)
                cost_info = usage.get("cost", {})
                total_cost += cost_info.get("total", 0)

        return SessionStats(
            session_file=str(self.session_manager.get_session_file()) if self.session_manager.get_session_file() else None,
            session_id=self.session_manager.get_session_id(),
            user_messages=user_messages,
            assistant_messages=assistant_messages,
            tool_calls=tool_calls,
            tool_results=tool_results,
            total_messages=len(messages),
            tokens={
                "input": total_input,
                "output": total_output,
                "cache_read": total_cache_read,
                "cache_write": total_cache_write,
                "total": total_input + total_output + total_cache_read + total_cache_write,
            },
            cost=total_cost,
        )

    def get_context_usage(self) -> Optional[ContextUsage]:
        """Get context usage estimate."""
        model = self.model
        if not model:
            return None

        context_window = model.contextWindow
        if context_window <= 0:
            return None

        # Estimate tokens from messages (rough estimate: 1 token ≈ 4 chars)
        messages = self.state.get("messages", [])
        total_chars = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total_chars += len(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        text = block.get("text", "")
                        total_chars += len(text)

        estimated_tokens = total_chars // 4
        percent = (estimated_tokens / context_window * 100) if context_window > 0 else 0

        return ContextUsage(
            tokens=estimated_tokens,
            context_window=context_window,
            percent=percent,
        )

    async def cycle_model(
        self,
        direction: str = "forward"
    ) -> Optional[ModelCycleResult]:
        """Cycle to next/previous model."""
        if self.scoped_models and len(self.scoped_models) > 1:
            return await self._cycle_scoped_model(direction)
        elif self.model_registry:
            return await self._cycle_available_model(direction)
        return None

    async def _cycle_scoped_model(self, direction: str) -> Optional[ModelCycleResult]:
        """Cycle through scoped models."""
        valid_models = list(self.scoped_models)

        if len(valid_models) <= 1:
            return None

        current_model = self.model
        current_index = -1
        for i, sm in enumerate(valid_models):
            sm_model = sm.get("model", {})
            if current_model and (
                sm_model.get("provider") == current_model.provider and
                sm_model.get("id") == current_model.id
            ):
                current_index = i
                break

        if current_index == -1:
            current_index = 0

        len_models = len(valid_models)
        if direction == "forward":
            next_index = (current_index + 1) % len_models
        else:
            next_index = (current_index - 1 + len_models) % len_models

        next_model = valid_models[next_index]
        model_dict = next_model.get("model", {})
        thinking = next_model.get("thinkingLevel", "medium")

        self.agent.set_model(model_dict)
        self.session_manager.append_model_change(
            model_dict.get("provider", ""),
            model_dict.get("id", "")
        )

        self.set_thinking_level(thinking)

        # Convert model_dict to Model object for return
        from pi.ai.types import ModelCost
        cost_dict = model_dict.get("cost", {})
        model_obj = Model(
            id=model_dict.get("id", ""),
            name=model_dict.get("name", ""),
            api=model_dict.get("api", ""),
            provider=model_dict.get("provider", ""),
            baseUrl=model_dict.get("baseUrl", ""),
            reasoning=model_dict.get("reasoning", False),
            input=model_dict.get("input", ["text"]),
            cost=ModelCost(
                input=cost_dict.get("input", 0.0),
                output=cost_dict.get("output", 0.0),
                cacheRead=cost_dict.get("cacheRead", 0.0),
                cacheWrite=cost_dict.get("cacheWrite", 0.0),
            ),
            contextWindow=model_dict.get("contextWindow", 0),
            maxTokens=model_dict.get("maxTokens", 0),
        )

        return ModelCycleResult(
            model=model_obj,
            thinking_level=self.thinking_level or "medium",
            is_scoped=True,
        )

    async def _cycle_available_model(self, direction: str) -> Optional[ModelCycleResult]:
        """Cycle through all available models."""
        if not self.model_registry:
            return None

        # Get all available models from model registry
        available_models = self.model_registry.list_models()
        if len(available_models) <= 1:
            return None

        # Convert ModelInfo objects to dicts for agent.set_model
        available_model_dicts = [
            {
                "provider": m.provider,
                "id": m.id,
                "name": m.name,
                "reasoning": m.reasoning,
                "api": m.api,
                "contextWindow": m.context_window,
                "maxTokens": m.max_tokens,
                "input": m.input,
            }
            for m in available_models
        ]

        current_model = self.model
        current_index = -1
        for i, m in enumerate(available_model_dicts):
            if current_model and (
                m.get("provider") == current_model.provider and
                m.get("id") == current_model.id
            ):
                current_index = i
                break

        if current_index == -1:
            current_index = 0

        len_models = len(available_model_dicts)
        if direction == "forward":
            next_index = (current_index + 1) % len_models
        else:
            next_index = (current_index - 1 + len_models) % len_models

        next_model_dict = available_model_dicts[next_index]

        self.agent.set_model(next_model_dict)
        self.session_manager.append_model_change(
            next_model_dict.get("provider", ""),
            next_model_dict.get("id", "")
        )

        self.set_thinking_level(self.thinking_level or "medium")

        # Convert dict to Model object for return
        from pi.ai.types import ModelCost
        cost_dict = next_model_dict.get("cost", {})
        model_obj = Model(
            id=next_model_dict.get("id", ""),
            name=next_model_dict.get("name", ""),
            api=next_model_dict.get("api", ""),
            provider=next_model_dict.get("provider", ""),
            baseUrl=next_model_dict.get("baseUrl", ""),
            reasoning=next_model_dict.get("reasoning", False),
            input=next_model_dict.get("input", ["text"]),
            cost=ModelCost(
                input=cost_dict.get("input", 0.0),
                output=cost_dict.get("output", 0.0),
                cacheRead=cost_dict.get("cacheRead", 0.0),
                cacheWrite=cost_dict.get("cacheWrite", 0.0),
            ),
            contextWindow=next_model_dict.get("contextWindow", 0),
            maxTokens=next_model_dict.get("maxTokens", 0),
        )

        return ModelCycleResult(
            model=model_obj,
            thinking_level=self.thinking_level or "medium",
            is_scoped=False,
        )

    def supports_xhigh_thinking(self) -> bool:
        """Check if current model supports xhigh thinking level."""
        model = self.model
        if not model:
            return False
        # Check for supportsXhigh attribute, fallback to False if not present
        return getattr(model, "supportsXhigh", False)

    def supports_thinking(self) -> bool:
        """Check if current model supports thinking/reasoning."""
        model = self.model
        if not model:
            return False
        return model.reasoning

    def get_available_thinking_levels(self) -> list[ThinkingLevel]:
        """Get available thinking levels for current model."""
        if not self.supports_thinking():
            return ["off"]
        return self._THINKING_LEVELS_WITH_XHIGH if self.supports_xhigh_thinking() else self._THINKING_LEVELS

    def cycle_thinking_level(self) -> Optional[ThinkingLevel]:
        """Cycle to next thinking level."""
        if not self.supports_thinking():
            return None

        levels = self.get_available_thinking_levels()
        current = self.thinking_level or "medium"

        try:
            current_index = levels.index(current)
        except ValueError:
            current_index = 0

        next_index = (current_index + 1) % len(levels)
        next_level = levels[next_index]

        self.set_thinking_level(next_level)
        return next_level

    def set_thinking_level(self, level: ThinkingLevel) -> None:
        """Set thinking level with clamping to model capabilities."""
        available_levels = self.get_available_thinking_levels()
        effective_level = self._clamp_thinking_level(level, available_levels)

        current_level = self.thinking_level
        is_changing = effective_level != current_level

        self.agent.set_thinking_level(effective_level)

        if is_changing:
            self.session_manager.append_thinking_level_change(effective_level)
            if self.settings_manager:
                self.settings_manager.set_default_thinking_level(effective_level)

    def _clamp_thinking_level(
        self,
        level: ThinkingLevel,
        available_levels: list[ThinkingLevel]
    ) -> ThinkingLevel:
        """Clamp thinking level to available levels."""
        ordered = self._THINKING_LEVELS_WITH_XHIGH
        available_set = set(available_levels)

        if level in available_set:
            return level

        try:
            requested_index = ordered.index(level)
        except ValueError:
            return available_levels[0] if available_levels else "off"

        for i in range(requested_index, len(ordered)):
            if ordered[i] in available_set:
                return ordered[i]

        for i in range(requested_index - 1, -1, -1):
            if ordered[i] in available_set:
                return ordered[i]

        return available_levels[0] if available_levels else "off"

    # =========================================================================
    # Tool Management (Phase 3)
    # =========================================================================

    def get_all_tools(self) -> list[dict[str, Any]]:
        """Get all configured tools with name, description, and parameters."""
        return [
            {
                "name": name,
                "description": tool.get("description", ""),
                "parameters": tool.get("parameters", {}),
            }
            for name, tool in self._tool_registry.items()
        ]

    def get_active_tool_names(self) -> list[str]:
        """Get the names of currently active tools."""
        tools = self.state.get("tools", [])
        return [t.get("name", "") for t in tools if isinstance(t, dict)]

    def set_active_tools_by_name(self, tool_names: list[str]) -> None:
        """Set active tools by name."""
        tools: list[Any] = []
        valid_tool_names: list[str] = []

        for name in tool_names:
            tool = self._tool_registry.get(name)
            if tool:
                tools.append(tool)
                valid_tool_names.append(name)

        self.agent.set_tools(tools)
        self._rebuild_system_prompt(valid_tool_names)

    def _rebuild_system_prompt(self, tool_names: list[str]) -> None:
        """Rebuild the system prompt with the given tool names."""
        # TODO: Implement system prompt rebuilding
        pass

    # =========================================================================
    # Queue & Message Management (Phase 5)
    # =========================================================================

    def clear_queue(self) -> dict[str, list[str]]:
        """Clear all queued messages and return them."""
        steering = list(self._steering_messages)
        follow_up = list(self._follow_up_messages)
        self._steering_messages = []
        self._follow_up_messages = []
        self.agent.clear_all_queues()
        return {"steering": steering, "follow_up": follow_up}

    @property
    def pending_message_count(self) -> int:
        """Number of pending messages."""
        return len(self._steering_messages) + len(self._follow_up_messages)

    def get_steering_messages(self) -> list[str]:
        """Get pending steering messages (read-only)."""
        return list(self._steering_messages)

    def get_follow_up_messages(self) -> list[str]:
        """Get pending follow-up messages (read-only)."""
        return list(self._follow_up_messages)

    async def send_custom_message(
        self,
        message: dict[str, Any],
        options: Optional[dict[str, Any]] = None,
    ) -> None:
        """Send a custom message to the session."""
        options = options or {}
        deliver_as = options.get("deliver_as", "nextTurn")
        trigger_turn = options.get("trigger_turn", False)

        app_message = {
            "role": "custom",
            "customType": message.get("customType"),
            "content": message.get("content"),
            "display": message.get("display"),
            "details": message.get("details"),
            "timestamp": datetime.now().isoformat(),
        }

        if self.is_streaming:
            if deliver_as == "followUp":
                await self.agent.follow_up(app_message)
            else:
                await self.agent.steer(app_message)
        elif trigger_turn:
            await self.agent.prompt(app_message)
        else:
            self.agent.append_message(app_message)

    async def send_user_message(
        self,
        content: str | list,
        options: Optional[dict[str, Any]] = None,
    ) -> None:
        """Send a user message to the agent."""
        options = options or {}
        text = content if isinstance(content, str) else str(content)

        await self.prompt(text, PromptOptions(
            expand_prompt_templates=False,
            streaming_behavior=options.get("deliver_as"),
            source="extension",
        ))

    # =========================================================================
    # Auto-Retry Logic (Phase 7)
    # =========================================================================

    def _is_retryable_error(self, message: dict) -> bool:
        """Check if error is retryable."""
        if message.get("stopReason") != "error" or not message.get("errorMessage"):
            return False

        err = message.get("errorMessage", "").lower()
        retryable_patterns = [
            "overloaded", "rate limit", "too many requests", "429",
            "500", "502", "503", "504", "service unavailable",
            "server error", "internal error", "connection error",
        ]
        return any(pattern in err for pattern in retryable_patterns)

    async def _handle_retryable_error(self, message: dict) -> bool:
        """Handle retryable errors with exponential backoff."""
        if not self.settings_manager:
            return False

        self._retry_attempt += 1
        max_retries = 3

        if self._retry_attempt > max_retries:
            self._retry_attempt = 0
            self._resolve_retry()
            return False

        if self._retry_attempt == 1 and not self._retry_promise:
            loop = asyncio.get_event_loop()
            self._retry_promise = loop.create_future()

        delay_ms = 1000 * (2 ** (self._retry_attempt - 1))

        messages = self.state.get("messages", [])
        if messages and messages[-1].get("role") == "assistant":
            self.agent.replace_messages(messages[:-1])

        await asyncio.sleep(delay_ms / 1000)
        await self.agent.continue_()

        return True

    def _complete_retry_promise(self) -> None:
        """Complete the retry promise."""
        if self._retry_promise and not self._retry_promise.done():
            self._retry_promise.set_result(None)

    def abort_retry(self) -> None:
        """Cancel in-progress retry."""
        if self._retry_abort_controller:
            self._retry_abort_controller.abort()
        self._resolve_retry()

    @property
    def is_retrying(self) -> bool:
        """Whether auto-retry is in progress."""
        return self._retry_promise is not None

    @property
    def auto_retry_enabled(self) -> bool:
        """Whether auto-retry is enabled."""
        if not self.settings_manager:
            return True
        return getattr(self.settings_manager._settings, "autoRetry", True)

    def set_auto_retry_enabled(self, enabled: bool) -> None:
        """Toggle auto-retry setting."""
        if self.settings_manager:
            setattr(self.settings_manager._settings, "autoRetry", enabled)
            self.settings_manager._save_global_settings()

    def _resolve_retry(self) -> None:
        """Resolve pending retry promise."""
        if self._retry_resolve:
            self._retry_resolve()
            self._retry_resolve = None
        if self._retry_promise and not self._retry_promise.done():
            self._retry_promise.set_result(None)
        self._retry_promise = None

    # =========================================================================
    # Compaction System (Phase 8)
    # =========================================================================

    async def compact(self, custom_instructions: Optional[str] = None) -> dict[str, Any]:
        """Manually compact session context."""
        from .compaction import prepare_compaction, compact as do_compact

        settings = {
            "enabled": True,
            "context_window": self.model.contextWindow if self.model else 200000,
            "threshold_percent": 80,
        }

        entries = self.session_manager.get_entries()
        preparation = prepare_compaction(entries, settings)

        if not preparation:
            return {
                "summary": "Nothing to compact",
                "firstKeptEntryId": "",
                "tokensBefore": 0,
                "aborted": False,
                "error": None,
            }

        model = self.model
        provider = model.provider if model else ""
        model_id = model.id if model else ""

        # Get API key from settings manager or environment
        api_key = ""
        if self.settings_manager:
            api_key = self.settings_manager.get_api_key(provider)

        try:
            result = await do_compact(
                preparation=preparation,
                model={"provider": provider, "id": model_id},
                api_key=api_key,
                custom_instructions=custom_instructions,
                signal=self._compaction_abort_controller,
            )

            # Create compaction entry
            from .session_manager import generate_id
            entry_id = generate_id(self.session_manager._entry_ids)

            # Record compaction in session
            self.session_manager._entries.append({
                "type": "compaction",
                "id": entry_id,
                "parentId": self.session_manager.get_leaf_id(),
                "timestamp": datetime.now().isoformat(),
                "summary": result.summary,
                "tokensBefore": result.tokens_before,
                "firstKeptEntryId": result.first_kept_entry_id,
                "details": result.details,
            })
            self.session_manager._entry_ids.add(entry_id)

            return {
                "summary": result.summary,
                "firstKeptEntryId": result.first_kept_entry_id,
                "tokensBefore": result.tokens_before,
                "details": result.details,
                "aborted": False,
                "error": None,
            }
        except asyncio.CancelledError:
            return {
                "summary": "",
                "firstKeptEntryId": "",
                "tokensBefore": preparation.total_tokens,
                "aborted": True,
                "error": "Compaction was cancelled",
            }
        except Exception as e:
            return {
                "summary": "",
                "firstKeptEntryId": "",
                "tokensBefore": preparation.total_tokens,
                "aborted": False,
                "error": str(e),
            }

    def abort_compaction(self) -> None:
        """Cancel in-progress compaction."""
        if self._compaction_abort_controller:
            self._compaction_abort_controller.abort()
        if self._auto_compaction_abort_controller:
            self._auto_compaction_abort_controller.abort()

    @property
    def is_compacting(self) -> bool:
        """Whether auto-compaction is running."""
        return (
            self._compaction_abort_controller is not None or
            self._auto_compaction_abort_controller is not None
        )

    @property
    def auto_compaction_enabled(self) -> bool:
        """Whether auto-compaction is enabled."""
        if not self.settings_manager:
            return True
        return self.settings_manager.get_auto_compaction()

    def set_auto_compaction_enabled(self, enabled: bool) -> None:
        """Toggle auto-compaction setting."""
        if self.settings_manager:
            setattr(self.settings_manager._settings, "autoCompaction", enabled)
            self.settings_manager._save_global_settings()

    # =========================================================================
    # Tree Navigation & Branching (Phase 9)
    # =========================================================================

    async def navigate_tree(
        self,
        target_id: str,
        options: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Navigate to a different node in the session tree."""
        options = options or {}
        old_leaf_id = self.session_manager.get_leaf_id()

        if target_id == old_leaf_id:
            return {"cancelled": False}

        target_entry = self.session_manager.get_entry(target_id)
        if not target_entry:
            raise ValueError(f"Entry {target_id} not found")

        # Navigate (simplified - branch summary to be implemented)
        branch = self.session_manager.get_branch()
        if target_entry in branch:
            target_index = branch.index(target_entry)
            self.session_manager._entries = branch[:target_index + 1]

        # Update agent state
        session_context = self.session_manager.build_session_context()
        self.agent.replace_messages(session_context.messages)

        editor_text = None
        if hasattr(target_entry, "message"):
            content = target_entry.message.get("content", "")
            if isinstance(content, str):
                editor_text = content
            elif isinstance(content, list):
                editor_text = "\n".join(
                    c.get("text", "") for c in content if c.get("type") == "text"
                )

        return {"editorText": editor_text, "cancelled": False}

    async def fork(self, entry_id: str) -> dict[str, Any]:
        """Create a fork from a specific entry."""
        selected_entry = self.session_manager.get_entry(entry_id)
        if not selected_entry:
            raise ValueError(f"Entry {entry_id} not found")

        if not hasattr(selected_entry, "message") or selected_entry.message.get("role") != "user":
            raise ValueError("Can only fork from user messages")

        content = selected_entry.message.get("content", "")
        if isinstance(content, str):
            selected_text = content
        elif isinstance(content, list):
            selected_text = "\n".join(
                c.get("text", "") for c in content if c.get("type") == "text"
            )
        else:
            selected_text = str(content)

        await self.new_session(parent_session=str(self.session_file))

        return {"selectedText": selected_text, "cancelled": False}

    def abort_branch_summary(self) -> None:
        """Cancel in-progress branch summarization."""
        if self._branch_summary_abort_controller:
            self._branch_summary_abort_controller.abort()

    def get_user_messages_for_forking(self) -> list[dict[str, str]]:
        """Get all user messages from session for fork selector."""
        entries = self.session_manager.get_entries()
        result = []

        for entry in entries:
            if not hasattr(entry, "message"):
                continue
            if entry.message.get("role") != "user":
                continue

            content = entry.message.get("content", "")
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                text = "\n".join(
                    c.get("text", "") for c in content if c.get("type") == "text"
                )
            else:
                text = str(content)

            if text:
                result.append({"entryId": entry.id, "text": text})

        return result

    # =========================================================================
    # HTML Export (Phase 11)
    # =========================================================================

    async def export_to_html(self, output_path: Optional[str] = None) -> str:
        """Export session to HTML."""
        from .export_html import export_session_to_html, HtmlExportConfig

        config = HtmlExportConfig(output_path=output_path)

        # Save session before export
        self.session_manager._save_session()

        # Export to HTML
        output_file = export_session_to_html(
            session_manager=self.session_manager,
            agent_state=self.state,
            config=config,
        )

        return output_file

    # =========================================================================
    # Extension System Integration (Phase 12)
    # =========================================================================

    async def bind_extensions(
        self,
        bindings: Optional[dict[str, Any]] = None,
    ) -> None:
        """Bind extension UI context and handlers."""
        if not bindings:
            return

        if "ui_context" in bindings:
            self._extension_ui_context = bindings["ui_context"]
        if "command_context_actions" in bindings:
            self._extension_command_context_actions = bindings["command_context_actions"]
        if "shutdown_handler" in bindings:
            self._extension_shutdown_handler = bindings["shutdown_handler"]
        if "on_error" in bindings:
            self._extension_error_listener = bindings["on_error"]

    def has_extension_handlers(self, event_type: str) -> bool:
        """Check if extensions have handlers for event type."""
        if not self._extension_runner:
            return False
        # Check if there are listeners for this event type
        return event_type in self._extension_runner._listeners

    @property
    def extension_runner(self) -> Optional[Any]:
        """Get extension runner."""
        return self._extension_runner


__all__ = [
    "SessionConfig",
    "SessionStats",
    "ContextUsage",
    "ModelCycleResult",
    "PromptOptions",
    "AgentSession",
]
