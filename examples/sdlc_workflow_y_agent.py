"""
SDLC 工作流 - 使用 YAgent 完成软件开发全生命周期

演示如何使用 YAgent 处理完整的软件开发生命周期：
学习 -> 开发 -> 测试 -> 上架 -> 运维
"""

import os
import asyncio
from typing import Dict, Any, List
from dotenv import load_dotenv

from intent_system import (
    YAgent,
    IntentDefinition,
    IntentMetadata,
    InputOutputSchema,
)


def print_section(title: str):
    """打印分节标题"""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


# ============================================================================
# SDLC 意图定义
# ============================================================================

async def study_intent(topic: str = "Python", duration: str = "1周") -> Dict[str, Any]:
    """
    学习意图 - 学习新技术、框架或概念

    Args:
        topic: 学习主题
        duration: 学习时长

    Returns:
        学习结果
    """
    return {
        "status": "completed",
        "result": f"已完成 {topic} 的学习（{duration}）",
        "knowledge_acquired": True,
        "skills_learned": [
            f"{topic} 基础概念",
            f"{topic} 核心特性",
            f"{topic} 最佳实践"
        ],
        "resources_used": [
            "官方文档",
            "在线教程",
            "实践项目"
        ],
        "next_step": "可以开始进入开发阶段"
    }


async def develop_intent(
    project: str = "新项目",
    features: int = 5,
    tech_stack: str = "Python"
) -> Dict[str, Any]:
    """
    开发意图 - 进行软件开发和编码工作

    Args:
        project: 项目名称
        features: 功能数量
        tech_stack: 技术栈

    Returns:
        开发结果
    """
    return {
        "status": "completed",
        "result": f"{project} 开发完成，实现 {features} 个功能",
        "code_written": True,
        "features_implemented": features,
        "tech_stack": tech_stack,
        "files_created": [
            "main.py",
            "config.py",
            "utils.py",
            "tests/"
        ],
        "code_quality": "良好",
        "documentation": "已完成",
        "next_step": "建议进行测试"
    }


async def test_intent(
    test_type: str = "全量测试",
    coverage_target: str = "85%"
) -> Dict[str, Any]:
    """
    测试意图 - 进行功能测试和质量保证

    Args:
        test_type: 测试类型
        coverage_target: 目标覆盖率

    Returns:
        测试结果
    """
    return {
        "status": "completed",
        "result": f"{test_type}完成，覆盖率: {coverage_target}",
        "bugs_found": 3,
        "bugs_fixed": 3,
        "test_cases": [
            "单元测试",
            "集成测试",
            "端到端测试"
        ],
        "coverage_achieved": "87%",
        "performance_test": "通过",
        "security_scan": "无漏洞",
        "next_step": "测试通过，可以准备部署"
    }


async def deploy_intent(
    environment: str = "production",
    version: str = "v1.0.0"
) -> Dict[str, Any]:
    """
    上架意图 - 将应用部署到生产环境

    Args:
        environment: 部署环境
        version: 版本号

    Returns:
        部署结果
    """
    return {
        "status": "completed",
        "result": f"版本 {version} 已成功部署到 {environment}",
        "deployment_id": f"deploy-{version.replace('.', '')}",
        "environment": environment,
        "deployment_time": "2025-01-15 10:30:00",
        "rollback_available": True,
        "health_check": "通过",
        "url": f"https://app.example.com ({environment})",
        "next_step": "进入运维监控阶段"
    }


async def maintain_intent(
    monitoring_type: str = "全面监控",
    alert_threshold: str = "正常"
) -> Dict[str, Any]:
    """
    运维意图 - 系统运维和持续监控

    Args:
        monitoring_type: 监控类型
        alert_threshold: 告警阈值

    Returns:
        运维结果
    """
    return {
        "status": "completed",
        "result": f"系统运行正常，{monitoring_type}已启用",
        "uptime": "99.9%",
        "active_users": 1250,
        "response_time": "45ms",
        "error_rate": "0.01%",
        "alerts": [],
        "metrics": {
            "cpu_usage": "45%",
            "memory_usage": "62%",
            "disk_usage": "38%",
            "network_io": "正常"
        },
        "backups": "最新备份已完成",
        "logs": "日志收集正常",
        "next_step": "持续监控，收集用户反馈"
    }


def create_sdlc_intents() -> List[IntentDefinition]:
    """
    创建 SDLC 工作流意图列表

    意图之间的依赖关系：
    study -> develop -> test -> deploy -> maintain

    Returns:
        意图定义列表
    """
    intents = []

    # 1. 学习意图
    study = IntentDefinition(
        metadata=IntentMetadata(
            id="sdlc_study",
            name="学习",
            description="学习新技术、框架或概念。包括阅读文档、实践练习、掌握基础等。",
            category="workflow",
            tags=["学习", "study", "培训", "onboarding"],
            priority=10,
            dependencies=[],
            timeout=300
        ),
        schema=InputOutputSchema(
            inputs={
                "topic": {
                    "type": "string",
                    "description": "要学习的主题或技术",
                    "required": False,
                    "default": "Python"
                },
                "duration": {
                    "type": "string",
                    "description": "学习时长",
                    "required": False,
                    "default": "1周"
                }
            },
            outputs={
                "status": {"type": "string"},
                "result": {"type": "string"},
                "knowledge_acquired": {"type": "boolean"}
            }
        ),
        executor=study_intent
    )
    intents.append(study)

    # 2. 开发意图（依赖于学习）
    develop = IntentDefinition(
        metadata=IntentMetadata(
            id="sdlc_develop",
            name="开发",
            description="进行软件开发和编码工作。包括需求分析、架构设计、编码实现等。",
            category="workflow",
            tags=["开发", "develop", "coding", "programming"],
            priority=20,
            dependencies=["sdlc_study"],
            timeout=600
        ),
        schema=InputOutputSchema(
            inputs={
                "project": {
                    "type": "string",
                    "description": "项目名称",
                    "required": False,
                    "default": "新项目"
                },
                "features": {
                    "type": "integer",
                    "description": "要实现的功能数量",
                    "required": False,
                    "default": 5
                },
                "tech_stack": {
                    "type": "string",
                    "description": "技术栈",
                    "required": False,
                    "default": "Python"
                }
            },
            outputs={
                "status": {"type": "string"},
                "result": {"type": "string"},
                "code_written": {"type": "boolean"},
                "features_implemented": {"type": "integer"}
            }
        ),
        executor=develop_intent
    )
    intents.append(develop)

    # 3. 测试意图（依赖于开发）
    test = IntentDefinition(
        metadata=IntentMetadata(
            id="sdlc_test",
            name="测试",
            description="进行功能测试和质量保证。包括单元测试、集成测试、性能测试等。",
            category="workflow",
            tags=["测试", "test", "qa", "quality"],
            priority=30,
            dependencies=["sdlc_develop"],
            timeout=300
        ),
        schema=InputOutputSchema(
            inputs={
                "test_type": {
                    "type": "string",
                    "description": "测试类型",
                    "required": False,
                    "default": "全量测试"
                },
                "coverage_target": {
                    "type": "string",
                    "description": "目标覆盖率",
                    "required": False,
                    "default": "85%"
                }
            },
            outputs={
                "status": {"type": "string"},
                "result": {"type": "string"},
                "bugs_found": {"type": "integer"},
                "bugs_fixed": {"type": "integer"}
            }
        ),
        executor=test_intent
    )
    intents.append(test)

    # 4. 上架意图（依赖于测试）
    deploy = IntentDefinition(
        metadata=IntentMetadata(
            id="sdlc_deploy",
            name="上架",
            description="将应用部署到生产环境。包括环境配置、数据迁移、健康检查等。",
            category="workflow",
            tags=["部署", "deploy", "发布", "release"],
            priority=40,
            dependencies=["sdlc_test"],
            timeout=180
        ),
        schema=InputOutputSchema(
            inputs={
                "environment": {
                    "type": "string",
                    "description": "部署环境",
                    "required": False,
                    "default": "production"
                },
                "version": {
                    "type": "string",
                    "description": "版本号",
                    "required": False,
                    "default": "v1.0.0"
                }
            },
            outputs={
                "status": {"type": "string"},
                "result": {"type": "string"},
                "deployment_id": {"type": "string"},
                "url": {"type": "string"}
            }
        ),
        executor=deploy_intent
    )
    intents.append(deploy)

    # 5. 运维意图（依赖于上架）
    maintain = IntentDefinition(
        metadata=IntentMetadata(
            id="sdlc_maintain",
            name="运维",
            description="系统运维和持续监控。包括性能监控、日志分析、故障处理等。",
            category="workflow",
            tags=["运维", "maintain", "monitor", "ops"],
            priority=50,
            dependencies=["sdlc_deploy"],
            timeout=120
        ),
        schema=InputOutputSchema(
            inputs={
                "monitoring_type": {
                    "type": "string",
                    "description": "监控类型",
                    "required": False,
                    "default": "全面监控"
                },
                "alert_threshold": {
                    "type": "string",
                    "description": "告警阈值",
                    "required": False,
                    "default": "正常"
                }
            },
            outputs={
                "status": {"type": "string"},
                "result": {"type": "string"},
                "uptime": {"type": "string"},
                "active_users": {"type": "integer"}
            }
        ),
        executor=maintain_intent
    )
    intents.append(maintain)

    return intents


# ============================================================================
# 演示场景
# ============================================================================

async def demo_single_intent(agent: YAgent):
    """演示：单个意图执行"""
    print_section("场景1: 单个意图执行 - 学习阶段")

    user_input = "我想学习 LangGraph 框架"

    print(f"\n用户输入: {user_input}")

    result = await agent.arun(user_input)

    # 检查是否有错误
    if not result.get("success", False) or "error" in result:
        print(f"\n[ERROR] 执行失败: {result.get('error', '未知错误')}")
        return

    print(f"\n检测结果:")
    print(f"  - 意图: {result.get('detected_intents', [])}")
    print(f"  - 置信度: {result.get('intent_confidence', 0):.2f}")
    print(f"  - 任务类型: {result.get('task_type', 'unknown')}")

    print(f"\n执行结果:")
    intent_results = result.get('intent_results', {})
    for intent_id, intent_result in intent_results.items():
        if isinstance(intent_result, dict):
            print(f"\n  [{intent_id}]")
            for key, value in intent_result.items():
                print(f"    {key}: {value}")


async def demo_sequential_workflow(agent: YAgent):
    """演示：顺序工作流"""
    print_section("场景2: 顺序工作流 - 学习到开发")

    user_input = "我学完 Python 了，现在开始开发用户管理系统"

    print(f"\n用户输入: {user_input}")

    result = await agent.arun(user_input)

    # 检查是否有错误
    if not result.get("success", False) or "error" in result:
        print(f"\n[ERROR] 执行失败: {result.get('error', '未知错误')}")
        return

    detected_intents = result.get('detected_intents', [])
    print(f"\n识别的意图: {detected_intents}")
    if detected_intents:
        print(f"执行顺序: {' -> '.join(detected_intents)}")

    print(f"\n执行结果:")
    intent_results = result.get('intent_results', {})
    for intent_id, intent_result in intent_results.items():
        if isinstance(intent_result, dict) and 'result' in intent_result:
            print(f"  [{intent_id}] {intent_result['result']}")


async def demo_multi_intent_orchestration(agent: YAgent):
    """演示：多意图编排"""
    print_section("场景3: 多意图编排 - 开发完成后测试并部署")

    user_input = "开发完成了，帮我测试一下，然后部署到生产环境"

    print(f"\n用户输入: {user_input}")

    result = await agent.arun(user_input)

    # 检查是否有错误
    if not result.get("success", False) or "error" in result:
        print(f"\n[ERROR] 执行失败: {result.get('error', '未知错误')}")
        return

    detected_intents = result.get('detected_intents', [])
    print(f"\n识别的意图: {detected_intents}")

    # 显示编排计划
    plan = result.get('orchestration_plan', {})
    if plan and 'execution_layers' in plan:
        print(f"\n执行计划:")
        print(f"  - 总层数: {plan.get('total_layers', 0)}")
        print(f"  - 执行顺序: {' -> '.join(plan.get('execution_order', []))}")

        print(f"\n执行层级:")
        for i, layer in enumerate(plan['execution_layers'], 1):
            print(f"  第 {i} 层: {layer}")

    print(f"\n执行结果:")
    intent_results = result.get('intent_results', {})
    for intent_id, intent_result in intent_results.items():
        if isinstance(intent_result, dict):
            print(f"\n  [{intent_id}]")
            if 'result' in intent_result:
                print(f"    结果: {intent_result['result']}")
            if 'deployment_id' in intent_result:
                print(f"    部署ID: {intent_result['deployment_id']}")


async def demo_full_sdlc_lifecycle(agent: YAgent):
    """演示：完整 SDLC 生命周期"""
    print_section("场景4: 完整 SDLC 生命周期")

    conversations = [
        "我想学习 FastAPI 框架",
        "学习完了，现在开始开发 REST API",
        "API 开发完成了，帮我做测试",
        "测试通过了，准备部署到生产环境",
        "系统已经上线，开始运维监控"
    ]

    session_id = "sdlc_demo_session"

    for i, user_input in enumerate(conversations, 1):
        print(f"\n[阶段 {i}] {user_input}")

        result = await agent.arun(user_input, session_id=session_id)

        # 检查是否有错误
        if not result.get("success", False) or "error" in result:
            print(f"  → [ERROR] 执行失败: {result.get('error', '未知错误')}")
            continue

        detected_intents = result.get('detected_intents', [])
        print(f"  → 识别意图: {detected_intents}")
        print(f"  → 置信度: {result.get('intent_confidence', 0):.2f}")

        # 显示关键结果
        intent_results = result.get('intent_results', {})
        for intent_id, intent_result in intent_results.items():
            if isinstance(intent_result, dict) and 'result' in intent_result:
                print(f"  → {intent_result['result']}")

        # 如果有反思结果，显示它
        if result.get('reflection_result'):
            reflection = result['reflection_result']
            print(f"  → 反思: 置信度 {reflection['confidence']:.2f}, {'继续' if reflection['should_continue'] else '完成'}")


async def demo_parallel_execution(agent: YAgent):
    """演示：并行执行（无依赖的意图）"""
    print_section("场景5: 模拟并行执行")

    # 这个场景展示意图系统如何处理可以并行的意图
    # 在 SDLC 中，某些阶段可能有并行任务

    user_input = "部署后同时进行性能监控和安全监控"

    print(f"\n用户输入: {user_input}")

    result = await agent.arun(user_input)

    # 检查是否有错误
    if not result.get("success", False) or "error" in result:
        print(f"\n[ERROR] 执行失败: {result.get('error', '未知错误')}")
        return

    detected_intents = result.get('detected_intents', [])
    print(f"\n识别的意图: {detected_intents}")

    # 显示执行摘要
    summary = result.get('execution_summary', {})
    print(f"\n执行摘要:")
    print(f"  - 总意图数: {summary.get('total_intents', 0)}")
    print(f"  - 成功: {summary.get('successful', 0)}")
    print(f"  - 失败: {summary.get('failed', 0)}")
    print(f"  - 总耗时: {summary.get('total_duration', 0):.2f}s")


async def demo_stream_execution(agent: YAgent):
    """演示：流式执行"""
    print_section("场景6: 流式执行 - 实时查看执行过程")

    user_input = "开发完成后进行测试"

    print(f"\n用户输入: {user_input}")
    print("\n开始流式执行...")

    count = 0
    try:
        async for event in agent.astream(user_input):
            count += 1
            for node_name, node_state in event.items():
                if isinstance(node_state, dict) and "intermediate_steps" in node_state:
                    steps = node_state.get("intermediate_steps", [])
                    if steps:
                        last_step = steps[-1]
                        print(f"  [步骤 {count}] {node_name} -> {last_step.get('step', 'unknown')}")
    except Exception as e:
        print(f"\n[ERROR] 流式执行错误: {str(e)}")

    print(f"\n流式执行完成，共 {count} 个事件")


async def demo_with_reflection(agent: YAgent):
    """演示：带反思的执行"""
    print_section("场景7: 反思机制 - 自动迭代优化")

    # 创建一个有最大迭代限制的 agent
    agent_with_reflection = YAgent(max_iterations=2)

    user_input = "帮我测试并分析结果"

    print(f"\n用户输入: {user_input}")
    print(f"最大迭代次数: 2")

    result = await agent_with_reflection.arun(user_input)

    # 检查是否有错误
    if not result.get("success", False) or "error" in result:
        print(f"\n[ERROR] 执行失败: {result.get('error', '未知错误')}")
        return

    print(f"\n执行完成:")
    print(f"  - 成功: {result['success']}")
    intermediate_steps = result.get('intermediate_steps', [])
    if intermediate_steps:
        print(f"  - 迭代次数: {intermediate_steps[-1].get('iteration', 0)}")

    if result.get('reflection_result'):
        reflection = result['reflection_result']
        print(f"\n反思结果:")
        print(f"  - 是否继续: {reflection['should_continue']}")
        print(f"  - 置信度: {reflection['confidence']:.2f}")
        print(f"  - 问题: {reflection['issues'] if reflection['issues'] else '无'}")
        print(f"  - 理由: {reflection['reasoning'][:100]}...")


# ============================================================================
# 主函数
# ============================================================================

async def main():
    """主函数"""
    print_section("SDLC 工作流 - 使用 YAgent")

    # 加载环境变量
    load_dotenv()

    # ========================================
    # 配置 YAgent
    # ========================================

    # 方式 1: 从环境变量或使用默认配置
    print("\n初始化 YAgent...")

    # 方式 2: 自定义配置（推荐用于测试或使用自定义端点）
    # 取消注释以下代码来使用自定义配置：

    """
    # 使用自定义 API Key 和 Base URL
    custom_api_key = os.getenv("OPENAI_API_KEY")
    custom_base_url = os.getenv("OPENAI_BASE_URL")  # 例如: "https://your-endpoint.com/v1"
    custom_model = os.getenv("MODEL_NAME")  # 例如: "gpt-4o"

    agent = YAgent(
        api_key=custom_api_key,
        base_url=custom_base_url,
        model_name=custom_model
    )
    """

    # 默认创建（使用环境变量）
    agent = YAgent(
        api_key="sk-1b7e48556f154e9ab4d40df712e0bec6",
        base_url="https://api.deepseek.com",
        model_name="deepseek-chat"
    )

    # 注册 SDLC 意图
    print("\n注册 SDLC 工作流意图...")
    sdlc_intents = create_sdlc_intents()

    for intent in sdlc_intents:
        agent.register_intent(intent)
        print(f"  [OK] {intent.metadata.name} ({intent.metadata.id})")

    print(f"\n总共注册了 {len(sdlc_intents)} 个 SDLC 意图")

    # ========================================
    # 配置说明
    # ========================================

    print_section("YAgent 配置说明")

    print("""
配置方式 1: 使用环境变量（推荐生产环境）
-------------------------------------------------
在 .env 文件中配置：
  OPENAI_API_KEY=sk-your-api-key
  OPENAI_BASE_URL=https://api.openai.com/v1
  MODEL_NAME=gpt-4o

然后创建 Agent：
  agent = YAgent()


配置方式 2: 使用初始化参数（推荐测试/自定义端点）
--------------------------------------------------
agent = YAgent(
    api_key="sk-your-api-key",
    base_url="https://your-endpoint.com/v1",
    model_name="your-model-name"
)


配置方式 3: 混合配置
--------------------------------------------------
agent = YAgent(
    api_key="sk-your-api-key"  # 自定义 key
    # base_url 使用环境变量
    # model_name 使用环境变量
)


国内 LLM 服务示例：
--------------------------------------------------
agent = YAgent(
    api_key="your-chinese-llm-key",
    base_url="https://your-chinese-llm.com/v1",
    model_name="your-model"
)
    """)

    # 检查 API Key
    has_api_key = bool(os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"))

    if not has_api_key:
        print("\n[WARNING] API Key not set!")
        print("Please set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env file")
        print("\nWill run with limited functionality...\n")

    try:
        # 运行演示场景
        print_section("运行演示场景")
        await demo_single_intent(agent)
        await demo_sequential_workflow(agent)
        await demo_multi_intent_orchestration(agent)
        await demo_full_sdlc_lifecycle(agent)
        await demo_parallel_execution(agent)
        await demo_stream_execution(agent)
        await demo_with_reflection(agent)

        # 总结
        print_section("演示完成")
        print("\nSDLC 工作流意图系统功能:")
        print("  1. [OK] 单个意图识别和执行")
        print("  2. [OK] 顺序工作流（带依赖）")
        print("  3. [OK] 多意图编排和 parallel执行")
        print("  4. [OK] 完整 SDLC 生命周期")
        print("  5. [OK] 反思机制和自动优化")
        print("  6. [OK] 流式执行和实时监控")
        print("  7. [OK] 会话持久化")

        if not has_api_key:
            print("\n[TIP] 设置 LLM API Key 可以使用更强大的意图解析能力")

    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
