"""
意图系统 - 基于 Dify 和 n8n 设计理念的意图注册与加载框架
"""

from intent_system.core.intent_definition import (
    IntentMetadata,
    InputOutputSchema,
    IntentDefinition
)
from intent_system.core.intent_registry import IntentRegistry
from intent_system.core.state import EnhancedAgentState

__version__ = "1.0.0"

__all__ = [
    "IntentMetadata",
    "InputOutputSchema",
    "IntentDefinition",
    "IntentRegistry",
    "EnhancedAgentState",
]
