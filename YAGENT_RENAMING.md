# YAgent 重命名说明

## 概述

`UnifiedAgent` 已正式重命名为 `YAgent`。这是一个更简洁、更易记的名称。

## 重命名映射

| 旧名称 | 新名称 |
|--------|--------|
| `UnifiedAgent` | `YAgent` |
| `UnifiedAgentState` | `YAgentState` |
| `create_unified_agent_graph()` | `create_yagent_graph()` |
| `intent_system/agent/` | `intent_system/yagent/` |

## 导入方式

### 新方式（推荐）

```python
from intent_system import YAgent

agent = YAgent()
result = agent.run("你的问题")
```

### 旧方式（仍然可用，向后兼容）

```python
from intent_system.agent import UnifiedAgent

agent = UnifiedAgent()
result = agent.run("你的问题")
```

## 更新的文件

### 核心文件
- `intent_system/yagent/__init__.py` - 新的 yagent 模块入口
- `intent_system/yagent/state.py` - YAgentState 定义
- `intent_system/yagent/nodes.py` - LangGraph 节点
- `intent_system/yagent/graph.py` - 图构建函数
- `intent_system/yagent/agent.py` - YAgent 类

### 导出更新
- `intent_system/__init__.py` - 现在导出 YAgent 而非 UnifiedAgent

### 测试文件
- `test_yagent_rename.py` - 验证重命名的测试脚本
- `test_unified_agent.py` - 仍然可用（使用旧名称）
- `test_sdlc_intents.py` - 无需更改（使用底层组件）

### 示例文件
- `examples/unified_agent_demo.py` - 已更新使用 YAgent
- `examples/sdlc_workflow_unified_agent.py` - 已更新使用 YAgent

## 文档更新

以下文档需要更新：

- [x] `REFACTORING_SUMMARY.md` - 需要更新为 YAgent
- [x] `SDLC_WORKFLOW_SUMMARY.md` - 需要更新为 YAgent
- [x] `CLAUDE.md` - 需要更新为 YAgent

## 向后兼容性

旧的 `agent` 模块和 `UnifiedAgent` 类仍然保留，确保现有代码不会中断。我们建议新项目使用 `YAgent`，但现有代码可以继续使用 `UnifiedAgent`。

```python
# 这两种方式都有效：
from intent_system import YAgent          # 新方式
from intent_system.agent import UnifiedAgent  # 旧方式

# 功能完全相同
```

## 迁移指南

### 1. 更新导入

```python
# 之前
from intent_system import UnifiedAgent, UnifiedAgentState

# 之后
from intent_system import YAgent, YAgentState
```

### 2. 更新类名

```python
# 之前
agent = UnifiedAgent()

# 之后
agent = YAgent()
```

### 3. 更新类型注解

```python
# 之前
def process_agent(agent: UnifiedAgent) -> None:
    pass

# 之后
def process_agent(agent: YAgent) -> None:
    pass
```

## 功能一致性

`YAgent` 和 `UnifiedAgent` 在功能上完全相同，只是名称不同。所有方法、属性和特性都保持不变：

- ✅ 意图识别和编排
- ✅ 反思机制
- ✅ 并行执行
- ✅ 数据流转
- ✅ 会话持久化
- ✅ 流式执行
- ✅ 自定义意图注册

## 测试验证

运行验证测试：

```bash
python test_yagent_rename.py
```

输出应该显示：

```
所有验证通过!

总结:
  - UnifiedAgent 已重命名为 YAgent
  - UnifiedAgentState 已重命名为 YAgentState
  - create_unified_agent_graph 已重命名为 create_yagent_graph
  - 可以通过 'from intent_system import YAgent' 导入
  - 旧的 agent 模块保留用于向后兼容
```

## 常见问题

### Q: 我现有的代码需要修改吗？
**A**: 不需要。旧的导入方式仍然可用。但建议新代码使用 `YAgent`。

### Q: YAgent 是什么意思？
**A**: "Y" 可以代表：
- **Y**our Agent（我们的 Agent）
- **Y**our（你的）Agent
- 或任何你喜欢的含义

### Q: 旧文档还有效吗？
**A**: 有效，但建议将 `UnifiedAgent` 替换为 `YAgent`。

## 未来计划

1. 在下一个主要版本中，可能会弃用 `UnifiedAgent`
2. 逐步将所有文档更新为使用 `YAgent`
3. 添加更多 `YAgent` 特有的功能

## 感谢

感谢所有使用和贡献这个项目的开发者！希望 `YAgent` 这个更简洁的名字能让您的开发体验更加愉快。
