"""
Model Registry and Utilities

Functions for working with AI models, including cost calculation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypeVar, Union

from .types import Api, KnownProvider, Model, Usage

TApi = TypeVar("TApi", bound=str)

# Model registry: provider -> model_id -> Model
_model_registry: Dict[str, Dict[str, Model]] = {}


def _init_registry_from_models(models: Dict[str, Dict[str, Any]]) -> None:
    """Initialize the model registry from a models dictionary."""
    global _model_registry
    _model_registry = {}

    for provider, provider_models in models.items():
        _model_registry[provider] = {}
        for model_id, model_data in provider_models.items():
            _model_registry[provider][model_id] = Model(
                id=model_data.get("id", model_id),
                name=model_data.get("name", model_id),
                api=model_data.get("api", ""),
                provider=model_data.get("provider", provider),
                baseUrl=model_data.get("baseUrl", ""),
                reasoning=model_data.get("reasoning", False),
                input=model_data.get("input", ["text"]),
                cost=model_data.get("cost", {}),
                contextWindow=model_data.get("contextWindow", 0),
                maxTokens=model_data.get("maxTokens", 0),
                headers=model_data.get("headers"),
                compat=model_data.get("compat"),
            )


def get_model(provider: str, model_id: str) -> Optional[Model]:
    """
    Get a model by provider and model ID.

    Args:
        provider: The provider name
        model_id: The model ID

    Returns:
        The model or None if not found
    """
    provider_models = _model_registry.get(provider)
    if provider_models:
        return provider_models.get(model_id)
    return None


def get_providers() -> List[str]:
    """
    Get all registered providers.

    Returns:
        List of provider names
    """
    return list(_model_registry.keys())


def get_models(provider: str) -> List[Model]:
    """
    Get all models for a provider.

    Args:
        provider: The provider name

    Returns:
        List of models for the provider
    """
    provider_models = _model_registry.get(provider)
    return list(provider_models.values()) if provider_models else []


def calculate_cost(model: Model, usage: Usage) -> Usage.cost.__class__:
    """
    Calculate the cost of a request based on model pricing and usage.

    Args:
        model: The model used
        usage: The usage statistics

    Returns:
        The cost breakdown
    """
    usage.cost.input = (model.cost.input / 1000000) * usage.input
    usage.cost.output = (model.cost.output / 1000000) * usage.output
    usage.cost.cacheRead = (model.cost.cacheRead / 1000000) * usage.cacheRead
    usage.cost.cacheWrite = (model.cost.cacheWrite / 1000000) * usage.cacheWrite
    usage.cost.total = (
        usage.cost.input +
        usage.cost.output +
        usage.cost.cacheRead +
        usage.cost.cacheWrite
    )
    return usage.cost


def supports_xhigh(model: Model) -> bool:
    """
    Check if a model supports xhigh thinking level.

    Supported today:
    - GPT-5.2 / GPT-5.3 model families
    - Anthropic Messages API Opus 4.6 models (xhigh maps to adaptive effort "max")

    Args:
        model: The model to check

    Returns:
        True if the model supports xhigh thinking
    """
    if "gpt-5.2" in model.id or "gpt-5.3" in model.id:
        return True

    if model.api == "anthropic-messages":
        return "opus-4-6" in model.id or "opus-4.6" in model.id

    return False


def models_are_equal(
    a: Optional[Model],
    b: Optional[Model],
) -> bool:
    """
    Check if two models are equal by comparing both their id and provider.
    Returns False if either model is None.

    Args:
        a: First model
        b: Second model

    Returns:
        True if the models are equal
    """
    if not a or not b:
        return False
    return a.id == b.id and a.provider == b.provider


# Initialize with empty registry - will be populated by generated models
_init_registry_from_models({})
