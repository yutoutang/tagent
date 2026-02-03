"""
执行追踪系统 - 记录和追踪意图的执行过程
"""

import time
from typing import Any, Dict, List, Optional
from intent_system.core.state import IntentExecutionTrace


class ExecutionTracker:
    """
    执行追踪器

    功能：
    1. 追踪会话
    2. 记录意图执行过程
    3. 生成执行摘要
    4. 错误追踪
    """

    def __init__(self):
        """初始化追踪器"""
        self.current_session_id: Optional[str] = None
        self.traces: List[IntentExecutionTrace] = []
        self.data_context: Dict[str, Any] = {}

    def start_session(self, session_id: str) -> None:
        """
        开始追踪会话

        Args:
            session_id: 会话ID
        """
        self.current_session_id = session_id
        self.traces = []
        self.data_context = {}

    def end_session(self) -> Dict[str, Any]:
        """
        结束会话并获取摘要

        Returns:
            执行摘要
        """
        summary = self.get_execution_summary()
        self.current_session_id = None
        return summary

    def start_intent(
        self,
        intent_id: str,
        input_data: Dict[str, Any]
    ) -> IntentExecutionTrace:
        """
        开始追踪意图执行

        Args:
            intent_id: 意图ID
            input_data: 输入数据

        Returns:
            执行追踪对象
        """
        trace = IntentExecutionTrace(
            intent_id=intent_id,
            start_time=time.time(),
            status="running",
            input_data=input_data
        )
        self.traces.append(trace)
        return trace

    def complete_intent(
        self,
        trace: IntentExecutionTrace,
        output_data: Any,
        error: Optional[str] = None
    ) -> None:
        """
        完成意图执行

        Args:
            trace: 执行追踪对象
            output_data: 输出数据
            error: 错误信息（如果失败）
        """
        trace.end_time = time.time()
        trace.output_data = output_data
        trace.status = "success" if error is None else "failed"
        trace.error = error

        # 将输出添加到数据上下文
        if error is None and output_data is not None:
            self.data_context[trace.intent_id] = output_data

    def fail_intent(
        self,
        trace: IntentExecutionTrace,
        error: str
    ) -> None:
        """
        标记意图执行失败

        Args:
            trace: 执行追踪对象
            error: 错误信息
        """
        self.complete_intent(trace, None, error)

    def retry_intent(
        self,
        trace: IntentExecutionTrace
    ) -> None:
        """
        重试意图执行

        Args:
            trace: 执行追踪对象
        """
        trace.retry_count += 1
        trace.start_time = time.time()
        trace.status = "running"
        trace.error = None

    def get_execution_summary(self) -> Dict[str, Any]:
        """
        获取执行摘要

        Returns:
            执行摘要字典，包含：
            - total_intents: 总意图数
            - successful: 成功数
            - failed: 失败数
            - total_duration: 总耗时
            - intents: 每个意图的详细信息
        """
        successful = [t for t in self.traces if t.status == "success"]
        failed = [t for t in self.traces if t.status == "failed"]
        running = [t for t in self.traces if t.status == "running"]

        total_duration = sum(
            (t.end_time or time.time()) - t.start_time
            for t in self.traces
        )

        return {
            "session_id": self.current_session_id,
            "total_intents": len(self.traces),
            "successful": len(successful),
            "failed": len(failed),
            "running": len(running),
            "total_duration": total_duration,
            "intents": [
                {
                    "intent_id": t.intent_id,
                    "status": t.status,
                    "duration": t.duration,
                    "retry_count": t.retry_count,
                    "error": t.error
                }
                for t in self.traces
            ]
        }

    def get_trace_by_intent(self, intent_id: str) -> Optional[IntentExecutionTrace]:
        """
        根据意图ID获取追踪记录

        Args:
            intent_id: 意图ID

        Returns:
            追踪记录，如果不存在则返回 None
        """
        for trace in self.traces:
            if trace.intent_id == intent_id:
                return trace
        return None

    def get_successful_intents(self) -> List[str]:
        """获取成功执行的意图ID列表"""
        return [
            t.intent_id for t in self.traces
            if t.status == "success"
        ]

    def get_failed_intents(self) -> List[str]:
        """获取执行失败的意图ID列表"""
        return [
            t.intent_id for t in self.traces
            if t.status == "failed"
        ]

    def get_total_duration(self) -> float:
        """获取总执行时长"""
        return sum(
            (t.end_time or time.time()) - t.start_time
            for t in self.traces
        )

    def is_all_success(self) -> bool:
        """检查是否所有意图都成功执行"""
        return all(t.status == "success" for t in self.traces)

    def has_failures(self) -> bool:
        """检查是否有失败的意图"""
        return any(t.status == "failed" for t in self.traces)

    def print_summary(self) -> None:
        """打印执行摘要（用于调试）"""
        summary = self.get_execution_summary()

        print("=" * 60)
        print(f"执行摘要 - 会话: {summary['session_id']}")
        print("=" * 60)
        print(f"总意图数: {summary['total_intents']}")
        print(f"成功: {summary['successful']}")
        print(f"失败: {summary['failed']}")
        print(f"总耗时: {summary['total_duration']:.2f}s")
        print()

        if summary['intents']:
            print("详细执行情况:")
            for intent_info in summary['intents']:
                status_symbol = "✓" if intent_info['status'] == "success" else "✗"
                print(
                    f"  {status_symbol} {intent_info['intent_id']}: "
                    f"{intent_info['status']} "
                    f"({intent_info['duration']:.2f}s)"
                )
                if intent_info['error']:
                    print(f"      错误: {intent_info['error']}")
                if intent_info['retry_count'] > 0:
                    print(f"      重试: {intent_info['retry_count']}次")

        print("=" * 60)
