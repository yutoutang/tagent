# Bug 修复记录

## 修复 1: CLI 异步调用问题

**错误信息**:
```
No synchronous function provided to "execute".
Either initialize with a synchronous function or invoke via the async API
```

**根本原因**:
- `intent_execute_node` 是异步函数
- CLI 使用同步的 `run()` 方法调用

**解决方案**:
- 修改 `cli_demo.py` 的 `process_query` 为异步函数
- 使用 `asyncio.run()` 包装异步调用

**文件**: `cli_demo.py`, `intent_system/yagent/agent.py`

---

## 修复 2: primary_intent=None 验证错误

**错误信息**:
```
1 validation error for IntentParseResult
primary_intent
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
```

**根本原因**:
- LLM 有时返回 `primary_intent: None`
- `IntentParseResult` 要求 `primary_intent` 必须是非空字符串
- 数据清洗函数未处理此情况

**解决方案**:
扩展 `_sanitize_result_dict` 函数，添加：

```python
# 处理 primary_intent: 如果为 None 或空，设置默认值
if 'primary_intent' not in result_dict or result_dict['primary_intent'] is None:
    # 获取第一个可用意图作为默认
    all_intents = self.registry.list_all()
    if all_intents:
        result_dict['primary_intent'] = all_intents[0].metadata.id
    else:
        result_dict['primary_intent'] = 'unknown'

# 处理 reasoning: 如果为 None，提供默认说明
if 'reasoning' not in result_dict or result_dict['reasoning'] is None:
    result_dict['reasoning'] = 'LLM 未提供详细说明'
```

**文件**: `intent_system/core/intent_parser.py`

**测试验证**:
```python
# 测试数据
{
    'primary_intent': None,
    'reasoning': None,
    'confidence': '0.8',
    'sub_intents': {},
    'parameters': [],
    'dependencies': {}
}

# 清洗后
{
    'primary_intent': 'calculator'  # 使用默认意图
    'reasoning': 'LLM 未提供详细说明'  # 提供默认说明
    'confidence': 0.8  # 转为 float
    'sub_intents': []  # 转为 list
    'parameters': {}  # 转为 dict
    'dependencies': []  # 转为 list
}
```

---

## 数据清洗策略

`_sanitize_result_dict` 函数现在处理所有可能的 LLM 输出格式问题：

| 字段 | 问题输入 | 清洗后 | 策略 |
|-----|---------|-------|------|
| `primary_intent` | `None` | 默认意图或 `'unknown'` | 使用注册表中的第一个意图 |
| `reasoning` | `None` | `'LLM 未提供详细说明'` | 提供默认说明 |
| `confidence` | `'0.8'` / `0` | `0.8` / `0.5` | 转为 float，失败时默认 0.5 |
| `sub_intents` | `{}` | `[]` | 空 dict → 空 list |
| `parameters` | `[]` | `{}` | 空 list → 空 dict |
| `dependencies` | `{}` | `[]` | 空 dict → 空 list |

---

## 提交记录

- **a8c1c98**: fix: 修复 primary_intent=None 导致的验证错误
- **4d4cea2**: fix: 修复 CLI 异步调用问题并优化错误处理

---

## 使用说明

现在可以正常运行 CLI：

```bash
python cli_demo.py
```

即使 LLM 返回格式不完全正确，框架也能自动处理并继续运行。

**注意**: 意图识别准确性仍取决于 LLM 的输出质量，建议：
1. 使用高质量的 LLM（如 GPT-4、Claude 3.5）
2. 提供清晰的意图描述
3. 在提示中明确要求返回特定格式
