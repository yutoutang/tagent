"""
测试 YAgent 流式调用功能

演示如何使用 YAgent 并查看流式输出
"""

import asyncio
from intent_system import YAgent


async def test_streaming():
    """测试流式调用"""
    print("\n" + "="*70)
    print("测试 YAgent 流式调用功能")
    print("="*70)

    # 创建 Agent (使用 DeepSeek)
    print("\n[初始化] 创建 YAgent...")
    agent = YAgent(
        api_key="sk-1b7e48556f154e9ab4d40df712e0bec6",
        base_url="https://api.deepseek.com",
        model_name="deepseek-chat"
    )

    # 注册一个简单的测试意图
    from intent_system import IntentDefinition, IntentMetadata, InputOutputSchema

    async def test_calculator(expression: str) -> str:
        """计算器"""
        try:
            result = eval(expression, {"__builtins__": {}}, {})
            return f"计算结果: {result}"
        except Exception as e:
            return f"错误: {str(e)}"

    test_intent = IntentDefinition(
        metadata=IntentMetadata(
            id="test_calculator",
            name="计算器",
            description="计算数学表达式",
            category="transform",
            tags=["math", "calculator"]
        ),
        schema=InputOutputSchema(
            inputs={
                "expression": {
                    "type": "string",
                    "description": "数学表达式",
                    "required": True
                }
            },
            outputs={"result": {"type": "string"}}
        ),
        executor=test_calculator
    )

    agent.register_intent(test_intent)
    print("[完成] 测试意图已注册\n")

    # 测试查询
    test_queries = [
        "帮我计算 25 * 4 + 10",
        "学习 Python 基础",
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*70}")
        print(f"测试查询 {i}: {query}")
        print(f"{'='*70}\n")

        try:
            result = await agent.arun(query, session_id="test_streaming")

            print(f"\n[执行结果]")
            print(f"  - 成功: {result.get('success', False)}")
            print(f"  - 意图: {result.get('detected_intents', [])}")
            print(f"  - 置信度: {result.get('intent_confidence', 0):.2f}")

            if result.get('result'):
                print(f"\n  最终结果: {result['result']}")

        except Exception as e:
            print(f"\n[错误] {str(e)}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*70}")
    print("测试完成!")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    asyncio.run(test_streaming())
