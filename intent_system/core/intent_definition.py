"""
意图定义系统 - 参考 n8n 的节点定义和 Dify 的 Schema 设计
"""

from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field


class IntentMetadata(BaseModel):
    """
    意图元数据 - 参考 n8n 的节点描述

    包含意图的基本信息和执行配置
    """
    id: str = Field(description="唯一标识符")
    name: str = Field(description="显示名称")
    description: str = Field(description="功能描述")
    category: str = Field(description="类别: data/transform/execute/control")
    version: str = Field(default="1.0.0", description="版本号")
    priority: int = Field(default=0, description="优先级，数值越大优先级越高")
    tags: List[str] = Field(default_factory=list, description="标签列表")

    # 执行配置
    timeout: int = Field(default=30, description="超时时间（秒）")
    retry_count: int = Field(default=0, description="重试次数")
    can_parallel: bool = Field(default=True, description="是否支持并行执行")

    # 依赖关系
    dependencies: List[str] = Field(
        default_factory=list,
        description="依赖的其他意图ID列表"
    )
    conflicts: List[str] = Field(
        default_factory=list,
        description="冲突的意图ID列表（不能同时执行）"
    )


class InputOutputSchema(BaseModel):
    """
    输入输出 Schema - 参考 Dify 的 JSON Schema 定义

    定义意图的输入参数和输出数据结构
    """
    # 输入参数定义
    inputs: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description=(
            "输入参数定义，key为参数名，value包含:\n"
            "- type: 参数类型\n"
            "- description: 参数描述\n"
            "- required: 是否必需\n"
            "- default: 默认值\n"
            "- enum: 可选值列表"
        )
    )

    # 输出数据结构
    outputs: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="输出数据结构定义"
    )

    # 数据映射示例 - n8n 风格
    output_mapping: Dict[str, str] = Field(
        default_factory=dict,
        description=(
            "输出映射表达式，支持 n8n 风格语法:\n"
            "如: {'result': '{{ $json.data }}'}\n"
            "用于将内部输出映射到标准格式"
        )
    )

    def validate_input(self, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        验证输入数据

        Args:
            data: 输入数据

        Returns:
            (是否有效, 错误信息)
        """
        for param_name, param_def in self.inputs.items():
            # 检查必需参数
            if param_def.get("required", False) and param_name not in data:
                return False, f"缺少必需参数: {param_name}"

            # 检查类型
            if param_name in data:
                param_type = param_def.get("type")
                if param_type == "string" and not isinstance(data[param_name], str):
                    return False, f"参数 {param_name} 应为字符串类型"
                elif param_type == "integer" and not isinstance(data[param_name], int):
                    return False, f"参数 {param_name} 应为整数类型"
                elif param_type == "number" and not isinstance(
                    data[param_name], (int, float)
                ):
                    return False, f"参数 {param_name} 应为数字类型"
                elif param_type == "boolean" and not isinstance(data[param_name], bool):
                    return False, f"参数 {param_name} 应为布尔类型"
                elif param_type == "array" and not isinstance(data[param_name], list):
                    return False, f"参数 {param_name} 应为数组类型"
                elif param_type == "object" and not isinstance(data[param_name], dict):
                    return False, f"参数 {param_name} 应为对象类型"

                # 检查枚举值
                if "enum" in param_def and data[param_name] not in param_def["enum"]:
                    return False, (
                        f"参数 {param_name} 的值应在 {param_def['enum']} 中"
                    )

        return True, None


class IntentDefinition(BaseModel):
    """
    意图完整定义 - 参考 n8n 的完整节点定义

    包含意图的元数据、Schema、执行逻辑和示例
    """
    metadata: IntentMetadata = Field(description="意图元数据")
    schema: InputOutputSchema = Field(description="输入输出 Schema")

    # 执行逻辑
    executor: Callable = Field(description="执行函数，接受输入参数并返回结果")

    # 验证规则（可选）
    validation_rules: Optional[Dict[str, Any]] = Field(
        default=None,
        description="自定义验证规则"
    )

    # 示例
    examples: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="使用示例，包含输入和预期输出"
    )

    class Config:
        arbitrary_types_allowed = True  # 允许 Callable 类型

    def validate_inputs(self, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        验证输入数据

        Args:
            data: 输入数据

        Returns:
            (是否有效, 错误信息)
        """
        return self.schema.validate_input(data)

    def get_input_defaults(self) -> Dict[str, Any]:
        """
        获取所有输入参数的默认值

        Returns:
            默认值字典
        """
        defaults = {}
        for param_name, param_def in self.schema.inputs.items():
            if "default" in param_def:
                defaults[param_name] = param_def["default"]
        return defaults

    def add_example(self, input_data: Dict[str, Any], output_data: Any) -> None:
        """
        添加使用示例

        Args:
            input_data: 输入数据
            output_data: 预期输出
        """
        self.examples.append({
            "input": input_data,
            "output": output_data
        })

    def __str__(self) -> str:
        """字符串表示"""
        return (
            f"Intent({self.metadata.id}, "
            f"name='{self.metadata.name}', "
            f"category='{self.metadata.category}')"
        )

    def __repr__(self) -> str:
        """详细表示"""
        return (
            f"IntentDefinition(\n"
            f"  id={self.metadata.id},\n"
            f"  name={self.metadata.name},\n"
            f"  category={self.metadata.category},\n"
            f"  inputs={list(self.schema.inputs.keys())},\n"
            f"  executor={self.executor.__name__ if hasattr(self.executor, '__name__') else 'lambda'}\n"
            f")"
        )
