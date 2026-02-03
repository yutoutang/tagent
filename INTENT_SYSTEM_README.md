# 意图注册与加载系统 - 使用指南

## 概述

这是一套参考 Dify 和 n8n 设计理念的意图注册与加载系统，基于 LangGraph 框架实现。

### 核心特性

1. **意图注册系统** - 模块化的意图定义与注册
2. **多意图识别** - 使用 LLM 智能识别用户输入中的多个意图
3. **动态编排** - 自动解析依赖关系，优化执行顺序
4. **并行执行** - 识别可并行执行的意图，提升效率
5. **数据流转** - n8n 风格的表达式，支持意图间数据传递
6. **执行追踪** - 完整的执行日志和调试信息

---

## 快速开始

### 1. 基本使用

```python
import asyncio
from intent_system.core import IntentRegistry
from intent_system.core.intent_parser import IntentParser
from intent_system.orchestration import IntentOrchestrator
from intent_system.execution import IntentExecutor
from intent_system.builtin_intents import register_builtin_data_intents
from dynamic_agent_framework import create_llm
from dotenv import load_dotenv

async def main():
    load_dotenv()

    # 初始化
    registry = IntentRegistry()
    llm = create_llm()

    # 注册内置意图
    register_builtin_data_intents(registry)

    # 创建组件
    parser = IntentParser(llm, registry)
    orchestrator = IntentOrchestrator(registry)
    executor = IntentExecutor(registry)

    # 解析用户输入
    result = parser.parse("帮我计算 25 * 4")
    print(f"识别意图: {result.primary_intent}")

    # 编排执行计划
    plan = orchestrator.orchestrate(result)
    print(f"执行层数: {len(plan.execution_layers)}")

    # 执行
    results = await executor.execute_plan_async(plan)
    print(f"执行结果: {results}")

asyncio.run(main())
```

### 2. 运行示例

```bash
# 基本用法示例
python examples/intent_basic_usage.py

# 自定义意图示例
python examples/custom_intent.py

# 集成示例
python intent_system_integration.py
```

---

## 核心概念

### 1. 意图定义

意图是系统中的基本执行单元，包含：

```python
from intent_system.core import IntentDefinition, IntentMetadata, InputOutputSchema
from langchain_core.tools import tool

@tool
async def my_function(param1: str, param2: int = 10) -> dict:
    """功能描述"""
    return {"result": "done"}

intent = IntentDefinition(
    metadata=IntentMetadata(
        id="my_intent",                    # 唯一标识
        name="我的意图",                    # 显示名称
        description="功能描述",              # 描述
        category="data",                    # 类别
        tags=["api", "external"],           # 标签
        priority=10,                        # 优先级
        timeout=30,                         # 超时时间
        dependencies=[]                     # 依赖
    ),
    schema=InputOutputSchema(
        inputs={                            # 输入参数定义
            "param1": {
                "type": "string",
                "description": "参数1",
                "required": True
            },
            "param2": {
                "type": "integer",
                "default": 10
            }
        },
        outputs={                           # 输出定义
            "result": {"type": "object"}
        }
    ),
    executor=my_function.func               # 执行函数
)
```

### 2. 意图解析

使用 LLM 智能识别用户意图：

```python
parser = IntentParser(llm, registry)

# 单意图
result = parser.parse("计算 25 * 4")
# result.primary_intent = "calculator"
# result.parameters = {"expression": "25 * 4"}

# 多意图
result = parser.parse("计算 25 * 4，然后搜索 Python")
# result.primary_intent = "calculator"
# result.sub_intents = [{"id": "web_search", ...}]
```

### 3. 意图编排

自动识别依赖关系并分层：

```python
orchestrator = IntentOrchestrator(registry)
plan = orchestrator.orchestrate(parse_result)

# plan.execution_layers: 每层的意图可并行执行
# [
#   ["calculator", "web_search"],  # 第一层：并行
#   ["data_analysis"]               # 第二层：依赖第一层
# ]
```

### 4. 数据流转

使用 n8n 风格的表达式：

```python
from intent_system.data_flow import DataFlowEngine

data_flow = DataFlowEngine()

# 引用前一步的输出
mapping = {
    "temperature": "{{ $json.temperature }}",
    "city": "{{ $json.city }}"
}

resolved = data_flow.resolve_mapping(mapping, previous_results)
```

---

## 内置意图

系统提供以下内置意图：

| 意图ID | 名称 | 类别 | 功能 |
|--------|------|------|------|
| `http_request` | HTTP 请求 | data | 发送 HTTP 请求 |
| `calculator` | 计算器 | transform | 计算数学表达式 |
| `web_search` | 网络搜索 | data | 搜索网络信息 |
| `data_analysis` | 数据分析 | transform | 分析数据统计 |
| `text_processing` | 文本处理 | transform | 处理文本 |
| `file_read` | 读取文件 | data | 读取文件内容 |

---

## 高级用法

### 1. 自定义意图

```python
from intent_system.core import IntentDefinition, IntentMetadata, InputOutputSchema
from langchain_core.tools import tool

@tool
async def weather_api(city: str) -> dict:
    """查询天气"""
    # 实际调用天气 API
    return {"city": city, "temp": 25, "condition": "晴朗"}

intent = IntentDefinition(
    metadata=IntentMetadata(
        id="weather",
        name="查询天气",
        description="获取城市天气信息",
        category="data",
        tags=["weather", "api"]
    ),
    schema=InputOutputSchema(
        inputs={
            "city": {"type": "string", "required": True}
        },
        outputs={"data": {"type": "object"}}
    ),
    executor=weather_api.func
)

registry.register(intent)
```

### 2. 意图依赖

```python
# 意图 B 依赖于意图 A
intent_b = IntentDefinition(
    metadata=IntentMetadata(
        id="intent_b",
        name="意图 B",
        dependencies=["intent_a"]  # B 依赖于 A
    ),
    ...
)
```

### 3. 并行执行

系统自动识别可并行的意图：

```python
# 用户输入
"同时计算 100/5、搜索 Python、处理文本"

# 系统识别为三个独立意图
plan.execution_layers = [
    ["calculator", "web_search", "text_processing"]  # 并行执行
]
```

### 4. 流式输出

```python
agent = IntentEnhancedAgent()

async for event in agent.astream_with_intents(
    "计算 25 * 4",
    use_intents=True
):
    if event["event"] == "layer_start":
        print(f"开始执行: {event['intents']}")
    elif event["event"] == "layer_complete":
        print(f"执行完成: {event['results']}")
```

---

## 与现有框架集成

### 方式 1: 使用 IntentEnhancedAgent

```python
from intent_system_integration import IntentEnhancedAgent

agent = IntentEnhancedAgent()

# 使用意图系统
result = agent.run_with_intents(
    "计算 25 * 4",
    use_intents=True
)

# 或使用原有方式
result = agent.run_with_intents(
    "计算 25 * 4",
    use_intents=False
)
```

### 方式 2: 直接集成到现有节点

```python
from dynamic_agent_framework import DynamicAgent

class MyAgent(DynamicAgent):
    def __init__(self):
        super().__init__()
        # 添加意图系统
        self.intent_registry = IntentRegistry()
        register_builtin_data_intents(self.intent_registry)

    def run(self, message: str, session_id: str = None):
        # 先尝试意图系统
        parser = IntentParser(self.llm, self.intent_registry)
        parse_result = parser.parse(message)

        if parse_result.confidence > 0.7:
            # 使用意图系统执行
            orchestrator = IntentOrchestrator(self.intent_registry)
            executor = IntentExecutor(self.intent_registry)
            plan = orchestrator.orchestrate(parse_result)
            return asyncio.run(executor.execute_plan_async(plan))

        # 降级到原有执行方式
        return super().run(message, session_id)
```

---

## 最佳实践

### 1. 意图粒度

保持意图单一职责：
- ✅ 好：`calculator` 只负责计算
- ❌ 差：`data_processor` 既计算又搜索又分析

### 2. 参数设计

清晰的参数定义：
```python
inputs={
    "expression": {              # 清晰的参数名
        "type": "string",
        "description": "数学表达式，如 '25 * 4'",
        "required": True,
        "pattern": r"^[\d\s+\-*/().]+$"  # 验证规则
    }
}
```

### 3. 错误处理

```python
@tool
async def my_tool(param: str) -> dict:
    try:
        result = process(param)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### 4. 依赖管理

明确声明依赖：
```python
metadata=IntentMetadata(
    dependencies=["step1", "step2"]  # 必须先执行 step1 和 step2
)
```

---

## 故障排除

### 问题 1: 意图识别失败

**原因**: LLM 无法识别意图

**解决**:
- 检查意图描述是否清晰
- 提供更多示例
- 调整系统提示

### 问题 2: 执行超时

**原因**: 意图执行时间过长

**解决**:
```python
metadata=IntentMetadata(
    timeout=60  # 增加超时时间
)
```

### 问题 3: 数据映射失败

**原因**: 表达式语法错误

**解决**:
```python
# 检查表达式语法
parser = ExpressionParser()
is_valid, error = parser.validate_expression("{{ $json.field }}")
```

---

## API 参考

详细的 API 文档请参考各模块的 docstring：

- `intent_system.core.intent_definition`
- `intent_system.core.intent_registry`
- `intent_system.core.intent_parser`
- `intent_system.orchestration.orchestrator`
- `intent_system.data_flow.data_flow_engine`
- `intent_system.execution.intent_executor`

---

## 许可证

MIT License

---

**版本**: 1.0.0
**更新日期**: 2026-02-03
