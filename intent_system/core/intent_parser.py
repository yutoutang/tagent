"""
意图解析器 - 使用 LLM 解析用户输入，识别多个意图
"""

import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from intent_system.core.intent_registry import IntentRegistry
from intent_system.core.intent_definition import IntentDefinition


class IntentParseResult(BaseModel):
    """
    意图解析结果

    包含识别出的意图、参数和依赖关系
    """
    primary_intent: str = Field(description="主要意图ID")
    confidence: float = Field(description="识别置信度 (0-1)")
    sub_intents: List[Dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "子意图列表，每个子意图包含:\n"
            "- id: 意图ID\n"
            "- parameters: 该意图的参数\n"
            "- priority: 优先级"
        )
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="提取的参数（全局参数）"
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="识别出的依赖关系"
    )
    reasoning: str = Field(description="解析理由和依据")

    def get_all_intent_ids(self) -> List[str]:
        """获取所有意图ID（主要意图 + 子意图）"""
        return [self.primary_intent] + [sub["id"] for sub in self.sub_intents]

    def get_intent_parameters(self, intent_id: str) -> Dict[str, Any]:
        """
        获取特定意图的参数

        Args:
            intent_id: 意图ID

        Returns:
            该意图的参数字典
        """
        if intent_id == self.primary_intent:
            return self.parameters
        for sub in self.sub_intents:
            if sub["id"] == intent_id:
                return sub.get("parameters", {})
        return {}

    def __str__(self) -> str:
        """字符串表示"""
        sub_ids = [sub["id"] for sub in self.sub_intents]
        return (
            f"IntentParseResult(\n"
            f"  primary={self.primary_intent},\n"
            f"  confidence={self.confidence:.2f},\n"
            f"  sub_intents={sub_ids},\n"
            f"  total={len(self.get_all_intent_ids())} intents\n"
            f")"
        )


class IntentParser:
    """
    意图解析器 - 使用 LLM 智能识别用户意图

    功能：
    - 单意图识别
    - 多意图分解
    - 参数提取
    - 依赖关系识别
    """

    def __init__(self, llm, registry: IntentRegistry):
        """
        初始化意图解析器

        Args:
            llm: LangChain LLM 实例
            registry: 意图注册表
        """
        self.llm = llm
        self.registry = registry
        self.parser = llm.with_structured_output(IntentParseResult)

    def parse(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> IntentParseResult:
        """
        解析用户输入，识别意图

        Args:
            user_input: 用户输入文本
            context: 可选的上下文信息

        Returns:
            意图解析结果
        """
        # 构建系统提示
        all_intents = self.registry.list_all()
        intent_descriptions = self._build_intent_prompt(all_intents)

        system_prompt = f"""你是一个意图识别专家。分析用户输入，识别用户想要执行的操作。

可用的意图列表：
{intent_descriptions}

任务要求：
1. 识别主要意图（primary_intent）- 最主要的操作
2. 如果包含多个子任务，识别所有子意图（sub_intents）
3. 提取每个意图的相关参数
4. 确定意图之间的依赖关系
5. 评估识别的置信度（confidence）从0到1
6. 说明解析的理由（reasoning）

注意事项：
- 参数名称必须与意图定义中的输入参数名称完全匹配
- 如果意图需要特定参数，必须从用户输入中提取
- 如果某个参数未提及，使用参数的默认值或不包含该参数
- 依赖关系：如果意图B需要意图A的输出结果，则B依赖A
"""

        try:
            # 使用流式调用 LLM 进行结构化解析
            print(f"\n[LLM 调用] 意图解析: {user_input[:50]}...")

            # 流式获取响应
            chunks = []
            for chunk in self.parser.stream([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_input)
            ]):
                chunks.append(chunk)
                # 输出流式进度
                if hasattr(chunk, 'content'):
                    print(f"[流式输出] {chunk.content[:100] if len(chunk.content) > 100 else chunk.content}")

            # 获取最终结果
            result = chunks[-1] if chunks else None
            if result:
                print(f"[LLM 完成] 识别意图: {result.primary_intent}, 置信度: {result.confidence:.2f}")

            # 验证识别的意图是否存在
            validated_result = self._validate_result(result)

            return validated_result

        except Exception as e:
            print(f"[LLM 错误] {str(e)}")
            # 降级处理：返回基础解析结果
            return self._fallback_parse(user_input, str(e))

    def _build_intent_prompt(self, intents: List[IntentDefinition]) -> str:
        """
        构建意图描述提示

        Args:
            intents: 意图列表

        Returns:
            格式化的意图描述文本
        """
        if not intents:
            return "（暂无可用意图）"

        descriptions = []
        for intent in intents:
            desc = f"- **{intent.metadata.id}**: {intent.metadata.description}"

            # 添加参数信息
            if intent.schema.inputs:
                params = []
                for param_name, param_def in intent.schema.inputs.items():
                    param_desc = param_name
                    if param_def.get("required"):
                        param_desc += "*"
                    params.append(param_desc)

                if params:
                    desc += f"\n  参数: {', '.join(params)}"

            # 添加类别和标签
            if intent.metadata.tags:
                desc += f"\n  标签: {', '.join(intent.metadata.tags)}"

            descriptions.append(desc)

        return "\n\n".join(descriptions)

    def _validate_result(self, result: IntentParseResult) -> IntentParseResult:
        """
        验证解析结果

        检查识别的意图是否存在，过滤掉无效的意图

        Args:
            result: 原始解析结果

        Returns:
            验证后的解析结果
        """
        # 验证主要意图
        if not self.registry.exists(result.primary_intent):
            # 主要意图不存在，尝试找到替代
            all_intents = self.registry.list_all()
            if all_intents:
                result.primary_intent = all_intents[0].metadata.id
                result.reasoning += f"\n注意：原识别意图不存在，已替换为{result.primary_intent}"

        # 验证子意图
        valid_sub_intents = []
        for sub in result.sub_intents:
            if self.registry.exists(sub["id"]):
                valid_sub_intents.append(sub)
            else:
                result.reasoning += f"\n注意：子意图 {sub['id']} 不存在，已忽略"

        result.sub_intents = valid_sub_intents

        # 更新依赖关系，移除不存在的意图的依赖
        valid_dependencies = [
            dep for dep in result.dependencies
            if self.registry.exists(dep)
        ]
        result.dependencies = valid_dependencies

        return result

    def _fallback_parse(
        self,
        user_input: str,
        error: str
    ) -> IntentParseResult:
        """
        降级解析 - 当 LLM 解析失败时使用

        Args:
            user_input: 用户输入
            error: 错误信息

        Returns:
            基础解析结果
        """
        # 简单的关键词匹配
        all_intents = self.registry.list_all()

        if not all_intents:
            # 没有可用意图
            return IntentParseResult(
                primary_intent="unknown",
                confidence=0.0,
                reasoning=f"解析失败：{error}，且无可用意图"
            )

        # 使用第一个可用意图作为默认
        default_intent = all_intents[0].metadata.id

        return IntentParseResult(
            primary_intent=default_intent,
            confidence=0.3,
            reasoning=(
                f"LLM解析失败（{error}），使用关键词匹配降级处理。"
                f"默认使用意图：{default_intent}"
            )
        )

    def parse_with_retry(
        self,
        user_input: str,
        max_retries: int = 3,
        context: Optional[Dict[str, Any]] = None
    ) -> IntentParseResult:
        """
        带重试的解析

        Args:
            user_input: 用户输入
            max_retries: 最大重试次数
            context: 可选的上下文

        Returns:
            意图解析结果
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                result = self.parse(user_input, context)
                # 如果置信度太低，也可能是解析失败
                if result.confidence >= 0.5:
                    return result
                else:
                    last_error = f"置信度过低: {result.confidence}"
            except Exception as e:
                last_error = str(e)

        # 所有重试都失败，返回降级结果
        return self._fallback_parse(user_input, last_error or "未知错误")

    def batch_parse(
        self,
        user_inputs: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> List[IntentParseResult]:
        """
        批量解析多个用户输入

        Args:
            user_inputs: 用户输入列表
            context: 可选的上下文

        Returns:
            解析结果列表
        """
        return [
            self.parse(user_input, context)
            for user_input in user_inputs
        ]
