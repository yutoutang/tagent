"""
工作流意图管理系统

集成到 intent_system 框架中，支持：
- 从JSON加载工作流意图定义
- 前置/后置意图关系管理
- 意图图谱生成和可视化
- 流程导航和指导
"""

from .workflow_manager import WorkflowIntentManager
from .workflow_intent import WorkflowIntentDefinition, WorkflowGuidance
from .json_loader import load_workflow_from_json

__all__ = [
    "WorkflowIntentManager",
    "WorkflowIntentDefinition",
    "WorkflowGuidance",
    "load_workflow_from_json",
]
