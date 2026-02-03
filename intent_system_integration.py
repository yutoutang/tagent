"""
意图系统与 LangGraph 框架集成

扩展现有的 DynamicAgent，添加意图识别和编排能力
"""

import asyncio
from typing import Any, Dict, List, Optional

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import AIMessage, HumanMessage

# 导入现有的框架组件
from dynamic_agent_framework import (
    AgentState,
    create_llm,
    DynamicAgent,
    tool_registry
)

# 导入意图系统组件
from intent_system.core import (
    IntentRegistry,
    EnhancedAgentState,
    IntentParseResult
)
from intent_system.core.intent_parser import IntentParser
from intent_system.orchestration import IntentOrchestrator
from intent_system.execution import IntentExecutor
from intent_system.data_flow import DataFlowEngine
from intent_system.builtin_intents import register_builtin_data_intents


# ============================================================
# 意图增强的 Agent
# ============================================================

class IntentEnhancedAgent(DynamicAgent):
    """
    意图增强的 Agent

    在原有 DynamicAgent 基础上添加：
    - 意图识别
    - 意图编排
    - 并行执行
    - 数据流转
    """

    def __init__(self, config: Optional[Dict] = None):
        """初始化 Agent"""
        super().__init__(config)

        # 初始化意图系统组件
        self.intent_registry = IntentRegistry()
        self.llm = create_llm()
        self.intent_parser = IntentParser(self.llm, self.intent_registry)
        self.intent_orchestrator = IntentOrchestrator(self.intent_registry)
        self.data_flow_engine = DataFlowEngine()

        # 注册内置意图
        register_builtin_data_intents(self.intent_registry)

    def register_intent(self, intent_def) -> None:
        """注册自定义意图"""
        self.intent_registry.register(intent_def)

    def run_with_intents(
        self,
        message: str,
        session_id: Optional[str] = None,
        use_intents: bool = True
    ) -> Dict[str, Any]:
        """
        使用意图系统运行

        Args:
            message: 用户消息
            session_id: 会话ID
            use_intents: 是否使用意图系统

        Returns:
            执行结果
        """
        if not use_intents:
            # 使用原有的执行方式
            return self.run(message, session_id)

        # 解析意图
        parse_result = self.intent_parser.parse(message)

        # 编排执行计划
        plan = self.intent_orchestrator.orchestrate(parse_result)

        # 执行
        executor = IntentExecutor(self.intent_registry, self.data_flow_engine)

        try:
            results = asyncio.run(executor.execute_plan_async(plan, session_id))

            return {
                "success": True,
                "result": results,
                "task_type": parse_result.primary_intent,
                "intent_confidence": parse_result.confidence,
                "execution_summary": executor.get_execution_summary()
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "task_type": parse_result.primary_intent
            }

    async def astream_with_intents(
        self,
        message: str,
        session_id: Optional[str] = None,
        use_intents: bool = True
    ):
        """异步流式运行（使用意图系统）"""
        if not use_intents:
            async for event in self.astream(message, session_id):
                yield event
            return

        # 解析意图
        parse_result = self.intent_parser.parse(message)

        # 编排
        plan = self.intent_orchestrator.orchestrate(parse_result)

        # 执行
        executor = IntentExecutor(self.intent_registry, self.data_flow_engine)

        # 按层流式输出
        for i, layer in enumerate(plan.execution_layers):
            yield {
                "event": "layer_start",
                "layer": i,
                "intents": layer
            }

            layer_results = await executor.execute_layer_async(layer, plan)

            yield {
                "event": "layer_complete",
                "layer": i,
                "results": layer_results
            }

        yield {
            "event": "complete",
            "summary": executor.get_execution_summary()
        }


# ============================================================
# 创建意图增强的计算图
# ============================================================

def create_intent_enhanced_graph():
    """
    创建意图增强的计算图

    在原有五节点工作流基础上，添加意图识别和编排节点
    """
    # 使用增强的状态
    graph = StateGraph(EnhancedAgentState)

    # 意图识别节点
    def intent_recognize_node(state: EnhancedAgentState) -> Dict:
        """识别用户意图"""
        messages = state["messages"]
        last_message = messages[-1] if messages else None

        if not last_message:
            return {"detected_intents": [], "intent_confidence": 0.0}

        # 创建意图解析器
        registry = IntentRegistry()
        register_builtin_data_intents(registry)
        llm = create_llm()
        parser = IntentParser(llm, registry)

        # 解析意图
        try:
            result = parser.parse(last_message.content)
            return {
                "detected_intents": result.get_all_intent_ids(),
                "intent_confidence": result.confidence,
                "intent_parameters": result.parameters
            }
        except Exception as e:
            return {
                "detected_intents": [],
                "intent_confidence": 0.0,
                "errors": [f"意图识别失败: {str(e)}"]
            }

    # 意图编排节点
    def intent_orchestrate_node(state: EnhancedAgentState) -> Dict:
        """编排意图执行计划"""
        detected_intents = state.get("detected_intents", [])

        if not detected_intents:
            return {"orchestration_plan": None}

        # 创建编排器
        registry = IntentRegistry()
        register_builtin_data_intents(registry)
        orchestrator = IntentOrchestrator(registry)

        # 创建简化的解析结果
        from intent_system.core.intent_parser import IntentParseResult
        parse_result = IntentParseResult(
            primary_intent=detected_intents[0],
            confidence=state.get("intent_confidence", 1.0),
            sub_intents=[
                {"id": iid, "parameters": {}}
                for iid in detected_intents[1:]
            ],
            parameters=state.get("intent_parameters", {}),
            dependencies=[],
            reasoning="从增强状态编排"
        )

        # 编排
        try:
            plan = orchestrator.orchestrate(parse_result)
            return {
                "orchestration_plan": plan,
                "current_layer": 0
            }
        except Exception as e:
            return {
                "orchestration_plan": None,
                "errors": [f"意图编排失败: {str(e)}"]
            }

    # 意图执行节点
    async def intent_execute_node(state: EnhancedAgentState) -> Dict:
        """执行意图"""
        plan = state.get("orchestration_plan")
        current_layer = state.get("current_layer", 0)

        if not plan or current_layer >= len(plan.execution_layers):
            return {"intent_execution_complete": True}

        # 创建执行器
        registry = IntentRegistry()
        register_builtin_data_intents(registry)
        data_flow = DataFlowEngine()
        executor = IntentExecutor(registry, data_flow)

        # 执行当前层
        layer = plan.execution_layers[current_layer]
        layer_results = await executor.execute_layer_async(layer, plan)

        # 更新状态
        new_results = {**state["intent_results"], **layer_results}
        new_context = {**state["data_context"], **layer_results}

        return {
            "intent_results": new_results,
            "data_context": new_context,
            "current_layer": current_layer + 1,
            "intent_execution_complete": current_layer + 1 >= len(plan.execution_layers),
            "execution_traces": executor.tracker.traces
        }

    # 添加节点
    graph.add_node("intent_recognize", intent_recognize_node)
    graph.add_node("intent_orchestrate", intent_orchestrate_node)
    graph.add_node("intent_execute", intent_execute_node)

    # 添加边（简化版，实际需要更复杂的路由）
    graph.add_edge(START, "intent_recognize")
    graph.add_edge("intent_recognize", "intent_orchestrate")

    # 条件路由
    def should_execute_intents(state: EnhancedAgentState) -> str:
        """决定是否执行意图"""
        if state.get("orchestration_plan"):
            return "execute"
        return "synthesize"

    def check_execution_complete(state: EnhancedAgentState) -> str:
        """检查执行是否完成"""
        plan = state.get("orchestration_plan")
        if plan and state.get("current_layer", 0) < len(plan.execution_layers):
            return "continue"
        return "synthesize"

    # 注意：这里简化了路由逻辑，实际需要更复杂的处理
    # graph.add_conditional_edges(...)

    return graph.compile()


# ============================================================
# 使用示例
# ============================================================

async def main():
    """使用示例"""
    print("=" * 60)
    print("意图增强 Agent 示例")
    print("=" * 60)

    from dotenv import load_dotenv
    load_dotenv()

    # 创建意图增强的 Agent
    agent = IntentEnhancedAgent()

    # 示例 1: 使用意图系统
    print("\n示例 1: 使用意图系统")
    result = agent.run_with_intents(
        "帮我计算 25 * 4，同时搜索 Python 信息",
        session_id="demo_1",
        use_intents=True
    )

    if result["success"]:
        print(f"✅ 执行成功")
        print(f"   意图: {result['task_type']}")
        print(f"   置信度: {result['intent_confidence']:.2f}")
        print(f"   结果: {result['result']}")
    else:
        print(f"❌ 执行失败: {result.get('error')}")

    # 示例 2: 流式输出
    print("\n示例 2: 流式输出")
    async for event in agent.astream_with_intents(
        "计算 100 / 5，然后分析结果",
        session_id="demo_2",
        use_intents=True
    ):
        if event["event"] == "layer_start":
            print(f"🔄 开始执行第 {event['layer']} 层: {event['intents']}")
        elif event["event"] == "layer_complete":
            print(f"✅ 第 {event['layer']} 层完成: {list(event['results'].keys())}")
        elif event["event"] == "complete":
            print(f"🎉 全部完成")
            summary = event["summary"]
            print(f"   总意图数: {summary['total_intents']}")
            print(f"   成功: {summary['successful']}")
            print(f"   总耗时: {summary['total_duration']:.2f}s")

    # 示例 3: 注册自定义意图
    print("\n示例 3: 注册自定义意图")

    from intent_system.core import IntentDefinition, IntentMetadata, InputOutputSchema
    from langchain_core.tools import tool

    @tool
    async def my_custom_tool(param: str) -> str:
        """自定义工具"""
        return f"处理结果: {param}"

    custom_intent = IntentDefinition(
        metadata=IntentMetadata(
            id="my_custom",
            name="我的自定义意图",
            description="自定义功能演示",
            category="execute"
        ),
        schema=InputOutputSchema(
            inputs={"param": {"type": "string", "required": True}},
            outputs={"result": {"type": "string"}}
        ),
        executor=my_custom_tool.func
    )

    agent.register_intent(custom_intent)
    print("✅ 自定义意图已注册")

    result = agent.run_with_intents("使用 my_custom 处理 hello")
    print(f"结果: {result}")


if __name__ == "__main__":
    asyncio.run(main())
