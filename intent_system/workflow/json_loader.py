"""
工作流JSON加载器

从JSON文件加载工作流意图定义
"""

import json
from pathlib import Path
from typing import Dict, List

from .workflow_intent import WorkflowIntentDefinition, WorkflowGuidance


def load_workflow_from_json(
    json_path: str,
    auto_register: bool = True,
    registry = None
) -> List[WorkflowIntentDefinition]:
    """
    从JSON文件加载工作流意图定义

    Args:
        json_path: JSON文件路径
        auto_register: 是否自动注册到IntentRegistry
        registry: IntentRegistry实例（如果auto_register=True）

    Returns:
        加载的工作流意图列表

    Raises:
        FileNotFoundError: 如果文件不存在
        ValueError: 如果JSON格式无效
    """
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"工作流定义文件不存在: {json_path}")

    # 读取JSON文件
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 解析意图定义
    intents = []
    for intent_data in data.get('intents', []):
        intent = _parse_intent_definition(intent_data)
        intents.append(intent)

        # 自动注册到标准意图注册表
        if auto_register and registry is not None:
            try:
                standard_intent = intent.to_intent_definition()
                registry.register(standard_intent)
            except Exception as e:
                import warnings
                warnings.warn(f"自动注册意图 {intent.id} 失败: {e}")

    return intents


def _parse_intent_definition(data: Dict) -> WorkflowIntentDefinition:
    """
    解析单个意图定义

    Args:
        data: 意图数据字典

    Returns:
        WorkflowIntentDefinition 实例
    """
    # 解析指导信息
    guidance = None
    if 'guidance' in data:
        g = data['guidance']
        guidance = WorkflowGuidance(
            entry=g.get('entry', ''),
            completion=g.get('completion', ''),
            next_actions=g.get('next_actions', [])
        )

    return WorkflowIntentDefinition(
        id=data['id'],
        name=data['name'],
        description=data['description'],
        category=data.get('category', 'workflow'),
        pre_intents=data.get('pre_intents', []),
        post_intents=data.get('post_intents', []),
        guidance=guidance,
        metadata=data.get('metadata', {})
    )


def export_workflow_to_json(
    intents: List[WorkflowIntentDefinition],
    json_path: str,
    description: str = ""
) -> None:
    """
    将工作流意图导出为JSON文件

    Args:
        intents: 工作流意图列表
        json_path: 输出文件路径
        description: 工作流描述
    """
    data = {
        "version": "1.0.0",
        "description": description,
        "intents": []
    }

    for intent in intents:
        intent_data = {
            "id": intent.id,
            "name": intent.name,
            "description": intent.description,
            "category": intent.category,
            "pre_intents": intent.pre_intents,
            "post_intents": intent.post_intents,
            "metadata": intent.metadata
        }

        if intent.guidance:
            intent_data["guidance"] = {
                "entry": intent.guidance.entry,
                "completion": intent.guidance.completion,
                "next_actions": intent.guidance.next_actions
            }

        data["intents"].append(intent_data)

    # 写入文件
    path = Path(json_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
