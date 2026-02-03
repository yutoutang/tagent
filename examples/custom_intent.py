"""
自定义意图示例

演示如何定义和注册自定义意图
"""

import asyncio
from dotenv import load_dotenv

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from intent_system.core import (
    IntentRegistry,
    IntentDefinition,
    IntentMetadata,
    InputOutputSchema
)
from intent_system.core.intent_parser import IntentParser
from intent_system.orchestration import IntentOrchestrator
from intent_system.execution import IntentExecutor
from intent_system.builtin_intents import register_builtin_data_intents

from langchain_core.tools import tool
from dynamic_agent_framework import create_llm


# ============================================================
# 自定义工具函数
# ============================================================

@tool
async def weather_fetcher(city: str, units: str = "celsius") -> dict:
    """
    获取天气信息（模拟）

    Args:
        city: 城市名称
        units: 温度单位 (celsius/fahrenheit)

    Returns:
        天气数据
    """
    # 模拟天气数据
    weather_data = {
        "北京": {"temp": 25, "condition": "晴朗", "humidity": 45},
        "上海": {"temp": 28, "condition": "多云", "humidity": 65},
        "深圳": {"temp": 32, "condition": "阴天", "humidity": 75},
    }

    data = weather_data.get(city, {"temp": 20, "condition": "未知", "humidity": 50})

    # 温度单位转换
    if units == "fahrenheit":
        data["temp"] = data["temp"] * 9 / 5 + 32

    return {
        "city": city,
        "temperature": data["temp"],
        "units": units,
        "condition": data["condition"],
        "humidity": data["humidity"]
    }


@tool
async def weather_analyzer(weather_data: dict, analysis_type: str = "summary") -> str:
    """
    分析天气数据

    Args:
        weather_data: 天气数据
        analysis_type: 分析类型

    Returns:
        分析报告
    """
    temp = weather_data.get("temperature", 0)
    condition = weather_data.get("condition", "未知")
    city = weather_data.get("city", "未知城市")

    if analysis_type == "summary":
        return f"{city}当前天气：{condition}，温度{temp}度"
    elif analysis_type == "detailed":
        return (
            f"{city}详细天气报告：\n"
            f"  - 温度：{temp}度\n"
            f"  - 状况：{condition}\n"
            f"  - 湿度：{weather_data.get('humidity', 0)}%"
        )
    else:
        return f"{city}天气分析完成"


@tool
async def report_generator(title: str, content: str, format_type: str = "markdown") -> str:
    """
    生成报告

    Args:
        title: 报告标题
        content: 报告内容
        format_type: 格式类型

    Returns:
        格式化的报告
    """
    if format_type == "markdown":
        return f"# {title}\n\n{content}"
    elif format_type == "html":
        return f"<h1>{title}</h1><p>{content}</p>"
    else:
        return f"{title}\n{content}"


# ============================================================
# 自定义意图定义
# ============================================================

def create_custom_intents():
    """创建自定义意图列表"""
    return [
        # 天气查询意图
        IntentDefinition(
            metadata=IntentMetadata(
                id="weather_fetch",
                name="查询天气",
                description="获取指定城市的天气信息",
                category="data",
                tags=["weather", "api", "external"],
                priority=15
            ),
            schema=InputOutputSchema(
                inputs={
                    "city": {
                        "type": "string",
                        "description": "城市名称",
                        "required": True
                    },
                    "units": {
                        "type": "string",
                        "description": "温度单位",
                        "default": "celsius",
                        "enum": ["celsius", "fahrenheit"]
                    }
                },
                outputs={
                    "data": {"type": "object", "description": "天气数据"}
                }
            ),
            executor=weather_fetcher.func
        ),

        # 天气分析意图（依赖于天气查询）
        IntentDefinition(
            metadata=IntentMetadata(
                id="weather_analyze",
                name="分析天气",
                description="分析天气数据并生成报告",
                category="transform",
                tags=["weather", "analysis"],
                priority=10,
                dependencies=["weather_fetch"]  # 依赖于天气查询
            ),
            schema=InputOutputSchema(
                inputs={
                    "weather_data": {
                        "type": "object",
                        "description": "天气数据",
                        "required": True
                    },
                    "analysis_type": {
                        "type": "string",
                        "description": "分析类型",
                        "default": "summary",
                        "enum": ["summary", "detailed"]
                    }
                },
                outputs={
                    "report": {"type": "string", "description": "分析报告"}
                }
            ),
            executor=weather_analyzer.func
        ),

        # 报告生成意图
        IntentDefinition(
            metadata=IntentMetadata(
                id="report_generate",
                name="生成报告",
                description="生成格式化的报告",
                category="transform",
                tags=["report", "format"],
                priority=5
            ),
            schema=InputOutputSchema(
                inputs={
                    "title": {
                        "type": "string",
                        "description": "报告标题",
                        "required": True
                    },
                    "content": {
                        "type": "string",
                        "description": "报告内容",
                        "required": True
                    },
                    "format_type": {
                        "type": "string",
                        "description": "格式类型",
                        "default": "markdown",
                        "enum": ["markdown", "html", "plain"]
                    }
                },
                outputs={
                    "report": {"type": "string", "description": "格式化报告"}
                }
            ),
            executor=report_generator.func
        )
    ]


async def main():
    """主函数"""
    print("=" * 60)
    print("自定义意图示例")
    print("=" * 60)

    load_dotenv()

    # 1. 初始化
    print("\n1. 初始化...")
    registry = IntentRegistry()
    llm = create_llm()

    # 2. 注册内置意图
    print("\n2. 注册内置意图...")
    register_builtin_data_intents(registry)
    print(f"   内置意图: {registry.count()} 个")

    # 3. 注册自定义意图
    print("\n3. 注册自定义意图...")
    custom_intents = create_custom_intents()
    for intent in custom_intents:
        try:
            registry.register(intent)
            print(f"   ✓ {intent.metadata.id}: {intent.metadata.name}")
        except ValueError as e:
            print(f"   ✗ {intent.metadata.id}: {e}")

    print(f"\n   总意图数: {registry.count()}")

    # 4. 创建组件
    parser = IntentParser(llm, registry)
    orchestrator = IntentOrchestrator(registry)
    executor = IntentExecutor(registry)

    # 5. 示例：查询并分析天气
    print("\n" + "=" * 60)
    print("示例：查询天气并生成报告")
    print("=" * 60)

    user_input = "帮我查一下北京的天气，然后分析一下，最后生成一个markdown格式的报告"
    print(f"\n用户输入: {user_input}")

    # 解析
    parse_result = parser.parse(user_input)
    print(f"\n识别到的意图:")
    print(f"  主要意图: {parse_result.primary_intent}")
    if parse_result.sub_intents:
        print(f"  子意图:")
        for sub in parse_result.sub_intents:
            print(f"    - {sub['id']}")

    # 编排
    plan = orchestrator.orchestrate(parse_result)
    print(f"\n编排计划:")
    print(f"  执行层数: {len(plan.execution_layers)}")
    for i, layer in enumerate(plan.execution_layers, 1):
        print(f"  第 {i} 层: {layer}")

    # 执行
    results = await executor.execute_plan_async(plan, "custom_session")
    print(f"\n执行结果:")
    for intent_id, result in results.items():
        print(f"\n  {intent_id}:")
        if isinstance(result, dict):
            for key, value in result.items():
                print(f"    {key}: {value}")
        else:
            print(f"    {result}")

    # 打印执行摘要
    print(f"\n执行摘要:")
    summary = executor.get_execution_summary()
    print(f"  总意图数: {summary['total_intents']}")
    print(f"  成功: {summary['successful']}")
    print(f"  失败: {summary['failed']}")
    print(f"  总耗时: {summary['total_duration']:.2f}s")

    print("\n" + "=" * 60)
    print("自定义意图示例运行完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
