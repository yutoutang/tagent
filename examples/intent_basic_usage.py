"""
意图系统基本用法示例

演示如何使用意图系统进行基本的意图识别、编排和执行
"""

import asyncio
from dotenv import load_dotenv

# 导入意图系统组件
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from intent_system.core import IntentRegistry
from intent_system.core.intent_parser import IntentParser
from intent_system.orchestration import IntentOrchestrator
from intent_system.execution import IntentExecutor
from intent_system.builtin_intents import register_builtin_data_intents

# 导入 LLM 创建函数
from dynamic_agent_framework import create_llm


async def main():
    """主函数"""
    print("=" * 60)
    print("意图系统基本用法示例")
    print("=" * 60)

    # 加载环境变量
    load_dotenv()

    # 1. 初始化组件
    print("\n1. 初始化组件...")
    registry = IntentRegistry()
    llm = create_llm()

    # 2. 注册内置意图
    print("\n2. 注册内置意图...")
    register_builtin_data_intents(registry)
    print(f"   已注册 {registry.count()} 个意图:")
    for intent in registry.list_all():
        print(f"   - {intent.metadata.id}: {intent.metadata.name}")

    # 3. 创建解析器和编排器
    print("\n3. 创建解析器和编排器...")
    parser = IntentParser(llm, registry)
    orchestrator = IntentOrchestrator(registry)
    executor = IntentExecutor(registry)

    # 4. 示例 1: 单意图识别与执行
    print("\n" + "=" * 60)
    print("示例 1: 单意图 - 计算数学表达式")
    print("=" * 60)

    user_input_1 = "帮我计算 25 * 4 + 10"
    print(f"\n用户输入: {user_input_1}")

    parse_result_1 = parser.parse(user_input_1)
    print(f"\n识别结果:")
    print(f"  主要意图: {parse_result_1.primary_intent}")
    print(f"  置信度: {parse_result_1.confidence:.2f}")
    print(f"  理由: {parse_result_1.reasoning}")

    # 编排
    plan_1 = orchestrator.orchestrate(parse_result_1)
    print(f"\n编排计划:")
    print(f"  执行层数: {len(plan_1.execution_layers)}")
    print(f"  执行顺序: {plan_1.execution_order}")

    # 执行
    results_1 = await executor.execute_plan_async(plan_1, "session_1")
    print(f"\n执行结果:")
    for intent_id, result in results_1.items():
        print(f"  {intent_id}: {result}")

    # 5. 示例 2: 多意图识别与并行执行
    print("\n" + "=" * 60)
    print("示例 2: 多意图 - 同时执行多个独立任务")
    print("=" * 60)

    user_input_2 = """
    同时帮我做以下几件事：
    1. 计算 100 / 5
    2. 搜索关于 Python 的信息
    3. 处理文本 'Hello World'，转成大写
    """
    print(f"\n用户输入: {user_input_2}")

    parse_result_2 = parser.parse(user_input_2)
    print(f"\n识别结果:")
    print(f"  主要意图: {parse_result_2.primary_intent}")
    print(f"  子意图数: {len(parse_result_2.sub_intents)}")
    if parse_result_2.sub_intents:
        print(f"  子意图列表:")
        for sub in parse_result_2.sub_intents:
            print(f"    - {sub['id']}")

    # 编排
    plan_2 = orchestrator.orchestrate(parse_result_2)
    print(f"\n编排计划:")
    print(f"  执行层数: {len(plan_2.execution_layers)}")
    for i, layer in enumerate(plan_2.execution_layers, 1):
        print(f"  第 {i} 层: {layer}")

    # 执行
    results_2 = await executor.execute_plan_async(plan_2, "session_2")
    print(f"\n执行结果:")
    for intent_id, result in results_2.items():
        print(f"  {intent_id}: {result}")

    # 打印执行摘要
    print(f"\n执行摘要:")
    summary_2 = executor.get_execution_summary()
    print(f"  总意图数: {summary_2['total_intents']}")
    print(f"  成功: {summary_2['successful']}")
    print(f"  失败: {summary_2['failed']}")
    print(f"  总耗时: {summary_2['total_duration']:.2f}s")

    # 6. 示例 3: 数据流转
    print("\n" + "=" * 60)
    print("示例 3: 数据流转 - 意图间传递数据")
    print("=" * 60)

    # 直接编排多个意图
    intent_ids = ["calculator", "data_analysis"]
    parameters = {"expression": "25 * 4"}

    print(f"\n意图序列: {intent_ids}")
    print(f"初始参数: {parameters}")

    plan_3 = orchestrator.orchestrate_from_intents(
        intent_ids,
        parameters,
        context={"expression": "25 * 4"}
    )

    print(f"\n编排计划:")
    print(f"  执行顺序: {plan_3.execution_order}")
    print(f"  数据映射: {plan_3.data_mappings}")

    results_3 = await executor.execute_plan_async(plan_3, "session_3")
    print(f"\n执行结果:")
    for intent_id, result in results_3.items():
        print(f"  {intent_id}: {result}")

    print("\n" + "=" * 60)
    print("示例运行完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
