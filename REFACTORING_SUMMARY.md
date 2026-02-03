# intent_system 模块重构说明

## 概述

本次重构将 `dynamic_agent_framework.py` 和 `intent_system_integration.py` 与 `intent_system` 模块的核心功能融合，创建了一个统一的 Agent 框架。

## 新架构

### 目录结构

```
intent_system/
├── agent/                    # 新增：统一 Agent 模块
│   ├── __init__.py
│   ├── state.py             # 统一状态定义
│   ├── nodes.py             # 所有 LangGraph 节点
│   ├── graph.py             # LangGraph 构建器
│   └── agent.py             # UnifiedAgent 类
├── core/                     # 原有核心模块
├── orchestration/           # 原有编排模块
├── execution/               # 原有执行模块
├── data_flow/               # 原有数据流模块
└── ...
```

### 核心组件

#### 1. UnifiedAgentState (state.py)

融合了原有的 `AgentState` 和 `EnhancedAgentState`：
- 消息历史
- 任务分类
- 意图识别
- 编排计划
- 执行结果
- 反思结果
- 执行追踪

#### 2. 节点系统 (nodes.py)

包含 5 个核心节点：

```python
START -> Intent Parse -> Orchestrate -> Execute -> Reflect -> Synthesize -> END
                              ↓                ↓
                          (无意图)        (迭代循环)
```

- **intent_parse_node**: 使用 LLM 识别用户意图
- **intent_orchestrate_node**: 构建 DAG 执行计划
- **intent_execute_node**: 按层并行执行意图
- **reflect_node**: 反思评估，决定是否继续
- **synthesize_node**: 综合生成最终回答

#### 3. 图构建 (graph.py)

使用 LangGraph 构建完整的工作流：
- 条件路由决策
- 会话持久化支持（MemorySaver）
- 组件注入（LLM, Registry, Orchestrator, Executor）

#### 4. UnifiedAgent 类 (agent.py)

提供简洁的接口：
```python
# 基本使用
agent = UnifiedAgent()
result = agent.run("计算 25 * 4")

# 简单聊天
response = agent.chat("你好")

# 异步执行
result = await agent.arun("搜索信息")

# 流式执行
for event in agent.stream("分析数据"):
    print(event)

# 注册自定义意图
agent.register_intent(custom_intent)
```

## 关键特性

### 1. 反思机制

反思节点会：
- 评估执行结果质量
- 检查是否有错误
- 决定是否需要重新执行
- 提供改进建议

```python
# 设置最大迭代次数
agent = UnifiedAgent(max_iterations=3)
result = agent.run("复杂任务")
```

### 2. 意图编排

- 自动构建 DAG
- 拓扑排序确定执行顺序
- 识别可并行执行的意图
- 按层执行以提高效率

### 3. 数据流转

- n8n 风格的表达式 (`{{ $json.field }}`)
- 意图间数据传递
- 上下文管理

### 4. 会话持久化

```python
# 使用相同 session_id 保持上下文
agent.run("我的名字是 Alice", session_id="user_123")
agent.run("我叫什么名字？", session_id="user_123")  # 会记住
```

## 使用方式

### 快速开始

```python
from intent_system import UnifiedAgent

# 创建 Agent
agent = UnifiedAgent()

# 运行
result = agent.run("你的问题")
print(result['result'])
```

### 自定义意图

```python
from intent_system.core import IntentDefinition, IntentMetadata, InputOutputSchema
from langchain_core.tools import tool

@tool
async def my_tool(param: str) -> str:
    """自定义工具"""
    return f"处理结果: {param}"

intent = IntentDefinition(
    metadata=IntentMetadata(
        id="my_intent",
        name="我的意图",
        description="功能描述",
        category="transform"
    ),
    schema=InputOutputSchema(
        inputs={"param": {"type": "string", "required": True}},
        outputs={"result": {"type": "string"}}
    ),
    executor=my_tool.func
)

agent = UnifiedAgent()
agent.register_intent(intent)
```

## 测试

运行测试套件：

```bash
python test_unified_agent.py
```

测试覆盖：
- 基本运行功能
- 简单聊天接口
- 多意图识别和执行
- 反思机制
- 流式执行
- 异步执行
- 自定义意图注册
- 会话持久化
- 错误处理
- 最大迭代次数限制
- 图描述

## 示例

查看完整示例：

```bash
python examples/unified_agent_demo.py
```

## 与原有代码的对比

### dynamic_agent_framework.py

**原有方式：**
```python
from dynamic_agent_framework import DynamicAgent
agent = DynamicAgent()
result = agent.run("查询")
```

**新方式：**
```python
from intent_system import UnifiedAgent
agent = UnifiedAgent()
result = agent.run("查询")
```

### intent_system_integration.py

**原有方式：**
```python
from intent_system_integration import IntentEnhancedAgent
agent = IntentEnhancedAgent()
result = agent.run_with_intents("查询", use_intents=True)
```

**新方式：**
```python
from intent_system import UnifiedAgent
agent = UnifiedAgent()
result = agent.run("查询")  # 意图系统已集成
```

## 迁移指南

### 1. 替换导入

```python
# 旧
from dynamic_agent_framework import DynamicAgent
from intent_system_integration import IntentEnhancedAgent

# 新
from intent_system import UnifiedAgent
```

### 2. 创建实例

```python
# 旧
agent = DynamicAgent()
agent = IntentEnhancedAgent()

# 新
agent = UnifiedAgent()
```

### 3. 运行 Agent

```python
# 旧
result = agent.run("查询")
result = agent.run_with_intents("查询", use_intents=True)

# 新
result = agent.run("查询")  # 自动使用意图系统
```

### 4. 注册工具/意图

```python
# 旧
agent.register_tool(name, tool_func, metadata)

# 新
from intent_system.core import IntentDefinition, ...
agent.register_intent(intent_definition)
```

## 环境变量

```
OPENAI_API_KEY=your-key-here
# 或
ANTHROPIC_API_KEY=your-key-here

LLM_PROVIDER=openai  # 或 anthropic
MODEL_NAME=gpt-4o    # 或 claude-3-5-sonnet-20241022
```

## 注意事项

1. **向后兼容**: 原有的 `dynamic_agent_framework.py` 和 `intent_system_integration.py` 仍然可用，但建议迁移到新的 `UnifiedAgent`

2. **API Key**: 确保设置了 `OPENAI_API_KEY` 或 `ANTHROPIC_API_KEY`

3. **异步支持**: 新框架完全支持异步操作

4. **反思机制**: 默认最大迭代次数为 3，可根据需要调整

## 未来计划

- [ ] 添加更多内置意图
- [ ] 支持自定义反思策略
- [ ] 添加执行结果可视化
- [ ] 支持分布式执行
- [ ] 添加性能监控和日志
