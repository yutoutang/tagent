"""
意图执行器 - 支持同步/异步、并行执行
"""

import asyncio
import time
from typing import Any, Dict, List, Optional

from intent_system.core.intent_registry import IntentRegistry
from intent_system.core.state import IntentOrchestrationPlan
from intent_system.execution.execution_tracker import ExecutionTracker
from intent_system.data_flow.data_flow_engine import DataFlowEngine


class IntentExecutor:
    """
    意图执行器

    功能：
    1. 执行单个意图
    2. 按层执行意图（支持并行）
    3. 执行完整计划
    4. 错误处理和重试
    """

    def __init__(
        self,
        registry: IntentRegistry,
        data_flow_engine: Optional[DataFlowEngine] = None
    ):
        """
        初始化执行器

        Args:
            registry: 意图注册表
            data_flow_engine: 数据流转引擎（可选）
        """
        self.registry = registry
        self.data_flow_engine = data_flow_engine or DataFlowEngine()
        self.tracker = ExecutionTracker()

    def execute_single_intent(
        self,
        intent_id: str,
        input_data: Dict[str, Any],
        timeout: Optional[float] = None
    ) -> Any:
        """
        执行单个意图（同步）

        Args:
            intent_id: 意图ID
            input_data: 输入数据
            timeout: 超时时间（秒）

        Returns:
            执行结果

        Raises:
            ValueError: 如果意图不存在
            TimeoutError: 如果执行超时
        """
        intent_def = self.registry.get(intent_id)
        if not intent_def:
            raise ValueError(f"Intent '{intent_id}' not found")

        # 开始追踪
        trace = self.tracker.start_intent(intent_id, input_data)

        # 验证输入
        is_valid, error_msg = intent_def.validate_inputs(input_data)
        if not is_valid:
            self.tracker.fail_intent(trace, error_msg)
            raise ValueError(f"Input validation failed: {error_msg}")

        # 设置超时
        timeout = timeout or intent_def.metadata.timeout

        try:
            # 执行意图
            if asyncio.iscoroutinefunction(intent_def.executor):
                # 异步执行
                result = asyncio.run(
                    asyncio.wait_for(
                        intent_def.executor(**input_data),
                        timeout=timeout
                    )
                )
            else:
                # 同步执行
                # 使用 signal 或 threading 实现超时（简化版）
                result = intent_def.executor(**input_data)

            # 完成追踪
            self.tracker.complete_intent(trace, result)
            return result

        except asyncio.TimeoutError:
            error = f"Execution timeout after {timeout}s"
            self.tracker.fail_intent(trace, error)
            raise TimeoutError(error)

        except Exception as e:
            error = str(e)
            self.tracker.fail_intent(trace, error)

            # 检查是否需要重试
            if trace.retry_count < intent_def.metadata.retry_count:
                self.tracker.retry_intent(trace)
                return self.execute_single_intent(intent_id, input_data, timeout)

            raise

    async def execute_single_intent_async(
        self,
        intent_id: str,
        input_data: Dict[str, Any],
        timeout: Optional[float] = None
    ) -> Any:
        """
        执行单个意图（异步）

        Args:
            intent_id: 意图ID
            input_data: 输入数据
            timeout: 超时时间（秒）

        Returns:
            执行结果
        """
        intent_def = self.registry.get(intent_id)
        if not intent_def:
            raise ValueError(f"Intent '{intent_id}' not found")

        trace = self.tracker.start_intent(intent_id, input_data)

        is_valid, error_msg = intent_def.validate_inputs(input_data)
        if not is_valid:
            self.tracker.fail_intent(trace, error_msg)
            raise ValueError(f"Input validation failed: {error_msg}")

        timeout = timeout or intent_def.metadata.timeout

        try:
            if asyncio.iscoroutinefunction(intent_def.executor):
                result = await asyncio.wait_for(
                    intent_def.executor(**input_data),
                    timeout=timeout
                )
            else:
                # 在线程池中执行同步函数
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, intent_def.executor, **input_data),
                    timeout=timeout
                )

            self.tracker.complete_intent(trace, result)
            return result

        except asyncio.TimeoutError:
            error = f"Execution timeout after {timeout}s"
            self.tracker.fail_intent(trace, error)
            raise

        except Exception as e:
            error = str(e)
            self.tracker.fail_intent(trace, error)

            if trace.retry_count < intent_def.metadata.retry_count:
                self.tracker.retry_intent(trace)
                return await self.execute_single_intent_async(
                    intent_id, input_data, timeout
                )

            raise

    def execute_plan(
        self,
        plan: IntentOrchestrationPlan,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行完整计划（同步）

        Args:
            plan: 意图编排计划
            session_id: 会话ID

        Returns:
            所有意图的执行结果
        """
        self.tracker.start_session(session_id or "default")

        results = {}

        try:
            for layer in plan.execution_layers:
                layer_results = self.execute_layer_sync(
                    layer,
                    plan
                )
                results.update(layer_results)

        finally:
            self.tracker.end_session()

        return results

    async def execute_plan_async(
        self,
        plan: IntentOrchestrationPlan,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行完整计划（异步）

        Args:
            plan: 意图编排计划
            session_id: 会话ID

        Returns:
            所有意图的执行结果
        """
        self.tracker.start_session(session_id or "default")

        results = {}

        try:
            for layer in plan.execution_layers:
                layer_results = await self.execute_layer_async(
                    layer,
                    plan
                )
                results.update(layer_results)

        finally:
            self.tracker.end_session()

        return results

    def execute_layer_sync(
        self,
        layer: List[str],
        plan: IntentOrchestrationPlan
    ) -> Dict[str, Any]:
        """
        执行一层意图（同步，串行）

        Args:
            layer: 意图ID列表
            plan: 编排计划

        Returns:
            该层意图的执行结果
        """
        results = {}

        for intent_id in layer:
            # 获取数据映射
            mapping = plan.data_mappings.get(intent_id, {})

            # 解析输入数据
            input_data = self.data_flow_engine.resolve_mapping(
                mapping,
                self.tracker.data_context
            )

            # 执行意图
            result = self.execute_single_intent(intent_id, input_data)
            results[intent_id] = result

        return results

    async def execute_layer_async(
        self,
        layer: List[str],
        plan: IntentOrchestrationPlan
    ) -> Dict[str, Any]:
        """
        执行一层意图（异步，并行）

        Args:
            layer: 意图ID列表
            plan: 编排计划

        Returns:
            该层意图的执行结果
        """
        # 创建所有任务
        tasks = []
        for intent_id in layer:
            task = self._execute_intent_in_layer(intent_id, plan)
            tasks.append(task)

        # 并行执行
        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        # 整理结果
        results = {}
        for intent_id, result in zip(layer, results_list):
            if isinstance(result, Exception):
                results[intent_id] = {"error": str(result)}
            else:
                results[intent_id] = result

        return results

    async def _execute_intent_in_layer(
        self,
        intent_id: str,
        plan: IntentOrchestrationPlan
    ) -> Any:
        """
        在层中执行单个意图

        Args:
            intent_id: 意图ID
            plan: 编排计划

        Returns:
            执行结果
        """
        mapping = plan.data_mappings.get(intent_id, {})
        input_data = self.data_flow_engine.resolve_mapping(
            mapping,
            self.tracker.data_context
        )

        return await self.execute_single_intent_async(intent_id, input_data)

    def get_execution_summary(self) -> Dict[str, Any]:
        """
        获取执行摘要

        Returns:
            执行摘要字典
        """
        return self.tracker.get_execution_summary()

    def print_execution_summary(self) -> None:
        """打印执行摘要"""
        self.tracker.print_summary()
