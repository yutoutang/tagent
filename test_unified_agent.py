"""
统一 Agent 测试套件

测试融合后的 intent_system.agent 模块的所有功能
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


def test_basic_run():
    """测试基本运行功能"""
    print("\n" + "=" * 60)
    print("测试 1: 基本运行功能")
    print("=" * 60)

    from intent_system.agent import UnifiedAgent

    agent = UnifiedAgent()

    # 测试计算意图
    result = agent.run("帮我计算 25 * 4")

    print(f"[OK] Success: {result['success']}")
    print(f"   检测到的意图: {result['detected_intents']}")
    print(f"   意图置信度: {result['intent_confidence']:.2f}")
    print(f"   任务类型: {result['task_type']}")
    print(f"   意图结果: {result['intent_results']}")
    print(f"   最终结果: {result['result'][:200] if result['result'] else 'N/A'}")

    assert result['success'], "执行应该成功"
    assert len(result['detected_intents']) > 0, "应该检测到意图"
    return result


def test_chat_interface():
    """测试简单聊天接口"""
    print("\n" + "=" * 60)
    print("测试 2: 简单聊天接口")
    print("=" * 60)

    from intent_system.agent import UnifiedAgent

    agent = UnifiedAgent()

    response = agent.chat("搜索 Python 异步编程的信息")

    print(f"[Chat] Response: {response[:300]}")

    assert response, "应该有回复"
    assert "错误" not in response, "不应包含错误"
    return response


def test_multi_intent():
    """测试多意图识别和执行"""
    print("\n" + "=" * 60)
    print("测试 3: 多意图识别和执行")
    print("=" * 60)

    from intent_system.agent import UnifiedAgent

    agent = UnifiedAgent()

    # 包含多个意图的请求
    result = agent.run("计算 100 / 5，然后分析结果")

    print(f"[OK] Success: {result['success']}")
    print(f"   检测到的意图: {result['detected_intents']}")
    print(f"   意图结果数量: {len(result['intent_results'])}")
    print(f"   执行摘要: {result['execution_summary']}")

    assert result['success'], "执行应该成功"
    return result


def test_reflection_mechanism():
    """测试反思机制"""
    print("\n" + "=" * 60)
    print("测试 4: 反思机制")
    print("=" * 60)

    from intent_system.agent import UnifiedAgent

    agent = UnifiedAgent(max_iterations=2)

    result = agent.run("计算 25 * 4")

    print(f"[OK] Success: {result['success']}")
    print(f"   反思结果: {result['reflection_result']}")

    if result['reflection_result']:
        print(f"   - 是否继续: {result['reflection_result']['should_continue']}")
        print(f"   - 置信度: {result['reflection_result']['confidence']:.2f}")
        print(f"   - 理由: {result['reflection_result']['reasoning'][:100]}")

    assert result['success'], "执行应该成功"
    return result


def test_stream_execution():
    """测试流式执行"""
    print("\n" + "=" * 60)
    print("测试 5: 流式执行")
    print("=" * 60)

    from intent_system.agent import UnifiedAgent

    agent = UnifiedAgent()

    print("开始流式执行...")
    for event in agent.stream("计算 50 + 30"):
        for node_name, node_state in event.items():
            if isinstance(node_state, dict) and "intermediate_steps" in node_state:
                steps = node_state.get("intermediate_steps", [])
                if steps:
                    last_step = steps[-1]
                    print(f"   [EXEC] {node_name}: {last_step.get('step', 'unknown')}")

    print("[OK] Stream execution completed")
    return True


async def test_async_execution():
    """测试异步执行"""
    print("\n" + "=" * 60)
    print("测试 6: 异步执行")
    print("=" * 60)

    from intent_system.agent import UnifiedAgent

    agent = UnifiedAgent()

    result = await agent.arun("计算 123 * 456")

    print(f"[OK] Success: {result['success']}")
    print(f"   意图结果: {result['intent_results']}")
    print(f"   最终结果: {result['result'][:200] if result['result'] else 'N/A'}")

    assert result['success'], "执行应该成功"
    return result


async def test_async_stream():
    """测试异步流式执行"""
    print("\n" + "=" * 60)
    print("测试 7: 异步流式执行")
    print("=" * 60)

    from intent_system.agent import UnifiedAgent

    agent = UnifiedAgent()

    count = 0
    async for event in agent.astream("分析数据: 1, 2, 3, 4, 5"):
        count += 1
        print(f"   [EVENT] {count}: {list(event.keys())}")

    print(f"[OK] Async stream completed, {count} events")
    return True


def test_custom_intent():
    """测试自定义意图注册"""
    print("\n" + "=" * 60)
    print("测试 8: 自定义意图注册")
    print("=" * 60)

    from intent_system.agent import UnifiedAgent
    from intent_system.core import IntentDefinition, IntentMetadata, InputOutputSchema
    from langchain_core.tools import tool

    @tool
    async def reverse_string(text: str) -> str:
        """反转字符串"""
        return text[::-1]

    # 创建自定义意图
    custom_intent = IntentDefinition(
        metadata=IntentMetadata(
            id="reverse_string",
            name="反转字符串",
            description="将输入的字符串反转",
            category="transform",
            tags=["string", "text"]
        ),
        schema=InputOutputSchema(
            inputs={
                "text": {
                    "type": "string",
                    "description": "要反转的字符串",
                    "required": True
                }
            },
            outputs={
                "result": {"type": "string"}
            }
        ),
        executor=reverse_string.func
    )

    agent = UnifiedAgent()
    agent.register_intent(custom_intent)

    print(f"[OK] Custom intent registered: {custom_intent.metadata.id}")

    # 列出所有意图
    intents = agent.list_intents()
    print(f"   总意图数: {len(intents)}")
    custom_found = any(i.metadata.id == "reverse_string" for i in intents)
    print(f"   自定义意图存在: {custom_found}")

    assert custom_found, "自定义意图应该存在"

    # 测试使用自定义意图
    result = agent.run("把 hello 反转")
    print(f"   执行结果: {result['intent_results']}")

    return result


def test_session_persistence():
    """测试会话持久化"""
    print("\n" + "=" * 60)
    print("测试 9: 会话持久化")
    print("=" * 60)

    from intent_system.agent import UnifiedAgent

    agent = UnifiedAgent()
    session_id = "test_session_123"

    # 第一次对话
    result1 = agent.run("我的名字是 Alice", session_id=session_id)
    print(f"   第1轮: {result1['result'][:100] if result1['result'] else 'N/A'}")

    # 第二次对话（应该记住上下文）
    result2 = agent.run("我叫什么名字？", session_id=session_id)
    print(f"   第2轮: {result2['result'][:100] if result2['result'] else 'N/A'}")

    print("✅ 会话持久化测试完成")
    return result2


def test_error_handling():
    """测试错误处理"""
    print("\n" + "=" * 60)
    print("测试 10: 错误处理")
    print("=" * 60)

    from intent_system.agent import UnifiedAgent

    agent = UnifiedAgent()

    # 测试无效输入
    result = agent.run("")

    print(f"   成功: {result['success']}")
    print(f"   错误: {result.get('error', 'N/A')}")
    print(f"   错误列表: {result['errors']}")

    # 即使有错误，也应该返回结果
    assert 'error' in result or 'errors' in result, "应该有错误信息"
    return result


def test_max_iterations():
    """测试最大迭代次数限制"""
    print("\n" + "=" * 60)
    print("测试 11: 最大迭代次数限制")
    print("=" * 60)

    from intent_system.agent import UnifiedAgent

    agent = UnifiedAgent(max_iterations=1)

    result = agent.run("计算 1 + 1")

    print(f"   最大迭代次数: 1")
    print(f"   实际迭代: {result.get('execution_summary', {}).get('total_intents', 0)}")

    # 检查是否在限制内完成
    assert result['success'], "执行应该成功"

    return result


def test_graph_description():
    """测试图描述"""
    print("\n" + "=" * 60)
    print("测试 12: 图描述")
    print("=" * 60)

    from intent_system.agent import UnifiedAgent

    agent = UnifiedAgent()

    graph_desc = agent.get_graph_description()

    print("图描述:")
    print(graph_desc)

    assert "Intent Parse" in graph_desc, "应包含意图解析节点"
    assert "Orchestrate" in graph_desc, "应包含编排节点"
    assert "Execute" in graph_desc, "应包含执行节点"
    assert "Reflect" in graph_desc, "应包含反思节点"
    assert "Synthesize" in graph_desc, "应包含综合节点"

    return graph_desc


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 70)
    print("统一 Agent 测试套件")
    print("=" * 70)

    tests = [
        ("基本运行功能", test_basic_run),
        ("简单聊天接口", test_chat_interface),
        ("多意图识别和执行", test_multi_intent),
        ("反思机制", test_reflection_mechanism),
        ("流式执行", test_stream_execution),
        ("自定义意图注册", test_custom_intent),
        ("会话持久化", test_session_persistence),
        ("错误处理", test_error_handling),
        ("最大迭代次数限制", test_max_iterations),
        ("图描述", test_graph_description),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            passed += 1
            print(f"[OK] {name} - PASSED")
        except Exception as e:
            failed += 1
            print(f"[FAIL] {name} - FAILED: {str(e)}")

    # 异步测试
    async_tests = [
        ("异步执行", test_async_execution),
        ("异步流式执行", test_async_stream),
    ]

    for name, test_func in async_tests:
        try:
            asyncio.run(test_func())
            passed += 1
            print(f"[OK] {name} - PASSED")
        except Exception as e:
            failed += 1
            print(f"[FAIL] {name} - FAILED: {str(e)}")

    # 汇总
    print("\n" + "=" * 70)
    print("测试汇总")
    print("=" * 70)
    print(f"总计: {passed + failed}")
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print(f"成功率: {passed / (passed + failed) * 100:.1f}%")

    return failed == 0


if __name__ == "__main__":
    # 检查环境变量
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print("WARNING: API Key not set")
        print("Please set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env file")
        print("\nExample .env:")
        print("OPENAI_API_KEY=your-key-here")
        print("LLM_PROVIDER=openai")
        print("MODEL_NAME=gpt-4o")
        sys.exit(1)

    # 运行测试
    success = run_all_tests()
    sys.exit(0 if success else 1)
