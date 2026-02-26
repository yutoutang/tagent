"""
Core type definitions for the AI abstraction layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    TypedDict,
    Union,
)
import time


# API Types
KnownApi = Literal[
    "openai-completions",
    "openai-responses",
    "azure-openai-responses",
    "openai-codex-responses",
    "anthropic-messages",
    "bedrock-converse-stream",
    "google-generative-ai",
    "google-gemini-cli",
    "google-vertex",
]

Api = Union[KnownApi, str]


# Provider Types
KnownProvider = Literal[
    "amazon-bedrock",
    "anthropic",
    "google",
    "google-gemini-cli",
    "google-antigravity",
    "google-vertex",
    "openai",
    "azure-openai-responses",
    "openai-codex",
    "github-copilot",
    "xai",
    "groq",
    "cerebras",
    "openrouter",
    "vercel-ai-gateway",
    "zai",
    "mistral",
    "minimax",
    "minimax-cn",
    "huggingface",
    "opencode",
    "kimi-coding",
]

Provider = Union[KnownProvider, str]


# Thinking Level
ThinkingLevel = Literal["minimal", "low", "medium", "high", "xhigh"]


class ThinkingBudgets(TypedDict, total=False):
    """Token budgets for each thinking level (token-based providers only)."""
    minimal: int
    low: int
    medium: int
    high: int


CacheRetention = Literal["none", "short", "long"]
Transport = Literal["sse", "websocket", "auto"]


class StreamOptions(TypedDict, total=False):
    """Base options all providers share."""
    temperature: Optional[float]
    maxTokens: Optional[int]
    signal: Optional[Any]  # AbortSignal equivalent
    apiKey: Optional[str]
    transport: Optional[Transport]
    cacheRetention: Optional[CacheRetention]
    sessionId: Optional[str]
    onPayload: Optional[Callable[[Any], None]]
    headers: Optional[Dict[str, str]]
    maxRetryDelayMs: Optional[int]
    metadata: Optional[Dict[str, Any]]


ProviderStreamOptions = Dict[str, Any]  # StreamOptions & Record<string, unknown>


class SimpleStreamOptions(StreamOptions, total=False):
    """Unified options with reasoning passed to streamSimple() and completeSimple()."""
    reasoning: Optional[ThinkingLevel]
    thinkingBudgets: Optional[ThinkingBudgets]


# Content Types
@dataclass
class TextContent:
    type: Literal["text"] = "text"
    text: str = ""
    textSignature: Optional[str] = None  # e.g., for OpenAI responses, the message ID


@dataclass
class ThinkingContent:
    type: Literal["thinking"] = "thinking"
    thinking: str = ""
    thinkingSignature: Optional[str] = None  # e.g., for OpenAI responses, the reasoning item ID


@dataclass
class ImageContent:
    type: Literal["image"] = "image"
    data: str = ""  # base64 encoded image data
    mimeType: str = ""  # e.g., "image/jpeg", "image/png"


@dataclass
class ToolCall:
    type: Literal["toolCall"] = "toolCall"
    id: str = ""
    name: str = ""
    arguments: Dict[str, Any] = field(default_factory=dict)
    thoughtSignature: Optional[str] = None  # Google-specific: opaque signature for reusing thought context


@dataclass
class UsageCost:
    input: float = 0.0
    output: float = 0.0
    cacheRead: float = 0.0
    cacheWrite: float = 0.0
    total: float = 0.0


@dataclass
class Usage:
    input: int = 0
    output: int = 0
    cacheRead: int = 0
    cacheWrite: int = 0
    totalTokens: int = 0
    cost: UsageCost = field(default_factory=UsageCost)


StopReason = Literal["stop", "length", "toolUse", "error", "aborted"]


@dataclass
class UserMessage:
    role: Literal["user"] = "user"
    content: Union[str, List[Union[TextContent, ImageContent]]] = ""
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))


@dataclass
class AssistantMessage:
    role: Literal["assistant"] = "assistant"
    content: List[Union[TextContent, ThinkingContent, ToolCall]] = field(default_factory=list)
    api: Api = ""
    provider: Provider = ""
    model: str = ""
    usage: Usage = field(default_factory=Usage)
    stopReason: StopReason = "stop"
    errorMessage: Optional[str] = None
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))


@dataclass
class ToolResultMessage:
    role: Literal["toolResult"] = "toolResult"
    toolCallId: str = ""
    toolName: str = ""
    content: List[Union[TextContent, ImageContent]] = field(default_factory=list)
    details: Optional[Any] = None
    isError: bool = False
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))


Message = Union[UserMessage, AssistantMessage, ToolResultMessage]


@dataclass
class Tool:
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema


@dataclass
class Context:
    systemPrompt: Optional[str] = None
    messages: List[Message] = field(default_factory=list)
    tools: Optional[List[Tool]] = None


# Event Types - Use Dict[str, Any] for flexibility
# This allows mixing dict and dataclass events
AssistantMessageEvent = Dict[str, Any]


# Compatibility Types
class OpenAICompletionsCompat(TypedDict, total=False):
    """Compatibility settings for OpenAI-compatible completions APIs."""
    supportsStore: Optional[bool]
    supportsDeveloperRole: Optional[bool]
    supportsReasoningEffort: Optional[bool]
    supportsUsageInStreaming: Optional[bool]
    maxTokensField: Optional[Literal["max_completion_tokens", "max_tokens"]]
    requiresToolResultName: Optional[bool]
    requiresAssistantAfterToolResult: Optional[bool]
    requiresThinkingAsText: Optional[bool]
    requiresMistralToolIds: Optional[bool]
    thinkingFormat: Optional[Literal["openai", "zai", "qwen"]]
    openRouterRouting: Optional["OpenRouterRouting"]
    vercelGatewayRouting: Optional["VercelGatewayRouting"]
    supportsStrictMode: Optional[bool]


class OpenAIResponsesCompat(TypedDict, total=False):
    """Compatibility settings for OpenAI Responses APIs."""
    pass


class OpenRouterRouting(TypedDict, total=False):
    """OpenRouter provider routing preferences."""
    only: Optional[List[str]]
    order: Optional[List[str]]


class VercelGatewayRouting(TypedDict, total=False):
    """Vercel AI Gateway routing preferences."""
    only: Optional[List[str]]
    order: Optional[List[str]]


# Model Types
@dataclass
class ModelCost:
    input: float = 0.0  # $/million tokens
    output: float = 0.0  # $/million tokens
    cacheRead: float = 0.0  # $/million tokens
    cacheWrite: float = 0.0  # $/million tokens


@dataclass
class Model:
    id: str
    name: str
    api: Api
    provider: Provider
    baseUrl: str
    reasoning: bool = False
    input: List[Literal["text", "image"]] = field(default_factory=lambda: ["text"])
    cost: ModelCost = field(default_factory=ModelCost)
    contextWindow: int = 0
    maxTokens: int = 0
    headers: Optional[Dict[str, str]] = None
    """Compatibility overrides for OpenAI-compatible APIs. If not set, auto-detected from baseUrl."""
    compat: Optional[Union[OpenAICompletionsCompat, OpenAIResponsesCompat]] = None


# Stream Function Type - defined at end to avoid circular imports
# This is used by api_registry and other modules
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .utils.event_stream import AssistantMessageEventStream

    StreamFunction = Callable[
        [Model, Context, Optional[StreamOptions]],
        AssistantMessageEventStream
    ]
else:
    # Runtime: use string annotation to avoid circular import
    StreamFunction = Any

