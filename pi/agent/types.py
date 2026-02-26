"""
Type definitions for the agent system.
Converted from TypeScript types.ts
"""
from typing import Any, Callable, TypeAlias, TypedDict, Union
from typing_extensions import Literal, NotRequired
from enum import Enum
import time

from pi.ai import Model, Message, AssistantMessage, ToolResultMessage


# ============================================================================
# Content Types
# ============================================================================

class TextContent(TypedDict):
    type: Literal["text"]
    text: str
    textSignature: NotRequired[str]


class ImageContent(TypedDict):
    type: Literal["image"]
    image: str
    mimeType: NotRequired[str]


class ThinkingContent(TypedDict):
    type: Literal["thinking"]
    thinking: str
    thinkingSignature: NotRequired[str]


class ToolCall(TypedDict):
    type: Literal["toolCall"]
    id: str
    name: str
    arguments: dict[str, Any]


ContentBlock = Union[TextContent, ImageContent, ThinkingContent, ToolCall]


# ============================================================================
# Message Types
# ============================================================================

class Usage(TypedDict):
    input: int
    output: int
    cacheRead: int
    cacheWrite: int
    totalTokens: int
    cost: dict[str, float]


class Cost(TypedDict):
    input: float
    output: float
    cacheRead: float
    cacheWrite: float
    total: float


class BaseMessage(TypedDict):
    role: str
    timestamp: int


# ============================================================================
# Streaming Types
# ============================================================================

class AssistantMessageEvent(TypedDict):
    type: str
    partial: NotRequired[AssistantMessage]
    contentIndex: NotRequired[int]
    delta: NotRequired[str]
    content: NotRequired[str]
    toolCall: NotRequired[ToolCall]

class ThinkingBudgets(TypedDict):
    minimal: int
    low: int
    medium: int
    high: int
    xhigh: int


# ============================================================================
# Agent Types
# ============================================================================

ThinkingLevel = Literal["off", "minimal", "low", "medium", "high", "xhigh"]


class CustomAgentMessages(TypedDict):
    """Extensible interface for custom app messages."""
    pass


AgentMessage = Union[Message, CustomAgentMessages]


class AgentToolResult(TypedDict):
    content: list[Union[TextContent, ImageContent]]
    details: Any


class Tool(TypedDict):
    name: str
    description: str
    parameters: dict[str, Any]


class AgentTool(Tool):
    label: str


class AgentState(TypedDict):
    systemPrompt: str
    model: Model
    thinkingLevel: ThinkingLevel
    tools: list[AgentTool]
    messages: list[AgentMessage]
    isStreaming: bool
    streamMessage: AgentMessage | None
    pendingToolCalls: set[str]
    error: str | None


class AgentContext(TypedDict):
    systemPrompt: str
    messages: list[AgentMessage]
    tools: list[AgentTool] | None


# ============================================================================
# Event Types
# ============================================================================

class AgentStartEvent(TypedDict):
    type: Literal["agent_start"]


class AgentEndEvent(TypedDict):
    type: Literal["agent_end"]
    messages: list[AgentMessage]


class TurnStartEvent(TypedDict):
    type: Literal["turn_start"]


class TurnEndEvent(TypedDict):
    type: Literal["turn_end"]
    message: AgentMessage
    toolResults: list[ToolResultMessage]


class MessageStartEvent(TypedDict):
    type: Literal["message_start"]
    message: AgentMessage


class MessageUpdateEvent(TypedDict):
    type: Literal["message_update"]
    message: AgentMessage
    assistantMessageEvent: AssistantMessageEvent


class MessageEndEvent(TypedDict):
    type: Literal["message_end"]
    message: AgentMessage


class ToolExecutionStartEvent(TypedDict):
    type: Literal["tool_execution_start"]
    toolCallId: str
    toolName: str
    args: Any


class ToolExecutionUpdateEvent(TypedDict):
    type: Literal["tool_execution_update"]
    toolCallId: str
    toolName: str
    args: Any
    partialResult: Any


class ToolExecutionEndEvent(TypedDict):
    type: Literal["tool_execution_end"]
    toolCallId: str
    toolName: str
    result: Any
    isError: bool


AgentEvent = Union[
    AgentStartEvent,
    AgentEndEvent,
    TurnStartEvent,
    TurnEndEvent,
    MessageStartEvent,
    MessageUpdateEvent,
    MessageEndEvent,
    ToolExecutionStartEvent,
    ToolExecutionUpdateEvent,
    ToolExecutionEndEvent,
]


# ============================================================================
# Type Aliases
# ============================================================================

StreamFn = Callable[..., Any]
AgentToolUpdateCallback = Callable[[AgentToolResult], None]
ConvertToLlmFn = Callable[[list[AgentMessage]], list[Message] | Any]
TransformContextFn = Callable[[list[AgentMessage], Any | None], Any]
GetApiKeyFn = Callable[[str], str | None | Any]
GetSteeringMessagesFn = Callable[[], Any]
GetFollowUpMessagesFn = Callable[[], Any]


# ============================================================================
# Configuration Types
# ============================================================================

class AgentLoopConfig(TypedDict):
    model: Model
    convertToLlm: ConvertToLlmFn
    transformContext: NotRequired[TransformContextFn | None]
    getApiKey: NotRequired[GetApiKeyFn | None]
    getSteeringMessages: NotRequired[GetSteeringMessagesFn | None]
    getFollowUpMessages: NotRequired[GetFollowUpMessagesFn | None]
    reasoning: NotRequired[ThinkingLevel | None]
    sessionId: NotRequired[str | None]
    thinkingBudgets: NotRequired[ThinkingBudgets | None]
    transport: NotRequired[Literal["sse"] | None]
    maxRetryDelayMs: NotRequired[int | None]
    apiKey: NotRequired[str | None]
    temperature: NotRequired[float | None]
    maxTokens: NotRequired[int | None]
    signal: NotRequired[Any | None]


class ProxyAssistantMessageEvent(TypedDict):
    type: str
    contentIndex: NotRequired[int]
    delta: NotRequired[str]
    contentSignature: NotRequired[str]
    id: NotRequired[str]
    toolName: NotRequired[str]
    reason: NotRequired[Literal["stop", "length", "toolUse", "aborted", "error"]]
    usage: NotRequired[Usage]
    errorMessage: NotRequired[str]


class ProxyStreamOptions(TypedDict):
    authToken: str
    proxyUrl: str
    signal: NotRequired[Any | None]
    temperature: NotRequired[float | None]
    maxTokens: NotRequired[int | None]
    reasoning: NotRequired[ThinkingLevel | None]
