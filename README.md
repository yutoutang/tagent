# Intent System - 智能意图管理系统

基于 LangGraph 实现的智能意图管理系统，支持动态意图识别、DAG 编排和并行执行。设计灵感来源于 Dify 和 n8n。

## 核心特性

### 1. 意图识别与编排
- **LLM 驱动**: 使用大语言模型智能识别用户意图
- **DAG 编排**: 自动构建有向无环图，处理意图依赖关系
- **并行执行**: 同层意图并行执行，提升效率

### 2. 数据流转
- **n8n 风格表达式**: 支持 `{{ $json.field }}` 语法引用前序结果
- **上下文管理**: 自动维护意图间的数据流转

### 3. YAgent 统一框架
- **5 阶段流程**: 解析 → 编排 → 执行 → 反思 → 综合
- **多轮对话**: 基于 LangGraph 的状态管理
- **迭代优化**: 自动判断是否需要继续执行

## 项目结构

```
tagent/
├── README.md                    # 本文档
├── CLI_GUIDE.md                 # CLI 使用指南
├── cli_demo.py                  # 🎉 交互式命令行工具
├── pyproject.toml              # 项目配置
├── requirements.txt            # 依赖列表
├── examples/                   # 示例代码
│   ├── custom_intent.py               # 自定义意图
│   ├── external_project_usage.py      # 外部项目集成
│   ├── intent_basic_usage.py          # 基础用法
│   ├── sdlc_workflow_y_agent.py       # SDLC 工作流示例
│   ├── test_sdlc_with_config.py       # 配置测试
│   ├── unified_agent_demo.py          # YAgent 演示
│   ├── workflow_example.py            # 工作流示例
│   ├── workflow_intent_engine.py      # 意图引擎
│   ├── workflow_intents.json          # 工作流定义
│   ├── workflow_system_example.py     # 系统示例
│   └── workflow_with_agent.py         # Agent + 工作流
└── intent_system/              # 核心代码
    ├── __init__.py
    ├── builtin_intents/        # 内置意图
    │   ├── __init__.py
    │   └── data_intents.py             # 数据处理意图
    ├── core/                   # 核心模块
    │   ├── intent_definition.py        # 意图定义
    │   ├── intent_parser.py            # 意图解析
    │   ├── intent_registry.py          # 意图注册
    │   └── state.py                    # 状态定义
    ├── data_flow/              # 数据流引擎
    │   ├── __init__.py
    │   └── data_flow_engine.py         # 数据流转
    ├── execution/               # 执行器
    │   ├── __init__.py
    │   ├── intent_executor.py          # 意图执行
    │   └── execution_tracker.py        # 执行追踪
    ├── orchestration/          # 编排器
    │   ├── __init__.py
    │   └── orchestrator.py             # DAG 编排
    ├── workflow/               # 工作流
    │   ├── __init__.py
    │   ├── json_loader.py              # JSON 加载
    │   ├── workflow_intent.py          # 工作流意图
    │   └── workflow_manager.py         # 工作流管理
    └── yagent/                 # YAgent
        ├── __init__.py
        ├── agent.py                    # Agent 类
        ├── graph.py                    # 计算图
        ├── nodes.py                    # 节点实现
        └── state.py                    # 状态定义
```

## 快速开始

### 🎉 方式 1：使用交互式 CLI（推荐）

直接运行 CLI demo，体验交互式意图识别：

```bash
python cli_demo.py
```

**功能特性**：
- 🎯 智能意图识别
- 💬 多轮对话支持
- 📊 实时执行反馈
- 📝 历史记录管理
- 🎨 美化的终端界面

**使用示例**：
```
You> 帮我计算 25 * 4 + 10
✓ 检测到意图: calculator (95% 置信度)
结果: 110

You> 将结果转换为大写
✓ 检测到意图: text_processing
结果: ONE HUNDRED TEN
```

详细使用说明请查看 [CLI_GUIDE.md](CLI_GUIDE.md)

### 方式 2：编程方式使用

#### 1. 安装依赖

```bash
pip install -r requirements.txt
```

##### 2. 配置环境变量

创建 `.env` 文件：

```env
# OpenAI
OPENAI_API_KEY=your-openai-api-key
LLM_PROVIDER=openai
MODEL_NAME=gpt-4o

# 或使用 Anthropic
# ANTHROPIC_API_KEY=your-anthropic-api-key
# LLM_PROVIDER=anthropic
# MODEL_NAME=claude-3-5-sonnet-20241022

# 或使用 DeepSeek
# OPENAI_API_KEY=your-deepseek-api-key
# LLM_PROVIDER=openai
# MODEL_NAME=deepseek-chat
# BASE_URL=https://api.deepseek.com
```

#### 3. 基本使用（编程方式）

#### 使用 YAgent（推荐）

```python
from intent_system import YAgent

# 创建 Agent
agent = YAgent()

# 运行
result = agent.run("帮我搜索 Python LangGraph 教程")

print(f"成功: {result['success']}")
print(f"结果: {result['result']}")
```

#### 自定义配置

```python
from intent_system import YAgent

# 使用 DeepSeek
agent = YAgent(
    api_key="sk-xxx",
    base_url="https://api.deepseek.com",
    model_name="deepseek-chat"
)

result = agent.run("你的查询")
```

#### 使用意图系统

```python
from intent_system import (
    IntentRegistry,
    IntentParser,
    IntentOrchestrator,
    IntentExecutor
)
from intent_system.builtin_intents import register_builtin_data_intents
from langchain_openai import ChatOpenAI

# 初始化
registry = IntentRegistry()
register_builtin_data_intents(registry)

llm = ChatOpenAI(model="gpt-4o")
parser = IntentParser(llm, registry)
orchestrator = IntentOrchestrator(registry)
executor = IntentExecutor(registry)

# 解析意图
result = parser.parse("帮我搜索今天的天气")

# 编排
plan = orchestrator.orchrate([result.primary_intent])

# 执行
final_result = executor.execute_plan(plan)
```

## 内置意图

| 意图 ID | 描述 | 参数 |
|---------|------|------|
| `http_request` | HTTP 请求 | url, method, headers, body |
| `calculator` | 数学计算 | expression |
| `web_search` | 网络搜索 | query, max_results |
| `data_analysis` | 数据分析 | data, operation |
| `text_processing` | 文本处理 | text, operation |
| `file_read` | 文件读取 | file_path |

## 示例代码

### 1. 基础意图使用

```bash
python examples/intent_basic_usage.py
```

### 2. 自定义意图

```bash
python examples/custom_intent.py
```

### 3. YAgent 演示

```bash
python examples/unified_agent_demo.py
```

### 4. 工作流示例

```bash
python examples/workflow_example.py
```

### 5. SDLC 工作流

```bash
python examples/sdlc_workflow_y_agent.py
```

## 高级用法

### 自定义意图

```python
from intent_system import IntentDefinition, IntentMetadata, InputOutputSchema
from intent_system import YAgent

async def my_tool(param: str) -> str:
    """我的自定义工具"""
    return f"处理结果: {param}"

# 定义意图
intent = IntentDefinition(
    metadata=IntentMetadata(
        id="my_tool",
        name="我的工具",
        description="自定义工具描述",
        category="transform",
        tags=["custom"]
    ),
    schema=InputOutputSchema(
        inputs={
            "param": {
                "type": "string",
                "description": "输入参数",
                "required": True
            }
        },
        outputs={"result": {"type": "string"}}
    ),
    executor=my_tool
)

# 注册并使用
agent = YAgent()
agent.register_intent(intent)
result = agent.run("使用我的工具处理 xxx")
```

### 数据流表达式

```python
mapping = {
    "temperature": "{{ $json.weather }}",
    "city": "{{ $json.city_name }}"
}
```

### 依赖关系

```python
metadata=IntentMetadata(
    id="step2",
    dependencies=["step1"]  # step1 完成后才能执行
)
```

## API 兼容性

支持以下 LLM 提供商：

- ✅ OpenAI (GPT-4, GPT-3.5)
- ✅ Anthropic (Claude 3.5 Sonnet)
- ✅ DeepSeek (兼容 OpenAI API)
- ✅ 其他兼容 OpenAI API 的服务

## 故障排除

### DeepSeek API 错误

确保使用最新版本，已修复 `response_format` 兼容性问题。

### 意图识别失败

检查：
1. LLM API Key 是否正确
2. 意图描述是否清晰
3. 网络连接是否正常

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
