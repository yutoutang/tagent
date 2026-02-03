"""
YAgent 使用示例

演示如何使用融合后的 intent_system.yagent.YAgent
"""

import os
import asyncio
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from intent_system import YAgent
from intent_system.core import IntentDefinition, IntentMetadata, InputOutputSchema
from langchain_core.tools import tool


def example_basic_usage():
    """示例 1: 基本使用"""
    print("\n" + "=" * 60)
    print("示例 1: 基本使用")
    print("=" * 60)

    # 创建 Agent
    agent = YAgent()

    # 简单对话
    response = agent.chat("帮我计算 25 * 4")
    print(f"回复: {response}")

    # 获取完整结果
    result = agent.run("计算 100 / 5")
    print(f"\n完整结果:")
    print(f"  - 成功: {result['success']}")
    print(f"  - 检测到的意图: {result['detected_intents']}")
    print(f"  - 意图置信度: {result['intent_confidence']:.2f}")
    print(f"  - 执行结果: {result['intent_results']}")


def example_multi_intent():
    """示例 2: 多意图处理"""
    print("\n" + "=" * 60)
    print("示例 2: 多意图处理")
    print("=" * 60)

    agent = YAgent()

    result = agent.run("计算 50 + 30，然后分析结果")

    print(f"检测到的意图: {result['detected_intents']}")
    print(f"执行摘要: {result['execution_summary']}")
    print(f"最终结果: {result['result'][:200]}...")


def example_stream():
    """示例 3: 流式执行"""
    print("\n" + "=" * 60)
    print("示例 3: 流式执行")
    print("=" * 60)

    agent = YAgent()

    print("开始流式执行...")
    for event in agent.stream("计算 123 + 456"):
        for node_name, node_state in event.items():
            if isinstance(node_state, dict) and "intermediate_steps" in node_state:
                steps = node_state.get("intermediate_steps", [])
                if steps:
                    last_step = steps[-1]
                    print(f"  [{node_name}] {last_step.get('step', 'unknown')}")

    print("执行完成!")


async def example_async():
    """示例 4: 异步执行"""
    print("\n" + "=" * 60)
    print("示例 4: 异步执行")
    print("=" * 60)

    agent = YAgent()

    result = await agent.arun("计算 999 * 888")
    print(f"结果: {result['intent_results']}")

    # 异步流式
    print("\n异步流式执行:")
    async for event in agent.astream("搜索 Python 信息"):
        print(f"  事件: {list(event.keys())}")


def example_custom_intent():
    """示例 5: 自定义意图"""
    print("\n" + "=" * 60)
    print("示例 5: 自定义意图")
    print("=" * 60)

    # 定义自定义意图
    @tool
    async def reverse_text(text: str) -> str:
        """反转文本"""
        return text[::-1]

    custom_intent = IntentDefinition(
        metadata=IntentMetadata(
            id="reverse_text",
            name="反转文本",
            description="将输入的文本反转",
            category="transform",
            tags=["text", "string"]
        ),
        schema=InputOutputSchema(
            inputs={
                "text": {
                    "type": "string",
                    "description": "要反转的文本",
                    "required": True
                }
            },
            outputs={"result": {"type": "string"}}
        ),
        executor=reverse_text.func
    )

    # 创建 Agent 并注册意图
    agent = YAgent()
    agent.register_intent(custom_intent)

    print(f"已注册自定义意图: {custom_intent.metadata.id}")

    # 使用自定义意图
    result = agent.run("把 hello world 反转")
    print(f"结果: {result['intent_results']}")


def example_reflection():
    """示例 6: 反思机制"""
    print("\n" + "=" * 60)
    print("示例 6: 反思机制")
    print("=" * 60)

    # 设置最大迭代次数
    agent = YAgent(max_iterations=2)

    result = agent.run("计算 25 * 4")

    print(f"执行成功: {result['success']}")
    if result['reflection_result']:
        print(f"反思结果:")
        print(f"  - 是否继续: {result['reflection_result']['should_continue']}")
        print(f"  - 置信度: {result['reflection_result']['confidence']:.2f}")
        print(f"  - 问题: {result['reflection_result']['issues']}")
        print(f"  - 理由: {result['reflection_result']['reasoning'][:100]}...")


def example_session():
    """示例 7: 会话持久化"""
    print("\n" + "=" * 60)
    print("示例 7: 会话持久化")
    print("=" * 60)

    agent = YAgent()
    session_id = "demo_session_001"

    # 多轮对话
    print("第一轮:")
    result1 = agent.run("我的名字是张三", session_id=session_id)
    print(f"  {result1['result'][:100]}...")

    print("\n第二轮:")
    result2 = agent.run("我叫什么名字？", session_id=session_id)
    print(f"  {result2['result'][:100]}...")


def example_graph_visualization():
    """示例 8: 图结构可视化"""
    print("\n" + "=" * 60)
    print("示例 8: 图结构可视化")
    print("=" * 60)

    agent = YAgent()

    graph_desc = agent.get_graph_description()
    print(graph_desc)


def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("统一 Agent (YAgent) 使用示例")
    print("=" * 70)

    # 检查 API Key
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print("\nWARNING: API Key not set!")
        print("Please set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env file\n")
        return

    try:
        # 运行示例
        example_basic_usage()
        example_multi_intent()
        example_stream()
        example_custom_intent()
        example_reflection()
        example_session()
        example_graph_visualization()

        # 异步示例
        asyncio.run(example_async())

        print("\n" + "=" * 70)
        print("所有示例运行完成!")
        print("=" * 70)

    except Exception as e:
        print(f"\nError: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
