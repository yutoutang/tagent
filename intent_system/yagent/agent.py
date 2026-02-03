"""
YAgent 类

提供简洁的接口来使用 YAgent 系统
"""

import asyncio
from typing import Any, Dict, List, Optional, AsyncIterator

from langchain_core.messages import HumanMessage, AIMessage

from intent_system.yagent.state import YAgentState
from intent_system.yagent.graph import create_yagent_graph, create_default_components
from intent_system.core.intent_registry import IntentRegistry
from intent_system.core.intent_definition import IntentDefinition
from intent_system.builtin_intents.data_intents import register_builtin_data_intents


class YAgent:
    """
    YAgent - 智能意图 Agent

    融合了 dynamic_agent_framework 和 intent_system 的所有功能：
    - 基于 LangGraph 的工作流
    - 意图识别和编排
    - 反思机制
    - 并行执行
    - 数据流转
    """

    def __init__(
        self,
        llm=None,
        intent_registry: Optional[IntentRegistry] = None,
        max_iterations: int = 3,
        config: Optional[Dict] = None,
        api_key: str = None,
        base_url: str = None,
        llm_provider: str = None,
        model_name: str = None
    ):
        """
        初始化 YAgent

        Args:
            llm: LLM 实例（可选，默认创建新实例）
            intent_registry: 意图注册表（可选，默认创建新实例）
            max_iterations: 最大反思迭代次数
            config: 额外配置
            api_key: OpenAI API Key（可选）
            base_url: LLM Base URL（可选）
            llm_provider: LLM 提供商（可选）
            model_name: 模型名称（可选）
        """
        # 创建组件（支持自定义配置）
        components = create_default_components(
            api_key=api_key,
            base_url=base_url,
            llm_provider=llm_provider,
            model_name=model_name
        )
        self.llm = llm or components["llm"]
        self.intent_registry = intent_registry or components["intent_registry"]
        self.orchestrator = components["orchestrator"]
        self.executor = components["executor"]
        self.data_flow_engine = components["data_flow_engine"]

        # 注册内置意图
        if not intent_registry:
            register_builtin_data_intents(self.intent_registry)

        # 创建计算图
        self.app = create_yagent_graph(
            llm=self.llm,
            intent_registry=self.intent_registry,
            orchestrator=self.orchestrator,
            executor=self.executor,
            data_flow_engine=self.data_flow_engine
        )

        # 默认配置
        self.config = config or {
            "configurable": {"thread_id": "default_session"}
        }
        self.max_iterations = max_iterations

    def run(
        self,
        message: str,
        session_id: Optional[str] = None,
        max_iterations: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        运行 YAgent

        Args:
            message: 用户消息
            session_id: 会话ID
            max_iterations: 最大迭代次数（覆盖默认值）

        Returns:
            执行结果字典
        """
        config = self.config.copy()
        if session_id:
            config["configurable"]["thread_id"] = session_id

        # 创建初始状态
        initial_state = YAgentState(
            messages=[HumanMessage(content=message)],
            max_iterations=max_iterations or self.max_iterations
        )

        try:
            # 执行图
            result_state = self.app.invoke(initial_state, config)

            # 返回结果
            return {
                "success": result_state.is_complete,
                "result": result_state.result,
                "task_type": result_state.task_type,
                "intent_confidence": result_state.intent_confidence,
                "detected_intents": result_state.detected_intents,
                "intent_results": result_state.intent_results,
                "execution_summary": result_state.get_execution_summary(),
                "reflection_result": result_state.reflection_result.model_dump() if result_state.reflection_result else None,
                "intermediate_steps": result_state.intermediate_steps,
                "errors": result_state.errors
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "errors": [str(e)]
            }

    def chat(
        self,
        message: str,
        session_id: Optional[str] = None
    ) -> str:
        """
        简单聊天接口

        Args:
            message: 用户消息
            session_id: 会话ID

        Returns:
            Agent 回复
        """
        result = self.run(message, session_id)
        if result["success"]:
            return result["result"] or "处理完成，但没有生成结果"
        else:
            return f"错误: {result.get('error', '未知错误')}"

    async def arun(
        self,
        message: str,
        session_id: Optional[str] = None,
        max_iterations: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        异步运行 YAgent

        Args:
            message: 用户消息
            session_id: 会话ID
            max_iterations: 最大迭代次数

        Returns:
            执行结果字典
        """
        config = self.config.copy()
        if session_id:
            config["configurable"]["thread_id"] = session_id

        initial_state = YAgentState(
            messages=[HumanMessage(content=message)],
            max_iterations=max_iterations or self.max_iterations
        )

        try:
            result_state = await self.app.ainvoke(initial_state, config)

            return {
                "success": result_state.is_complete,
                "result": result_state.result,
                "task_type": result_state.task_type,
                "intent_confidence": result_state.intent_confidence,
                "detected_intents": result_state.detected_intents,
                "intent_results": result_state.intent_results,
                "execution_summary": result_state.get_execution_summary(),
                "reflection_result": result_state.reflection_result.model_dump() if result_state.reflection_result else None,
                "intermediate_steps": result_state.intermediate_steps,
                "errors": result_state.errors
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "errors": [str(e)]
            }

    async def astream(
        self,
        message: str,
        session_id: Optional[str] = None,
        max_iterations: Optional[int] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        异步流式运行 YAgent

        Args:
            message: 用户消息
            session_id: 会话ID
            max_iterations: 最大迭代次数

        Yields:
            执行事件
        """
        config = self.config.copy()
        if session_id:
            config["configurable"]["thread_id"] = session_id

        initial_state = YAgentState(
            messages=[HumanMessage(content=message)],
            max_iterations=max_iterations or self.max_iterations
        )

        try:
            async for event in self.app.astream(initial_state, config):
                yield event

        except Exception as e:
            yield {
                "error": str(e),
                "success": False
            }

    def stream(
        self,
        message: str,
        session_id: Optional[str] = None,
        max_iterations: Optional[int] = None
   ):
        """
        同步流式运行 YAgent

        Args:
            message: 用户消息
            session_id: 会话ID
            max_iterations: 最大迭代次数

        Yields:
            执行事件
        """
        config = self.config.copy()
        if session_id:
            config["configurable"]["thread_id"] = session_id

        initial_state = YAgentState(
            messages=[HumanMessage(content=message)],
            max_iterations=max_iterations or self.max_iterations
        )

        try:
            for event in self.app.stream(initial_state, config):
                yield event

        except Exception as e:
            yield {
                "error": str(e),
                "success": False
            }

    def register_intent(self, intent: IntentDefinition) -> None:
        """
        注册自定义意图

        Args:
            intent: 意图定义
        """
        self.intent_registry.register(intent)

    def register_intents(self, intents: List[IntentDefinition]) -> None:
        """
        批量注册意图

        Args:
            intents: 意图定义列表
        """
        for intent in intents:
            self.intent_registry.register(intent)

    def list_intents(self) -> List[Dict[str, Any]]:
        """
        列出所有已注册的意图

        Returns:
            意图列表
        """
        return self.intent_registry.list_all()

    def get_intent(self, intent_id: str) -> Optional[IntentDefinition]:
        """
        获取特定意图

        Args:
            intent_id: 意图ID

        Returns:
            意图定义或 None
        """
        return self.intent_registry.get(intent_id)

    def set_max_iterations(self, max_iterations: int) -> None:
        """
        设置最大迭代次数

        Args:
            max_iterations: 最大迭代次数
        """
        self.max_iterations = max_iterations

    def get_graph_description(self) -> str:
        """
        获取计算图描述

        Returns:
            Mermaid 格式的图描述
        """
        from intent_system.yagent.graph import visualize_graph
        return visualize_graph()

    def reset_session(self, session_id: str) -> None:
        """
        重置会话状态

        Args:
            session_id: 会话ID
        """
        # LangGraph 的 checkpointer 会自动管理状态
        # 这里提供一个接口来清除特定会话（如果需要）
        config = self.config.copy()
        config["configurable"]["thread_id"] = session_id

        try:
            # 获取当前状态
            current_state = self.app.get_state(config)
            if current_state:
                # 清除状态（通过更新一个空状态）
                empty_state = YAgentState(
                    messages=[],
                    is_complete=True
                )
                self.app.update_state(config, empty_state)
        except Exception:
            # 如果获取状态失败，说明会话不存在，无需处理
            pass
