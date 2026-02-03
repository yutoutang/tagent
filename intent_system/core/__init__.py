"""
核心模块 - 意图定义、注册表和状态管理
"""

from intent_system.core.intent_definition import (
    IntentMetadata,
    InputOutputSchema,
    IntentDefinition
)
from intent_system.core.intent_registry import IntentRegistry
from intent_system.core.state import EnhancedAgentState

__all__ = [
    "IntentMetadata",
    "InputOutputSchema",
    "IntentDefinition",
    "IntentRegistry",
    "EnhancedAgentState",
]
