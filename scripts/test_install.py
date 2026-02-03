#!/usr/bin/env python3
"""
Intent System 安装测试脚本

用于验证 intent_system 包是否可以正确导入和使用
"""

import sys

def test_imports():
    """测试所有主要模块的导入"""
    print("=" * 60)
    print("Intent System 安装测试")
    print("=" * 60)

    tests_passed = 0
    tests_failed = 0

    # 测试核心模块导入
    print("\n1. 测试核心模块导入...")
    try:
        from intent_system import (
            __version__,
            IntentMetadata,
            InputOutputSchema,
            IntentDefinition,
            IntentRegistry,
            IntentParser,
            IntentParseResult,
            EnhancedAgentState
        )
        print(f"   ✓ 核心模块导入成功 (版本: {__version__})")
        tests_passed += 1
    except ImportError as e:
        print(f"   ✗ 核心模块导入失败: {e}")
        tests_failed += 1

    # 测试编排模块
    print("\n2. 测试编排模块导入...")
    try:
        from intent_system import IntentOrchestrator
        print("   ✓ IntentOrchestrator 导入成功")
        tests_passed += 1
    except ImportError as e:
        print(f"   ✗ IntentOrchestrator 导入失败: {e}")
        tests_failed += 1

    # 测试执行模块
    print("\n3. 测试执行模块导入...")
    try:
        from intent_system import IntentExecutor
        print("   ✓ IntentExecutor 导入成功")
        tests_passed += 1
    except ImportError as e:
        print(f"   ✗ IntentExecutor 导入失败: {e}")
        tests_failed += 1

    # 测试数据流转模块
    print("\n4. 测试数据流转模块导入...")
    try:
        from intent_system import DataFlowEngine
        print("   ✓ DataFlowEngine 导入成功")
        tests_passed += 1
    except ImportError as e:
        print(f"   ✗ DataFlowEngine 导入失败: {e}")
        tests_failed += 1

    # 测试工作流模块
    print("\n5. 测试工作流模块导入...")
    try:
        from intent_system import (
            WorkflowIntentManager,
            WorkflowIntentDefinition,
            WorkflowGuidance,
            load_workflow_from_json
        )
        print("   ✓ 工作流模块导入成功")
        tests_passed += 1
    except ImportError as e:
        print(f"   ✗ 工作流模块导入失败: {e}")
        tests_failed += 1

    # 测试内置意图
    print("\n6. 测试内置意图导入...")
    try:
        from intent_system import register_builtin_data_intents
        print("   ✓ 内置意图导入成功")
        tests_passed += 1
    except ImportError as e:
        print(f"   ✗ 内置意图导入失败: {e}")
        tests_failed += 1

    # 功能测试
    print("\n7. 测试基本功能...")
    try:
        from intent_system import IntentRegistry, IntentDefinition, IntentMetadata, InputOutputSchema

        registry = IntentRegistry()
        intent = IntentDefinition(
            metadata=IntentMetadata(
                id="test",
                name="Test",
                description="Test intent",
                category="test"
            ),
            schema=InputOutputSchema(),
            executor=lambda **kwargs: {"status": "ok"}
        )
        registry.register(intent)

        if registry.count() == 1:
            print("   ✓ 意图注册功能正常")
            tests_passed += 1
        else:
            print("   ✗ 意图注册功能异常")
            tests_failed += 1
    except Exception as e:
        print(f"   ✗ 功能测试失败: {e}")
        tests_failed += 1

    # 总结
    print("\n" + "=" * 60)
    print(f"测试完成: {tests_passed} 通过, {tests_failed} 失败")
    print("=" * 60)

    if tests_failed == 0:
        print("\n✓ 所有测试通过！Intent System 安装成功。")
        return 0
    else:
        print(f"\n✗ 有 {tests_failed} 个测试失败，请检查安装。")
        return 1


if __name__ == "__main__":
    sys.exit(test_imports())
