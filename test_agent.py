"""
测试动态 Agent 框架
"""

import os
from dotenv import load_dotenv
from dynamic_agent_framework import DynamicAgent, tool_registry
from langchain_core.tools import tool


def test_basic_functionality():
    """测试基本功能"""
    print("=" * 60)
    print("测试 1: 基本功能测试")
    print("=" * 60)

    load_dotenv()

    # 检查 API Key
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠️  警告: 未设置 API Key，请检查 .env 文件")
        print("   复制 .env.example 为 .env 并填入你的 API Key")
        return

    agent = DynamicAgent()

    # 测试任务分类
    test_cases = [
        ("帮我分析这段 Python 代码", "coding"),
        ("计算 100 * 25", "calculation"),
        ("搜索最新的 AI 技术", "research"),
        ("今天天气怎么样", "general"),
    ]

    for query, expected_type in test_cases:
        print(f"\n📋 查询: {query}")
        print(f"   预期类型: {expected_type}")

        result = agent.run(query, session_id=f"test_{expected_type}")

        if result["success"]:
            print(f"   ✅ 识别类型: {result['task_type']}")
            print(f"   ✅ 置信度: {result.get('task_confidence', 'N/A')}")
            if result['intermediate_steps']:
                print(f"   ✅ 执行步骤: {len(result['intermediate_steps'])} 步")
        else:
            print(f"   ❌ 错误: {result.get('error', 'Unknown error')}")


def test_custom_tool():
    """测试自定义工具"""
    print("\n" + "=" * 60)
    print("测试 2: 自定义工具测试")
    print("=" * 60)

    @tool
    def weather_checker(city: str) -> str:
        """查询城市天气"""
        # 模拟天气查询
        weather_data = {
            "北京": "晴天，温度 15°C",
            "上海": "多云，温度 18°C",
            "深圳": "阴天，温度 22°C",
        }
        return weather_data.get(city, f"{city} 的天气信息暂未获取")

    # 注册自定义工具
    agent = DynamicAgent()
    agent.register_tool(
        "weather_checker",
        weather_checker,
        {
            "task_types": ["research", "general"],
            "description": "天气查询工具"
        }
    )

    print("✅ 已注册自定义工具: weather_checker")

    # 测试自定义工具
    result = agent.chat("查询北京的天气", session_id="test_weather")
    print(f"\n📋 查询: 查询北京的天气")
    print(f"📤 回答: {result}")


def test_multi_turn_conversation():
    """测试多轮对话"""
    print("\n" + "=" * 60)
    print("测试 3: 多轮对话测试")
    print("=" * 60)

    load_dotenv()
    agent = DynamicAgent()

    session_id = "test_conversation_1"
    conversation = [
        "我想计算一个数学问题",
        "计算 25 * 4",
        "再加上 100",
    ]

    for i, query in enumerate(conversation, 1):
        print(f"\n📋 第 {i} 轮: {query}")
        result = agent.chat(query, session_id=session_id)
        print(f"📤 回答: {result}")


def test_streaming():
    """测试流式输出"""
    print("\n" + "=" * 60)
    print("测试 4: 流式输出测试")
    print("=" * 60)

    load_dotenv()
    agent = DynamicAgent()

    print("\n📋 查询: 帮我分析代码并搜索相关资料")

    import asyncio

    async def stream_test():
        step_count = 0
        async for event in agent.astream(
            "帮我分析 Python 中的 async/await 用法",
            session_id="test_stream"
        ):
            step_count += 1
            print(f"  🔄 步骤 {step_count}: {list(event.keys())}")

            # 打印状态更新
            for node_name, node_state in event.items():
                if "task_type" in node_state:
                    print(f"     📊 任务类型: {node_state['task_type']}")
                if "is_complete" in node_state and node_state["is_complete"]:
                    print(f"     ✅ 完成")

        print(f"\n✅ 总共 {step_count} 个步骤")

    asyncio.run(stream_test())


def test_error_handling():
    """测试错误处理"""
    print("\n" + "=" * 60)
    print("测试 5: 错误处理测试")
    print("=" * 60)

    load_dotenv()
    agent = DynamicAgent()

    # 测试无效输入
    print("\n📋 测试空输入")
    result = agent.chat("", session_id="test_error_1")
    print(f"📤 回答: {result}")

    # 测试复杂计算（可能超出限制）
    print("\n📋 测试复杂计算")
    result = agent.chat("计算 999999 ** 999999", session_id="test_error_2")
    print(f"📤 回答: {result}")


def test_tool_listing():
    """测试工具列表"""
    print("\n" + "=" * 60)
    print("测试 6: 工具列表")
    print("=" * 60)

    agent = DynamicAgent()
    tools = agent.list_tools()

    print(f"\n🛠️  可用工具总数: {len(tools)}\n")

    for tool_info in tools:
        print(f"  📦 {tool_info['name']}")
        print(f"     描述: {tool_info.get('description', 'N/A')}")
        print(f"     任务类型: {', '.join(tool_info.get('task_types', []))}")
        print()


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("🚀 动态 Agent 框架 - 测试套件")
    print("=" * 60)

    try:
        test_basic_functionality()
        test_custom_tool()
        test_multi_turn_conversation()
        test_streaming()
        test_error_handling()
        test_tool_listing()

        print("\n" + "=" * 60)
        print("✅ 所有测试完成！")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"\n\n❌ 测试过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
