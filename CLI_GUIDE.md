# CLI Demo 使用指南

## 快速启动

直接运行 CLI demo：

```bash
python cli_demo.py
```

## 界面预览

```
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║        Intent System - 智能意图管理系统                  ║
║        Interactive CLI v1.0                              ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

基于 LangGraph 的智能意图识别与编排框架
支持 OpenAI / Anthropic / DeepSeek API

可用命令:
  help      - 显示帮助信息
  clear     - 清空屏幕
  history   - 显示对话历史
  session   - 开始新会话
  info      - 显示系统信息
  exit      或 quit - 退出程序

正在初始化 Intent System...
✓ 新会话已创建 (ID: 00158a92)
✓ Intent System 初始化成功

You>
```

## 使用示例

### 1. 数学计算

```
You> 帮我计算 25 * 4 + 10

正在处理...

✓ 执行成功

🎯 检测到的意图: calculator
📊 意图置信度: 95.00%

结果:
──────────────────────────────────────────────────────────────
计算结果: 110
──────────────────────────────────────────────────────────────
```

### 2. 文本处理

```
You> 将以下文本转换为大写：hello world

正在处理...

✓ 执行成功

🎯 检测到的意图: text_processing
📊 意图置信度: 88.50%

结果:
──────────────────────────────────────────────────────────────
HELLO WORLD
──────────────────────────────────────────────────────────────
```

### 3. 多轮对话

```
You> 计算 100 除以 5
... 执行并显示结果 ...

You> 再把结果乘以 3
... 基于上一次结果继续计算 ...
```

### 4. 查看历史

```
You> history

=== 对话历史 (3 条) ===

[1] 用户: 计算 100 除以 5
    状态: 成功
    意图: calculator
    结果: 计算结果: 20.0

[2] 用户: 再把结果乘以 3
    状态: 成功
    意图: calculator
    结果: 计算结果: 60.0

[3] 用户: 帮我计算 25 * 4 + 10
    状态: 成功
    意图: calculator
    结果: 计算结果: 110
```

## 内置意图

| 意图 | 功能 | 示例 |
|-----|------|------|
| `calculator` | 数学计算 | "计算 25 * 4" |
| `text_processing` | 文本处理 | "转换为大写" |
| `data_analysis` | 数据分析 | "分析数据" |
| `web_search` | 网络搜索 | "搜索 Python 教程" |
| `http_request` | HTTP 请求 | "GET 请求到 api.example.com" |
| `file_read` | 文件读取 | "读取 README.md" |

## 高级功能

### 自定义配置

编辑 `.env` 文件：

```env
# 使用 DeepSeek
OPENAI_API_KEY=sk-your-deepseek-key
BASE_URL=https://api.deepseek.com
MODEL_NAME=deepseek-chat

# 或使用 OpenAI
OPENAI_API_KEY=sk-your-openai-key
MODEL_NAME=gpt-4o

# 或使用 Anthropic
ANTHROPIC_API_KEY=sk-your-anthropic-key
LLM_PROVIDER=anthropic
MODEL_NAME=claude-3-5-sonnet-20241022
```

### 会话管理

```
You> session
✓ 新会话已创建 (ID: a1b2c3d4)
```

### 查看系统信息

```
You> info

=== 系统信息 ===

LLM 配置:
  提供商: openai
  模型: deepseek-chat

会话信息:
  会话ID: a1b2c3d4
  历史记录: 5 条

系统状态:
  Agent: 已初始化
  运行中: True
```

## 开发说明

### 添加自定义意图

```python
from intent_system import YAgent, IntentDefinition, IntentMetadata, InputOutputSchema

async def my_tool(param: str) -> str:
    """自定义工具"""
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

# 在 CLI 中使用
agent = YAgent()
agent.register_intent(intent)
```

## 故障排除

### 1. API Key 错误

```
✗ 初始化失败: Incorrect API key provided
```

**解决方案**：检查 `.env` 文件中的 API Key 是否正确

### 2. 网络连接问题

```
✗ 执行出错: Connection error
```

**解决方案**：检查网络连接和代理设置

### 3. 意图识别失败

```
✗ 执行失败: 无法识别意图
```

**解决方案**：
- 确保描述清晰明确
- 使用内置意图的触发词
- 查看帮助了解可用意图

## 退出程序

```
You> exit

再见！
```

或按 `Ctrl+C` 中断，然后输入 `exit` 退出。
