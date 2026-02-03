# 动态 Agent 调用框架

基于 LangGraph 实现的智能 agent 调用框架，支持动态任务识别、工具加载和多 agent 协作。

## 🌟 核心特性

### 1. 动态任务识别
- **智能分类**: 自动识别任务类型（编程、研究、分析、计算等）
- **置信度评估**: 对分类结果进行置信度评分
- **LLM 驱动**: 使用大语言模型进行语义理解

### 2. 动态工具加载
- **工具注册系统**: 灵活的工具注册与管理机制
- **按需加载**: 根据任务类型自动加载相关工具
- **扩展性强**: 轻松添加自定义工具

### 3. 多阶段执行流程
- **分类 → 规划 → 执行 → 反思 → 综合**
- 支持迭代优化
- 自动判断任务完成状态

### 4. 状态管理
- 基于 LangGraph 的状态管理
- 支持多轮对话
- 持久化会话支持

### 5. 错误处理
- 完善的错误捕获与报告
- 最大迭代次数限制
- 优雅降级

## 📁 项目结构

```
agent-f/
├── dynamic_agent_framework.py   # 主框架实现
├── test_agent.py                 # 测试套件
├── tools_config.json             # 工具配置文件
├── requirements.txt              # Python 依赖
├── .env.example                  # 环境变量示例
└── README.md                     # 本文档
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填入你的 API Key：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
OPENAI_API_KEY=your-openai-api-key
# 或者使用 Anthropic
ANTHROPIC_API_KEY=your-anthropic-api-key
LLM_PROVIDER=openai
MODEL_NAME=gpt-4o
```

### 3. 基本使用

```python
from dotenv import load_dotenv
from dynamic_agent_framework import DynamicAgent

# 加载环境变量
load_dotenv()

# 创建 agent
agent = DynamicAgent()

# 简单对话
result = agent.chat("帮我计算 25 * 4")
print(result)

# 或者获取完整结果
response = agent.run("搜索 Python 异步编程资料")
print(f"任务类型: {response['task_type']}")
print(f"执行结果: {response['result']}")
print(f"中间步骤: {response['intermediate_steps']}")
```

### 4. 自定义工具

```python
from langchain_core.tools import tool

# 定义自定义工具
@tool
def my_custom_tool(param: str) -> str:
    """自定义工具的描述"""
    return f"处理结果: {param}"

# 注册工具
agent = DynamicAgent()
agent.register_tool(
    "my_custom_tool",
    my_custom_tool,
    {
        "task_types": ["coding", "research"],
        "description": "我的自定义工具"
    }
)

# 使用 agent
result = agent.chat("使用我的自定义工具处理 xxx")
```

## 🏗️ 架构设计

### 计算图结构

```
    ┌─────────────┐
    │   START     │
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │  Classify   │  ← 任务识别与分类
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │    Plan     │  ← 制定执行计划
    └──────┬──────┘
           │
           ▼
      ┌────────┐
      │ Decide │  ← 决策路由
      └───┬────┘
          │
    ┌─────┴─────┐
    │           │
    ▼           ▼
┌─────────┐ ┌──────────┐
│ Execute │ │ Synthesize│
└────┬────┘ └──────────┘
     │
     ▼
┌─────────┐
│ Reflect │  ← 反思与评估
└────┬────┘
     │
     ▼
  ┌────┴─────┐
  │  Decide  │  ← 继续或结束
  └────┬─────┘
       │
       ▼
    ┌────────┐
    │   END  │
    └────────┘
```

### 核心组件

#### 1. ToolRegistry (工具注册表)
- 管理所有可用工具
- 支持按任务类型检索工具
- 动态加载工具配置

#### 2. AgentState (状态定义)
```python
class AgentState(TypedDict):
    messages: List[BaseMessage]          # 对话历史
    task_type: Optional[str]             # 任务类型
    task_confidence: Optional[float]     # 分类置信度
    available_tools: List[Dict]          # 可用工具列表
    executed_tools: List[str]            # 已执行工具
    result: Optional[str]                # 最终结果
    intermediate_steps: List[Dict]       # 中间步骤
    iteration: int                       # 当前迭代
    max_iterations: int                  # 最大迭代次数
    is_complete: bool                    # 完成标志
    errors: List[str]                    # 错误列表
    metadata: Dict[str, Any]             # 元数据
```

#### 3. 节点 (Nodes)

**task_classifier_node**
- 使用 LLM 识别任务类型
- 加载相关工具
- 评估分类置信度

**planner_node**
- 分析可用工具
- 制定执行计划
- 确定执行顺序

**executor_node**
- 执行工具调用
- 处理工具返回结果
- 管理执行流程

**reflector_node**
- 评估当前结果
- 决定是否继续
- 防止无限循环

**synthesizer_node**
- 综合所有步骤
- 生成最终答案
- 格式化输出

## 🧪 运行测试

```bash
python test_agent.py
```

测试包括：
1. 基本功能测试
2. 自定义工具测试
3. 多轮对话测试
4. 流式输出测试
5. 错误处理测试
6. 工具列表测试

## 📊 任务类型

框架支持以下任务类型：

| 类型 | 描述 | 相关工具 |
|-----|------|---------|
| `coding` | 编程、代码分析、开发 | code_analyzer, api_client |
| `research` | 信息搜索、调研 | web_searcher, document_summarizer |
| `analysis` | 数据分析、推理 | data_calculator, code_analyzer |
| `calculation` | 数学计算 | data_calculator |
| `general` | 一般对话 | 所有工具 |

## 🔧 高级用法

### 流式输出

```python
import asyncio

async def stream_example():
    agent = DynamicAgent()

    async for event in agent.astream("搜索 LangGraph 教程"):
        print(f"事件: {event}")

asyncio.run(stream_example())
```

### 自定义配置

```python
custom_config = {
    "configurable": {
        "thread_id": "custom_session_123"
    }
}

agent = DynamicAgent(config=custom_config)
```

### 多 agent 协作

```python
# 创建多个 agent 实例
coder_agent = DynamicAgent()
researcher_agent = DynamicAgent()

# 串联使用
research_result = researcher_agent.run("研究 Python 性能优化")
code_suggestion = coder_agent.run(f"基于以下研究写代码: {research_result['result']}")
```

## 🛠️ 内置工具

### code_analyzer
- **功能**: 分析代码并提供建议
- **参数**: `code` (代码), `language` (语言)
- **任务类型**: coding, analysis

### web_searcher
- **功能**: 搜索网络信息
- **参数**: `query` (查询), `max_results` (结果数)
- **任务类型**: research, general

### data_calculator
- **功能**: 计算数学表达式
- **参数**: `expression` (表达式)
- **任务类型**: calculation, analysis

### document_summarizer
- **功能**: 总结文档内容
- **参数**: `text` (文本)
- **任务类型**: research, analysis

### api_client
- **功能**: 调用 API 接口
- **参数**: `endpoint` (端点), `method` (方法)
- **任务类型**: coding, general

## 🔒 最佳实践

### 1. 错误处理
```python
result = agent.run("your query")

if result["success"]:
    print(result["result"])
else:
    print(f"错误: {result['error']}")
    for error in result["errors"]:
        print(f"  - {error}")
```

### 2. 会话管理
```python
# 使用相同 session_id 保持上下文
agent.chat("第一个问题", session_id="user_123")
agent.chat("跟进问题", session_id="user_123")
```

### 3. 工具设计
```python
@tool
def good_tool(param: str, optional: int = 10) -> str:
    """
    清晰的工具描述有助于 LLM 正确使用

    Args:
        param: 参数说明
        optional: 可选参数说明

    Returns:
        返回值说明
    """
    return f"结果: {param}"
```

## 🐛 故障排除

### 问题 1: API Key 错误
```
解决方案: 检查 .env 文件中的 API Key 是否正确
```

### 问题 2: 工具未被调用
```
解决方案: 确保工具的描述清晰，并在 task_types 中正确分类
```

### 问题 3: 无限循环
```
解决方案: 检查 max_iterations 设置，默认为 5
```

## 📚 参考资料

- [LangGraph 官方文档](https://python.langchain.com/docs/langgraph)
- [LangChain 文档](https://python.langchain.com/)
- [OpenAI API 文档](https://platform.openai.com/docs)

## 📝 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📧 联系

如有问题或建议，请创建 Issue。
