"""
统一 Agent 状态定义

融合原有的 AgentState 和 EnhancedAgentState，提供统一的状态管理
"""

from typing import Any, Dict, List, Optional, Annotated
from enum import Enum
from operator import add

from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """任务类型枚举"""
    CODING = "coding"
    RESEARCH = "research"
    ANALYSIS = "analysis"
    CALCULATION = "calculation"
    GENERAL = "general"


class IntentExecutionTrace(BaseModel):
    """
    意图执行追踪记录
    """
    intent_id: str = Field(description="意图 ID")
    start_time: float = Field(description="开始时间戳")
    end_time: Optional[float] = Field(default=None, description="结束时间戳")
    status: str = Field(
        default="pending",
        description="状态: pending/running/success/failed"
    )
    input_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="输入数据"
    )
    output_data: Optional[Any] = Field(default=None, description="输出数据")
    error: Optional[str] = Field(default=None, description="错误信息")
    retry_count: int = Field(default=0, description="重试次数")

    @property
    def duration(self) -> Optional[float]:
        """获取执行时长"""
        if self.end_time is not None:
            return self.end_time - self.start_time
        return None


class ReflectionResult(BaseModel):
    """
    反思结果
    """
    should_continue: bool = Field(description="是否需要继续执行")
    confidence: float = Field(description="对当前结果的置信度 0-1")
    issues: List[str] = Field(
        default_factory=list,
        description="发现的问题列表"
    )
    suggestions: List[str] = Field(
        default_factory=list,
        description="改进建议列表"
    )
    reasoning: str = Field(description="反思理由")


class UnifiedAgentState(BaseModel):
    """
    统一 Agent 状态

    融合了原有的 AgentState 和 EnhancedAgentState 的所有功能
    """

    # ========== 消息相关 ==========
    messages: List[BaseMessage] = Field(
        default_factory=list,
        description="对话历史消息"
    )

    # ========== 任务分类相关 ==========
    task_type: Optional[TaskType] = Field(
        default=None,
        description="任务类型"
    )
    task_confidence: Optional[float] = Field(
        default=None,
        description="任务分类置信度"
    )

    # ========== 意图识别相关 ==========
    detected_intents: List[str] = Field(
        default_factory=list,
        description="检测到的意图ID列表"
    )
    intent_confidence: float = Field(
        default=0.0,
        description="意图识别置信度 (0-1)"
    )
    intent_parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="从用户输入中提取的意图参数"
    )

    # ========== 工具相关 ==========
    available_tools: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="可用工具列表"
    )
    executed_tools: List[str] = Field(
        default_factory=list,
        description="已执行的工具列表"
    )

    # ========== 编排计划相关 ==========
    orchestration_plan: Optional[Dict[str, Any]] = Field(
        default=None,
        description="意图编排计划"
    )

    # ========== 执行状态相关 ==========
    intent_results: Dict[str, Any] = Field(
        default_factory=dict,
        description="已执行意图的结果"
    )
    current_layer: int = Field(
        default=0,
        description="当前执行的层级索引"
    )

    # ========== 执行结果相关 ==========
    result: Optional[str] = Field(
        default=None,
        description="最终执行结果"
    )
    intermediate_steps: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="中间执行步骤"
    )

    # ========== 反思相关 ==========
    reflection_result: Optional[ReflectionResult] = Field(
        default=None,
        description="反思结果"
    )

    # ========== 追踪相关 ==========
    execution_traces: List[IntentExecutionTrace] = Field(
        default_factory=list,
        description="意图执行追踪记录列表"
    )

    # ========== 数据上下文相关 ==========
    data_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="数据流转上下文"
    )

    # ========== 控制流相关 ==========
    iteration: int = Field(
        default=0,
        description="当前迭代次数"
    )
    max_iterations: int = Field(
        default=3,
        description="最大迭代次数"
    )
    is_complete: bool = Field(
        default=False,
        description="是否完成"
    )

    # ========== 错误处理相关 ==========
    errors: List[str] = Field(
        default_factory=list,
        description="错误列表"
    )

    # ========== 元数据相关 ==========
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="元数据"
    )

    class Config:
        arbitrary_types_allowed = True

    def add_execution_trace(self, trace: IntentExecutionTrace) -> None:
        """添加执行追踪记录"""
        self.execution_traces.append(trace)

    def update_intent_result(self, intent_id: str, result: Any) -> None:
        """更新意图执行结果"""
        self.intent_results[intent_id] = result
        self.data_context[intent_id] = result

    def is_intent_executed(self, intent_id: str) -> bool:
        """检查意图是否已执行"""
        return intent_id in self.intent_results

    def get_execution_summary(self) -> Dict[str, Any]:
        """获取执行摘要"""
        successful = [t for t in self.execution_traces if t.status == "success"]
        failed = [t for t in self.execution_traces if t.status == "failed"]

        total_duration = sum(
            (t.end_time or t.start_time) - t.start_time
            for t in self.execution_traces
            if t.end_time is not None
        )

        return {
            "total_intents": len(self.execution_traces),
            "successful": len(successful),
            "failed": len(failed),
            "total_duration": total_duration,
            "intents": [
                {
                    "intent_id": t.intent_id,
                    "status": t.status,
                    "duration": t.duration,
                    "error": t.error
                }
                for t in self.execution_traces
            ]
        }

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """转换为字典（处理不可序列化的对象）"""
        data = super().model_dump(**kwargs)
        # 处理 messages 中的 BaseMessage
        data["messages"] = [
            {"type": type(m).__name__, "content": m.content}
            for m in self.messages
        ]
        return data
