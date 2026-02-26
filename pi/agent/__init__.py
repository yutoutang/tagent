"""
Pi Agent - A Python agent framework for LLM-powered applications.

Converted from TypeScript @mariozechner/agent package.
"""

# Core Agent
from .agent import Agent, AgentOptions
from .message_utils import default_convert_to_llm

# Loop functions
from .agent_loop import (
    agent_loop,
    agent_loop_continue,
)

# Proxy utilities
from .proxy import stream_proxy, ProxyMessageEventStream

# Event Stream
from .event_stream import EventStream

# Tools
from .tools import (
    BaseTool,
    ToolExecutor,
    SyncToolWrapper,
    tool,
    ToolRegistry,
    ToolSchema,
    ParameterType,
    ParameterProperty,
    NoOpTool,
    EchoTool,
    CalculatorTool,
    GetCurrentTimeTool,
    WebSearchTool,
    get_default_registry,
    get_builtin_tools,
)

# Message utilities
from .message_utils import (
    dicts_to_agent_messages,
    create_user_message,
    create_user_message_from_content,
    default_convert_to_llm,
)

# Import AI types directly for Message types
from ..ai import UserMessage, AssistantMessage, ToolResultMessage

# Types
from .types import (
    # Content types
    TextContent,
    ImageContent,
    ThinkingContent,
    ToolCall,
    ContentBlock,
    # Message types
    Usage,
    Cost,
    BaseMessage,
    # Model types
    Model,
    ThinkingBudgets,
    # Agent types
    ThinkingLevel,
    CustomAgentMessages,
    AgentMessage,
    AgentToolResult,
    Tool,
    AgentTool,
    AgentState,
    AgentContext,
    # Event types
    AgentEvent,
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
    # Configuration types
    AgentLoopConfig,
    ProxyAssistantMessageEvent,
    ProxyStreamOptions,
)

__all__ = [
    # Core Agent
    "Agent",
    "AgentOptions",
    "default_convert_to_llm",
    # Message utilities
    "dicts_to_agent_messages",
    "create_user_message",
    "create_user_message_from_content",
    # Loop functions
    "agent_loop",
    "agent_loop_continue",
    # Proxy utilities
    "stream_proxy",
    "ProxyMessageEventStream",
    # Event Stream
    "EventStream",
    # Tools
    "BaseTool",
    "ToolExecutor",
    "SyncToolWrapper",
    "tool",
    "ToolRegistry",
    "ToolSchema",
    "ParameterType",
    "ParameterProperty",
    "NoOpTool",
    "EchoTool",
    "CalculatorTool",
    "GetCurrentTimeTool",
    "WebSearchTool",
    "get_default_registry",
    "get_builtin_tools",
    # Content types
    "TextContent",
    "ImageContent",
    "ThinkingContent",
    "ToolCall",
    "ContentBlock",
    # Message types
    "Usage",
    "Cost",
    "BaseMessage",
    "UserMessage",
    "AssistantMessage",
    "ToolResultMessage",
    "Message",
    # Model types
    "Model",
    "ThinkingBudgets",
    # Agent types
    "ThinkingLevel",
    "CustomAgentMessages",
    "AgentMessage",
    "AgentToolResult",
    "Tool",
    "AgentTool",
    "AgentState",
    "AgentContext",
    # Event types
    "AgentEvent",
    "AgentStartEvent",
    "AgentEndEvent",
    "TurnStartEvent",
    "TurnEndEvent",
    "MessageStartEvent",
    "MessageUpdateEvent",
    "MessageEndEvent",
    "ToolExecutionStartEvent",
    "ToolExecutionUpdateEvent",
    "ToolExecutionEndEvent",
    # Configuration types
    "AgentLoopConfig",
    "ProxyAssistantMessageEvent",
    "ProxyStreamOptions",
]
