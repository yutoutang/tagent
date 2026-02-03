"""
工作流意图管理系统 - 集成LLM Agent的真实示例

展示如何使用 intent_system 框架的完整功能：
1. 使用 IntentParser + LLM 识别意图
2. 使用 IntentOrchestrator 编排执行计划
3. 使用 IntentExecutor 执行意图
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入工作流意图管理模块
from intent_system.workflow import WorkflowIntentManager, load_workflow_from_json
from intent_system.workflow.workflow_intent import WorkflowIntentDefinition

# 导入标准意图系统组件
from intent_system.core import IntentRegistry
from intent_system.core.intent_definition import IntentDefinition, IntentMetadata, InputOutputSchema
from intent_system.core.intent_parser import IntentParser
from intent_system.orchestration import IntentOrchestrator
from intent_system.execution import IntentExecutor

# 导入LLM创建函数
from dynamic_agent_framework import create_llm

# 导入环境变量加载
from dotenv import load_dotenv


def print_section(title: str):
    """打印分节标题"""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def print_result(label: str, content: str):
    """打印结果"""
    print(f"\n{label}:")
    print("-" * 50)
    print(content)


# 定义实际的工作流执行函数
def execute_study(**kwargs):
    """执行学习阶段"""
    topic = kwargs.get('topic', 'Python')
    return {
        "status": "completed",
        "result": f"已完成 {topic} 的学习",
        "knowledge_acquired": True
    }


def execute_develop(**kwargs):
    """执行开发阶段"""
    project = kwargs.get('project', '新项目')
    return {
        "status": "completed",
        "result": f"{project} 开发完成",
        "code_written": True,
        "features_implemented": 5
    }


def execute_test(**kwargs):
    """执行测试阶段"""
    test_coverage = kwargs.get('test_coverage', '80%')
    return {
        "status": "completed",
        "result": f"测试完成，覆盖率: {test_coverage}",
        "bugs_found": 2,
        "bugs_fixed": 2
    }


def execute_deploy(**kwargs):
    """执行部署阶段"""
    environment = kwargs.get('environment', 'production')
    return {
        "status": "completed",
        "result": f"已部署到 {environment}",
        "deployment_id": "deploy-12345"
    }


def execute_maintain(**kwargs):
    """执行运维阶段"""
    return {
        "status": "completed",
        "result": "系统运行正常",
        "uptime": "99.9%"
    }


def create_workflow_intent_definitions():
    """
    创建带有实际执行器的工作流意图定义

    Returns:
        工作流意图列表
    """
    intents = []

    # 学习意图
    study_intent = WorkflowIntentDefinition(
        id="study",
        name="学习",
        description="学习新技术、框架或概念",
        category="workflow",
        pre_intents=[],
        post_intents=["develop"],
        guidance={
            "entry": "欢迎开始学习！建议先阅读官方文档，了解基础概念。",
            "completion": "学习完成！下一步可以进入开发阶段。",
            "next_actions": ["开始开发项目", "查看更多学习资源"]
        }
    )
    study_intent.executor = execute_study
    intents.append(study_intent)

    # 开发意图
    develop_intent = WorkflowIntentDefinition(
        id="develop",
        name="开发",
        description="进行软件开发和编码工作",
        category="workflow",
        pre_intents=["study"],
        post_intents=["test", "deploy"],
        guidance={
            "entry": "开始开发阶段！确保代码质量和规范。",
            "completion": "开发完成！接下来需要进行测试或准备部署。",
            "next_actions": ["运行测试", "准备部署", "代码审查"]
        }
    )
    develop_intent.executor = execute_develop
    intents.append(develop_intent)

    # 测试意图
    test_intent = WorkflowIntentDefinition(
        id="test",
        name="测试",
        description="进行功能测试和质量保证",
        category="workflow",
        pre_intents=["develop"],
        post_intents=["deploy"],
        guidance={
            "entry": "进入测试阶段！建议编写单元测试和集成测试。",
            "completion": "测试完成！如果测试通过，可以准备部署。",
            "next_actions": ["准备部署", "修复问题", "生成报告"]
        }
    )
    test_intent.executor = execute_test
    intents.append(test_intent)

    # 部署意图
    deploy_intent = WorkflowIntentDefinition(
        id="deploy",
        name="上架",
        description="将应用部署到生产环境",
        category="workflow",
        pre_intents=["develop", "test"],
        post_intents=["maintain"],
        guidance={
            "entry": "准备部署！确保环境配置正确，备份重要数据。",
            "completion": "部署成功！应用已上线，后续进入运维阶段。",
            "next_actions": ["开始运维监控", "查看部署日志"]
        }
    )
    deploy_intent.executor = execute_deploy
    intents.append(deploy_intent)

    # 运维意图
    maintain_intent = WorkflowIntentDefinition(
        id="maintain",
        name="运维",
        description="系统运维和持续监控",
        category="workflow",
        pre_intents=["deploy"],
        post_intents=[],
        guidance={
            "entry": "进入运维阶段！建立监控告警机制，及时处理问题。",
            "completion": "运维任务完成。建议定期检查系统状态。",
            "next_actions": ["收集用户反馈", "规划新版本", "优化性能"]
        }
    )
    maintain_intent.executor = execute_maintain
    intents.append(maintain_intent)

    return intents


async def main():
    """主函数"""
    print_section("工作流意图系统 - 集成LLM Agent示例")

    # 加载环境变量
    load_dotenv()

    # 检查 API key
    has_api_key = bool(os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"))

    if not has_api_key:
        print("\n⚠️  未检测到 LLM API Key")
        print("\n请设置以下环境变量之一：")
        print("  - OPENAI_API_KEY (用于 GPT)")
        print("  - ANTHROPIC_API_KEY (用于 Claude)")
        print("\n或者在项目根目录创建 .env 文件：")
        print("  OPENAI_API_KEY=your-key-here")
        print("\n将使用模拟模式运行...\n")

    # 1. 初始化核心组件
    print("1. 初始化核心组件...")

    registry = IntentRegistry()

    if has_api_key:
        try:
            llm = create_llm()
            print(f"   ✓ LLM 已初始化: {type(llm).__name__}")
        except Exception as e:
            print(f"   ⚠️  LLM 初始化失败: {e}")
            print("   将使用关键词匹配模式")
            llm = None
    else:
        llm = None
        print("   ℹ️  使用关键词匹配模式（无需 LLM）")

    # 2. 创建并注册工作流意图
    print("\n2. 创建并注册工作流意图...")

    workflow_intents = create_workflow_intent_definitions()

    for intent in workflow_intents:
        # 转换为标准意图定义并注册到注册表
        standard_intent = intent.to_intent_definition()
        # 覆盖执行器为我们定义的实际函数
        standard_intent.executor = intent.executor
        registry.register(standard_intent)
        print(f"   ✓ 已注册: {intent.name} ({intent.id})")

    print(f"\n   注册表中共有 {registry.count()} 个意图")

    # 3. 初始化 Agent 组件
    print("\n3. 初始化 Agent 组件...")

    if llm:
        parser = IntentParser(llm, registry)
        print("   ✓ IntentParser - 使用 LLM 解析意图")
    else:
        parser = None
        print("   ℹ️  IntentParser - 使用关键词匹配（无 LLM）")

    orchestrator = IntentOrchestrator(registry)
    executor = IntentExecutor(registry)

    print("   ✓ IntentOrchestrator - 编排执行计划")
    print("   ✓ IntentExecutor - 执行意图")

    # 辅助函数：解析意图
    def parse_intent(user_input: str):
        """解析用户输入"""
        if parser:
            return parser.parse(user_input)
        else:
            # 降级：关键词匹配
            from intent_system.core.intent_parser import IntentParseResult
            user_lower = user_input.lower()

            # 简单的关键词匹配
            intent_map = {
                "study": ["学习", "study", "learn"],
                "develop": ["开发", "develop", "coding", "编程"],
                "test": ["测试", "test", "testing"],
                "deploy": ["部署", "deploy", "上架", "发布"],
                "maintain": ["运维", "maintain", "维护", "monitor"]
            }

            best_intent = ""
            best_score = 0
            for intent_id, keywords in intent_map.items():
                score = sum(1 for kw in keywords if kw in user_lower)
                if score > best_score:
                    best_score = score
                    best_intent = intent_id

            if not best_intent:
                best_intent = "study"  # 默认

            return IntentParseResult(
                primary_intent=best_intent,
                confidence=0.8 if best_score > 0 else 0.3,
                reasoning="关键词匹配识别",
                parameters={},
                sub_intents=[]
            )

    # 4. 场景演示：完整工作流
    print_section("4. 场景演示：完整工作流")

    # 场景1：用户想开始学习
    print("\n>>> 用户: 我想学习Python开发")

    # 解析意图
    parse_result = parse_intent("我想学习Python开发")

    print_result("解析结果",
        f"主要意图: {parse_result.primary_intent}\n"
        f"置信度: {parse_result.confidence:.2f}\n"
        f"解析理由: {parse_result.reasoning}"
    )

    # 编排执行计划
    plan = orchestrator.orchestrate(parse_result)

    print_result("编排计划",
        f"执行层数: {len(plan.execution_layers)}\n"
        f"执行顺序: {' -> '.join(plan.execution_order)}\n"
        f"数据映射: {len(plan.data_mappings)} 个意图需要数据映射"
    )

    # 执行计划
    print("\n执行意图...")
    results = await executor.execute_plan_async(plan, "session_001")

    print_result("执行结果", "\n".join(
        f"  {intent_id}: {result.get('result', result)}"
        for intent_id, result in results.items()
    ))

    # 场景2：继续开发流程
    print_section("场景2：继续开发流程")

    print("\n>>> 用户: 学习完成了，现在开始开发功能")

    parse_result = parse_intent("学习完成了，现在开始开发功能")

    print_result("解析结果",
        f"主要意图: {parse_result.primary_intent}\n"
        f"置信度: {parse_result.confidence:.2f}"
    )

    plan = orchestrator.orchestrate(parse_result)

    print_result("编排计划",
        f"执行顺序: {' -> '.join(plan.execution_order)}"
    )

    results = await executor.execute_plan_async(plan, "session_002")

    print_result("执行结果", "\n".join(
        f"  {intent_id}: {result.get('result', result)}"
        for intent_id, result in results.items()
    ))

    # 场景3：多意图编排
    print_section("场景3：多意图编排 - 开发后测试并部署")

    print("\n>>> 用户: 我开发完了，帮我测试然后部署到生产环境")

    # 模拟多意图识别
    user_input = "我开发完了，帮我测试然后部署到生产环境"

    if parser:
        parse_result = parser.parse(user_input)
    else:
        # 手动构造多意图结果
        from intent_system.core.intent_parser import IntentParseResult
        parse_result = IntentParseResult(
            primary_intent="test",
            confidence=0.85,
            reasoning="识别到多个连续操作",
            parameters={},
            sub_intents=[
                {"id": "deploy", "parameters": {"environment": "production"}}
            ],
            dependencies=["develop"]
        )

    print_result("解析结果",
        f"主要意图: {parse_result.primary_intent}\n"
        f"子意图: {[s['id'] for s in parse_result.sub_intents]}\n"
        f"置信度: {parse_result.confidence:.2f}"
    )

    plan = orchestrator.orchestrate(parse_result)

    print_result("编排计划",
        f"执行层数: {len(plan.execution_layers)}\n"
        f"执行顺序: {' -> '.join(plan.execution_order)}"
    )

    # 显示执行层（可并行执行）
    for i, layer in enumerate(plan.execution_layers, 1):
        print(f"\n  第 {i} 层: {layer}")

    results = await executor.execute_plan_async(plan, "session_003")

    print_result("执行结果", "\n".join(
        f"  {intent_id}: {result.get('result', result)}"
        for intent_id, result in results.items()
    ))

    # 4. 显示执行摘要
    print_section("4. 执行摘要")

    summary = executor.get_execution_summary()
    print(f"\n总执行意图数: {summary['total_intents']}")
    print(f"成功: {summary['successful']}")
    print(f"失败: {summary['failed']}")
    print(f"总耗时: {summary['total_duration']:.2f}s")

    # 5. 交互式对话演示
    print_section("5. 交互式对话演示")

    conversations = [
        "我想学习人工智能",
        "学习完了，开始开发AI应用",
        "开发完成了，帮我测试一下",
        "测试通过了，准备部署",
        "系统上线后需要运维"
    ]

    print("\n模拟用户对话流程：\n")

    for i, user_msg in enumerate(conversations, 1):
        print(f"[轮次 {i}] 用户: {user_msg}")

        try:
            parse_result = parse_intent(user_msg)
            plan = orchestrator.orchestrate(parse_result)

            parser_type = "LLM" if parser else "关键词匹配"
            print(f"       Agent ({parser_type}): 识别意图 '{parse_result.primary_intent}' (置信度: {parse_result.confidence:.2f})")

            # 执行并显示结果
            results = await executor.execute_plan_async(plan, f"session_{i:03d}")

            for intent_id, result in results.items():
                if isinstance(result, dict) and 'result' in result:
                    print(f"              → {result['result']}")

        except Exception as e:
            print(f"       Agent: 执行出错 - {e}")

        print()

    print_section("示例运行完成！")

    if not has_api_key:
        print("\n💡 提示：设置 LLM API Key 可以使用更强大的意图解析能力")
        print("   参考 .env.example 文件配置")


if __name__ == "__main__":
    asyncio.run(main())
