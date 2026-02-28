"""
Model resolver for pi-coding.

Converted from TypeScript core/model-resolver.ts
"""
from typing import Any, Optional, List
from dataclasses import dataclass

from pi.agent.types import ThinkingLevel
from pi.ai.types import Model
from .model_registry import ModelRegistry


@dataclass
class ModelConfig:
    """Model configuration."""
    provider: str
    id: str
    reasoning: bool = False


@dataclass
class ResolveModelResult:
    """Result from resolving a model."""
    model: Optional[Model]
    thinking_level: ThinkingLevel


def find_initial_model(
    scoped_models: List[dict[str, Any]],
    is_continuing: bool,
    default_provider: Optional[str],
    default_model_id: Optional[str],
    default_thinking_level: Optional[ThinkingLevel],
    model_registry: ModelRegistry,
) -> ResolveModelResult:
    """
    Find the initial model to use.

    Checks in order:
    1. Scoped models (if provided)
    2. Settings default
    3. First available model with credentials

    Args:
        scoped_models: Models available for cycling
        is_continuing: Whether continuing an existing session
        default_provider: Default provider from settings
        default_model_id: Default model ID from settings
        default_thinking_level: Default thinking level from settings
        model_registry: ModelRegistry instance

    Returns:
        ResolveModelResult with model and thinking level
    """
    # Try scoped models first
    if scoped_models:
        for scoped in scoped_models:
            provider = scoped.get("provider", "")
            model_id = scoped.get("id", "")
            if provider and model_id:
                model = model_registry.find(provider, model_id)
                if model and model_registry.get_api_key(model):
                    thinking = scoped.get("thinkingLevel", default_thinking_level)
                    return ResolveModelResult(
                        model=model,
                        thinking_level=thinking or "medium",
                    )

    # Try settings default
    if default_provider and default_model_id:
        model = model_registry.find(default_provider, default_model_id)
        if model and model_registry.get_api_key(model):
            return ResolveModelResult(
                model=model,
                thinking_level=default_thinking_level or "medium",
            )

    # Try provider default from settings
    if default_provider:
        # Get first available model from provider
        models = model_registry.list_models(default_provider)
        for model_info in models:
            model_obj = model_registry.find(default_provider, model_info.id)
            if model_obj and model_registry.get_api_key(model_obj):
                return ResolveModelResult(
                    model=model_obj,
                    thinking_level=default_thinking_level or "medium",
                )

    # Try any available model with credentials
    all_models = model_registry.list_models()
    for model_info in all_models:
        model_obj = model_registry.find(model_info.provider, model_info.id)
        if model_obj and model_registry.get_api_key(model_obj):
            return ResolveModelResult(
                model=model_obj,
                thinking_level=default_thinking_level or "medium",
            )

    # No model available
    return ResolveModelResult(
        model=None,
        thinking_level=default_thinking_level or "medium",
    )


def resolve_model(
    model_pattern: str,
    thinking_level: Optional[ThinkingLevel],
    model_registry: ModelRegistry,
) -> Optional[ResolveModelResult]:
    """
    Resolve a model pattern to a specific model.

    Pattern formats:
    - "provider/id" - specific model
    - "provider/id:thinking" - specific model with thinking level
    - "id" - search for model by ID

    Args:
        model_pattern: Model pattern string
        thinking_level: Optional thinking level override
        model_registry: ModelRegistry instance

    Returns:
        ResolveModelResult or None if not found
    """
    # Parse pattern
    parts = model_pattern.split(":")

    # Check for thinking level suffix
    parsed_thinking: Optional[ThinkingLevel] = None
    if len(parts) > 1:
        thinking_str = parts[-1]
        if thinking_str in ("off", "minimal", "low", "medium", "high", "xhigh"):
            parsed_thinking = thinking_str
            parts.pop()

    # Join remaining parts
    model_spec = ":".join(parts)

    # Check for provider/id format
    if "/" in model_spec:
        provider, model_id = model_spec.split("/", 1)
        model = model_registry.find(provider, model_id)
        if model:
            return ResolveModelResult(
                model=model,
                thinking_level=parsed_thinking or thinking_level or "medium",
            )

    # Search by model ID
    results = model_registry.search(model_spec)
    if results:
        model_info = results[0]
        model = model_registry.find(model_info.provider, model_info.id)
        if model:
            return ResolveModelResult(
                model=model,
                thinking_level=parsed_thinking or thinking_level or "medium",
            )

    return None


__all__ = [
    "ModelConfig",
    "ResolveModelResult",
    "find_initial_model",
    "resolve_model",
]
