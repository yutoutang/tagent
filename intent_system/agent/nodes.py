"""
统一 Agent 节点定义

包含所有 LangGraph 节点：意图解析、编排、执行、反思、综合
"""

import time
import asyncio
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from intent_system.agent.state import (
    UnifiedAgentState,
    ReflectionResult,
    IntentExecutionTrace,
    TaskType
)
from intent_system.core.intent_registry import IntentRegistry
from intent_system.core.intent_parser import IntentParser, IntentParseResult
from intent_system.orchestration.orchestrator import IntentOrchestrator
from intent_system.execution.intent_executor import IntentExecutor
from intent_system.data_flow.data_flow_engine import DataFlowEngine
from intent_system.builtin_intents.data_intents import register_builtin_data_intents


def create_llm():
    """创建 LLM 实例"""
    import os
    from langchain_openai import ChatOpenAI
    from langchain_anthropic import ChatAnthropic

    provider = os.getenv("LLM_PROVIDER", "openai")

    if provider == "anthropic":
        return ChatAnthropic(
            model=os.getenv("MODEL_NAME", "claude-3-5-sonnet-20241022"),
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
    else:
        return ChatOpenAI(
            model=os.getenv("MODEL_NAME", "gpt-4o"),
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0
        )


# ============================================================================
# 意图解析节点
# ============================================================================

def intent_parse_node(state: UnifiedAgentState, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    意图解析节点

    使用 LLM 识别用户输入中的意图
    """
    messages = state.messages
    last_message = messages[-1] if messages else None

    if not last_message:
        return {
            "detected_intents": [],
            "intent_confidence": 0.0,
            "errors": ["没有输入消息"]
        }

    # 初始化组件
    registry = config.get("intent_registry", IntentRegistry())
    register_builtin_data_intents(registry)
    llm = config.get("llm", create_llm())

    parser = IntentParser(llm, registry)

    try:
        # 解析意图
        result: IntentParseResult = parser.parse(last_message.content)

        # 同时进行任务分类
        task_type = _classify_task(result.primary_intent, registry)

        return {
            "detected_intents": result.get_all_intent_ids(),
            "intent_confidence": result.confidence,
            "intent_parameters": result.parameters,
            "task_type": task_type,
            "task_confidence": result.confidence,
            "intermediate_steps": [{
                "step": "intent_parse",
                "intents": result.get_all_intent_ids(),
                "confidence": result.confidence,
                "reasoning": result.reasoning
            }]
        }

    except Exception as e:
        return {
            "detected_intents": [],
            "intent_confidence": 0.0,
            "errors": [f"意图解析失败: {str(e)}"]
        }


def _classify_task(primary_intent: str, registry: IntentRegistry) -> TaskType:
    """根据意图分类任务类型"""
    intent_def = registry.get(primary_intent)
    if not intent_def:
        return TaskType.GENERAL

    category = intent_def.metadata.category

    # 映射意图类别到任务类型
    category_mapping = {
        "data": TaskType.RESEARCH,
        "transform": TaskType.ANALYSIS,
        "execute": TaskType.CODING,
        "control": TaskType.GENERAL
    }

    return category_mapping.get(category, TaskType.GENERAL)


# ============================================================================
# 意图编排节点
# ============================================================================

def intent_orchestrate_node(state: UnifiedAgentState, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    意图编排节点

    构建执行计划（DAG），确定执行顺序和并行层级
    """
    detected_intents = state.detected_intents

    if not detected_intents:
        return {
            "orchestration_plan": None,
            "errors": state.errors + ["没有检测到意图"]
        }

    # 初始化组件
    registry = config.get("intent_registry", IntentRegistry())
    register_builtin_data_intents(registry)
    orchestrator = config.get("orchestrator", IntentOrchestrator(registry))

    try:
        # 创建解析结果
        parse_result = IntentParseResult(
            primary_intent=detected_intents[0],
            confidence=state.intent_confidence,
            sub_intents=[
                {"id": iid, "parameters": {}}
                for iid in detected_intents[1:]
            ],
            parameters=state.intent_parameters,
            dependencies=[],
            reasoning="从状态编排"
        )

        # 编排
        plan = orchestrator.orchestrate(parse_result)

        # 转换计划为可序列化格式
        plan_dict = {
            "execution_graph": plan.execution_graph,
            "execution_layers": plan.execution_layers,
            "data_mappings": plan.data_mappings,
            "execution_order": plan.execution_order,
            "total_intents": plan.total_intents,
            "total_layers": plan.total_layers
        }

        return {
            "orchestration_plan": plan_dict,
            "current_layer": 0,
            "intermediate_steps": state.intermediate_steps + [{
                "step": "orchestrate",
                "layers": plan.total_layers,
                "intents": plan.total_intents
            }]
        }

    except Exception as e:
        return {
            "orchestration_plan": None,
            "errors": state.errors + [f"意图编排失败: {str(e)}"]
        }


# ============================================================================
# 意图执行节点
# ============================================================================

async def intent_execute_node(state: UnifiedAgentState, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    意图执行节点

    按层执行意图，支持并行执行
    """
    plan = state.orchestration_plan
    current_layer = state.current_layer

    if not plan or current_layer >= len(plan.get("execution_layers", [])):
        return {"is_complete": True}

    # 初始化组件
    registry = config.get("intent_registry", IntentRegistry())
    register_builtin_data_intents(registry)
    data_flow = config.get("data_flow_engine", DataFlowEngine())
    executor = config.get("executor", IntentExecutor(registry, data_flow))

    # 执行当前层
    layer = plan["execution_layers"][current_layer]
    layer_results = await _execute_layer_async(
        layer,
        plan,
        executor,
        state.data_context
    )

    # 更新追踪记录
    new_traces = list(state.execution_traces)
    for intent_id, result in layer_results.items():
        trace = IntentExecutionTrace(
            intent_id=intent_id,
            start_time=time.time(),
            end_time=time.time(),
            status="success" if not isinstance(result, dict) or "error" not in result else "failed",
            output_data=result
        )
        new_traces.append(trace)

    # 合并结果
    new_intent_results = {**state.intent_results, **layer_results}
    new_data_context = {**state.data_context, **layer_results}

    # 检查是否完成
    is_complete = current_layer + 1 >= len(plan["execution_layers"])

    return {
        "intent_results": new_intent_results,
        "data_context": new_data_context,
        "current_layer": current_layer + 1,
        "execution_traces": new_traces,
        "is_complete": is_complete,
        "intermediate_steps": state.intermediate_steps + [{
            "step": "execute",
            "layer": current_layer,
            "results": list(layer_results.keys())
        }]
    }


async def _execute_layer_async(
    layer: List[str],
    plan: Dict[str, Any],
    executor: IntentExecutor,
    data_context: Dict[str, Any]
) -> Dict[str, Any]:
    """执行一层意图（并行）"""

    async def execute_single(intent_id: str) -> tuple[str, Any]:
        # 获取数据映射
        mapping = plan["data_mappings"].get(intent_id, {})

        # 解析输入数据
        input_data = executor.data_flow_engine.resolve_mapping(
            mapping,
            data_context
        )

        # 执行意图
        try:
            result = await executor.execute_single_intent_async(intent_id, input_data)
            return intent_id, result
        except Exception as e:
            return intent_id, {"error": str(e)}

    # 并行执行
    tasks = [execute_single(intent_id) for intent_id in layer]
    results = await asyncio.gather(*tasks)

    return dict(results)


# ============================================================================
# 反思节点
# ============================================================================

def reflect_node(state: UnifiedAgentState, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    反思节点

    评估当前执行结果，决定是否需要继续迭代优化
    """
    iteration = state.iteration
    max_iterations = state.max_iterations
    intent_results = state.intent_results

    # 如果已达最大迭代次数，直接完成
    if iteration >= max_iterations:
        return {
            "reflection_result": ReflectionResult(
                should_continue=False,
                confidence=0.5,
                reasoning=f"达到最大迭代次数 ({max_iterations})"
            ),
            "is_complete": True
        }

    # 如果没有执行任何意图，标记完成
    if not intent_results:
        return {
            "reflection_result": ReflectionResult(
                should_continue=False,
                confidence=0.3,
                reasoning="没有执行任何意图"
            ),
            "is_complete": True,
            "errors": state.errors + ["没有执行任何意图"]
        }

    # 使用 LLM 进行反思
    llm = config.get("llm", create_llm())

    # 构建反思提示
    reflection_prompt = _build_reflection_prompt(state)

    try:
        response = llm.invoke([
            SystemMessage(content="你是一个执行结果评估专家。分析当前结果并给出建议。"),
            HumanMessage(content=reflection_prompt)
        ])

        # 解析反思结果
        reflection_result = _parse_reflection(response.content, intent_results)

        return {
            "reflection_result": reflection_result,
            "is_complete": not reflection_result.should_continue,
            "iteration": iteration + 1,
            "intermediate_steps": state.intermediate_steps + [{
                "step": "reflect",
                "should_continue": reflection_result.should_continue,
                "confidence": reflection_result.confidence,
                "reasoning": reflection_result.reasoning
            }]
        }

    except Exception as e:
        # LLM 反思失败，使用简单逻辑
        has_errors = any(
            isinstance(r, dict) and "error" in r
            for r in intent_results.values()
        )

        return {
            "reflection_result": ReflectionResult(
                should_continue=has_errors and iteration < max_iterations,
                confidence=0.5 if not has_errors else 0.2,
                reasoning=f"反思失败: {str(e)}, {'有错误需要重试' if has_errors else '执行完成'}"
            ),
            "is_complete": not has_errors,
            "iteration": iteration + 1
        }


def _build_reflection_prompt(state: UnifiedAgentState) -> str:
    """构建反思提示"""
    prompt = f"""请评估以下执行结果：

**迭代次数**: {state.iteration + 1} / {state.max_iterations}

**执行结果**:
"""

    for intent_id, result in state.intent_results.items():
        status = "✅ 成功" if not isinstance(result, dict) or "error" not in result else "❌ 失败"
        prompt += f"\n- {intent_id}: {status}\n"
        if isinstance(result, dict):
            prompt += f"  结果: {str(result)[:200]}\n"

    prompt += f"""
**用户原始请求**: {state.messages[-1].content if state.messages else 'N/A'}

请评估：
1. 当前结果是否满足用户需求？
2. 是否存在错误或需要改进的地方？
3. 是否需要继续执行或重新尝试？

以 JSON 格式返回：
{{
    "should_continue": true/false,
    "confidence": 0.0-1.0,
    "issues": ["问题1", "问题2"],
    "suggestions": ["建议1", "建议2"],
    "reasoning": "评估理由"
}}
"""

    return prompt


def _parse_reflection(response_text: str, intent_results: Dict) -> ReflectionResult:
    """解析反思结果"""
    # 简单解析（实际可以使用更复杂的 JSON 解析）
    should_continue = "continue" in response_text.lower() or "retry" in response_text.lower()

    # 计算置信度
    successful_count = sum(
        1 for r in intent_results.values()
        if not isinstance(r, dict) or "error" not in r
    )
    confidence = successful_count / len(intent_results) if intent_results else 0.0

    # 提取问题和建议
    issues = []
    suggestions = []

    for intent_id, result in intent_results.items():
        if isinstance(result, dict) and "error" in result:
            issues.append(f"{intent_id}: {result['error']}")

    return ReflectionResult(
        should_continue=should_continue and confidence < 0.8,
        confidence=confidence,
        issues=issues,
        suggestions=suggestions,
        reasoning=response_text[:500]  # 截断
    )


# ============================================================================
# 综合节点
# ============================================================================

def synthesize_node(state: UnifiedAgentState, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    综合节点

    生成最终回答，整合所有执行结果
    """
    intent_results = state.intent_results
    messages = state.messages

    # 使用 LLM 生成综合回答
    llm = config.get("llm", create_llm())

    # 构建综合提示
    synthesis_prompt = _build_synthesis_prompt(state)

    try:
        response = llm.invoke([
            SystemMessage(content="你是一个专业助手，负责整合执行结果并生成清晰的回答。"),
            HumanMessage(content=synthesis_prompt)
        ])

        return {
            "result": response.content,
            "messages": messages + [AIMessage(content=response.content)],
            "is_complete": True
        }

    except Exception as e:
        # LLM 综合失败，使用简单格式
        simple_result = _simple_synthesis(state)

        return {
            "result": simple_result,
            "messages": messages + [AIMessage(content=simple_result)],
            "is_complete": True,
            "errors": state.errors + [f"LLM综合失败: {str(e)}"]
        }


def _build_synthesis_prompt(state: UnifiedAgentState) -> str:
    """构建综合提示"""
    prompt = f"""基于以下执行结果，生成一个清晰、准确的最终回答：

**用户请求**: {state.messages[-1].content if state.messages else 'N/A'}

**执行结果**:
"""

    for intent_id, result in state.intent_results.items():
        prompt += f"\n### {intent_id}\n"
        if isinstance(result, dict):
            prompt += f"```json\n{result}\n```\n"
        else:
            prompt += f"{result}\n"

    if state.reflection_result:
        prompt += f"\n**评估**: {state.reflection_result.reasoning}\n"

    prompt += """
请生成一个自然、友好的回答，整合以上所有结果。回答应该：
1. 直接回应用户请求
2. 突出关键信息
3. 如果有错误，说明情况
4. 使用清晰的格式
"""

    return prompt


def _simple_synthesis(state: UnifiedAgentState) -> str:
    """简单综合（备用方案）"""
    lines = ["# 执行结果\n"]

    for intent_id, result in state.intent_results.items():
        lines.append(f"\n## {intent_id}")
        if isinstance(result, dict):
            if "error" in result:
                lines.append(f"❌ 错误: {result['error']}")
            else:
                lines.append(f"✅ {result}")
        else:
            lines.append(str(result))

    return "\n".join(lines)
