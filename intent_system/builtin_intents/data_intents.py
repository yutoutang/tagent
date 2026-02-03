"""
内置数据意图 - 常用的数据获取和转换意图
"""

from typing import Any, Dict
from langchain_core.tools import tool
from intent_system.core.intent_definition import IntentDefinition, IntentMetadata, InputOutputSchema
from intent_system.core.intent_registry import IntentRegistry


# ============================================================
# 内置工具函数
# ============================================================

@tool
async def builtin_http_request(url: str, method: str = "GET") -> Dict[str, Any]:
    """
    HTTP 请求工具

    Args:
        url: 请求URL
        method: HTTP方法 (GET/POST/PUT/DELETE)

    Returns:
        响应数据（模拟）
    """
    # 模拟 HTTP 请求
    return {
        "status": 200,
        "method": method,
        "url": url,
        "data": {
            "message": f"成功请求 {url}",
            "timestamp": "2024-01-01T00:00:00Z"
        }
    }


@tool
async def builtin_calculator(expression: str) -> float:
    """
    计算器工具 - 计算数学表达式

    Args:
        expression: 数学表达式，如 "25 * 4 + 10"

    Returns:
        计算结果
    """
    try:
        # 注意：生产环境应该使用更安全的表达式解析器
        result = eval(expression, {"__builtins__": {}}, {})
        return float(result)
    except Exception as e:
        raise ValueError(f"计算错误: {str(e)}")


@tool
async def builtin_web_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    网络搜索工具

    Args:
        query: 搜索查询
        max_results: 最大结果数

    Returns:
        搜索结果（模拟）
    """
    # 模拟搜索结果
    results = [
        {
            "title": f"关于 '{query}' 的搜索结果 {i+1}",
            "url": f"https://example.com/result{i+1}",
            "snippet": f"这是关于{query}的搜索结果摘要..."
        }
        for i in range(min(max_results, 3))
    ]

    return {
        "query": query,
        "total_results": len(results),
        "results": results
    }


@tool
async def builtin_data_analysis(data: Any, analysis_type: str = "summary") -> Dict[str, Any]:
    """
    数据分析工具

    Args:
        data: 待分析的数据
        analysis_type: 分析类型 (summary/stats/count)

    Returns:
        分析结果
    """
    if isinstance(data, list):
        count = len(data)
        return {
            "type": analysis_type,
            "count": count,
            "data_type": "list",
            "summary": f"列表包含 {count} 个元素"
        }
    elif isinstance(data, dict):
        keys = list(data.keys())
        return {
            "type": analysis_type,
            "keys": keys,
            "count": len(keys),
            "data_type": "dict",
            "summary": f"字典包含 {len(keys)} 个键"
        }
    elif isinstance(data, str):
        return {
            "type": analysis_type,
            "length": len(data),
            "data_type": "string",
            "summary": f"字符串包含 {len(data)} 个字符"
        }
    else:
        return {
            "type": analysis_type,
            "data_type": type(data).__name__,
            "value": str(data)
        }


@tool
async def builtin_text_processing(
    text: str,
    operation: str = "count"
) -> Dict[str, Any]:
    """
    文本处理工具

    Args:
        text: 待处理文本
        operation: 操作类型 (count/lower/upper/reverse)

    Returns:
        处理结果
    """
    if operation == "count":
        result = len(text)
        return {"operation": "count", "result": result}
    elif operation == "lower":
        result = text.lower()
        return {"operation": "lower", "result": result}
    elif operation == "upper":
        result = text.upper()
        return {"operation": "upper", "result": result}
    elif operation == "reverse":
        result = text[::-1]
        return {"operation": "reverse", "result": result}
    else:
        return {"error": f"未知操作: {operation}"}


# ============================================================
# 意图定义
# ============================================================

def get_http_request_intent() -> IntentDefinition:
    """获取 HTTP 请求意图"""
    return IntentDefinition(
        metadata=IntentMetadata(
            id="http_request",
            name="HTTP 请求",
            description="发送 HTTP 请求获取数据",
            category="data",
            tags=["http", "api", "network", "external"],
            priority=10,
            timeout=30
        ),
        schema=InputOutputSchema(
            inputs={
                "url": {
                    "type": "string",
                    "description": "请求URL",
                    "required": True
                },
                "method": {
                    "type": "string",
                    "description": "HTTP方法",
                    "default": "GET",
                    "enum": ["GET", "POST", "PUT", "DELETE"]
                }
            },
            outputs={
                "response": {
                    "type": "object",
                    "description": "响应数据"
                }
            }
        ),
        executor=builtin_http_request.func
    )


def get_calculator_intent() -> IntentDefinition:
    """获取计算器意图"""
    return IntentDefinition(
        metadata=IntentMetadata(
            id="calculator",
            name="计算器",
            description="计算数学表达式",
            category="transform",
            tags=["math", "calculation", "compute"],
            priority=20,
            timeout=5
        ),
        schema=InputOutputSchema(
            inputs={
                "expression": {
                    "type": "string",
                    "description": "数学表达式，如 '25 * 4 + 10'",
                    "required": True
                }
            },
            outputs={
                "result": {
                    "type": "number",
                    "description": "计算结果"
                }
            }
        ),
        executor=builtin_calculator.func
    )


def get_web_search_intent() -> IntentDefinition:
    """获取网络搜索意图"""
    return IntentDefinition(
        metadata=IntentMetadata(
            id="web_search",
            name="网络搜索",
            description="搜索网络信息",
            category="data",
            tags=["search", "web", "research"],
            priority=15,
            timeout=20
        ),
        schema=InputOutputSchema(
            inputs={
                "query": {
                    "type": "string",
                    "description": "搜索查询",
                    "required": True
                },
                "max_results": {
                    "type": "integer",
                    "description": "最大结果数",
                    "default": 5
                }
            },
            outputs={
                "results": {
                    "type": "array",
                    "description": "搜索结果列表"
                }
            }
        ),
        executor=builtin_web_search.func
    )


def get_data_analysis_intent() -> IntentDefinition:
    """获取数据分析意图"""
    return IntentDefinition(
        metadata=IntentMetadata(
            id="data_analysis",
            name="数据分析",
            description="分析数据的统计信息",
            category="transform",
            tags=["analysis", "stats", "data"],
            priority=5
        ),
        schema=InputOutputSchema(
            inputs={
                "data": {
                    "type": "any",
                    "description": "待分析的数据",
                    "required": True
                },
                "analysis_type": {
                    "type": "string",
                    "description": "分析类型",
                    "default": "summary",
                    "enum": ["summary", "stats", "count"]
                }
            },
            outputs={
                "analysis": {
                    "type": "object",
                    "description": "分析结果"
                }
            }
        ),
        executor=builtin_data_analysis.func
    )


def get_text_processing_intent() -> IntentDefinition:
    """获取文本处理意图"""
    return IntentDefinition(
        metadata=IntentMetadata(
            id="text_processing",
            name="文本处理",
            description="处理文本数据",
            category="transform",
            tags=["text", "string", "process"],
            priority=3
        ),
        schema=InputOutputSchema(
            inputs={
                "text": {
                    "type": "string",
                    "description": "待处理文本",
                    "required": True
                },
                "operation": {
                    "type": "string",
                    "description": "操作类型",
                    "default": "count",
                    "enum": ["count", "lower", "upper", "reverse"]
                }
            },
            outputs={
                "result": {
                    "type": "object",
                    "description": "处理结果"
                }
            }
        ),
        executor=builtin_text_processing.func
    )


def get_file_read_intent() -> IntentDefinition:
    """获取文件读取意图（示例）"""
    async def file_read(file_path: str) -> str:
        """读取文件内容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return f"错误: 文件 {file_path} 不存在"
        except Exception as e:
            return f"错误: {str(e)}"

    return IntentDefinition(
        metadata=IntentMetadata(
            id="file_read",
            name="读取文件",
            description="读取文本文件内容",
            category="data",
            tags=["file", "io", "read"],
            priority=8
        ),
        schema=InputOutputSchema(
            inputs={
                "file_path": {
                    "type": "string",
                    "description": "文件路径",
                    "required": True
                }
            },
            outputs={
                "content": {
                    "type": "string",
                    "description": "文件内容"
                }
            }
        ),
        executor=file_read
    )


# ============================================================
# 批量注册函数
# ============================================================

def register_builtin_data_intents(registry: IntentRegistry) -> None:
    """
    注册所有内置数据意图

    Args:
        registry: 意图注册表
    """
    intents = [
        get_http_request_intent(),
        get_calculator_intent(),
        get_web_search_intent(),
        get_data_analysis_intent(),
        get_text_processing_intent(),
        get_file_read_intent()
    ]

    for intent in intents:
        try:
            registry.register(intent)
        except ValueError as e:
            # 忽略重复注册错误
            if "already registered" not in str(e):
                raise
