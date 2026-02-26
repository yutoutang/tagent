"""
API Provider Registry

Manages registration and retrieval of API providers for streaming.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Dict, Generic, Optional, TypeVar

from .types import (
    Api,
    Context,
    Model,
    SimpleStreamOptions,
    StreamOptions,
)

if TYPE_CHECKING:
    from .utils.event_stream import AssistantMessageEventStream

TApi = TypeVar("TApi", bound=str)
TOptions = TypeVar("TOptions", bound=Dict[str, Any])

# Type aliases for stream functions
StreamFunction = Callable[
    [Model, Context, Optional[StreamOptions]],
    "AssistantMessageEventStream"
]
StreamSimpleFunction = Callable[
    [Model, Context, Optional[SimpleStreamOptions]],
    "AssistantMessageEventStream"
]


@dataclass
class ApiProvider(Generic[TApi, TOptions]):
    """API Provider configuration."""
    api: TApi
    stream: StreamFunction
    stream_simple: StreamFunction


@dataclass
class _ApiProviderInternal:
    """Internal API provider representation."""
    api: Api
    stream: StreamFunction
    stream_simple: StreamSimpleFunction


@dataclass
class _RegisteredApiProvider:
    """Registered API provider with optional source ID."""
    provider: _ApiProviderInternal
    source_id: Optional[str] = None


# Global registry
_api_provider_registry: Dict[str, _RegisteredApiProvider] = {}


def _wrap_stream(
    api: Api,
    stream: StreamFunction,
) -> StreamFunction:
    """Wrap a stream function with API validation."""
    def wrapped(model: Model, context: Context, options: Optional[StreamOptions] = None) -> "AssistantMessageEventStream":
        if model.api != api:
            raise ValueError(f"Mismatched api: {model.api} expected {api}")
        return stream(model, context, options)
    return wrapped


def _wrap_stream_simple(
    api: Api,
    stream_simple: StreamFunction,
) -> StreamSimpleFunction:
    """Wrap a stream_simple function with API validation."""
    def wrapped(model: Model, context: Context, options: Optional[SimpleStreamOptions] = None) -> "AssistantMessageEventStream":
        if model.api != api:
            raise ValueError(f"Mismatched api: {model.api} expected {api}")
        return stream_simple(model, context, options)
    return wrapped


def register_api_provider(
    provider: ApiProvider,
    source_id: Optional[str] = None,
) -> None:
    """
    Register an API provider.

    Args:
        provider: The API provider configuration
        source_id: Optional source identifier for later unregistration
    """
    _api_provider_registry[provider.api] = _RegisteredApiProvider(
        provider=_ApiProviderInternal(
            api=provider.api,
            stream=_wrap_stream(provider.api, provider.stream),
            stream_simple=_wrap_stream_simple(provider.api, provider.stream_simple),
        ),
        source_id=source_id,
    )


def get_api_provider(api: Api) -> Optional[_ApiProviderInternal]:
    """
    Get an API provider by API name.

    Args:
        api: The API name

    Returns:
        The API provider or None if not found
    """
    entry = _api_provider_registry.get(api)
    return entry.provider if entry else None


def get_api_providers() -> list[_ApiProviderInternal]:
    """
    Get all registered API providers.

    Returns:
        List of all registered API providers
    """
    return [entry.provider for entry in _api_provider_registry.values()]


def unregister_api_providers(source_id: str) -> None:
    """
    Unregister all API providers from a specific source.

    Args:
        source_id: The source identifier to unregister
    """
    apis_to_remove = [
        api for api, entry in _api_provider_registry.items()
        if entry.source_id == source_id
    ]
    for api in apis_to_remove:
        del _api_provider_registry[api]


def clear_api_providers() -> None:
    """Clear all registered API providers."""
    _api_provider_registry.clear()
