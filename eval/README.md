# Eval 评测框架

一个灵活的 LLM Agent 评测框架，支持 YAML 配置、HTTP 提示词接口和多种评测指标。

## 功能特性

- **YAML 配置文件**：支持通过 YAML 文件配置所有评测参数
- **环境变量替换**：支持 `${ENV_VAR}` 语法在配置中使用环境变量
- **HTTP 提示词接口**：支持从 HTTP 端点获取提示词模板
- **多 LLM 提供商**：支持 OpenAI、Anthropic 和自定义兼容端点
- **灵活的指标系统**：内置准确率指标，支持自定义指标
- **同步/异步执行**：支持并行评测
- **数据集管理**：JSON 格式的评测数据集

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 创建配置文件

```yaml
# my_eval.yaml
name: "my_evaluation"
description: "我的评测任务"

llm:
  api_key: "${OPENAI_API_KEY}"  # 或使用 sk: "${OPENAI_API_KEY}"
  model_name: "gpt-4o"
  base_url: null  # 可选：自定义端点
  temperature: 0.0

prompt:
  prompt_template: "分析以下文本: {input}"
  cache_enabled: true

metrics:
  - name: "accuracy"
    type: "accuracy"
    weight: 1.0
    threshold: 0.8
    params:
      metric_name: "exact_match"

dataset_path: "eval/data/evaluation_dataset.json"
parallel: false
```

### 3. 创建数据集

```json
{
  "name": "my_dataset",
  "items": [
    {
      "input": "问题文本",
      "expected": "期望答案"
    }
  ]
}
```

### 4. 运行评测

```python
from eval import evaluate_from_config

results = evaluate_from_config("my_eval.yaml")

for result in results:
    print(f"Score: {result.overall_score:.2f}")
    print(f"Output: {result.output}")
```

## 配置说明

### LLM 配置

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `api_key` / `sk` | string | 是 | API 密钥（支持两种字段名） |
| `model_name` | string | 是 | 模型名称 |
| `base_url` | string | 否 | 自定义 API 端点 |
| `provider` | string | 否 | 提供商 (openai/anthropic/custom) |
| `temperature` | float | 否 | 温度参数 (0-2) |
| `max_tokens` | int | 否 | 最大输出 token 数 |
| `timeout` | int | 否 | 请求超时时间（秒） |

### 提示词配置

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `prompt_url` | string | 否 | HTTP 提示词接口 URL |
| `prompt_template` | string | 否 | 内联提示词模板 |
| `prompt_headers` | dict | 否 | HTTP 请求头 |
| `cache_enabled` | bool | 否 | 是否缓存提示词 |

### 指标配置

内置指标：
- `exact_match`：精确匹配
- `contains_keyword`：关键词包含

## 自定义指标

```python
from eval.core.metrics.base import BaseMetric, MetricResult
from eval.core.registry import register_metric

@register_metric("my_metric")
class MyCustomMetric(BaseMetric):
    def compute(self, output, expected=None, **kwargs):
        # 计算逻辑
        score = self._calculate_score(output, expected)
        return MetricResult(
            name="my_metric",
            score=score,
            passed=score >= self.threshold
        )
```

## 测试

运行组件测试：

```bash
python eval/examples/test_framework.py
```

## 目录结构

```
eval/
├── core/           # 核心组件（配置、模型、评估器接口）
├── llm/            # LLM 客户端和提示词提供器
├── metrics/         # 评测指标
├── datasets/        # 数据集管理
├── execution/       # 执行引擎
├── config/          # 配置文件
├── examples/        # 使用示例
└── data/           # 示例数据集
```

## 示例

- `eval/config/default.yaml` - 默认配置模板
- `eval/config/examples/basic_eval.yaml` - 基础评测示例
- `eval/config/examples/custom_eval.yaml` - 使用 HTTP 提示词的示例
- `eval/examples/basic_evaluation.py` - 基础使用示例
- `eval/examples/custom_metrics.py` - 自定义指标示例
