"""
工作流意图引擎使用示例

演示如何使用工作流意图引擎进行意图识别、图谱导航和流程指导
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from examples.workflow_intent_engine import WorkflowIntentEngine


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
    print_section("工作流意图引擎示例")

    # 1. 初始化引擎并加载意图定义
    print("\n1. 初始化引擎并加载意图定义...")

    engine = WorkflowIntentEngine()
    json_path = Path(__file__).parent / "workflow_intents.json"

    count = engine.load_from_json(str(json_path))
    print(f"   已加载 {count} 个意图")

    # 2. 查看所有意图
    print_section("2. 所有可用意图")

    intents = engine.list_all_intents()
    for intent in intents:
        print(f"\n   [{intent['id']}] {intent['name']}")
        print(f"       {intent['description']}")

    # 3. 可视化意图图谱
    print_section("3. 意图谱可视化")

    print(engine.visualize_graph())

    # 4. 场景演示：从学习开始
    print_section("4. 场景演示：完整工作流")

    # 场景1：用户想开始学习
    user_input_1 = "我想学习Python开发"
    print(f"\n用户: {user_input_1}")

    result_1 = engine.get_workflow_suggestion(user_input_1)
    if result_1["recognized"]:
        print_result("识别的意图", result_1["current_intent_name"])
        print_result("进入指导", result_1["entry_guidance"])

        if result_1["path_str"]:
            print_result("完整路径", result_1["path_str"])

        if result_1["next_str"]:
            print_result("后续流程", result_1["next_str"])

        # 设置当前意图
        engine.set_current_intent(result_1["current_intent"])

    # 场景2：学习完成，询问下一步
    print_section("场景2：学习完成")

    current = engine.get_status()["current_intent"]
    if current:
        completion_result = engine.process_completion(current)
        print_result("完成指导", completion_result["completion_guidance"])

        if completion_result["next_intent_names"]:
            print_result("后续选项", " 或 ".join(completion_result["next_intent_names"]))

        print_result("建议操作", "\n".join(f"- {a}" for a in completion_result["next_actions"]))

    # 场景3：用户开始开发
    user_input_3 = "我准备开始开发了"
    print(f"\n用户: {user_input_3}")

    result_3 = engine.get_workflow_suggestion(user_input_3)
    if result_3["recognized"]:
        print_result("识别的意图", result_3["current_intent_name"])
        print_result("进入指导", result_3["entry_guidance"])

        if result_3["next_str"]:
            print_result("后续流程", result_3["next_str"])

        engine.set_current_intent(result_3["current_intent"])

    # 场景4：开发完成后的多种选择
    print_section("场景4：开发完成 - 面临选择")

    current = engine.get_status()["current_intent"]
    if current:
        completion_result = engine.process_completion(current)
        print_result("完成指导", completion_result["completion_guidance"])

        print("\n此时你可以选择：")
        for i, next_name in enumerate(completion_result["next_intent_names"], 1):
            print(f"  {i}. {next_name}")

        print_result("建议操作", "\n".join(f"- {a}" for a in completion_result["next_actions"]))

    # 场景5：用户选择测试
    user_input_5 = "我想进行测试"
    print(f"\n用户: {user_input_5}")

    result_5 = engine.get_workflow_suggestion(user_input_5)
    if result_5["recognized"]:
        print_result("识别的意图", result_5["current_intent_name"])
        print_result("进入指导", result_5["entry_guidance"])

        engine.set_current_intent(result_5["current_intent"])

        # 显示路径
        if result_5["path_str"]:
            print_result("已完成", result_5["path_str"])

    # 场景6：用户想直接部署
    print_section("场景5：直接准备部署")

    user_input_6 = "准备上架部署"
    print(f"\n用户: {user_input_6}")

    result_6 = engine.get_workflow_suggestion(user_input_6)
    if result_6["recognized"]:
        print_result("识别的意图", result_6["current_intent_name"])
        print_result("进入指导", result_6["entry_guidance"])

        # 检查前置条件
        pre_intents = engine.get_pre_intents(result_6["current_intent"])
        if pre_intents:
            pre_names = [engine._intents[i].name for i in pre_intents if i in engine._intents]
            print_result("前置要求", "、".join(pre_names))

    # 场景7：最终运维
    print_section("场景6：运维阶段")

    user_input_7 = "应用已经上线，现在需要运维"
    print(f"\n用户: {user_input_7}")

    result_7 = engine.get_workflow_suggestion(user_input_7)
    if result_7["recognized"]:
        print_result("识别的意图", result_7["current_intent_name"])
        print_result("进入指导", result_7["entry_guidance"])

        if result_7["path_str"]:
            print_result("完整路径", result_7["path_str"])

        if not result_7["next_intent_names"]:
            print_result("流程状态", "这是最后一个阶段，完成后整个工作流结束")

    # 5. 交互式对话演示
    print_section("5. 交互式对话演示")

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

        result = engine.get_workflow_suggestion(user_msg)
        if result["recognized"]:
            # 简化的回复格式
            next_str = result["next_str"] if result.get("next_str") else "（完成）"
            print(f"       助手: {result['entry_guidance']} ")
            print(f"              后续: {next_str}")

            engine.set_current_intent(result["current_intent"])

    # 6. 显示引擎状态
    print_section("6. 引擎状态")

    status = engine.get_status()
    print(f"\n总意图数: {status['total_intents']}")
    print(f"当前意图: {status['current_intent'] or '未设置'}")
    print(f"执行历史: {' -> '.join(status['execution_history']) if status['execution_history'] else '无'}")

    print_section("示例运行完成！")


if __name__ == "__main__":
    main()
