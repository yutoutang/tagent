"""
YAgent 计算图构建

使用 LangGraph 构建完整的 Agent 流程，包含意图解析、编排、执行、反思、综合
"""

from typing import Dict, Any, Literal

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from intent_system.yagent.state import YAgentState
from intent_system.yagent.nodes import (
    intent_parse_node,
    intent_orchestrate_node,
    intent_execute_node,
    reflect_node,
    synthesize_node
)
from intent_system.core.intent_registry import IntentRegistry
from intent_system.orchestration.orchestrator import IntentOrchestrator
from intent_system.execution.intent_executor import IntentExecutor
from intent_system.data_flow.data_flow_engine import DataFlowEngine
from intent_system.builtin_intents.data_intents import register_builtin_data_intents


def create_default_components(
    api_key: str = None,
    base_url: str = None,
    llm_provider: str = None,
    model_name: str = None,
    **kwargs
) -> Dict[str, Any]:
    """创建默认组件

    Args:
        api_key: OpenAI API Key（可选）
        base_url: LLM Base URL（可选）
        llm_provider: LLM 提供商（可选）
        model_name: 模型名称（可选）
        **kwargs: 其他参数

    Returns:
        组件字典
    """
    import os
    from langchain_openai import ChatOpenAI
    from langchain_anthropic import ChatAnthropic

    # 优先使用传入的参数，否则从环境变量读取
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    base_url = base_url or os.getenv("OPENAI_BASE_URL")
    has_openai_key = bool(api_key)

    has_anthropic_key = bool(os.getenv("ANTHROPIC_API_KEY"))
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    # 创建 LLM
    provider = llm_provider or os.getenv("LLM_PROVIDER", "openai")
    model = model_name or os.getenv("MODEL_NAME", "gpt-4o")

    if provider == "anthropic" and anthropic_key:
        llm = ChatAnthropic(
            model=model,
            api_key=anthropic_key
        )
    elif provider == "openai" and has_openai_key:
        llm_kwargs = {"model": model, "api_key": api_key, "temperature": 0}
        if base_url:
            llm_kwargs["base_url"] = base_url
        llm = ChatOpenAI(**llm_kwargs)
    else:
        # 没有 API Key，返回 None（使用降级模式）
        llm = None

    # 创建意图系统组件
    registry = IntentRegistry()
    register_builtin_data_intents(registry)

    orchestrator = IntentOrchestrator(registry)
    executor = IntentExecutor(registry, DataFlowEngine())

    return {
        "llm": llm,
        "intent_registry": registry,
        "orchestrator": orchestrator,
        "executor": executor,
        "data_flow_engine": DataFlowEngine()
    }


def route_after_parse(state) -> Literal["orchestrate", "synthesize"]:
    """
    解析后路由决策

    如果检测到意图，进入编排；否则直接综合
    """
    # 处理 dict 或 YAgentState
    detected_intents = state.get("detected_intents", []) if isinstance(state, dict) else state.detected_intents

    if detected_intents:
        return "orchestrate"
    return "synthesize"


def route_after_orchestrate(state) -> Literal["execute", "synthesize"]:
    """
    编排后路由决策

    如果有编排计划，进入执行；否则直接综合
    """
    # 处理 dict 或 YAgentState
    orchestration_plan = state.get("orchestration_plan") if isinstance(state, dict) else state.orchestration_plan

    if orchestration_plan:
        return "execute"
    return "synthesize"


def route_after_execute(state) -> Literal["reflect", "synthesize", "execute"]:
    """
    执行后路由决策

    如果所有层都执行完成，进入反思；否则继续执行
    """
    # 处理 dict 或 YAgentState
    orchestration_plan = state.get("orchestration_plan") if isinstance(state, dict) else state.orchestration_plan
    current_layer = state.get("current_layer", 0) if isinstance(state, dict) else state.current_layer

    if orchestration_plan:
        plan = orchestration_plan if isinstance(orchestration_plan, dict) else {}
        total_layers = len(plan.get("execution_layers", []))

        if current_layer >= total_layers:
            return "reflect"
        return "execute"

    return "synthesize"


def route_after_reflect(state) -> Literal["execute", "synthesize"]:
    """
    反思后路由决策

    根据反思结果决定是否继续执行还是综合
    """
    # 处理 dict 或 YAgentState
    reflection_result = state.get("reflection_result") if isinstance(state, dict) else state.reflection_result

    if reflection_result and reflection_result.get("should_continue") if isinstance(reflection_result, dict) else reflection_result.should_continue:
        # 重置执行状态，重新执行
        return "execute"
    return "synthesize"


def create_yagent_graph(
    llm=None,
    intent_registry=None,
    orchestrator=None,
    executor=None,
    data_flow_engine=None
) -> StateGraph:
    """
    创建 YAgent 计算图

    流程:
    START → Intent Parse → Orchestrate → Execute → Reflect → Synthesize → END
                                ↓               ↓
                            (无意图)      (迭代循环)

    Args:
        llm: LLM 实例
        intent_registry: 意图注册表
        orchestrator: 意图编排器
        executor: 意图执行器
        data_flow_engine: 数据流转引擎

    Returns:
        编译后的 StateGraph
    """

    # 创建或使用提供的组件
    if not all([llm, intent_registry, orchestrator, executor, data_flow_engine]):
        components = create_default_components()
        llm = llm or components["llm"]
        intent_registry = intent_registry or components["intent_registry"]
        orchestrator = orchestrator or components["orchestrator"]
        executor = executor or components["executor"]
        data_flow_engine = data_flow_engine or components["data_flow_engine"]

    # 构建配置字典
    config = {
        "llm": llm,
        "intent_registry": intent_registry,
        "orchestrator": orchestrator,
        "executor": executor,
        "data_flow_engine": data_flow_engine
    }

    # 初始化状态图
    graph = StateGraph(YAgentState)

    # 创建节点包装器（处理 config 参数）
    def parse_wrapper(state):
        return intent_parse_node(state, config)

    def orchestrate_wrapper(state):
        return intent_orchestrate_node(state, config)

    async def execute_wrapper(state):
        return await intent_execute_node(state, config)

    def reflect_wrapper(state):
        return reflect_node(state, config)

    def synthesize_wrapper(state):
        return synthesize_node(state, config)

    # 添加节点
    graph.add_node("intent_parse", parse_wrapper)
    graph.add_node("orchestrate", orchestrate_wrapper)
    graph.add_node("execute", execute_wrapper)
    graph.add_node("reflect", reflect_wrapper)
    graph.add_node("synthesize", synthesize_wrapper)

    # 添加边
    graph.add_edge(START, "intent_parse")

    # 从解析节点路由
    graph.add_conditional_edges(
        "intent_parse",
        route_after_parse,
        {
            "orchestrate": "orchestrate",
            "synthesize": "synthesize"
        }
    )

    # 从编排节点路由
    graph.add_conditional_edges(
        "orchestrate",
        route_after_orchestrate,
        {
            "execute": "execute",
            "synthesize": "synthesize"
        }
    )

    # 从执行节点路由
    graph.add_conditional_edges(
        "execute",
        route_after_execute,
        {
            "execute": "execute",
            "reflect": "reflect",
            "synthesize": "synthesize"
        }
    )

    # 从反思节点路由
    graph.add_conditional_edges(
        "reflect",
        route_after_reflect,
        {
            "execute": "execute",
            "synthesize": "synthesize"
        }
    )

    # 从综合节点到结束
    graph.add_edge("synthesize", END)

    # 编译图（添加持久化支持）
    memory = MemorySaver()
    app = graph.compile(checkpointer=memory)

    return app


def visualize_graph() -> str:
    """
    可视化图结构（返回 Mermaid 格式）

    Returns:
        Mermaid 格式的图描述
    """
    return """
```mermaid
graph TD
    START([START]) --> PARSE[Intent Parse]
    PARSE --> |有意图| ORCH[Orchestrate]
    PARSE --> |无意图| SYNTH[Synthesize]

    ORCH --> |有计划| EXEC[Execute]
    ORCH --> |无计划| SYNTH

    EXEC --> |继续执行| EXEC
    EXEC --> |完成| REFLECT[Reflect]

    REFLECT --> |需要继续| EXEC
    REFLECT --> |完成| SYNTH

    SYNTH --> END([END])

    style PARSE fill:#e1f5fe
    style ORCH fill:#fff3e0
    style EXEC fill:#e8f5e9
    style REFLECT fill:#fce4ec
    style SYNTH fill:#f3e5f5
```
"""
