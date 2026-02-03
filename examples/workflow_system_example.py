"""
工作流意图管理系统示例

展示如何使用集成到 intent_system 框架的工作流意图管理功能
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入工作流意图管理模块
from intent_system.workflow import WorkflowIntentManager, load_workflow_from_json

# 导入标准意图系统组件
from intent_system.core import IntentRegistry
from intent_system.core.intent_parser import IntentParser

# 导入LLM创建函数（可选，用于高级意图识别）
from dynamic_agent_framework import create_llm

# 导入环境变量加载
from dotenv import load_dotenv


def print_section(title: str):
    """打印分节标题"""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def print_result(label: str, content: str):
    """打印结果"""
    print(f"\n{label}:")
    print("-" * 40)
    print(content)


def main():
    """主函数"""
    print_section("工作流意图管理系统示例")

    # 加载环境变量（如果需要使用LLM）
    load_dotenv()

    # 1. 初始化标准意图注册表
    print("\n1. 初始化意图注册表...")
    registry = IntentRegistry()

    # 2. 初始化工作流管理器（集成框架）
    print("\n2. 初始化工作流管理器...")

    # 选项A：不使用LLM（仅关键词匹配）
    manager = WorkflowIntentManager(registry=registry)

    # 选项B：使用LLM进行意图识别（需要设置API密钥）
    # llm = create_llm()
    # parser = IntentParser(llm, registry)
    # manager = WorkflowIntentManager(parser=parser, registry=registry)

    # 3. 从JSON加载工作流定义
    print("\n3. 加载工作流定义...")
    json_path = Path(__file__).parent / "workflow_intents.json"
    count = manager.load_from_json(str(json_path), auto_register=True)
    print(f"   已加载 {count} 个工作流意图")
    print(f"   已注册到标准注册表: {registry.count()} 个意图")

    # 4. 查看所有意图
    print_section("4. 所有可用意图")

    intents = manager.list_all_intents()
    for intent in intents:
        print(f"\n   [{intent['id']}] {intent['name']}")
        print(f"       {intent['description']}")

    # 5. 验证与标准框架的集成
    print_section("5. 验证标准框架集成")

    print("\n标准注册表中的意图:")
    for std_intent in registry.list_all():
        print(f"   - {std_intent.metadata.id}: {std_intent.metadata.name}")
        print(f"     依赖: {std_intent.metadata.dependencies}")

    # 验证依赖关系
    print("\n依赖关系验证:")
    errors = registry.validate_dependencies()
    if errors:
        print("   发现问题:")
        for error in errors:
            print(f"   - {error}")
    else:
        print("   ✓ 所有依赖关系有效")

    # 6. 可视化意图图谱
    print_section("6. 意图谱可视化")

    print(manager.visualize_graph())

    # 7. 生成Graphviz DOT（可选，用于生成图形化图谱）
    print_section("7. Graphviz DOT格式（可用于生成图形）")
    print(manager.get_graphviz_dot())

    # 8. 场景演示：完整工作流
    print_section("8. 场景演示：完整工作流")

    # 场景1：用户想开始学习
    user_input_1 = "我想学习Python开发"
    print(f"\n用户: {user_input_1}")

    result_1 = manager.get_workflow_suggestion(user_input_1)
    if result_1["recognized"]:
        print_result("识别的意图", result_1["current_intent_name"])
        print_result("置信度", f"{result_1['confidence']:.2f}")
        print_result("进入指导", result_1["entry_guidance"])

        if result_1["path_str"]:
            print_result("完整路径", result_1["path_str"])

        if result_1["next_str"]:
            print_result("后续流程", result_1["next_str"])

        manager.set_current_intent(result_1["current_intent"])

    # 场景2：学习完成
    print_section("场景2：学习完成")

    current = manager.get_status()["current_intent"]
    if current:
        completion_result = manager.process_completion(current)
        print_result("完成指导", completion_result["completion_guidance"])

        if completion_result["next_intent_names"]:
            print_result("后续选项", " 或 ".join(completion_result["next_intent_names"]))

        print_result("建议操作", "\n".join(f"- {a}" for a in completion_result["next_actions"]))

    # 场景3：进入开发阶段
    user_input_3 = "我准备开始开发了"
    print(f"\n用户: {user_input_3}")

    result_3 = manager.get_workflow_suggestion(user_input_3)
    if result_3["recognized"]:
        print_result("识别的意图", result_3["current_intent_name"])
        print_result("进入指导", result_3["entry_guidance"])

        if result_3["next_str"]:
            print_result("后续流程", result_3["next_str"])

        manager.set_current_intent(result_3["current_intent"])

    # 场景4：开发完成，面临选择
    print_section("场景4：开发完成 - 面临选择")

    current = manager.get_status()["current_intent"]
    if current:
        completion_result = manager.process_completion(current)
        print_result("完成指导", completion_result["completion_guidance"])

        print("\n此时你可以选择：")
        for i, next_name in enumerate(completion_result["next_intent_names"], 1):
            print(f"  {i}. {next_name}")

        print_result("建议操作", "\n".join(f"- {a}" for a in completion_result["next_actions"]))

    # 场景5：选择测试路径
    user_input_5 = "我想进行测试"
    print(f"\n用户: {user_input_5}")

    result_5 = manager.get_workflow_suggestion(user_input_5)
    if result_5["recognized"]:
        print_result("识别的意图", result_5["current_intent_name"])
        print_result("进入指导", result_5["entry_guidance"])

        manager.set_current_intent(result_5["current_intent"])

        # 显示已完成路径
        if result_5["path_str"]:
            print_result("已完成", result_5["path_str"])

    # 场景6：选择部署路径（替代测试）
    print_section("场景5：选择部署路径")

    user_input_6 = "准备上架部署"
    print(f"\n用户: {user_input_6}")

    result_6 = manager.get_workflow_suggestion(user_input_6)
    if result_6["recognized"]:
        print_result("识别的意图", result_6["current_intent_name"])
        print_result("进入指导", result_6["entry_guidance"])

        # 检查前置条件
        pre_intents = manager.get_pre_intents(result_6["current_intent"])
        if pre_intents:
            pre_names = [manager._intents[i].name for i in pre_intents if i in manager._intents]
            print_result("前置要求", "、".join(pre_names))

    # 场景7：最终运维
    print_section("场景6：运维阶段")

    user_input_7 = "应用已经上线，现在需要运维"
    print(f"\n用户: {user_input_7}")

    result_7 = manager.get_workflow_suggestion(user_input_7)
    if result_7["recognized"]:
        print_result("识别的意图", result_7["current_intent_name"])
        print_result("进入指导", result_7["entry_guidance"])

        if result_7["path_str"]:
            print_result("完整路径", result_7["path_str"])

        if not result_7["next_intent_names"]:
            print_result("流程状态", "这是最后一个阶段，完成后整个工作流结束")

    # 9. 交互式对话演示
    print_section("9. 交互式对话演示")

    conversations = [
        "我想学习新框架",
        "开始开发功能",
        "运行测试",
        "准备部署到生产环境",
        "系统上线后的运维工作"
    ]

    print("\n模拟用户对话流程：\n")
    for i, user_msg in enumerate(conversations, 1):
        print(f"[轮次 {i}] 用户: {user_msg}")

        result = manager.get_workflow_suggestion(user_msg)
        if result["recognized"]:
            next_str = result["next_str"] if result.get("next_str") else "（完成）"
            print(f"       助手: {result['entry_guidance']}")
            print(f"              后续: {next_str}")

            manager.set_current_intent(result["current_intent"])

    # 10. 显示最终状态
    print_section("10. 引擎状态")

    status = manager.get_status()
    print(f"\n总意图数: {status['total_intents']}")
    print(f"当前意图: {status['current_intent'] or '未设置'}")
    print(f"执行历史: {' -> '.join(status['execution_history']) if status['execution_history'] else '无'}")

    print_section("示例运行完成！")


if __name__ == "__main__":
    main()
