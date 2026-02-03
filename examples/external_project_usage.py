"""
在其他项目中使用 Intent System 的示例

假设你已经通过 pip install -e 安装了 intent_system 包
"""

# 方式1: 直接从 intent_system 导入
from intent_system import (
    IntentRegistry,
    IntentDefinition,
    IntentMetadata,
    InputOutputSchema,
    IntentParser,
    IntentOrchestrator,
    IntentExecutor
)

# 方式2: 导入工作流模块
from intent_system.workflow import WorkflowIntentManager, load_workflow_from_json


def example_basic_usage():
    """基础使用示例"""
    print("=" * 60)
    print("示例1: 基础意图注册与执行")
    print("=" * 60)

    # 1. 创建注册表
    registry = IntentRegistry()

    # 2. 定义一个简单的意图
    def hello_executor(**kwargs):
        name = kwargs.get('name', 'World')
        return {"message": f"Hello, {name}!"}

    hello_intent = IntentDefinition(
        metadata=IntentMetadata(
            id="hello",
            name="问候",
            description="向用户打招呼",
            category="greeting"
        ),
        schema=InputOutputSchema(),
        executor=hello_executor
    )

    # 3. 注册意图
    registry.register(hello_intent)
    print(f"\n✓ 已注册意图: {hello_intent.metadata.name}")

    # 4. 执行意图
    result = hello_intent.executor(name="Alice")
    print(f"\n✓ 执行结果: {result['message']}")


def example_workflow_usage():
    """工作流使用示例"""
    print("\n" + "=" * 60)
    print("示例2: 工作流管理")
    print("=" * 60)

    # 创建工作流管理器
    manager = WorkflowIntentManager()

    # 从 JSON 加载工作流定义（假设文件存在）
    # manager.load_from_json("workflow_intents.json")

    # 识别意图
    user_input = "我想学习Python开发"
    intent_id, confidence = manager.recognize_intent(user_input)

    print(f"\n用户输入: {user_input}")
    print(f"识别意图: {intent_id} (置信度: {confidence:.2f})")


def example_complete_workflow():
    """完整工作流示例"""
    print("\n" + "=" * 60)
    print("示例3: 完整的工作流流程")
    print("=" * 60)

    # 导入必要的模块
    import asyncio
    from intent_system.core.intent_parser import IntentParseResult

    # 1. 初始化组件
    registry = IntentRegistry()
    orchestrator = IntentOrchestrator(registry)
    executor = IntentExecutor(registry)

    # 2. 定义几个工作流意图
    def study_executor(**kwargs):
        return {"status": "completed", "result": "学习完成"}

    def develop_executor(**kwargs):
        return {"status": "completed", "result": "开发完成"}

    # 注册意图
    for name, desc, executor_func in [
        ("study", "学习新知识", study_executor),
        ("develop", "开发功能", develop_executor),
    ]:
        intent = IntentDefinition(
            metadata=IntentMetadata(
                id=name,
                name=name,
                description=desc,
                category="workflow"
            ),
            schema=InputOutputSchema(),
            executor=executor_func
        )
        registry.register(intent)

    print(f"\n✓ 注册了 {registry.count()} 个意图")

    # 3. 创建解析结果
    parse_result = IntentParseResult(
        primary_intent="study",
        confidence=0.9,
        reasoning="用户想要学习",
        parameters={},
        sub_intents=[]
    )

    # 4. 编排计划
    plan = orchestrator.orchestrate(parse_result)

    print(f"\n✓ 编排计划: {' -> '.join(plan.execution_order)}")

    # 5. 执行计划
    async def execute():
        results = await executor.execute_plan_async(plan, "test_session")
        for intent_id, result in results.items():
            print(f"   - {intent_id}: {result.get('result', result)}")

    asyncio.run(execute())


def main():
    """运行所有示例"""
    print("\n" + "=" * 70)
    print("Intent System - 在其他项目中的使用示例")
    print("=" * 70)
    print("\n这些示例展示了如何在安装 intent_system 后在其他项目中使用")
    print("安装方式: pip install -e /path/to/tagent")

    example_basic_usage()
    example_workflow_usage()
    example_complete_workflow()

    print("\n" + "=" * 70)
    print("所有示例运行完成！")
    print("=" * 70)

    print("\n💡 提示:")
    print("  - 参考 INTENT_SYSTEM_INSTALL.md 了解更多安装方式")
    print("  - 查看 examples/ 目录获取更多完整示例")


if __name__ == "__main__":
    main()
