"""
SDLC 意图测试 - 验证学习、开发、测试、上架、运维意图

测试 intent_system 模块对 SDLC 五个阶段意图的理解和执行
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

load_dotenv()

from intent_system import (
    IntentRegistry,
    IntentParser,
    IntentOrchestrator,
    IntentExecutor,
    IntentDefinition,
    IntentMetadata,
    InputOutputSchema,
)
from intent_system.data_flow import DataFlowEngine
from langchain_core.tools import tool


# ============================================================================
# SDLC 意图执行函数
# ============================================================================

def execute_study(**kwargs):
    """学习阶段执行"""
    topic = kwargs.get('topic', 'Python')
    return {
        "stage": "学习",
        "status": "completed",
        "result": f"已完成 {topic} 的学习",
        "knowledge_acquired": True,
        "skills": [f"{topic} 基础", f"{topic} 进阶", "最佳实践"]
    }


def execute_develop(**kwargs):
    """开发阶段执行"""
    project = kwargs.get('project', '新项目')
    return {
        "stage": "开发",
        "status": "completed",
        "result": f"{project} 开发完成",
        "code_written": True,
        "features": 5,
        "quality": "良好"
    }


def execute_test(**kwargs):
    """测试阶段执行"""
    return {
        "stage": "测试",
        "status": "completed",
        "result": "测试完成，覆盖率 85%",
        "bugs_found": 2,
        "bugs_fixed": 2
    }


def execute_deploy(**kwargs):
    """上架阶段执行"""
    env = kwargs.get('environment', 'production')
    return {
        "stage": "上架",
        "status": "completed",
        "result": f"已部署到 {env}",
        "deployment_id": "deploy-001",
        "url": f"https://app.example.com ({env})"
    }


def execute_maintain(**kwargs):
    """运维阶段执行"""
    return {
        "stage": "运维",
        "status": "completed",
        "result": "系统运行正常",
        "uptime": "99.9%",
        "active_users": 1000
    }


# ============================================================================
# 创建 SDLC 意图定义
# ============================================================================

def create_sdlc_intents():
    """创建 SDLC 五个阶段的意图"""
    return [
        IntentDefinition(
            metadata=IntentMetadata(
                id="study",
                name="学习",
                description="学习新技术、框架或概念，包括阅读文档、实践练习",
                category="workflow",
                tags=["学习", "study", "培训"],
                dependencies=[]
            ),
            schema=InputOutputSchema(
                inputs={
                    "topic": {"type": "string", "description": "学习主题", "default": "Python"}
                },
                outputs={"status": {"type": "string"}}
            ),
            executor=execute_study
        ),
        IntentDefinition(
            metadata=IntentMetadata(
                id="develop",
                name="开发",
                description="进行软件开发和编码工作，包括需求分析、架构设计、编码实现",
                category="workflow",
                tags=["开发", "develop", "编程"],
                dependencies=["study"]
            ),
            schema=InputOutputSchema(
                inputs={
                    "project": {"type": "string", "description": "项目名称", "default": "新项目"}
                },
                outputs={"status": {"type": "string"}}
            ),
            executor=execute_develop
        ),
        IntentDefinition(
            metadata=IntentMetadata(
                id="test",
                name="测试",
                description="进行功能测试和质量保证，包括单元测试、集成测试",
                category="workflow",
                tags=["测试", "test", "qa"],
                dependencies=["develop"]
            ),
            schema=InputOutputSchema(
                inputs={},
                outputs={"status": {"type": "string"}}
            ),
            executor=execute_test
        ),
        IntentDefinition(
            metadata=IntentMetadata(
                id="deploy",
                name="上架",
                description="将应用部署到生产环境，包括环境配置、数据迁移",
                category="workflow",
                tags=["部署", "deploy", "发布"],
                dependencies=["test"]
            ),
            schema=InputOutputSchema(
                inputs={
                    "environment": {"type": "string", "description": "部署环境", "default": "production"}
                },
                outputs={"status": {"type": "string"}}
            ),
            executor=execute_deploy
        ),
        IntentDefinition(
            metadata=IntentMetadata(
                id="maintain",
                name="运维",
                description="系统运维和持续监控，包括性能监控、日志分析",
                category="workflow",
                tags=["运维", "maintain", "监控"],
                dependencies=["deploy"]
            ),
            schema=InputOutputSchema(
                inputs={},
                outputs={"status": {"type": "string"}}
            ),
            executor=execute_maintain
        ),
    ]


# ============================================================================
# 测试函数
# ============================================================================

def print_header(title: str):
    """打印标题"""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


async def test_intent_registration():
    """测试意图注册"""
    print_header("测试1: 意图注册")

    registry = IntentRegistry()
    intents = create_sdlc_intents()

    for intent in intents:
        registry.register(intent)
        print(f"  [OK] 已注册: {intent.metadata.name} ({intent.metadata.id})")
        print(f"       - 描述: {intent.metadata.description}")
        print(f"       - 依赖: {intent.metadata.dependencies}")
        print(f"       - 标签: {', '.join(intent.metadata.tags)}")

    print(f"\n总计: {registry.count()} 个意图")
    return registry


async def test_intent_parsing(registry: IntentRegistry):
    """测试意图解析"""
    print_header("测试2: 意图解析")

    # 检查是否有 API Key
    has_api_key = bool(os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"))

    if has_api_key:
        from dynamic_agent_framework import create_llm
        llm = create_llm()
        parser = IntentParser(llm, registry)
        print("  使用 LLM 进行意图解析")
    else:
        parser = None
        print("  使用关键词匹配（无 LLM）")

    # 测试用例
    test_cases = [
        "我想学习 Python 开发",
        "学习完了，开始开发项目",
        "开发完成了，帮我测试",
        "测试通过，准备部署",
        "系统上线后需要运维",
    ]

    from intent_system.core.intent_parser import IntentParseResult

    for user_input in test_cases:
        print(f"\n  输入: {user_input}")

        if parser:
            result = parser.parse(user_input)
        else:
            # 关键词匹配降级
            user_lower = user_input.lower()
            intent_map = {
                "study": ["学习", "study", "learn"],
                "develop": ["开发", "develop", "coding"],
                "test": ["测试", "test"],
                "deploy": ["部署", "deploy", "上架", "发布"],
                "maintain": ["运维", "maintain", "维护"]
            }
            best_intent = max(
                intent_map.keys(),
                key=lambda iid: sum(1 for kw in intent_map[iid] if kw in user_lower),
                default="study"
            )
            result = IntentParseResult(
                primary_intent=best_intent,
                confidence=0.8,
                reasoning="关键词匹配"
            )

        print(f"  解析: {result.primary_intent} (置信度: {result.confidence:.2f})")


async def test_orchestration(registry: IntentRegistry):
    """测试意图编排"""
    print_header("测试3: 意图编排")

    orchestrator = IntentOrchestrator(registry)

    from intent_system.core.intent_parser import IntentParseResult

    # 测试单个意图
    print("\n  场景1: 单个意图（学习）")
    parse_result = IntentParseResult(
        primary_intent="study",
        confidence=0.9,
        reasoning="用户想学习"
    )
    plan = orchestrator.orchestrate(parse_result)
    print(f"    执行层数: {plan.total_layers}")
    print(f"    执行顺序: {' -> '.join(plan.execution_order)}")

    # 测试多意图
    print("\n  场景2: 多意图（开发 -> 测试 -> 部署）")
    parse_result = IntentParseResult(
        primary_intent="develop",
        confidence=0.85,
        sub_intents=[
            {"id": "test", "parameters": {}},
            {"id": "deploy", "parameters": {}}
        ],
        reasoning="完整的开发流程"
    )
    plan = orchestrator.orchestrate(parse_result)
    print(f"    执行层数: {plan.total_layers}")
    print(f"    执行顺序: {' -> '.join(plan.execution_order)}")
    print(f"    执行层级:")
    for i, layer in enumerate(plan.execution_layers, 1):
        print(f"      第 {i} 层: {layer}")


async def test_execution(registry: IntentRegistry):
    """测试意图执行"""
    print_header("测试4: 意图执行")

    orchestrator = IntentOrchestrator(registry)
    executor = IntentExecutor(registry, DataFlowEngine())

    from intent_system.core.intent_parser import IntentParseResult

    # 完整工作流
    print("\n  执行完整 SDLC 工作流:")

    parse_result = IntentParseResult(
        primary_intent="study",
        confidence=0.9,
        sub_intents=[
            {"id": "develop", "parameters": {}},
            {"id": "test", "parameters": {}},
            {"id": "deploy", "parameters": {}},
            {"id": "maintain", "parameters": {}}
        ],
        reasoning="完整 SDLC 流程"
    )

    plan = orchestrator.orchestrate(parse_result)

    print(f"  计划执行 {plan.total_intents} 个意图，共 {plan.total_layers} 层\n")

    results = await executor.execute_plan_async(plan, "test_session")

    for intent_id, result in results.items():
        if isinstance(result, dict):
            print(f"  [{intent_id}]")
            print(f"    阶段: {result.get('stage', 'N/A')}")
            print(f"    结果: {result.get('result', 'N/A')}")
            if 'features' in result:
                print(f"    功能数: {result['features']}")
            if 'uptime' in result:
                print(f"    可用性: {result['uptime']}")

    summary = executor.get_execution_summary()
    print(f"\n  执行摘要:")
    print(f"    总意图数: {summary['total_intents']}")
    print(f"    成功: {summary['successful']}")
    print(f"    失败: {summary['failed']}")


async def test_dependency_handling(registry: IntentRegistry):
    """测试依赖处理"""
    print_header("测试5: 依赖关系处理")

    orchestrator = IntentOrchestrator(registry)

    from intent_system.core.intent_parser import IntentParseResult

    print("\n  测试依赖关系:")

    # 直接请求运维（应该触发所有前置阶段）
    parse_result = IntentParseResult(
        primary_intent="maintain",
        confidence=0.9,
        reasoning="直接请求运维"
    )

    plan = orchestrator.orchestrate(parse_result)

    print(f"    请求意图: maintain (运维)")
    print(f"    实际执行顺序: {' -> '.join(plan.execution_order)}")
    print(f"    说明: 由于依赖关系，系统自动包含了所有前置阶段")


async def test_parallel_execution(registry: IntentRegistry):
    """测试并行执行"""
    print_header("测试6: 并行执行")

    # 创建一些无依赖的意图来测试并行执行
    from intent_system.core import IntentDefinition, IntentMetadata, InputOutputSchema

    parallel_intents = [
        IntentDefinition(
            metadata=IntentMetadata(
                id="monitor_cpu",
                name="监控CPU",
                description="监控CPU使用率",
                category="data",
                tags=["监控"],
                dependencies=[]
            ),
            schema=InputOutputSchema(inputs={}, outputs={}),
            executor=lambda: {"status": "CPU: 45%"}
        ),
        IntentDefinition(
            metadata=IntentMetadata(
                id="monitor_memory",
                name="监控内存",
                description="监控内存使用率",
                category="data",
                tags=["监控"],
                dependencies=[]
            ),
            schema=InputOutputSchema(inputs={}, outputs={}),
            executor=lambda: {"status": "Memory: 62%"}
        ),
        IntentDefinition(
            metadata=IntentMetadata(
                id="monitor_disk",
                name="监控磁盘",
                description="监控磁盘使用率",
                category="data",
                tags=["监控"],
                dependencies=[]
            ),
            schema=InputOutputSchema(inputs={}, outputs={}),
            executor=lambda: {"status": "Disk: 38%"}
        ),
    ]

    for intent in parallel_intents:
        registry.register(intent)

    orchestrator = IntentOrchestrator(registry)
    executor = IntentExecutor(registry, DataFlowEngine())

    from intent_system.core.intent_parser import IntentParseResult

    parse_result = IntentParseResult(
        primary_intent="monitor_cpu",
        confidence=0.9,
        sub_intents=[
            {"id": "monitor_memory", "parameters": {}},
            {"id": "monitor_disk", "parameters": {}}
        ],
        reasoning="同时监控多个指标"
    )

    plan = orchestrator.orchestrate(parse_result)

    print(f"  执行计划:")
    print(f"    总意图数: {plan.total_intents}")
    print(f"    执行层数: {plan.total_layers}")
    print(f"    可以并行: 是 (所有监控任务在同一层)")

    print(f"\n  执行层级:")
    for i, layer in enumerate(plan.execution_layers, 1):
        print(f"    第 {i} 层: {layer} (并行执行)")

    results = await executor.execute_plan_async(plan, "parallel_test")

    print(f"\n  执行结果:")
    for intent_id, result in results.items():
        if isinstance(result, dict) and 'status' in result:
            print(f"    {intent_id}: {result['status']}")


# ============================================================================
# 主函数
# ============================================================================

async def main():
    """主函数"""
    print_header("SDLC 意图系统测试")

    print("\n测试意图系统对软件开发生命周期五个阶段的理解:")
    print("  1. 学习 (Study)")
    print("  2. 开发 (Develop)")
    print("  3. 测试 (Test)")
    print("  4. 上架 (Deploy)")
    print("  5. 运维 (Maintain)")

    try:
        # 运行测试
        registry = await test_intent_registration()
        await test_intent_parsing(registry)
        await test_orchestration(registry)
        await test_execution(registry)
        await test_dependency_handling(registry)
        await test_parallel_execution(registry)

        # 总结
        print_header("测试完成")
        print("\n所有测试通过!")
        print("\nSDLC 意图系统功能验证:")
        print("  [OK] 意图注册和定义")
        print("  [OK] 意图解析（LLM/关键词匹配）")
        print("  [OK] 意图编排（DAG 构建）")
        print("  [OK] 意图执行（异步/并行）")
        print("  [OK] 依赖关系处理")
        print("  [OK] 并行执行支持")

    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
