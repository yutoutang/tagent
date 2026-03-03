"""
Pi SDK - Main programmatic API for pi-coding.

Converted from TypeScript core/sdk.ts
"""
from typing import Any, Optional, List
from pathlib import Path
from dataclasses import dataclass

from pi.agent import Agent
from pi.agent.types import ThinkingLevel
from .agent_session import AgentSession
from .session_manager import SessionManager
from .settings_manager import SettingsManager
from .auth_storage import AuthStorage
from .model_registry import ModelRegistry
from .model_resolver import find_initial_model
from .resource_loader import DefaultResourceLoader
from ..tools import get_builtin_tools
from ...ai import Model


@dataclass
class CreateAgentSessionOptions:
    """Options for creating an agent session."""
    cwd: Optional[str | Path] = None
    agent_dir: Optional[str | Path] = None
    auth_storage: Optional[AuthStorage] = None
    model_registry: Optional[ModelRegistry] = None
    model: Optional[Model] = None
    thinking_level: Optional[ThinkingLevel] = None
    scoped_models: Optional[List[dict[str, Any]]] = None
    tools: Optional[List[Any]] = None
    custom_tools: Optional[List[Any]] = None
    resource_loader: Optional[Any] = None
    session_manager: Optional[SessionManager] = None
    settings_manager: Optional[SettingsManager] = None


@dataclass
class CreateAgentSessionResult:
    """Result from creating an agent session."""
    session: AgentSession
    extensions_result: Any  # LoadExtensionsResult
    model_fallback_message: Optional[str] = None


async def create_agent_session(
    options: CreateAgentSessionOptions = CreateAgentSessionOptions(),
) -> CreateAgentSessionResult:
    """
    Create an AgentSession with the specified options.

    This is the main entry point for using pi-coding programmatically.

    Args:
        options: Configuration options

    Returns:
        CreateAgentSessionResult with session and metadata

    Example:
        ```python
        # Minimal - uses defaults
        result = await create_agent_session()
        session = result.session

        # With explicit model
        result = await create_agent_session(CreateAgentSessionOptions(
            model={"provider": "anthropic", "id": "claude-opus-4-5"},
            thinking_level="high",
        ))

        # Continue previous session
        result = await create_agent_session(CreateAgentSessionOptions(
            continue_session=True,
        ))
        ```
    """
    from ..config import get_agent_dir
    from ..core.defaults import DEFAULT_SYSTEM_PROMPT, DEFAULT_THINKING_LEVEL, get_default_system_prompt
    from ..core.messages import convertToLlm
    from ..core.timings import time
    import asyncio

    cwd = Path(options.cwd) if options.cwd else Path.cwd()
    agent_dir = Path(options.agent_dir) if options.agent_dir else get_agent_dir()

    # Use provided or create AuthStorage and ModelRegistry
    auth_storage = options.auth_storage or AuthStorage.create(agent_dir / "auth.json")
    model_registry = options.model_registry or ModelRegistry(
        auth_storage,
        agent_dir / "models.json",
    )

    settings_manager = options.settings_manager or SettingsManager.create(cwd, agent_dir)
    session_manager = options.session_manager or SessionManager.create(cwd)

    # Load resources
    resource_loader = options.resource_loader or DefaultResourceLoader({
        "cwd": str(cwd),
        "agentDir": str(agent_dir),
        "settingsManager": settings_manager,
    })
    await resource_loader.reload()
    time("resourceLoader.reload")

    # Check for existing session
    existing_session = session_manager.build_session_context()
    has_existing_session = len(existing_session.messages) > 0
    has_thinking_entry = any(
        e.type == "thinking_level_change"
        for e in session_manager.get_branch()
    )

    model = options.model
    model_fallback_message: Optional[str] = None

    # Restore model from session if available
    if not model and has_existing_session and existing_session.model:
        provider = existing_session.model["provider"]
        model_id = existing_session.model["modelId"]
        restored_model = model_registry.find(provider, model_id)
        if restored_model and model_registry.get_api_key(restored_model):
            model = restored_model
        else:
            model_fallback_message = f"Could not restore model {provider}/{model_id}"

    # Find initial model if none set
    if not model:
        result = find_initial_model(
            scoped_models=options.scoped_models or [],
            is_continuing=has_existing_session,
            default_provider=settings_manager.get_default_provider(),
            default_model_id=settings_manager.get_default_model(),
            default_thinking_level=settings_manager.get_default_thinking_level(),
            model_registry=model_registry,
        )
        model = result.model
        if not model:
            model_fallback_message = (
                "No models available. Use /login or set an API key environment variable. "
                "Then use /model to select a model."
            )
        elif model_fallback_message:
            provider = model.provider
            model_id = model.id
            model_fallback_message += f". Using {provider}/{model_id}"

    thinking_level = options.thinking_level

    # Restore thinking level from session
    if thinking_level is None and has_existing_session:
        thinking_level = (
            existing_session.thinking_level
            if has_thinking_entry
            else settings_manager.get_default_thinking_level() or DEFAULT_THINKING_LEVEL
        )

    # Fall back to settings default
    if thinking_level is None:
        thinking_level = settings_manager.get_default_thinking_level() or DEFAULT_THINKING_LEVEL

    # Clamp to model capabilities
    if not model or not model.reasoning:
        thinking_level = "off"

    # Get tools
    default_active_tools = ["read", "bash", "edit", "write"]
    all_tools = {t.name: t for t in get_builtin_tools()}

    if options.tools:
        initial_tools = [
            all_tools[name] for name in options.tools if name in all_tools
        ]
    else:
        initial_tools = [all_tools[name] for name in default_active_tools if name in all_tools]

    # Create convertToLlm wrapper that filters images if blockImages is enabled
    def convert_to_llm_with_block_images(messages):
        from ..core.messages import convertToLlm
        converted = convertToLlm(messages)
        if not settings_manager.get_block_images():
            return converted
        # Filter out ImageContent blocks
        filtered = []
        for msg in converted:
            if msg.role in ("user", "toolResult"):
                content = msg.content if isinstance(msg.content, list) else [msg.content]
                filtered_content = []
                for block in content:
                    if block.type != "image":
                        filtered_content.append(block)
                msg.content = filtered_content
            filtered.append(msg)
        return filtered

    # Create agent options
    from pi.agent import AgentOptions
    agent_opts = AgentOptions(
        initial_state={
            "systemPrompt": get_default_system_prompt(),
            "model": model,
            "thinkingLevel": thinking_level,
            "tools": [],
        },
        convert_to_llm=convert_to_llm_with_block_images,
        session_id=session_manager.get_session_id(),
        transform_context=None,  # Extension support would go here
        steering_mode=settings_manager.get_steering_mode(),
        follow_up_mode=settings_manager.get_follow_up_mode(),
        transport=settings_manager.get_transport(),
        thinking_budgets={
            "minimal": settings_manager.get_thinking_budgets().minimal,
            "low": settings_manager.get_thinking_budgets().low,
            "medium": settings_manager.get_thinking_budgets().medium,
            "high": settings_manager.get_thinking_budgets().high,
            "xhigh": settings_manager.get_thinking_budgets().xhigh,
        },
        max_retry_delay_ms=settings_manager.get_retry_settings().max_delay_ms,
        get_api_key=lambda provider: model_registry.get_api_key_for_provider(provider),
    )

    # Create agent
    agent = Agent(agent_opts)

    # Restore messages if session has existing data
    if has_existing_session:
        agent.replace_messages(existing_session.messages)
        if not has_thinking_entry:
            session_manager.append_thinking_level_change(thinking_level)
    else:
        # Save initial model and thinking level
        if model:
            session_manager.append_model_change(model.provider, model.id)
        session_manager.append_thinking_level_change(thinking_level)

    # Create agent session
    session = AgentSession(
        agent=agent,
        session_manager=session_manager,
        settings_manager=settings_manager,
        cwd=cwd,
        scoped_models=options.scoped_models,
        resource_loader=resource_loader,
        custom_tools=options.custom_tools,
        model_registry=model_registry,
        initial_active_tool_names=options.tools or default_active_tools,
    )

    extensions_result = resource_loader.get_extensions()

    return CreateAgentSessionResult(
        session=session,
        extensions_result=extensions_result,
        model_fallback_message=model_fallback_message,
    )


# Re-export tools
from ..tools import (
    ReadTool,
    WriteTool,
    BashTool,
    get_builtin_tools,
)


__all__ = [
    "CreateAgentSessionOptions",
    "CreateAgentSessionResult",
    "create_agent_session",
    # Re-exports
    "ReadTool",
    "WriteTool",
    "BashTool",
    "get_builtin_tools",
]
