"""
动态 Agent 调用框架
基于 LangGraph 实现任务识别、动态工具加载和多 agent 协作
"""

import os
import json
from typing import Any, Dict, List, Optional, TypedDict, Annotated
from enum import Enum
from operator import add
from pathlib import Path

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, Field


# ============================================================================
# 1. 任务分类与状态定义
# ============================================================================

class TaskType(str, Enum):
    """任务类型枚举"""
    CODING = "coding"
    RESEARCH = "research"
    ANALYSIS = "analysis"
    CALCULATION = "calculation"
    GENERAL = "general"


class AgentState(TypedDict):
    """Agent 共享状态"""
    # 消息历史（使用 add_messages reducer 自动追加）
    messages: Annotated[List[BaseMessage], add_messages]

    # 任务识别
    task_type: Optional[str]
    task_confidence: Optional[float]

    # 动态工具
    available_tools: List[Dict[str, Any]]
    executed_tools: List[str]

    # 执行结果
    result: Optional[str]
    intermediate_steps: Annotated[List[Dict], add]

    # 控制流
    iteration: int
    max_iterations: int
    is_complete: bool

    # 错误处理
    errors: Annotated[List[str], add]

    # 元数据
    metadata: Dict[str, Any]


class TaskClassification(BaseModel):
    """任务分类结果"""
    task_type: TaskType = Field(description="任务类型")
    confidence: float = Field(description="分类置信度 0-1")
    required_tools: List[str] = Field(description="需要的工具列表")
    reasoning: str = Field(description="分类理由")


# ============================================================================
# 2. 工具注册系统
# ============================================================================

class ToolRegistry:
    """动态工具注册表"""

    def __init__(self):
        self._tools: Dict[str, Any] = {}
        self._tool_metadata: Dict[str, Dict] = {}

    def register(self, name: str, tool_func: Any, metadata: Optional[Dict] = None):
        """注册工具"""
        self._tools[name] = tool_func
        self._tool_metadata[name] = metadata or {}

    def get(self, name: str) -> Optional[Any]:
        """获取工具"""
        return self._tools.get(name)

    def get_by_task_type(self, task_type: str) -> List[Any]:
        """根据任务类型获取相关工具"""
        return [
            self._tools[name]
            for name, meta in self._tool_metadata.items()
            if task_type.lower() in meta.get("task_types", [])
        ]

    def list_tools(self) -> List[Dict[str, Any]]:
        """列出所有工具及其元数据"""
        return [
            {"name": name, **meta}
            for name, meta in self._tool_metadata.items()
        ]

    def load_tools_from_config(self, config_path: str):
        """从配置文件加载工具定义"""
        config = json.loads(Path(config_path).read_text())
        for tool_config in config.get("tools", []):
            # 这里可以动态加载工具模块
            pass


# 全局工具注册表
tool_registry = ToolRegistry()


# ============================================================================
# 3. 内置工具定义
# ============================================================================

@tool
def code_analyzer(code: str, language: str = "python") -> str:
    """分析代码并提供建议"""
    return f"分析了 {language} 代码，发现 {len(code.splitlines())} 行代码"


@tool
def web_searcher(query: str, max_results: int = 5) -> str:
    """搜索网络信息"""
    return f"找到 {max_results} 个关于 '{query}' 的结果"


@tool
def data_calculator(expression: str) -> str:
    """计算数学表达式"""
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return f"计算结果: {result}"
    except Exception as e:
        return f"计算错误: {str(e)}"


@tool
def document_summarizer(text: str) -> str:
    """总结文档内容"""
    return f"文档总结（共 {len(text)} 个字符）: {text[:100]}..."


@tool
def api_client(endpoint: str, method: str = "GET") -> str:
    """调用 API 接口"""
    return f"调用 API: {method} {endpoint}"


# 注册内置工具
tool_registry.register("code_analyzer", code_analyzer, {
    "task_types": ["coding", "analysis"],
    "description": "代码分析与建议"
})

tool_registry.register("web_searcher", web_searcher, {
    "task_types": ["research", "general"],
    "description": "网络搜索"
})

tool_registry.register("data_calculator", data_calculator, {
    "task_types": ["calculation", "analysis"],
    "description": "数学计算"
})

tool_registry.register("document_summarizer", document_summarizer, {
    "task_types": ["research", "analysis"],
    "description": "文档总结"
})

tool_registry.register("api_client", api_client, {
    "task_types": ["coding", "general"],
    "description": "API 调用"
})


# ============================================================================
# 4. LLM 初始化
# ============================================================================

def create_llm():
    """创建 LLM 实例"""
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
# 5. Agent 节点定义
# ============================================================================

def task_classifier_node(state: AgentState) -> Dict[str, Any]:
    """任务分类节点 - 识别任务类型并加载相应工具"""
    messages = state["messages"]
    last_message = messages[-1] if messages else None

    if not last_message:
        return {"task_type": TaskType.GENERAL, "task_confidence": 0.5}

    # 使用 LLM 进行结构化任务分类
    llm = create_llm()
    classifier = llm.with_structured_output(TaskClassification)

    system_prompt = """你是一个任务分类专家。分析用户请求并分类为以下类型之一：
- coding: 编程、代码分析、开发任务
- research: 信息搜索、调研、文档处理
- analysis: 数据分析、推理、评估
- calculation: 数学计算、数值处理
- general: 一般对话、其他任务

同时识别完成任务需要的工具。"""

    try:
        result = classifier.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=last_message.content)
        ])

        # 根据任务类型加载相应工具
        relevant_tools = tool_registry.get_by_task_type(result.task_type)
        tools_info = [
            {"name": tool.name, "description": tool.description}
            for tool in relevant_tools
        ]

        return {
            "task_type": result.task_type,
            "task_confidence": result.confidence,
            "available_tools": tools_info,
            "intermediate_steps": [{
                "step": "classification",
                "result": result.dict()
            }]
        }

    except Exception as e:
        return {
            "task_type": TaskType.GENERAL,
            "task_confidence": 0.5,
            "errors": [f"分类失败: {str(e)}"]
        }


def planner_node(state: AgentState) -> Dict[str, Any]:
    """规划节点 - 制定执行计划"""
    task_type = state.get("task_type", TaskType.GENERAL)
    available_tools = state.get("available_tools", [])

    llm = create_llm()

    prompt = f"""任务类型: {task_type}
可用工具: {', '.join([t['name'] for t in available_tools])}

请制定一个执行计划来完成用户的任务。考虑：
1. 需要使用哪些工具
2. 执行的顺序
3. 预期的中间步骤
"""

    try:
        response = llm.invoke([
            HumanMessage(content=prompt),
            *state["messages"][-3:]  # 包含最近的对话上下文
        ])

        return {
            "messages": [response],
            "intermediate_steps": [{
                "step": "planning",
                "plan": response.content
            }]
        }

    except Exception as e:
        return {"errors": [f"规划失败: {str(e)}"]}


def executor_node(state: AgentState) -> Dict[str, Any]:
    """执行节点 - 执行工具并处理结果"""
    task_type = state.get("task_type", TaskType.GENERAL)
    iteration = state.get("iteration", 0)

    # 获取相关工具
    relevant_tools = tool_registry.get_by_task_type(task_type)

    if not relevant_tools:
        return {
            "messages": [AIMessage(content="没有可用的相关工具")],
            "is_complete": True
        }

    # 创建带工具的 LLM
    llm = create_llm()
    llm_with_tools = llm.bind_tools(relevant_tools)

    try:
        # 执行工具调用
        response = llm_with_tools.invoke(state["messages"])

        # 检查是否有工具调用
        if response.tool_calls:
            executed_tools = []
            results = []

            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                # 执行工具
                tool_obj = tool_registry.get(tool_name)
                if tool_obj:
                    result = tool_obj.invoke(tool_args)
                    executed_tools.append(tool_name)
                    results.append(f"{tool_name}: {result}")

            return {
                "messages": [response, AIMessage(content="\n".join(results))],
                "executed_tools": executed_tools,
                "intermediate_steps": [{
                    "step": "execution",
                    "tools": executed_tools,
                    "iteration": iteration
                }]
            }
        else:
            # 没有工具调用，任务完成
            return {
                "messages": [response],
                "is_complete": True,
                "result": response.content
            }

    except Exception as e:
        return {
            "errors": [f"执行失败: {str(e)}"],
            "is_complete": True
        }


def reflector_node(state: AgentState) -> Dict[str, Any]:
    """反思节点 - 评估结果并决定是否需要继续"""
    messages = state["messages"]
    executed_tools = state.get("executed_tools", [])
    is_complete = state.get("is_complete", False)
    iteration = state.get("iteration", 0)

    if is_complete or iteration >= state.get("max_iterations", 5):
        return {"is_complete": True}

    # 使用 LLM 评估是否需要继续
    llm = create_llm()

    prompt = f"""已执行的工具: {', '.join(executed_tools)}
当前迭代: {iteration}

评估是否需要继续执行以完成任务。如果已经得到满意的答案，返回 "complete"。
如果需要更多信息或执行更多步骤，返回 "continue"。"""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])

        should_continue = "continue" in response.content.lower()

        return {
            "is_complete": not should_continue,
            "iteration": iteration + 1,
            "intermediate_steps": [{
                "step": "reflection",
                "decision": "continue" if should_continue else "complete"
            }]
        }

    except Exception as e:
        return {
            "errors": [f"反思失败: {str(e)}"],
            "is_complete": True
        }


def synthesizer_node(state: AgentState) -> Dict[str, Any]:
    """综合节点 - 生成最终回答"""
    messages = state["messages"]
    intermediate_steps = state.get("intermediate_steps", [])

    llm = create_llm()

    prompt = f"""基于以下执行步骤，生成最终回答：

执行步骤:
{json.dumps(intermediate_steps, indent=2, ensure_ascii=False)}

对话历史:
{[m.content for m in messages[-5:]]}

请提供清晰、准确的最终答案。"""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])

        return {
            "result": response.content,
            "messages": [response],
            "is_complete": True
        }

    except Exception as e:
        return {
            "errors": [f"综合失败: {str(e)}"],
            "result": f"处理完成，但综合步骤出错: {str(e)}"
        }


# ============================================================================
# 6. 路由逻辑
# ============================================================================

def should_continue(state: AgentState) -> str:
    """决定是否继续执行"""
    if state.get("is_complete", False):
        return "synthesize"
    if state.get("iteration", 0) >= state.get("max_iterations", 5):
        return "synthesize"
    if state.get("errors"):
        return "synthesize"
    return "execute"


def route_after_planning(state: AgentState) -> str:
    """规划后路由决策"""
    task_type = state.get("task_type", "")
    available_tools = state.get("available_tools", [])

    if not available_tools:
        # 没有可用工具，直接生成回答
        return "synthesize"

    # 有工具可用，进入执行阶段
    return "execute"


# ============================================================================
# 7. 图构建
# ============================================================================

def create_dynamic_agent_graph():
    """创建动态 agent 计算图"""

    # 初始化状态图
    graph = StateGraph(AgentState)

    # 添加节点
    graph.add_node("classify", task_classifier_node)
    graph.add_node("plan", planner_node)
    graph.add_node("execute", executor_node)
    graph.add_node("reflect", reflector_node)
    graph.add_node("synthesize", synthesizer_node)

    # 添加边
    graph.add_edge(START, "classify")
    graph.add_edge("classify", "plan")
    graph.add_conditional_edges(
        "plan",
        route_after_planning,
        {
            "execute": "execute",
            "synthesize": "synthesize"
        }
    )
    graph.add_conditional_edges(
        "execute",
        should_continue,
        {
            "execute": "reflect",
            "synthesize": "synthesize"
        }
    )
    graph.add_conditional_edges(
        "reflect",
        should_continue,
        {
            "execute": "execute",
            "synthesize": "synthesize"
        }
    )
    graph.add_edge("synthesize", END)

    # 编译图（添加持久化支持）
    memory = MemorySaver()
    app = graph.compile(checkpointer=memory)

    return app


# ============================================================================
# 8. Agent 接口
# ============================================================================

class DynamicAgent:
    """动态 Agent 接口"""

    def __init__(self, config: Optional[Dict] = None):
        """初始化 agent"""
        self.app = create_dynamic_agent_graph()
        self.config = config or {
            "configurable": {"thread_id": "default_session"}
        }

    def run(self, message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """运行 agent"""
        config = self.config.copy()
        if session_id:
            config["configurable"]["thread_id"] = session_id

        initial_state: AgentState = {
            "messages": [HumanMessage(content=message)],
            "task_type": None,
            "task_confidence": None,
            "available_tools": [],
            "executed_tools": [],
            "result": None,
            "intermediate_steps": [],
            "iteration": 0,
            "max_iterations": 5,
            "is_complete": False,
            "errors": [],
            "metadata": {}
        }

        try:
            result = self.app.invoke(initial_state, config)
            return {
                "success": True,
                "result": result.get("result"),
                "task_type": result.get("task_type"),
                "intermediate_steps": result.get("intermediate_steps"),
                "errors": result.get("errors", [])
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "errors": [str(e)]
            }

    async def astream(self, message: str, session_id: Optional[str] = None):
        """异步流式运行"""
        config = self.config.copy()
        if session_id:
            config["configurable"]["thread_id"] = session_id

        initial_state: AgentState = {
            "messages": [HumanMessage(content=message)],
            "task_type": None,
            "task_confidence": None,
            "available_tools": [],
            "executed_tools": [],
            "result": None,
            "intermediate_steps": [],
            "iteration": 0,
            "max_iterations": 5,
            "is_complete": False,
            "errors": [],
            "metadata": {}
        }

        async for event in self.app.astream(initial_state, config):
            yield event

    def chat(self, message: str, session_id: Optional[str] = None) -> str:
        """简单聊天接口"""
        result = self.run(message, session_id)
        if result["success"]:
            return result["result"] or "处理完成"
        else:
            return f"错误: {result.get('error', '未知错误')}"

    def register_tool(self, name: str, tool_func: Any, metadata: Optional[Dict] = None):
        """注册新工具"""
        tool_registry.register(name, tool_func, metadata)

    def list_tools(self) -> List[Dict]:
        """列出所有可用工具"""
        return tool_registry.list_tools()


# ============================================================================
# 9. 使用示例
# ============================================================================

def main():
    """主函数 - 使用示例"""

    # 加载环境变量
    from dotenv import load_dotenv
    load_dotenv()

    # 创建 agent
    agent = DynamicAgent()

    print("=" * 60)
    print("动态 Agent 调用框架")
    print("=" * 60)

    # 示例 1: 编程任务
    print("\n📝 示例 1: 编程任务")
    result1 = agent.chat(
        "帮我分析这段代码: def hello(): print('world')",
        session_id="session_1"
    )
    print(f"结果: {result1}")

    # 示例 2: 计算任务
    print("\n🔢 示例 2: 计算任务")
    result2 = agent.chat(
        "计算 25 * 4 + 10",
        session_id="session_2"
    )
    print(f"结果: {result2}")

    # 示例 3: 研究任务
    print("\n🔍 示例 3: 研究任务")
    result3 = agent.chat(
        "搜索关于 Python 异步编程的信息",
        session_id="session_3"
    )
    print(f"结果: {result3}")

    # 示例 4: 查看可用工具
    print("\n🛠️ 可用工具:")
    for tool_info in agent.list_tools():
        print(f"  - {tool_info['name']}: {tool_info.get('description', 'N/A')}")


if __name__ == "__main__":
    main()
