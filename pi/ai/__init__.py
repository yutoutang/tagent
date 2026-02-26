"""
AI Provider Abstraction Layer

A unified interface for multiple AI providers including OpenAI, Anthropic, Google, and more.
"""

from .types import (
    Api,
    KnownApi,
    Provider,
    KnownProvider,
    ThinkingLevel,
    ThinkingBudgets,
    CacheRetention,
    Transport,
    StreamOptions,
    ProviderStreamOptions,
    SimpleStreamOptions,
    StreamFunction,
    TextContent,
    ThinkingContent,
    ImageContent,
    ToolCall,
    Usage,
    StopReason,
    UserMessage,
    AssistantMessage,
    ToolResultMessage,
    Message,
    Tool,
    Context,
    AssistantMessageEvent,
    OpenAICompletionsCompat,
    OpenAIResponsesCompat,
    OpenRouterRouting,
    VercelGatewayRouting,
    Model,
)

from .api_registry import (
    ApiProvider,
    register_api_provider,
    get_api_provider,
    get_api_providers,
    unregister_api_providers,
    clear_api_providers,
)

from .env_api_keys import get_env_api_key
from .models import get_model, get_providers, get_models, calculate_cost, supports_xhigh, models_are_equal
from .stream import complete, stream_simple, complete_simple
from .utils.event_stream import EventStream, AssistantMessageEventStream, create_assistant_message_event_stream
from .utils.json_parse import parse_streaming_json
from .utils.overflow import is_context_overflow, get_overflow_patterns
from .utils.validation import validate_tool_call, validate_tool_arguments

__all__ = [
    # Types
    "Api",
    "KnownApi",
    "Provider",
    "KnownProvider",
    "ThinkingLevel",
    "ThinkingBudgets",
    "CacheRetention",
    "Transport",
    "StreamOptions",
    "ProviderStreamOptions",
    "SimpleStreamOptions",
    "StreamFunction",
    "TextContent",
    "ThinkingContent",
    "ImageContent",
    "ToolCall",
    "Usage",
    "StopReason",
    "UserMessage",
    "AssistantMessage",
    "ToolResultMessage",
    "Message",
    "Tool",
    "Context",
    "AssistantMessageEvent",
    "OpenAICompletionsCompat",
    "OpenAIResponsesCompat",
    "OpenRouterRouting",
    "VercelGatewayRouting",
    "Model",
    # API Registry
    "ApiProvider",
    "register_api_provider",
    "get_api_provider",
    "get_api_providers",
    "unregister_api_providers",
    "clear_api_providers",
    # Env API Keys
    "get_env_api_key",
    # Models
    "get_model",
    "get_providers",
    "get_models",
    "calculate_cost",
    "supports_xhigh",
    "models_are_equal",
    # Stream
    "stream",
    "complete",
    "stream_simple",
    "complete_simple",
    # Utils
    "EventStream",
    "AssistantMessageEventStream",
    "create_assistant_message_event_stream",
    "parse_streaming_json",
    "is_context_overflow",
    "get_overflow_patterns",
    "validate_tool_call",
    "validate_tool_arguments",
]
