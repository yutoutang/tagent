# Intent System 安装使用指南

## 简介

Intent System 是一个基于 Dify 和 n8n 设计理念的意图注册与编排框架，支持 LLM 驱动的意图解析、依赖管理和工作流编排。

## 安装方式

### 方式1：从本地源码安装（推荐用于开发）

```bash
# 进入项目目录
cd /path/to/tagent

# 安装为可编辑模式（开发时修改会立即生效）
pip install -e .

# 或者直接安装
pip install .
```

### 方式2：从 GitHub 克隆后安装

```bash
# 克隆仓库
git clone https://github.com/yutoutang/tagent.git
cd tagent

# 安装
pip install -e .
```

### 方式3：仅复制 intent_system 目录

将 `intent_system` 目录复制到你的项目中，然后：

```python
# 确保项目根目录在 Python 路径中
import sys
sys.path.insert(0, '/path/to/your/project')

from intent_system import IntentRegistry, IntentParser
```

## 使用示例

### 基础使用 - 意图注册与执行

```python
import asyncio
from intent_system import (
    IntentRegistry,
    IntentDefinition,
    IntentMetadata,
    InputOutputSchema,
    IntentParser,
    IntentOrchestrator,
    IntentExecutor
)
from langchain_openai import ChatOpenAI

# 1. 初始化组件
registry = IntentRegistry()
llm = ChatOpenAI(model="gpt-4o")
parser = IntentParser(llm, registry)
orchestrator = IntentOrchestrator(registry)
executor = IntentExecutor(registry)

# 2. 定义意图
def my_task_executor(**kwargs):
    return {"result": f"执行任务，参数: {kwargs}"}

intent = IntentDefinition(
    metadata=IntentMetadata(
        id="my_task",
        name="我的任务",
        description="执行一个自定义任务"
    ),
    schema=InputOutputSchema(),
    executor=my_task_executor
)

registry.register(intent)

# 3. 解析用户输入
parse_result = parser.parse("帮我执行那个任务")

# 4. 编排执行计划
plan = orchestrator.orchestrate(parse_result)

# 5. 执行
async def main():
    results = await executor.execute_plan_async(plan, "session_001")
    print(results)

asyncio.run(main())
```

### 工作流使用

```python
from intent_system.workflow import WorkflowIntentManager

# 初始化管理器
manager = WorkflowIntentManager()

# 从 JSON 加载工作流定义
manager.load_from_json("workflow_intents.json")

# 识别意图并获取建议
result = manager.get_workflow_suggestion("我想学习Python开发")
print(f"识别意图: {result['current_intent_name']}")
print(f"进入指导: {result['entry_guidance']}")
print(f"后续流程: {result['next_str']}")
```

### JSON 格式工作流定义

```json
{
  "version": "1.0.0",
  "description": "软件开发生命周期",
  "intents": [
    {
      "id": "study",
      "name": "学习",
      "description": "学习新技术",
      "category": "workflow",
      "pre_intents": [],
      "post_intents": ["develop"],
      "guidance": {
        "entry": "开始学习！",
        "completion": "学习完成！",
        "next_actions": ["开始开发"]
      }
    }
  ]
}
```

## 模块结构

```
intent_system/
├── core/              # 核心模块
│   ├── intent_definition.py   # 意图定义
│   ├── intent_registry.py     # 意图注册表
│   ├── intent_parser.py       # 意图解析器
│   └── state.py               # 状态管理
├── orchestration/     # 编排模块
│   └── orchestrator.py        # 意图编排器
├── execution/         # 执行模块
│   ├── intent_executor.py     # 意图执行器
│   └── execution_tracker.py   # 执行追踪
├── data_flow/         # 数据流转
│   └── data_flow_engine.py    # 数据流转引擎
├── workflow/          # 工作流模块
│   ├── workflow_intent.py      # 工作流意图定义
│   ├── workflow_manager.py     # 工作流管理器
│   └── json_loader.py          # JSON 加载器
└── builtin_intents/   # 内置意图
    └── data_intents.py         # 数据类意图
```

## 依赖项

```
pydantic>=2.0.0
langchain>=0.2.0
langchain-core>=0.2.0
langchain-openai>=0.1.0
langchain-anthropic>=0.1.0
python-dotenv>=1.0.0
```

## 常见问题

### Q: 导入时报错找不到模块？

A: 确保已正确安装包：
```bash
pip install -e /path/to/tagent
```

### Q: 如何在不同项目中使用？

A: 有两种方式：

1. **作为包安装**（推荐）：
```bash
# 在 tagent 目录
pip install -e .

# 在其他项目中直接导入
from intent_system import IntentRegistry
```

2. **复制目录**：
```bash
# 复制 intent_system 目录到你的项目
cp -r /path/to/tagent/intent_system /path/to/your/project/

# 在代码中添加路径
import sys
sys.path.insert(0, '/path/to/your/project')
from intent_system import IntentRegistry
```

### Q: 如何在虚拟环境中使用？

A:
```bash
# 创建虚拟环境
python -m venv myenv
source myenv/bin/activate  # Linux/Mac
# 或 myenv\Scripts\activate  # Windows

# 安装
cd /path/to/tagent
pip install -e .

# 在其他项目中使用
```

## 完整示例

参考项目中的示例文件：
- `examples/workflow_with_agent.py` - 完整的工作流与 Agent 集成示例
- `examples/intent_basic_usage.py` - 基础意图使用示例

## 更多信息

- GitHub: https://github.com/yutoutang/tagent
- 完整文档: https://github.com/yutoutang/tagent/blob/main/README.md
