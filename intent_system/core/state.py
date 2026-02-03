"""
状态定义 - 扩展现有的 AgentState，添加意图相关字段
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# 导入现有的 AgentState
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dynamic_agent_framework import AgentState


class IntentExecutionTrace(BaseModel):
    """
    意图执行追踪记录

    记录单个意图的执行过程
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


class IntentOrchestrationPlan(BaseModel):
    """
    意图编排计划

    包含执行图、层级和数据映射
    """
    execution_graph: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="执行图（DAG），key为意图ID，value为依赖它的意图列表"
    )
    execution_layers: List[List[str]] = Field(
        default_factory=list,
        description="执行层级，每层的意图可并行执行"
    )
    data_mappings: Dict[str, Dict[str, str]] = Field(
        default_factory=dict,
        description="数据映射，key为意图ID，value为输入数据映射"
    )
    execution_order: List[str] = Field(
        default_factory=list,
        description="执行顺序列表"
    )

    @property
    def total_intents(self) -> int:
        """获取总意图数"""
        return len(self.execution_order)

    @property
    def total_layers(self) -> int:
        """获取总层数"""
        return len(self.execution_layers)


class EnhancedAgentState(AgentState):
    """
    增强的 Agent 状态 - 扩展现有 AgentState

    在原有状态基础上添加意图管理相关字段
    """

    # ========== 意图识别相关 ==========
    detected_intents: List[str] = Field(
        default_factory=list,
        description="检测到的意图ID列表"
    )
    intent_confidence: float = Field(
        default=0.0,
        description="意图识别的置信度 (0-1)"
    )
    intent_parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="从用户输入中提取的意图参数"
    )

    # ========== 编排计划相关 ==========
    orchestration_plan: Optional[IntentOrchestrationPlan] = Field(
        default=None,
        description="意图编排计划"
    )

    # ========== 执行状态相关 ==========
    intent_results: Dict[str, Any] = Field(
        default_factory=dict,
        description="已执行意图的结果，key为意图ID"
    )
    current_layer: int = Field(
        default=0,
        description="当前执行的层级索引"
    )

    # ========== 追踪相关 ==========
    execution_traces: List[IntentExecutionTrace] = Field(
        default_factory=list,
        description="意图执行追踪记录列表"
    )

    # ========== 数据上下文相关 ==========
    data_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="数据流转上下文，存储意图间的共享数据"
    )

    # ========== 控制相关 ==========
    intent_execution_complete: bool = Field(
        default=False,
        description="意图执行是否完成"
    )

    def add_execution_trace(self, trace: IntentExecutionTrace) -> None:
        """添加执行追踪记录"""
        self.execution_traces.append(trace)

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

    def update_intent_result(self, intent_id: str, result: Any) -> None:
        """更新意图执行结果"""
        self.intent_results[intent_id] = result
        # 同时更新数据上下文
        self.data_context[intent_id] = result

    def is_intent_executed(self, intent_id: str) -> bool:
        """检查意图是否已执行"""
        return intent_id in self.intent_results
