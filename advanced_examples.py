"""
高级示例 - 展示动态 Agent 框架的更多用法
"""

import asyncio
from typing import List, Dict, Any
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from dynamic_agent_framework import DynamicAgent, tool_registry


# ============================================================================
# 示例 1: 复杂工具定义
# ============================================================================

@tool
def database_query(sql: str, database: str = "default") -> str:
    """
    执行数据库查询（模拟）

    Args:
        sql: SQL 查询语句
        database: 数据库名称

    Returns:
        查询结果
    """
    # 模拟数据库查询
    if "SELECT" in sql.upper():
        return f"[模拟结果] 从 {database} 查询到 5 行数据"
    elif "INSERT" in sql.upper():
        return f"[模拟结果] 在 {database} 插入 1 行数据"
    elif "UPDATE" in sql.upper():
        return f"[模拟结果] 在 {database} 更新 3 行数据"
    else:
        return f"[模拟结果] 执行 SQL: {sql}"


@tool
def file_processor(file_path: str, operation: str = "read") -> str:
    """
    处理文件操作

    Args:
        file_path: 文件路径
        operation: 操作类型 (read, write, analyze)

    Returns:
        操作结果
    """
    if operation == "read":
        return f"读取文件: {file_path}，共 100 行"
    elif operation == "write":
        return f"写入文件: {file_path}"
    elif operation == "analyze":
        return f"分析文件: {file_path}，发现 3 个问题"
    else:
        return f"未知操作: {operation}"


@tool
def api_requester(url: str, method: str = "GET", data: str = "") -> str:
    """
    发起 API 请求

    Args:
        url: API 端点 URL
        method: HTTP 方法 (GET, POST, PUT, DELETE)
        data: 请求体数据

    Returns:
        API 响应
    """
    return f"[模拟响应] {method} {url} -> 200 OK: {data[:50]}"


def setup_advanced_tools():
    """设置高级工具"""
    agent = DynamicAgent()

    # 注册数据库工具
    agent.register_tool(
        "database_query",
        database_query,
        {
            "task_types": ["coding", "analysis"],
            "description": "数据库查询工具",
            "complexity": "high"
        }
    )

    # 注册文件处理工具
    agent.register_tool(
        "file_processor",
        file_processor,
        {
            "task_types": ["coding", "analysis"],
            "description": "文件处理工具",
            "complexity": "medium"
        }
    )

    # 注册 API 请求工具
    agent.register_tool(
        "api_requester",
        api_requester,
        {
            "task_types": ["coding", "general"],
            "description": "API 请求工具",
            "complexity": "medium"
        }
    )

    return agent


def example_complex_workflow():
    """示例：复杂工作流"""
    print("=" * 60)
    print("示例 1: 复杂工作流")
    print("=" * 60)

    load_dotenv()
    agent = setup_advanced_tools()

    # 复杂任务：需要多个工具协作
    task = """
    我需要完成以下任务：
    1. 查询数据库获取用户数据
    2. 将结果写入文件
    3. 调用 API 通知其他系统
    """

    print(f"\n📋 任务: {task}")
    print("\n执行中...\n")

    result = agent.run(task, session_id="complex_workflow")

    if result["success"]:
        print(f"✅ 任务类型: {result['task_type']}")
        print(f"✅ 置信度: {result.get('task_confidence', 'N/A')}")

        if result['intermediate_steps']:
            print(f"\n📊 执行步骤:")
            for i, step in enumerate(result['intermediate_steps'], 1):
                print(f"  {i}. {step.get('step', 'unknown')}")

        print(f"\n📤 最终结果:\n{result['result']}")
    else:
        print(f"❌ 错误: {result.get('error')}")


# ============================================================================
# 示例 2: 流式处理
# ============================================================================

async def example_streaming_workflow():
    """示例：流式处理工作流"""
    print("\n" + "=" * 60)
    print("示例 2: 流式处理")
    print("=" * 60)

    load_dotenv()
    agent = setup_advanced_tools()

    task = "分析数据库数据并生成报告"
    print(f"\n📋 任务: {task}\n")

    step_count = 0
    async for event in agent.astream(task, session_id="streaming_workflow"):
        step_count += 1

        # 解析事件
        for node_name, node_state in event.items():
            print(f"🔄 步骤 {step_count}: {node_name}")

            # 显示关键状态
            if "task_type" in node_state:
                print(f"   📊 任务类型: {node_state['task_type']}")

            if "available_tools" in node_state and node_state['available_tools']:
                print(f"   🛠️  可用工具: {len(node_state['available_tools'])} 个")

            if "executed_tools" in node_state and node_state['executed_tools']:
                print(f"   ✅ 已执行: {', '.join(node_state['executed_tools'])}")

            if "is_complete" in node_state and node_state["is_complete"]:
                print(f"   ✨ 完成")

    print(f"\n✅ 总共 {step_count} 个步骤")


# ============================================================================
# 示例 3: 多轮对话与上下文保持
# ============================================================================

def example_multi_turn_conversation():
    """示例：多轮对话"""
    print("\n" + "=" * 60)
    print("示例 3: 多轮对话")
    print("=" * 60)

    load_dotenv()
    agent = setup_advanced_tools()

    session_id = "conversation_001"

    conversation = [
        "你好，我需要处理一些数据",
        "查询数据库中的订单表",
        "把结果保存到 report.txt",
        "然后发送到 API",
        "最后总结一下整个过程"
    ]

    print(f"\n💬 会话 ID: {session_id}\n")

    for i, query in enumerate(conversation, 1):
        print(f"👤 用户 (第 {i} 轮): {query}")

        result = agent.chat(query, session_id=session_id)

        print(f"🤖 Agent: {result[:200]}...")
        print()


# ============================================================================
# 示例 4: 批量处理
# ============================================================================

def example_batch_processing():
    """示例：批量处理多个任务"""
    print("\n" + "=" * 60)
    print("示例 4: 批量处理")
    print("=" * 60)

    load_dotenv()
    agent = setup_advanced_tools()

    tasks = [
        "计算 25 * 4",
        "查询用户表",
        "分析代码质量",
        "发送通知邮件"
    ]

    print(f"\n📦 批量处理 {len(tasks)} 个任务\n")

    results = []
    for i, task in enumerate(tasks, 1):
        print(f"📋 任务 {i}/{len(tasks)}: {task}")

        result = agent.run(task, session_id=f"batch_task_{i}")

        results.append({
            "task": task,
            "success": result["success"],
            "task_type": result.get("task_type"),
            "result": result.get("result", "")[:100]
        })

        print(f"   {'✅' if result['success'] else '❌'} {result.get('task_type', 'N/A')}")
        print()

    # 汇总
    print("\n📊 处理汇总:")
    success_count = sum(1 for r in results if r["success"])
    print(f"  总任务数: {len(results)}")
    print(f"  成功: {success_count}")
    print(f"  失败: {len(results) - success_count}")

    # 按任务类型统计
    type_counts: Dict[str, int] = {}
    for r in results:
        if r["task_type"]:
            type_counts[r["task_type"]] = type_counts.get(r["task_type"], 0) + 1

    print(f"\n  任务类型分布:")
    for task_type, count in type_counts.items():
        print(f"    - {task_type}: {count}")


# ============================================================================
# 示例 5: 自定义任务路由
# ============================================================================

class TaskRouterAgent(DynamicAgent):
    """自定义任务路由 Agent"""

    def __init__(self):
        super().__init__()
        # 添加特殊的路由逻辑
        self.task_mappings = {
            "数据分析": ["analysis", "calculation"],
            "开发": ["coding"],
            "调研": ["research"],
        }

    def route_task(self, query: str) -> List[str]:
        """自定义路由逻辑"""
        for keyword, task_types in self.task_mappings.items():
            if keyword in query:
                return task_types
        return ["general"]


def example_custom_routing():
    """示例：自定义路由"""
    print("\n" + "=" * 60)
    print("示例 5: 自定义任务路由")
    print("=" * 60)

    load_dotenv()
    agent = TaskRouterAgent()

    query = "我需要进行数据分析任务"
    print(f"\n📋 查询: {query}")

    # 获取路由结果
    suggested_types = agent.route_task(query)
    print(f"🔀 路由到: {', '.join(suggested_types)}")

    # 执行任务
    result = agent.chat(query, session_id="custom_routing")
    print(f"\n📤 结果: {result[:200]}...")


# ============================================================================
# 示例 6: 工具链组合
# ============================================================================

def example_tool_chain():
    """示例：工具链组合"""
    print("\n" + "=" * 60)
    print("示例 6: 工具链组合")
    print("=" * 60)

    load_dotenv()
    agent = setup_advanced_tools()

    # 定义工具链任务
    task = """
    执行以下工具链：
    1. 使用 database_query 查询数据
    2. 使用 file_processor 保存结果
    3. 使用 api_requester 发送通知
    """

    print(f"\n🔗 工具链任务")
    print(f"{task}\n")

    result = agent.run(task, session_id="tool_chain")

    if result["success"]:
        print(f"✅ 执行成功")
        print(f"📊 任务类型: {result['task_type']}")

        # 显示工具执行顺序
        if result['intermediate_steps']:
            print(f"\n🔧 工具执行顺序:")
            for step in result['intermediate_steps']:
                if step.get('step') == 'execution':
                    tools = step.get('tools', [])
                    if tools:
                        print(f"  → {' → '.join(tools)}")

        print(f"\n📤 最终结果:\n{result['result']}")
    else:
        print(f"❌ 执行失败: {result.get('error')}")


# ============================================================================
# 主函数
# ============================================================================

def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("🚀 高级示例集合")
    print("=" * 60)

    try:
        # 示例 1: 复杂工作流
        example_complex_workflow()

        # 示例 2: 流式处理
        asyncio.run(example_streaming_workflow())

        # 示例 3: 多轮对话
        example_multi_turn_conversation()

        # 示例 4: 批量处理
        example_batch_processing()

        # 示例 5: 自定义路由
        example_custom_routing()

        # 示例 6: 工具链
        example_tool_chain()

        print("\n" + "=" * 60)
        print("✅ 所有示例执行完成！")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\n⚠️  被用户中断")
    except Exception as e:
        print(f"\n\n❌ 执行出错: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
