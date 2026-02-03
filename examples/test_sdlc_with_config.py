"""
SDLC 工作流 - 使用自定义配置示例

演示如何在 sdlc_workflow_y_agent.py 中使用自定义 API Key、Base URL 和 Model Name
"""

import asyncio
import os
from dotenv import load_dotenv

from intent_system import YAgent, IntentDefinition, IntentMetadata, InputOutputSchema
from langchain_core.tools import tool
from examples.sdlc_workflow_y_agent import create_sdlc_intents


def print_section(title: str):
    """打印分节标题"""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


# ============================================================================
# 自定义配置示例
# ============================================================================

async def demo_custom_config():
    """演示使用自定义配置"""
    print_section("演示: 使用自定义配置")

    # 示例 1: 使用自定义端点（如国内 LLM 服务）
    print("\n示例 1: 使用国内 LLM 服务")
    print("-" * 50)

    # 配置（替换为你的实际配置）
    config = {
        "api_key": "sk-your-chinese-api-key",
        "base_url": "https://your-chinese-llm-provider.com/v1",
        "model_name": "your-model-name"
    }

    print(f"配置:")
    print(f"  API Key: {config['api_key'][:20]}...")
    print(f"  Base URL: {config['base_url']}")
    print(f"  Model: {config['model_name']}")

    # 创建 Agent
    agent = YAgent(**config)
    print("\n[OK] YAgent 创建成功")

    # 注册意图
    for intent in create_sdlc_intents():
        agent.register_intent(intent)

    print(f"[OK] 已注册 {len(create_sdlc_intents())} 个 SDLC 意图")

    # 测试查询
    print("\n执行测试查询...")
    result = await agent.arun("学习 Python 基础", session_id="test_001")

    print(f"执行成功: {result['success']}")
    print(f"检测意图: {result['detected_intents']}")
    if result['intent_results']:
        for intent_id, r in result['intent_results'].items():
            print(f"  - {intent_id}: {r.get('result', r)}")


async def demo_env_config():
    """演示使用环境变量配置"""
    print_section("演示: 使用环境变量配置")

    print("\n在 .env 文件中配置:")
    print("-" * 50)
    print("""
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-4o

# 或者使用国内服务
# OPENAI_API_KEY=your-chinese-api-key
# OPENAI_BASE_URL=https://your-chinese-llm.com/v1
# MODEL_NAME=your-model
    """)

    # 加载环境变量
    load_dotenv()

    # 检查配置
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    model = os.getenv("MODEL_NAME")

    print("\n当前环境变量配置:")
    print(f"  API Key: {'已设置' if api_key else '未设置'}")
    print(f"  Base URL: {base_url or '未设置'}")
    print(f"  Model: {model or '未设置'}")

    if api_key:
        agent = YAgent()
        print("\n[OK] YAgent 创建成功（使用环境配置）")
    else:
        print("\n[INFO] 未设置 API Key，将使用降级模式")


async def demo_partial_config():
    """演示部分自定义配置"""
    print_section("演示: 部分自定义配置")

    print("\n只自定义 API Key，其他使用环境变量:")
    print("-" * 50)

    # 只设置 API Key
    custom_api_key = os.getenv("OPENAI_API_KEY")

    if custom_api_key:
        agent = YAgent(api_key=custom_api_key)
        print(f"[OK] 使用自定义 API Key: {custom_api_key[:20]}...")
    else:
        print("[INFO] 请先在环境变量中设置 OPENAI_API_KEY")


async def demo_switch_provider():
    """演示切换 LLM 提供商"""
    print_section("演示: 切换 LLM 提供商")

    print("\n切换到 Anthropic Claude:")
    print("-" * 50)

    # 检查是否有 Anthropic Key
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    if anthropic_key:
        agent = YAgent(
            llm_provider="anthropic",
            model_name="claude-3-5-sonnet-20241022"
        )
        print("[OK] 已切换到 Anthropic Claude")
        print(f"  模型: claude-3-5-sonnet-20241022")
    else:
        print("[INFO] 未设置 ANTHROPIC_API_KEY")


async def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("SDLC 工作流 - 自定义配置演示")
    print("=" * 70)

    print("\n本演示展示如何在 sdlc_workflow_y_agent.py 中配置 YAgent:")

    try:
        # 演示各种配置方式
        await demo_custom_config()
        await demo_env_config()
        await demo_partial_config()
        await demo_switch_provider()

        # 总结
        print_section("总结")
        print("""
在 sdlc_workflow_y_agent.py 中使用自定义配置：

方式 1: 修改 main() 函数中的代码
-------------------------------------------
在 main() 函数中，将：

    agent = YAgent()

替换为：

    custom_api_key = os.getenv("OPENAI_API_KEY")
    custom_base_url = os.getenv("OPENAI_BASE_URL")
    custom_model = os.getenv("MODEL_NAME")

    agent = YAgent(
        api_key=custom_api_key,
        base_url=custom_base_url,
        model_name=custom_model
    )


方式 2: 使用命令行参数
-------------------------------------------
python sdlc_workflow_y_agent.py \\
    --api-key sk-your-key \\
    --base-url https://your-endpoint.com/v1 \\
    --model your-model


方式 3: 使用 .env 文件（推荐）
-------------------------------------------
在项目根目录创建 .env 文件：
  OPENAI_API_KEY=sk-your-key
  OPENAI_BASE_URL=https://api.openai.com/v1
  MODEL_NAME=gpt-4o

然后直接运行：
  python sdlc_workflow_y_agent.py
        """)

    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
