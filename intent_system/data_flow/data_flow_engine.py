"""
数据流转引擎 - n8n 风格的数据映射和表达式解析
"""

import re
import json
from typing import Any, Dict, List, Optional


class ExpressionParser:
    """
    表达式解析器 - 支持 n8n 风格的表达式

    支持的语法：
    - {{ $json.field }} - 引用 JSON 数据
    - {{ $json.user.name }} - 嵌套路径
    - {{ $json.items[0].id }} - 数组索引
    - $variable - 简单变量引用
    """

    def __init__(self):
        """初始化表达式解析器"""
        # n8n 风格表达式正则
        self.n8n_pattern = re.compile(r'\{\{\s*\$json\.([^}]+)\s*\}\}')

    def evaluate(
        self,
        expression: str,
        context: Dict[str, Any]
    ) -> Any:
        """
        评估表达式

        Args:
            expression: 表达式字符串
            context: 上下文数据

        Returns:
            评估结果
        """
        # 处理 n8n 风格: {{ $json.field }}
        if '{{' in expression and '}}' in expression:
            return self._evaluate_n8n_expression(expression, context)

        # 处理简单变量: $variable
        elif expression.startswith('$') and '{{' not in expression:
            var_name = expression[1:]
            return context.get(var_name, expression)

        # 尝试解析为 JSON
        elif expression.startswith('{') or expression.startswith('['):
            try:
                return json.loads(expression)
            except json.JSONDecodeError:
                return expression

        # 直接值
        else:
            # 尝试转换为数字
            try:
                if '.' in expression:
                    return float(expression)
                else:
                    return int(expression)
            except ValueError:
                return expression

    def _evaluate_n8n_expression(
        self,
        expr: str,
        context: Dict[str, Any]
    ) -> Any:
        """
        评估 n8n 风格表达式

        Args:
            expr: 表达式
            context: 上下文数据

        Returns:
            评估结果
        """
        # 查找所有表达式
        matches = self.n8n_pattern.findall(expr)

        if not matches:
            return expr

        # 如果只有一个表达式且没有其他文本，直接返回值
        if len(matches) == 1 and expr.strip().startswith('{{') and expr.strip().endswith('}}'):
            value = self._get_nested_value(context, matches[0])
            return value if value is not None else expr

        # 替换所有表达式
        result = expr
        for match in matches:
            value = self._get_nested_value(context, match)
            if value is not None:
                result = result.replace(f'{{{{ $json.{match} }}}}', str(value))

        return result

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """
        获取嵌套值

        支持路径语法：
        - field
        - user.name
        - items[0].id
        - data.users[0].addresses[1].city

        Args:
            data: 数据字典
            path: 路径字符串

        Returns:
            找到的值，未找到则返回 None
        """
        if not data:
            return None

        # 解析路径
        # 将 items[0].id 转换为 ["items", "0", "id"]
        keys = self._parse_path(path)

        value = data
        for key in keys:
            if value is None:
                return None

            # 处理数字索引
            if key.isdigit():
                if isinstance(value, list) and int(key) < len(value):
                    value = value[int(key)]
                else:
                    return None
            # 处理字典键
            elif isinstance(value, dict):
                value = value.get(key)
            else:
                return None

        return value

    def _parse_path(self, path: str) -> List[str]:
        """
        解析路径字符串

        Args:
            path: 路径字符串，如 "user.name" 或 "items[0].id"

        Returns:
            键列表
        """
        # 替换 [ 为 .[. 以便于分割
        path = path.replace('[', '.[')
        # 分割
        parts = path.split('.')
        # 过滤空字符串并移除 ]
        keys = [
            part.replace(']', '')
            for part in parts
            if part
        ]
        return keys

    def validate_expression(self, expression: str) -> tuple[bool, Optional[str]]:
        """
        验证表达式语法

        Args:
            expression: 表达式字符串

        Returns:
            (是否有效, 错误信息)
        """
        if not expression:
            return True, None

        # 检查 n8n 表达式的括号匹配
        if '{{' in expression or '}}' in expression:
            open_count = expression.count('{{')
            close_count = expression.count('}}')
            if open_count != close_count:
                return False, f"表达式括号不匹配: {{有{open_count}个，}}有{close_count}个"

        return True, None


class DataFlowEngine:
    """
    数据流转引擎

    功能：
    1. 解析数据映射表达式
    2. 数据转换
    3. 数据验证
    """

    def __init__(self):
        """初始化数据流转引擎"""
        self.expression_parser = ExpressionParser()

    def resolve_mapping(
        self,
        mapping: Dict[str, str],
        previous_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        解析数据映射

        Args:
            mapping: 数据映射字典，key为参数名，value为表达式
            previous_results: 前面意图的执行结果

        Returns:
            解析后的数据字典
        """
        resolved = {}

        for key, expression in mapping.items():
            resolved[key] = self.expression_parser.evaluate(
                expression,
                previous_results
            )

        return resolved

    def transform_data(
        self,
        data: Any,
        transform_config: Dict[str, Any]
    ) -> Any:
        """
        数据转换

        Args:
            data: 原始数据
            transform_config: 转换配置

        Returns:
            转换后的数据
        """
        transform_type = transform_config.get('type')

        if transform_type == 'json_extract':
            return self._json_extract(data, transform_config.get('path', ''))

        elif transform_type == 'map':
            return self._map_fields(data, transform_config.get('field_map', {}))

        elif transform_type == 'filter':
            return self._filter_data(data, transform_config.get('condition'))

        elif transform_type == 'rename':
            return self._rename_fields(data, transform_config.get('field_rename', {}))

        elif transform_type == 'aggregate':
            return self._aggregate(data, transform_config.get('operation'))

        else:
            return data

    def _json_extract(self, data: Any, path: str) -> Any:
        """提取 JSON 路径数据"""
        if not isinstance(data, dict):
            return data

        return self.expression_parser._get_nested_value(data, path)

    def _map_fields(
        self,
        data: Dict[str, Any],
        field_map: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        字段映射

        Args:
            data: 原始数据
            field_map: 字段映射字典，key为旧字段名，value为新字段名

        Returns:
            映射后的数据
        """
        if not isinstance(data, dict):
            return data

        result = {}
        for old_key, new_key in field_map.items():
            if old_key in data:
                result[new_key] = data[old_key]

        # 保留未映射的字段
        for key, value in data.items():
            if key not in field_map:
                result[key] = value

        return result

    def _filter_data(
        self,
        data: Any,
        condition: Dict[str, Any]
    ) -> Any:
        """
        数据过滤

        Args:
            data: 原始数据（列表或字典）
            condition: 过滤条件

        Returns:
            过滤后的数据
        """
        if isinstance(data, list):
            return [
                item for item in data
                if self._match_condition(item, condition)
            ]
        elif isinstance(data, dict):
            return {
                key: value for key, value in data.items()
                if self._match_condition({'key': key, 'value': value}, condition)
            }
        else:
            return data

    def _match_condition(
        self,
        item: Dict[str, Any],
        condition: Dict[str, Any]
    ) -> bool:
        """
        匹配条件

        Args:
            item: 数据项
            condition: 条件字典

        Returns:
            是否匹配
        """
        field = condition.get('field')
        operator = condition.get('operator', '==')
        value = condition.get('value')

        if field not in item:
            return False

        item_value = item[field]

        if operator == '==':
            return item_value == value
        elif operator == '!=':
            return item_value != value
        elif operator == '>':
            return item_value > value
        elif operator == '<':
            return item_value < value
        elif operator == '>=':
            return item_value >= value
        elif operator == '<=':
            return item_value <= value
        elif operator == 'in':
            return item_value in value
        elif operator == 'contains':
            return value in item_value if isinstance(item_value, (str, list)) else False
        else:
            return False

    def _rename_fields(
        self,
        data: Dict[str, Any],
        field_rename: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        字段重命名

        Args:
            data: 原始数据
            field_rename: 重命名映射，key为旧名称，value为新名称

        Returns:
            重命名后的数据
        """
        if not isinstance(data, dict):
            return data

        result = {}
        for key, value in data.items():
            new_key = field_rename.get(key, key)
            result[new_key] = value

        return result

    def _aggregate(
        self,
        data: Any,
        operation: str
    ) -> Any:
        """
        数据聚合

        Args:
            data: 原始数据（通常是列表）
            operation: 聚合操作 (count/sum/avg/min/max/first/last)

        Returns:
            聚合结果
        """
        if not isinstance(data, list):
            return data

        if not data:
            return None

        if operation == 'count':
            return len(data)

        elif operation == 'sum':
            return sum(data)

        elif operation == 'avg':
            return sum(data) / len(data) if data else 0

        elif operation == 'min':
            return min(data)

        elif operation == 'max':
            return max(data)

        elif operation == 'first':
            return data[0] if data else None

        elif operation == 'last':
            return data[-1] if data else None

        else:
            return data

    def merge_data(
        self,
        *data_sources: Dict[str, Any],
        strategy: str = 'merge'
    ) -> Dict[str, Any]:
        """
        合并多个数据源

        Args:
            *data_sources: 多个数据源字典
            strategy: 合并策略 (merge/overwrite/concat)

        Returns:
            合并后的数据
        """
        if strategy == 'merge':
            # 递归合并
            result = {}
            for source in data_sources:
                if isinstance(source, dict):
                    result.update(source)
            return result

        elif strategy == 'overwrite':
            # 后面的覆盖前面的
            result = {}
            for source in data_sources:
                if isinstance(source, dict):
                    result = {**result, **source}
            return result

        elif strategy == 'concat':
            # 合并列表
            result = {}
            for i, source in enumerate(data_sources):
                if isinstance(source, dict):
                    for key, value in source.items():
                        if key not in result:
                            result[key] = []
                        result[key].append(value)
            return result

        else:
            return {}
