#!/usr/bin/env python3
"""
快速启动脚本 - 一键体验动态 Agent 框架
"""

import sys
import os
from pathlib import Path


def check_environment():
    """检查环境配置"""
    print("=" * 60)
    print("🔍 环境检查")
    print("=" * 60)

    issues = []

    # 检查 Python 版本
    if sys.version_info < (3, 9):
        issues.append(f"❌ Python 版本过低: {sys.version_info.major}.{sys.version_info.minor} (需要 >= 3.9)")
    else:
        print(f"✅ Python 版本: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")

    # 检查依赖
    try:
        import langgraph
        print(f"✅ LangGraph: {langgraph.__version__}")
    except ImportError:
        issues.append("❌ LangGraph 未安装")

    try:
        import langchain
        print(f"✅ LangChain: {langchain.__version__}")
    except ImportError:
        issues.append("❌ LangChain 未安装")

    # 检查环境变量
    env_file = Path(".env")
    if not env_file.exists():
        issues.append("❌ .env 文件不存在")
        print("\n💡 提示: 复制 .env.example 为 .env 并配置 API Key")
        print("   cp .env.example .env")
    else:
        print(f"✅ .env 文件存在")

        from dotenv import load_dotenv
        load_dotenv()

        if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
            issues.append("❌ 未设置 API Key (OPENAI_API_KEY 或 ANTHROPIC_API_KEY)")
        else:
            provider = os.getenv("LLM_PROVIDER", "openai")
            print(f"✅ LLM Provider: {provider}")

    print()

    if issues:
        print("⚠️  发现问题:")
        for issue in issues:
            print(f"   {issue}")
        print()
        return False

    print("✅ 环境检查通过！\n")
    return True


def show_menu():
    """显示菜单"""
    print("=" * 60)
    print("🚀 动态 Agent 框架 - 快速启动")
    print("=" * 60)
    print()
    print("请选择:")
    print()
    print("  1. 📊 查看计算图结构")
    print("  2. 🧪 运行测试套件")
    print("  3. 🚀 查看高级示例")
    print("  4. 💬 交互式对话")
    print("  5. 📚 查看文档")
    print("  6. ❌ 退出")
    print()


def interactive_chat():
    """交互式对话"""
    from dotenv import load_dotenv
    from dynamic_agent_framework import DynamicAgent

    load_dotenv()
    agent = DynamicAgent()

    print("\n" + "=" * 60)
    print("💬 交互式对话模式")
    print("=" * 60)
    print("\n提示: 输入 'quit' 或 'exit' 退出\n")

    session_id = "interactive_session"

    while True:
        try:
            user_input = input("👤 你: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['quit', 'exit', '退出']:
                print("\n👋 再见！")
                break

            print("\n🤖 Agent: ", end="", flush=True)

            result = agent.chat(user_input, session_id=session_id)
            print(result)
            print()

        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            break
        except Exception as e:
            print(f"\n❌ 错误: {str(e)}\n")


def run_visualizer():
    """运行可视化"""
    from visualize_graph import main as vis_main
    vis_main()


def run_tests():
    """运行测试"""
    from test_agent import run_all_tests
    run_all_tests()


def run_advanced_examples():
    """运行高级示例"""
    from advanced_examples import main as adv_main
    adv_main()


def show_docs():
    """显示文档"""
    readme_path = Path("README.md")

    if readme_path.exists():
        print("\n" + "=" * 60)
        print("📚 README.md")
        print("=" * 60)
        print(readme_path.read_text())
    else:
        print("\n❌ README.md 文件不存在")


def main():
    """主函数"""
    # 检查环境
    if not check_environment():
        print("⚠️  请先解决环境问题后再运行")
        print("💡 安装依赖: pip install -r requirements.txt")
        return

    # 显示菜单
    while True:
        show_menu()

        try:
            choice = input("请输入选项 (1-6): ").strip()

            if choice == "1":
                run_visualizer()
            elif choice == "2":
                run_tests()
            elif choice == "3":
                run_advanced_examples()
            elif choice == "4":
                interactive_chat()
            elif choice == "5":
                show_docs()
            elif choice == "6":
                print("\n👋 再见！")
                break
            else:
                print("\n❌ 无效选项，请重新选择\n")

            input("\n按 Enter 继续...")

        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            break
        except Exception as e:
            print(f"\n❌ 错误: {str(e)}\n")


if __name__ == "__main__":
    main()
