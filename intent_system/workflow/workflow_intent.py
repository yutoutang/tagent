"""
工作流意图定义

扩展标准意图定义，支持前置/后置意图关系和流程指导
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from intent_system.core.intent_definition import IntentDefinition


class WorkflowGuidance(BaseModel):
    """
    工作流指导信息

    为工作流中的每个阶段提供进入和完成时的指导
    """
    entry: str = Field(description="进入该意图阶段时的指导")
    completion: str = Field(description="完成该意图阶段时的指导")
    next_actions: List[str] = Field(
        default_factory=list,
        description="建议的下一步操作列表"
    )


class WorkflowIntentDefinition(BaseModel):
    """
    工作流意图定义

    扩展标准意图，添加工作流特性：
    - 前置意图 (pre_intents): 必须先完成这些意图才能执行当前意图
    - 后置意图 (post_intents): 当前意图完成后可以执行这些意图
    - 指导信息 (guidance): 提供流程导航和操作建议
    """
    # 标准意图字段
    id: str = Field(description="唯一标识符")
    name: str = Field(description="显示名称")
    description: str = Field(description="功能描述")
    category: str = Field(default="workflow", description="类别")

    # 工作流关系
    pre_intents: List[str] = Field(
        default_factory=list,
        description="前置意图ID列表（依赖关系）"
    )
    post_intents: List[str] = Field(
        default_factory=list,
        description="后置意图ID列表（可导航到的意图）"
    )

    # 流程指导
    guidance: Optional[WorkflowGuidance] = Field(
        default=None,
        description="工作流指导信息"
    )

    # 执行器（可选）
    executor: Optional[callable] = Field(
        default=None,
        description="意图执行函数"
    )

    # 元数据
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="额外的元数据"
    )

    class Config:
        arbitrary_types_allowed = True

    def to_intent_definition(self) -> IntentDefinition:
        """
        转换为标准意图定义

        Returns:
            IntentDefinition 实例
        """
        from intent_system.core.intent_definition import (
            IntentMetadata,
            InputOutputSchema
        )

        # 创建元数据
        metadata = IntentMetadata(
            id=self.id,
            name=self.name,
            description=self.description,
            category=self.category,
            dependencies=self.pre_intents,  # 前置意图作为依赖
            tags=self.metadata.get("tags", [])
        )

        # 创建空的schema（工作流意图可能不需要特定的输入输出）
        schema = InputOutputSchema()

        # 创建执行器（如果有）
        executor = self.executor or (lambda **kwargs: {"status": "completed"})

        return IntentDefinition(
            metadata=metadata,
            schema=schema,
            executor=executor
        )

    def get_display_path(self, all_intents: Dict[str, 'WorkflowIntentDefinition']) -> str:
        """
        获取显示路径

        Args:
            all_intents: 所有意图的字典

        Returns:
            格式化的路径字符串
        """
        parts = []

        # 添加前置意图
        if self.pre_intents:
            pre_names = []
            for pre_id in self.pre_intents:
                if pre_id in all_intents:
                    pre_names.append(all_intents[pre_id].name)
            if pre_names:
                parts.append(" -> ".join(pre_names))

        # 添加当前意图
        parts.append(self.name)

        # 添加后置意图
        if self.post_intents:
            post_names = []
            for post_id in self.post_intents:
                if post_id in all_intents:
                    post_names.append(all_intents[post_id].name)
            if post_names:
                parts.append(" -> ".join(post_names))

        return " -> ".join(parts)

    def __str__(self) -> str:
        """字符串表示"""
        return f"WorkflowIntent({self.id}, name='{self.name}')"

    def __repr__(self) -> str:
        """详细表示"""
        return (
            f"WorkflowIntentDefinition(\n"
            f"  id={self.id},\n"
            f"  name={self.name},\n"
            f"  pre_intents={self.pre_intents},\n"
            f"  post_intents={self.post_intents}\n"
            f")"
        )
