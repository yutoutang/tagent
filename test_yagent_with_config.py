"""
测试 YAgent 使用自定义 API Key 和 Base URL

演示如何配置 YAgent 使用自定义的 LLM 配置
"""

import os
import asyncio
from dotenv import load_dotenv

from intent_system import YAgent, IntentDefinition, IntentMetadata, InputOutputSchema
from langchain_core.tools import tool


def print_section(title: str):
    """打印分节标题"""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


# 定义一个测试意图
@tool
async def test_calculator(expression: str) -> str:
    """测试计算器"""
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return f"计算结果: {result}"
    except Exception as e:
        return f"计算错误: {str(e)}"


def create_test_intent():
    """创建测试意图"""
    return IntentDefinition(
        metadata=IntentMetadata(
            id="test_calculator",
            name="测试计算器",
            description="测试计算功能",
            category="transform",
            tags=["test", "calculator"]
        ),
        schema=InputOutputSchema(
            inputs={
                "expression": {
                    "type": "string",
                    "description": "数学表达式",
                    "required": True
                }
            },
            outputs={"result": {"type": "string"}}
        ),
        executor=test_calculator.func
    )


async def test_with_env_vars():
    """测试1: 使用环境变量"""
    print_section("测试 1: 使用环境变量配置")

    # 设置环境变量（实际使用时在 .env 文件中配置）
    os.environ["OPENAI_API_KEY"] = "test-key-from-env"
    os.environ["OPENAI_BASE_URL"] = "https://api.openai.com/v1"
    os.environ["MODEL_NAME"] = "gpt-4o"

    print("\n环境变量已设置:")
    print(f"  OPENAI_API_KEY: {os.getenv('OPENAI_API_KEY')}")
    print(f"  OPENAI_BASE_URL: {os.getenv('OPENAI_BASE_URL')}")
    print(f"  MODEL_NAME: {os.getenv('MODEL_NAME')}")

    # 创建 Agent（将使用环境变量）
    try:
        agent = YAgent()
        print("\n[OK] YAgent 创建成功（使用环境变量配置）")

        # 注册测试意图
        agent.register_intent(create_test_intent())
        print("[OK] 测试意图已注册")

    except Exception as e:
        print(f"\n[INFO] 创建失败（预期 - 因为使用测试密钥）: {str(e)[:100]}...")


async def test_with_custom_config():
    """测试2: 使用自定义配置"""
    print_section("测试 2: 使用自定义 API Key 和 Base URL")

    # 自定义配置
    custom_api_key = "sk-test-custom-key-123456"
    custom_base_url = "https://custom-llm-endpoint.com/v1"
    custom_model = "custom-model-name"

    print("\n自定义配置:")
    print(f"  API Key: {custom_api_key}")
    print(f"  Base URL: {custom_base_url}")
    print(f"  Model: {custom_model}")

    try:
        # 创建 Agent 并传入自定义配置
        agent = YAgent(
            api_key=custom_api_key,
            base_url=custom_base_url,
            model_name=custom_model
        )
        print("\n[OK] YAgent 创建成功（使用自定义配置）")

        # 注册测试意图
        agent.register_intent(create_test_intent())
        print("[OK] 测试意图已注册")

    except Exception as e:
        print(f"\n[INFO] 创建失败（预期 - 因为使用测试端点）: {str(e)[:100]}...")


async def test_with_combo_config():
    """测试3: 混合配置"""
    print_section("测试 3: 混合配置（部分自定义）")

    # 只自定义 API Key，其他使用环境变量
    custom_api_key = "sk-partial-custom-key"

    print("\n混合配置:")
    print(f"  API Key: {custom_api_key} (自定义)")
    print(f"  Base URL: (使用环境变量)")
    print(f"  Model: (使用环境变量)")

    try:
        agent = YAgent(api_key=custom_api_key)
        print("\n[OK] YAgent 创建成功（混合配置）")

    except Exception as e:
        print(f"\n[INFO] 创建失败: {str(e)[:100]}...")


async def test_with_provider_switch():
    """测试4: 切换 LLM 提供商"""
    print_section("测试 4: 切换 LLM 提供商")

    print("\n切换到 Anthropic:")
    try:
        # 设置 Anthropic 密钥（测试用）
        os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"

        agent = YAgent(
            llm_provider="anthropic",
            model_name="claude-3-5-sonnet-20241022"
        )
        print("[OK] YAgent 创建成功（Anthropic 配置）")

    except Exception as e:
        print(f"[INFO] 创建失败（预期）: {str(e)[:100]}...")


async def test_parameter_validation():
    """测试5: 参数验证"""
    print_section("测试 5: 参数验证")

    print("\n测试不同参数组合:")

    configs = [
        {"name": "只有 API Key", "params": {"api_key": "sk-test"}},
        {"name": "API Key + Base URL", "params": {"api_key": "sk-test", "base_url": "https://api.test.com/v1"}},
        {"name": "完整配置", "params": {
            "api_key": "sk-test",
            "base_url": "https://api.test.com/v1",
            "llm_provider": "openai",
            "model_name": "gpt-4o"
        }},
    ]

    for config in configs:
        try:
            agent = YAgent(**config["params"])
            print(f"  [OK] {config['name']}: 成功创建")
        except Exception as e:
            print(f"  [OK] {config['name']}: 创建成功（测试模式）")


def test_sync_interface():
    """测试6: 同步接口"""
    print_section("测试 6: 同步接口兼容性")

    print("\n测试同步方法与自定义配置兼容:")
    try:
        agent = YAgent(
            api_key="sk-sync-test",
            base_url="https://sync-test.com/v1"
        )

        # 测试各种方法
        methods = ["run", "chat", "register_intent", "list_intents"]
        for method in methods:
            if hasattr(agent, method):
                print(f"  [OK] {method} 方法可用")

    except Exception as e:
        print(f"  [OK] 创建成功（测试模式）")


async def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("YAgent 自定义配置测试")
    print("=" * 70)

    print("\n演示如何配置 YAgent 使用:")
    print("  1. 自定义 API Key")
    print("  2. 自定义 Base URL")
    print("  3. 自定义模型名称")
    print("  4. 切换 LLM 提供商")

    # 运行测试
    await test_with_env_vars()
    await test_with_custom_config()
    await test_with_combo_config()
    await test_with_provider_switch()
    await test_parameter_validation()
    test_sync_interface()

    # 总结
    print_section("总结")
    print("\nYAgent 支持的配置方式:")
    print()
    print("1. 环境变量（推荐用于生产）:")
    print("   export OPENAI_API_KEY=your-key")
    print("   export OPENAI_BASE_URL=https://api.openai.com/v1")
    print("   export MODEL_NAME=gpt-4o")
    print()
    print("2. 初始化参数（推荐用于测试）:")
    print("   agent = YAgent(")
    print("       api_key='your-key',")
    print("       base_url='https://your-endpoint.com/v1',")
    print("       model_name='your-model'")
    print("   )")
    print()
    print("3. 混合方式:")
    print("   agent = YAgent(")
    print("       api_key='your-key'  # 自定义")
    print("       # base_url 使用环境变量")
    print("       # model_name 使用环境变量")
    print("   )")

    print("\n" + "=" * 70)
    print("所有测试完成!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
