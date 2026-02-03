"""
工作流意图管理器

核心功能：
1. 加载管理工作流意图
2. 构建和可视化意图图谱
3. 提供流程导航和指导
4. 集成意图解析器
"""

from typing import Any, Dict, List, Optional, Tuple
from collections import deque

from .workflow_intent import WorkflowIntentDefinition
from .json_loader import load_workflow_from_json


class WorkflowIntentManager:
    """
    工作流意图管理器

    管理工作流意图的生命周期，提供导航、指导和图谱可视化功能
    """

    def __init__(self, parser=None, registry=None):
        """
        初始化工作流管理器

        Args:
            parser: IntentParser实例（可选，用于意图识别）
            registry: IntentRegistry实例（可选）
        """
        self._intents: Dict[str, WorkflowIntentDefinition] = {}
        self._parser = parser
        self._registry = registry
        self._current_intent: Optional[str] = None
        self._execution_history: List[str] = []

        # 意图谱（邻接表）
        self._graph: Dict[str, List[str]] = {}  # 正向图
        self._reverse_graph: Dict[str, List[str]] = {}  # 反向图

    def load_from_json(
        self,
        json_path: str,
        auto_register: bool = True
    ) -> int:
        """
        从JSON文件加载工作流定义

        Args:
            json_path: JSON文件路径
            auto_register: 是否自动注册到IntentRegistry

        Returns:
            加载的意图数量
        """
        intents = load_workflow_from_json(
            json_path,
            auto_register=auto_register,
            registry=self._registry
        )

        for intent in intents:
            self._intents[intent.id] = intent

        # 重新构建图谱
        self._build_graph()

        return len(intents)

    def register_intent(self, intent: WorkflowIntentDefinition) -> None:
        """
        注册工作流意图

        Args:
            intent: 工作流意图定义
        """
        self._intents[intent.id] = intent
        self._build_graph()

        # 同时注册到标准注册表
        if self._registry:
            standard_intent = intent.to_intent_definition()
            self._registry.register(standard_intent)

    def _build_graph(self) -> None:
        """构建意图图谱"""
        self._graph = {}
        self._reverse_graph = {}

        for intent_id, intent in self._intents.items():
            # 正向图：后置关系
            self._graph[intent_id] = intent.post_intents.copy()

            # 反向图：前置关系
            self._reverse_graph[intent_id] = intent.pre_intents.copy()

    def recognize_intent(
        self,
        user_input: str,
        use_llm: bool = True
    ) -> Tuple[str, float]:
        """
        识别用户意图

        Args:
            user_input: 用户输入
            use_llm: 是否使用LLM解析（需要设置parser）

        Returns:
            (意图ID, 置信度)
        """
        # 优先使用LLM解析器
        if use_llm and self._parser:
            try:
                result = self._parser.parse(user_input)
                if result.primary_intent in self._intents:
                    return result.primary_intent, result.confidence
            except Exception:
                pass  # 降级到关键词匹配

        # 降级：关键词匹配
        return self._keyword_match(user_input)

    def _keyword_match(self, user_input: str) -> Tuple[str, float]:
        """
        关键词匹配识别意图

        Args:
            user_input: 用户输入

        Returns:
            (意图ID, 置信度)
        """
        user_input_lower = user_input.lower()
        scores = {}

        for intent_id, intent in self._intents.items():
            score = 0.0

            # 匹配名称
            if intent.name.lower() in user_input_lower:
                score += 0.5

            # 匹配描述关键词
            keywords = self._extract_keywords(intent.description)
            for keyword in keywords:
                if keyword in user_input_lower:
                    score += 0.2

            # 匹配ID
            if intent_id.lower() in user_input_lower:
                score += 0.4

            scores[intent_id] = min(score, 1.0)

        if not scores:
            return "", 0.0

        best_intent = max(scores, key=scores.get)
        return best_intent, scores[best_intent]

    def _extract_keywords(self, text: str) -> List[str]:
        """从文本中提取关键词"""
        keywords = []
        words = text.split()

        # 简单停用词列表
        stopwords = {'的', '是', '在', '和', '或', '与', '进行', '通过', '为了', '实现'}

        for word in words:
            if len(word) > 1 and word not in stopwords:
                keywords.append(word.lower())

        return keywords

    def set_current_intent(self, intent_id: str) -> bool:
        """
        设置当前意图

        Args:
            intent_id: 意图ID

        Returns:
            是否成功设置
        """
        if intent_id not in self._intents:
            return False

        self._current_intent = intent_id
        return True

    def get_entry_guidance(self, intent_id: str) -> Optional[str]:
        """
        获取进入意图时的指导

        Args:
            intent_id: 意图ID

        Returns:
            指导文本，不存在则返回None
        """
        intent = self._intents.get(intent_id)
        if intent and intent.guidance:
            return intent.guidance.entry
        return None

    def get_completion_guidance(self, intent_id: str) -> Optional[str]:
        """
        获取完成意图时的指导

        Args:
            intent_id: 意图ID

        Returns:
            指导文本，不存在则返回None
        """
        intent = self._intents.get(intent_id)
        if intent and intent.guidance:
            return intent.guidance.completion
        return None

    def get_next_actions(self, intent_id: str) -> List[str]:
        """
        获取建议的下一步操作

        Args:
            intent_id: 意图ID

        Returns:
            下一步操作列表
        """
        intent = self._intents.get(intent_id)
        if intent and intent.guidance:
            return intent.guidance.next_actions
        return []

    def get_next_intents(self, intent_id: str) -> List[str]:
        """获取后置意图列表"""
        return self._graph.get(intent_id, [])

    def get_pre_intents(self, intent_id: str) -> List[str]:
        """获取前置意图列表"""
        return self._reverse_graph.get(intent_id, [])

    def get_intent_path(self, intent_id: str) -> List[str]:
        """
        获取从起点到当前意图的完整路径

        Args:
            intent_id: 目标意图ID

        Returns:
            意图ID路径列表
        """
        path = []
        visited = set()

        def dfs(current: str) -> bool:
            if current in visited:
                return False

            visited.add(current)
            path.insert(0, current)

            pre_intents = self.get_pre_intents(current)
            if not pre_intents:
                return True

            # 只追踪第一条路径
            for pre_intent in pre_intents[:1]:
                if dfs(pre_intent):
                    return True

            path.remove(current)
            return False

        dfs(intent_id)
        return path

    def get_workflow_suggestion(self, user_input: str) -> Dict[str, Any]:
        """
        根据用户输入获取工作流建议

        Args:
            user_input: 用户输入

        Returns:
            包含识别结果、路径和指导的字典
        """
        # 识别意图
        intent_id, confidence = self.recognize_intent(user_input)

        if not intent_id:
            return {
                "recognized": False,
                "message": "未能识别您的意图，请重新描述。"
            }

        intent = self._intents[intent_id]

        # 获取完整路径
        path = self.get_intent_path(intent_id)
        path_names = [self._intents[i].name for i in path if i in self._intents]

        # 获取后置意图
        next_intents = self.get_next_intents(intent_id)
        next_names = [self._intents[i].name for i in next_intents if i in self._intents]

        return {
            "recognized": True,
            "current_intent": intent_id,
            "current_intent_name": intent.name,
            "confidence": confidence,
            "path": path,
            "path_names": path_names,
            "path_str": " -> ".join(path_names) if path_names else "",
            "entry_guidance": self.get_entry_guidance(intent_id),
            "next_intents": next_intents,
            "next_intent_names": next_names,
            "next_str": " -> ".join(next_names) if next_names else "（完成）",
            "next_actions": self.get_next_actions(intent_id)
        }

    def process_completion(self, intent_id: str) -> Dict[str, Any]:
        """
        处理意图完成事件

        Args:
            intent_id: 已完成的意图ID

        Returns:
            包含完成指导和后续建议的字典
        """
        intent = self._intents.get(intent_id)
        if not intent:
            return {
                "error": f"意图不存在: {intent_id}"
            }

        # 记录执行历史
        self._execution_history.append(intent_id)

        # 获取后置意图
        next_intents = self.get_next_intents(intent_id)
        next_names = [self._intents[i].name for i in next_intents if i in self._intents]

        return {
            "completed_intent": intent_id,
            "completed_intent_name": intent.name,
            "completion_guidance": self.get_completion_guidance(intent_id),
            "next_intents": next_intents,
            "next_intent_names": next_names,
            "next_actions": self.get_next_actions(intent_id),
            "suggestion": f"{intent.name}已完成！建议下一步: {' 或 '.join(next_names) if next_names else '整个流程已完成'}"
        }

    def visualize_graph(self) -> str:
        """
        生成意图图谱的可视化文本

        Returns:
            图谱的文本表示
        """
        lines = []
        lines.append("=" * 60)
        lines.append("工作流意图图谱")
        lines.append("=" * 60)

        for intent_id, intent in self._intents.items():
            lines.append(f"\n【{intent.name}】({intent_id})")
            lines.append(f"  描述: {intent.description}")

            pre_intents = intent.pre_intents
            if pre_intents:
                pre_names = [self._intents[i].name for i in pre_intents if i in self._intents]
                lines.append(f"  前置: {' -> '.join(pre_names)} -> {intent.name}")

            post_intents = intent.post_intents
            if post_intents:
                post_names = [self._intents[i].name for i in post_intents if i in self._intents]
                lines.append(f"  后置: {intent.name} -> {' -> '.join(post_names)}")

        return "\n".join(lines)

    def list_all_intents(self) -> List[Dict[str, Any]]:
        """列出所有意图"""
        return [
            {
                "id": intent.id,
                "name": intent.name,
                "description": intent.description,
                "category": intent.category
            }
            for intent in self._intents.values()
        ]

    def get_status(self) -> Dict[str, Any]:
        """获取管理器状态"""
        return {
            "total_intents": len(self._intents),
            "current_intent": self._current_intent,
            "execution_history": self._execution_history.copy(),
            "available_intents": list(self._intents.keys())
        }

    def get_graphviz_dot(self) -> str:
        """
        生成Graphviz DOT格式的图谱

        Returns:
            DOT格式字符串
        """
        lines = ["digraph WorkflowIntentGraph {"]
        lines.append("  rankdir=LR;")
        lines.append("  node [shape=box, style=rounded];")

        # 添加节点
        for intent_id, intent in self._intents.items():
            label = f"{intent.name}\\n({intent_id})"
            lines.append(f'  "{intent_id}" [label="{label}"];')

        # 添加边（后置关系）
        for intent_id, next_ids in self._graph.items():
            for next_id in next_ids:
                lines.append(f'  "{intent_id}" -> "{next_id}";')

        lines.append("}")
        return "\n".join(lines)
