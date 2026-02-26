"""
Stream Functions

High-level streaming functions for AI completions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, TypeVar

from .api_registry import get_api_provider
from .env_api_keys import get_env_api_key
from .providers.register_builtins import register_built_in_api_providers
from .types import (
    Api,
    AssistantMessage,
    Context,
    Model,
    ProviderStreamOptions,
    SimpleStreamOptions,
    StreamOptions,
)

if TYPE_CHECKING:
    from .utils.event_stream import AssistantMessageEventStream

TApi = TypeVar("TApi", bound=str)

# Register built-in providers on module load
register_built_in_api_providers()


def _resolve_api_provider(api: Api):
    """Resolve an API provider by API name."""
    provider = get_api_provider(api)
    if not provider:
        raise ValueError(f"No API provider registered for api: {api}")
    return provider


async def sample_stream(
    model: Model,
    context: Context,
    options: Optional[ProviderStreamOptions] = None,
) -> "AssistantMessageEventStream":
    """
    Stream a completion from a model.

    Args:
        model: The model to use
        context: The conversation context
        options: Optional streaming options

    Returns:
        An event stream of assistant message events
    """
    provider = _resolve_api_provider(model.api)
    return provider.stream(model, context, options)


async def complete(
    model: Model,
    context: Context,
    options: Optional[ProviderStreamOptions] = None,
) -> AssistantMessage:
    """
    Complete a request and return the final message.

    Args:
        model: The model to use
        context: The conversation context
        options: Optional streaming options

    Returns:
        The completed assistant message
    """
    s = stream_simple(model, context, options)
    return await s.result()


def stream_simple(
    model: Model,
    context: Context,
    options: Optional[SimpleStreamOptions] = None,
) -> "AssistantMessageEventStream":
    """
    Stream a completion with simplified options.

    Args:
        model: The model to use
        context: The conversation context
        options: Optional simplified streaming options

    Returns:
        An event stream of assistant message events
    """
    provider = _resolve_api_provider(model.api)
    return provider.stream_simple(model, context, options)


async def complete_simple(
    model: Model,
    context: Context,
    options: Optional[SimpleStreamOptions] = None,
) -> AssistantMessage:
    """
    Complete a request with simplified options and return the final message.

    Args:
        model: The model to use
        context: The conversation context
        options: Optional simplified streaming options

    Returns:
        The completed assistant message
    """
    s = stream_simple(model, context, options)
    return await s.result()
