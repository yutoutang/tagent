"""
Register Built-in API Providers

Registers all built-in API providers for the AI abstraction layer.
"""

from __future__ import annotations

from ..api_registry import ApiProvider, clear_api_providers, register_api_provider
from .anthropic import stream_anthropic, stream_simple_anthropic
from .openai_completions import stream_openai_completions, stream_simple_openai_completions
from .google import stream_google, stream_simple_google


def register_built_in_api_providers() -> None:
    """Register all built-in API providers."""
    # Anthropic Messages API
    register_api_provider(ApiProvider(
        api="anthropic-messages",
        stream=stream_anthropic,
        stream_simple=stream_simple_anthropic,
    ))

    # OpenAI Completions API
    register_api_provider(ApiProvider(
        api="openai-completions",
        stream=stream_openai_completions,
        stream_simple=stream_simple_openai_completions,
    ))

    # Google Generative AI API
    register_api_provider(ApiProvider(
        api="google-generative-ai",
        stream=stream_google,
        stream_simple=stream_simple_google,
    ))

    # Note: Additional providers can be added here:
    # - openai-responses
    # - azure-openai-responses
    # - openai-codex-responses
    # - google-gemini-cli
    # - google-vertex
    # - bedrock-converse-stream


def reset_api_providers() -> None:
    """Reset API providers to default state."""
    clear_api_providers()
    register_built_in_api_providers()


# Auto-register on import
register_built_in_api_providers()
