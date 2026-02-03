"""
内置意图库 - 常用的数据获取和转换意图
"""

from intent_system.builtin_intents.data_intents import (
    register_builtin_data_intents,
    get_http_request_intent,
    get_calculator_intent,
    get_file_read_intent
)

__all__ = [
    "register_builtin_data_intents",
    "get_http_request_intent",
    "get_calculator_intent",
    "get_file_read_intent"
]
