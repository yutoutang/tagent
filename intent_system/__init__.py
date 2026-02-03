"""
Intent System - 基于 Dify 和 n8n 设计理念的意图注册与编排框架

主要功能：
- 意图定义与注册
- LLM 驱动的意图解析
- 意图编排与依赖管理
- 异步意图执行
- 工作流意图管理
- 数据流转引擎

基础使用：
    >>> from intent_system import IntentRegistry, IntentDefinition
    >>> from intent_system import IntentParser, IntentOrchestrator, IntentExecutor
    >>>
    >>> registry = IntentRegistry()
    >>> parser = IntentParser(llm, registry)
    >>> orchestrator = IntentOrchestrator(registry)
    >>> executor = IntentExecutor(registry)

工作流使用：
    >>> from intent_system.workflow import WorkflowIntentManager
    >>> manager = WorkflowIntentManager()
    >>> manager.load_from_json("workflow.json")
"""

__version__ = "1.0.0"

# 核心模块
from intent_system.core.intent_definition import (
    IntentMetadata,
    InputOutputSchema,
    IntentDefinition
)
from intent_system.core.intent_registry import IntentRegistry
from intent_system.core.intent_parser import IntentParser, IntentParseResult
from intent_system.core.state import EnhancedAgentState

# 编排模块
from intent_system.orchestration import IntentOrchestrator

# 执行模块
from intent_system.execution import IntentExecutor

# 数据流转模块
from intent_system.data_flow import DataFlowEngine

# 工作流模块
from intent_system.workflow import (
    WorkflowIntentManager,
    WorkflowIntentDefinition,
    WorkflowGuidance,
    load_workflow_from_json
)

# 内置意图
from intent_system.builtin_intents import register_builtin_data_intents

__all__ = [
    # 版本
    "__version__",

    # 核心模块
    "IntentMetadata",
    "InputOutputSchema",
    "IntentDefinition",
    "IntentRegistry",
    "IntentParser",
    "IntentParseResult",
    "EnhancedAgentState",

    # 编排模块
    "IntentOrchestrator",

    # 执行模块
    "IntentExecutor",

    # 数据流转
    "DataFlowEngine",

    # 工作流
    "WorkflowIntentManager",
    "WorkflowIntentDefinition",
    "WorkflowGuidance",
    "load_workflow_from_json",

    # 内置意图
    "register_builtin_data_intents",
]
