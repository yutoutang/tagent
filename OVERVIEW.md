# 项目概览

## 📁 项目结构

```
agent-f/
│
├── 📄 dynamic_agent_framework.py   # 🔧 核心框架 - 动态 Agent 调用框架主文件
│                                    #   - 任务分类系统
│                                    #   - 工具注册表
│                                    #   - Agent 节点定义
│                                    #   - 计算图构建
│                                    #   - DynamicAgent 类
│
├── 🧪 test_agent.py                 # 测试套件 - 完整的测试用例
│                                    #   - 基本功能测试
│                                    #   - 自定义工具测试
│                                    #   - 多轮对话测试
│                                    #   - 流式输出测试
│                                    #   - 错误处理测试
│
├── 🚀 advanced_examples.py          # 高级示例 - 实战案例
│                                    #   - 复杂工作流
│                                    #   - 流式处理
│                                    #   - 多轮对话
│                                    #   - 批量处理
│                                    #   - 自定义路由
│                                    #   - 工具链组合
│
├── 📊 visualize_graph.py            # 可视化工具 - 计算图结构展示
│                                    #   - 图结构可视化
│                                    #   - 状态流转示例
│                                    #   - 工具注册表说明
│                                    #   - 执行模式展示
│
├── 🎯 quickstart.py                 # 快速启动 - 交互式启动脚本
│                                    #   - 环境检查
│                                    #   - 菜单系统
│                                    #   - 交互式对话
│                                    #   - 一键运行各种示例
│
├── 📋 README.md                     # 项目文档 - 完整的使用说明
│                                    #   - 快速开始指南
│                                    #   - 架构设计
│                                    #   - API 文档
│                                    #   - 最佳实践
│
├── 📦 requirements.txt              # Python 依赖包列表
│
├── ⚙️  tools_config.json            # 工具配置文件
│                                    #   - 工具定义
│                                    #   - 任务类型映射
│                                    #   - 工具组配置
│
├── 🔧 .env.example                  # 环境变量示例
│
└── 🚫 .gitignore                    # Git 忽略规则
```

## 🎯 核心功能

### 1. 动态任务识别
- 使用 LLM 智能分类任务类型
- 支持多种任务类型（编程、研究、分析、计算等）
- 置信度评估

### 2. 工具注册系统
- 灵活的工具注册与管理
- 按任务类型自动加载工具
- 支持自定义工具

### 3. 多阶段执行流程
```
Classify → Plan → Execute → Reflect → Synthesize
           ↑                    ↑
           └────────────────────┘
              (迭代优化)
```

### 4. 状态管理
- 基于 LangGraph 的状态管理
- 支持多轮对话
- 会话持久化

### 5. 错误处理
- 完善的错误捕获
- 自动重试机制
- 优雅降级

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置环境
```bash
cp .env.example .env
# 编辑 .env 文件，填入 API Key
```

### 3. 运行示例
```bash
# 方式 1: 使用快速启动脚本
python quickstart.py

# 方式 2: 直接运行主文件
python dynamic_agent_framework.py

# 方式 3: 运行测试
python test_agent.py

# 方式 4: 查看高级示例
python advanced_examples.py
```

## 📊 计算图架构

```
┌─────────────┐
│   START     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Classify   │ ← 任务识别
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    Plan     │ ← 制定计划
└──────┬──────┘
       │
       ▼
   ┌────────┐
   │ Decide │ ← 路由决策
   └───┬────┘
       │
┌──────┴──────┐
│             │
▼             ▼
Execute    Synthesize
│             │
▼            │
Reflect ──────┘
│
▼
END
```

## 🛠️ 内置工具

| 工具名 | 功能 | 任务类型 |
|--------|------|----------|
| code_analyzer | 代码分析 | coding, analysis |
| web_searcher | 网络搜索 | research, general |
| data_calculator | 数学计算 | calculation, analysis |
| document_summarizer | 文档总结 | research, analysis |
| api_client | API 调用 | coding, general |

## 💡 使用示例

### 基础使用
```python
from dynamic_agent_framework import DynamicAgent

agent = DynamicAgent()
result = agent.chat("计算 25 * 4")
print(result)
```

### 自定义工具
```python
from langchain_core.tools import tool

@tool
def my_tool(param: str) -> str:
    """自定义工具"""
    return f"结果: {param}"

agent = DynamicAgent()
agent.register_tool("my_tool", my_tool, {
    "task_types": ["coding"],
    "description": "我的工具"
})
```

### 流式输出
```python
import asyncio

async for event in agent.astream("搜索资料"):
    print(event)
```

## 📚 文件说明

| 文件 | 行数 | 说明 |
|------|------|------|
| dynamic_agent_framework.py | ~600 | 核心框架实现 |
| test_agent.py | ~300 | 测试套件 |
| advanced_examples.py | ~400 | 高级示例 |
| visualize_graph.py | ~200 | 可视化工具 |
| quickstart.py | ~150 | 快速启动脚本 |
| README.md | ~500 | 完整文档 |

## 🔑 关键类和函数

### ToolRegistry
```python
# 工具注册表
tool_registry.register(name, tool_func, metadata)
tool_registry.get(name)
tool_registry.get_by_task_type(task_type)
tool_registry.list_tools()
```

### DynamicAgent
```python
# Agent 类
agent = DynamicAgent(config)
agent.run(message, session_id)
agent.chat(message, session_id)
async agent.astream(message, session_id)
agent.register_tool(name, tool_func, metadata)
agent.list_tools()
```

### AgentState
```python
# 状态定义
class AgentState(TypedDict):
    messages: List[BaseMessage]
    task_type: Optional[str]
    available_tools: List[Dict]
    executed_tools: List[str]
    result: Optional[str]
    intermediate_steps: List[Dict]
    iteration: int
    max_iterations: int
    is_complete: bool
    errors: List[str]
    metadata: Dict[str, Any]
```

## 🎓 学习路径

1. **初学者** → `quickstart.py` → 交互式体验
2. **开发者** → `README.md` → 完整文档
3. **进阶** → `advanced_examples.py` → 实战案例
4. **深度理解** → `dynamic_agent_framework.py` → 源码
5. **测试** → `test_agent.py` → 验证功能

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 📝 许可证

MIT License

---

**作者**: Claude Code
**版本**: 1.0.0
**更新日期**: 2026-02-03
