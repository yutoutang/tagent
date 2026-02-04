#!/usr/bin/env python3
"""
Intent System 交互式 CLI 命令行工具

一个功能完整的命令行界面，支持：
- 交互式对话
- 实时显示执行过程
- 多轮会话管理
- 意图识别与执行
- 美化的输出格式
"""

import os
import sys
import asyncio
from typing import Optional
from datetime import datetime

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from intent_system import YAgent
from intent_system.core import IntentDefinition, IntentMetadata, InputOutputSchema
from langchain_core.tools import tool


class Colors:
    """终端颜色"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class IntentCLI:
    """Intent System 交互式 CLI"""

    def __init__(self):
        """初始化 CLI"""
        self.agent = None
        self.session_id = None
        self.history = []
        self.running = True

    def print_banner(self):
        """打印欢迎横幅"""
        banner = f"""
{Colors.OKCYAN}{Colors.BOLD}
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║        Intent System - 智能意图管理系统                  ║
║        Interactive CLI v1.0                              ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
{Colors.ENDC}
{Colors.OKGREEN}
基于 LangGraph 的智能意图识别与编排框架
支持 OpenAI / Anthropic / DeepSeek API
{Colors.ENDC}
"""
        print(banner)
        self.print_commands()

    def print_commands(self):
        """打印可用命令"""
        print(f"{Colors.HEADER}可用命令:{Colors.ENDC}")
        print(f"  {Colors.OKCYAN}help{Colors.ENDC}      - 显示帮助信息")
        print(f"  {Colors.OKCYAN}clear{Colors.ENDC}     - 清空屏幕")
        print(f"  {Colors.OKCYAN}history{Colors.ENDC}   - 显示对话历史")
        print(f"  {Colors.OKCYAN}session{Colors.ENDC}   - 开始新会话")
        print(f"  {Colors.OKCYAN}info{Colors.ENDC}      - 显示系统信息")
        print(f"  {Colors.OKCYAN}exit{Colors.ENDC}      或 {Colors.OKCYAN}quit{Colors.ENDC} - 退出程序")
        print()

    def print_help(self):
        """打印帮助信息"""
        print(f"\n{Colors.BOLD}{Colors.HEADER}=== Intent System CLI 帮助 ==={Colors.ENDC}\n")

        print(f"{Colors.OKCYAN}基本使用:{Colors.ENDC}")
        print("  直接输入您的需求，系统会自动识别意图并执行")
        print("  例如:")
        print("    - 帮我计算 25 * 4 + 10")
        print("    - 搜索 Python LangGraph 教程")
        print("    - 分析这段代码的性能")

        print(f"\n{Colors.OKCYAN}高级功能:{Colors.ENDC}")
        print("  - 支持多轮对话，可以连续提问")
        print("  - 自动识别意图，支持 DAG 编排")
        print("  - 并行执行独立任务")
        print("  - 智能数据流转")

        print(f"\n{Colors.OKCYAN}内置意图:{Colors.ENDC}")
        print("  - calculator: 数学计算")
        print("  - web_search: 网络搜索")
        print("  - text_processing: 文本处理")
        print("  - data_analysis: 数据分析")
        print("  - http_request: HTTP 请求")
        print("  - file_read: 文件读取")

        self.print_commands()

    def print_system_info(self):
        """显示系统信息"""
        print(f"\n{Colors.BOLD}{Colors.HEADER}=== 系统信息 ==={Colors.ENDC}\n")

        # 环境变量信息
        provider = os.getenv("LLM_PROVIDER", "openai")
        model = os.getenv("MODEL_NAME", "gpt-4o")

        print(f"{Colors.OKCYAN}LLM 配置:{Colors.ENDC}")
        print(f"  提供商: {provider}")
        print(f"  模型: {model}")

        # 会话信息
        print(f"\n{Colors.OKCYAN}会话信息:{Colors.ENDC}")
        print(f"  会话ID: {self.session_id or '未设置'}")
        print(f"  历史记录: {len(self.history)} 条")

        # 状态
        print(f"\n{Colors.OKCYAN}系统状态:{Colors.ENDC}")
        print(f"  Agent: {'已初始化' if self.agent else '未初始化'}")
        print(f"  运行中: {self.running}")

        print()

    def print_history(self):
        """显示对话历史"""
        if not self.history:
            print(f"\n{Colors.WARNING}暂无对话历史{Colors.ENDC}\n")
            return

        print(f"\n{Colors.BOLD}{Colors.HEADER}=== 对话历史 ({len(self.history)} 条) ==={Colors.ENDC}\n")

        for i, item in enumerate(self.history, 1):
            print(f"{Colors.OKCYAN}[{i}]{Colors.ENDC} {Colors.BOLD}用户:{Colors.ENDC} {item['query']}")
            if item.get('result'):
                result = item['result']
                success = result.get('success', False)
                status_color = Colors.OKGREEN if success else Colors.FAIL

                print(f"    {status_color}状态:{Colors.ENDC} {'成功' if success else '失败'}")

                if success:
                    intents = result.get('detected_intents', [])
                    if intents:
                        print(f"    {Colors.OKBLUE}意图:{Colors.ENDC} {', '.join(intents)}")

                    output = result.get('result')
                    if output:
                        # 截断过长的输出
                        if len(str(output)) > 200:
                            output = str(output)[:200] + "..."
                        print(f"    {Colors.OKGREEN}结果:{Colors.ENDC} {output}")
                else:
                    error = result.get('error', '未知错误')
                    print(f"    {Colors.FAIL}错误:{Colors.ENDC} {error}")

            print()

    def clear_screen(self):
        """清空屏幕"""
        os.system('clear' if os.name == 'posix' else 'cls')

    def new_session(self):
        """开始新会话"""
        import uuid
        self.session_id = str(uuid.uuid4())[:8]
        self.history = []
        print(f"\n{Colors.OKGREEN}✓ 新会话已创建 (ID: {self.session_id}){Colors.ENDC}\n")

    def initialize_agent(self):
        """初始化 Agent"""
        if self.agent is None:
            print(f"{Colors.OKCYAN}正在初始化 Intent System...{Colors.ENDC}")

            try:
                # 从环境变量读取配置
                api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
                base_url = os.getenv("BASE_URL")  # 用于 DeepSeek 等
                model = os.getenv("MODEL_NAME")

                # 创建 Agent
                if api_key:
                    self.agent = YAgent(
                        api_key=api_key,
                        base_url=base_url,
                        model_name=model
                    )
                else:
                    self.agent = YAgent()

                # 创建会话
                if not self.session_id:
                    self.new_session()

                print(f"{Colors.OKGREEN}✓ Intent System 初始化成功{Colors.ENDC}\n")
                return True

            except Exception as e:
                print(f"{Colors.FAIL}✗ 初始化失败: {e}{Colors.ENDC}\n")
                return False
        return True

    async def process_query_async(self, query: str):
        """异步处理用户查询"""
        if not query.strip():
            return

        # 确保已初始化
        if not self.initialize_agent():
            return

        print(f"\n{Colors.BOLD}{Colors.HEADER}正在处理...{Colors.ENDC}\n")

        try:
            # 使用异步 API 调用 Agent
            result = await self.agent.arun(query, session_id=self.session_id)

            # 记录历史
            self.history.append({
                'query': query,
                'result': result,
                'timestamp': datetime.now()
            })

            # 显示结果
            self.display_result(result)

        except Exception as e:
            print(f"{Colors.FAIL}✗ 执行出错: {e}{Colors.ENDC}\n")
            import traceback
            traceback.print_exc()

    def process_query(self, query: str):
        """处理用户查询（同步包装）"""
        if not query.strip():
            return

        # 运行异步处理
        asyncio.run(self.process_query_async(query))

    def display_result(self, result: dict):
        """显示执行结果"""
        success = result.get('success', False)

        if success:
            # 成功
            print(f"{Colors.OKGREEN}✓ 执行成功{Colors.ENDC}\n")

            # 检测到的意图
            intents = result.get('detected_intents', [])
            if intents:
                print(f"{Colors.OKBLUE}🎯 检测到的意图:{Colors.ENDC} {', '.join(intents)}")

            # 置信度
            confidence = result.get('intent_confidence', 0)
            if confidence > 0:
                print(f"{Colors.OKBLUE}📊 意图置信度:{Colors.ENDC} {confidence:.2%}")

            # 执行结果
            output = result.get('result')
            if output:
                print(f"\n{Colors.BOLD}{Colors.OKGREEN}结果:{Colors.ENDC}")
                print(f"{Colors.OKGREEN}{'─' * 60}{Colors.ENDC}")
                print(output)
                print(f"{Colors.OKGREEN}{'─' * 60}{Colors.ENDC}")

            # 执行摘要
            summary = result.get('execution_summary')
            if summary and summary.get('total_intents', 0) > 0:
                print(f"\n{Colors.OKBLUE}📈 执行摘要:{Colors.ENDC}")
                print(f"  总意图数: {summary.get('total_intents', 0)}")
                print(f"  成功: {summary.get('successful', 0)}")
                print(f"  失败: {summary.get('failed', 0)}")

        else:
            # 失败
            print(f"{Colors.FAIL}✗ 执行失败{Colors.ENDC}\n")

            error = result.get('error', '未知错误')
            print(f"{Colors.FAIL}错误信息:{Colors.ENDC} {error}")

            errors = result.get('errors', [])
            if errors:
                print(f"\n{Colors.FAIL}详细错误:{Colors.ENDC}")
                for err in errors:
                    print(f"  - {err}")

        print()

    def run(self):
        """运行 CLI 主循环"""
        self.print_banner()

        # 预初始化
        self.initialize_agent()

        # 主循环
        while self.running:
            try:
                # 读取用户输入
                user_input = input(f"{Colors.BOLD}{Colors.OKCYAN}You>{Colors.ENDC} ").strip()

                if not user_input:
                    continue

                # 处理命令
                if user_input.lower() in ['exit', 'quit', 'q']:
                    self.running = False
                    print(f"\n{Colors.OKGREEN}再见！{Colors.ENDC}\n")
                    break

                elif user_input.lower() == 'help':
                    self.print_help()

                elif user_input.lower() == 'clear':
                    self.clear_screen()
                    self.print_banner()

                elif user_input.lower() == 'history':
                    self.print_history()

                elif user_input.lower() == 'session':
                    self.new_session()

                elif user_input.lower() == 'info':
                    self.print_system_info()

                else:
                    # 处理查询
                    self.process_query(user_input)

            except KeyboardInterrupt:
                print(f"\n\n{Colors.WARNING}使用 'exit' 或 'quit' 退出程序{Colors.ENDC}\n")

            except EOFError:
                self.running = False
                print(f"\n\n{Colors.OKGREEN}再见！{Colors.ENDC}\n")
                break


def main():
    """主函数"""
    cli = IntentCLI()
    cli.run()


if __name__ == "__main__":
    main()
