"""
工作流意图引擎 - 支持JSON定义和意图图谱

功能：
1. 从JSON文件加载意图定义
2. 构建意图图谱
3. 根据用户输入识别意图
4. 根据意图关系给出后续指导
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class IntentGuidance:
    """意图指导信息"""
    entry: str  # 进入意图时的指导
    completion: str  # 完成意图时的指导
    next_actions: List[str]  # 可执行的下一步操作


@dataclass
class WorkflowIntent:
    """工作流意图定义"""
    id: str
    name: str
    description: str
    category: str
    pre_intents: List[str] = field(default_factory=list)
    post_intents: List[str] = field(default_factory=list)
    guidance: Optional[IntentGuidance] = None


@dataclass
class IntentNode:
    """意图图谱节点"""
    intent: WorkflowIntent
    depth: int = 0  # 在图谱中的深度


class WorkflowIntentEngine:
    """
    工作流意图引擎

    核心功能：
    1. 从JSON加载意图定义
    2. 构建意图图谱
    3. 识别用户意图
    4. 提供导航指导
    """

    def __init__(self):
        """初始化引擎"""
        self._intents: Dict[str, WorkflowIntent] = {}
        self._intent_graph: Dict[str, List[str]] = {}  # 前置图谱
        self._reverse_graph: Dict[str, List[str]] = {}  # 后置图谱
        self._current_intent: Optional[str] = None
        self._execution_history: List[str] = []

    def load_from_json(self, json_path: str) -> int:
        """
        从JSON文件加载意图定义

        Args:
            json_path: JSON文件路径

        Returns:
            加载的意图数量
        """
        path = Path(json_path)
        if not path.exists():
            raise FileNotFoundError(f"意图定义文件不存在: {json_path}")

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        count = 0
        for intent_data in data.get('intents', []):
            intent = self._parse_intent(intent_data)
            self._register_intent(intent)
            count += 1

        # 构建意图图谱
        self._build_graph()

        return count

    def _parse_intent(self, data: Dict[str, Any]) -> WorkflowIntent:
        """解析意图数据"""
        guidance = None
        if 'guidance' in data:
            g = data['guidance']
            guidance = IntentGuidance(
                entry=g.get('entry', ''),
                completion=g.get('completion', ''),
                next_actions=g.get('next_actions', [])
            )

        return WorkflowIntent(
            id=data['id'],
            name=data['name'],
            description=data['description'],
            category=data['category'],
            pre_intents=data.get('pre_intents', []),
            post_intents=data.get('post_intents', []),
            guidance=guidance
        )

    def _register_intent(self, intent: WorkflowIntent) -> None:
        """注册意图"""
        self._intents[intent.id] = intent

    def _build_graph(self) -> None:
        """构建意图图谱"""
        self._intent_graph = {}
        self._reverse_graph = {}

        for intent_id, intent in self._intents.items():
            # 前置图谱：intent_id -> pre_intents
            self._intent_graph[intent_id] = intent.pre_intents.copy()

            # 后置图谱：intent_id -> post_intents
            self._reverse_graph[intent_id] = intent.post_intents.copy()

    def recognize_intent(self, user_input: str) -> Tuple[str, float]:
        """
        识别用户意图

        Args:
            user_input: 用户输入

        Returns:
            (意图ID, 置信度)
        """
        user_input_lower = user_input.lower()

        # 简单的关键词匹配（实际应用中可使用LLM或更复杂的NLP）
        scores = {}
        for intent_id, intent in self._intents.items():
            score = 0.0

            # 匹配意图名称
            if intent.name.lower() in user_input_lower:
                score += 0.5

            # 匹配意图描述中的关键词
            keywords = self._extract_keywords(intent.description)
            for keyword in keywords:
                if keyword in user_input_lower:
                    score += 0.2

            # 匹配ID
            if intent_id.lower() in user_input_lower:
                score += 0.4

            scores[intent_id] = min(score, 1.0)

        # 返回得分最高的意图
        if not scores:
            return "", 0.0

        best_intent = max(scores, key=scores.get)
        confidence = scores[best_intent]

        return best_intent, confidence

    def _extract_keywords(self, text: str) -> List[str]:
        """从文本中提取关键词"""
        # 简单的分词（中文按字符分词，英文按空格分词）
        keywords = []
        words = text.split()

        for word in words:
            # 过滤掉常见的停用词
            if len(word) > 1 and word not in ['的', '是', '在', '和', '或', '与', '进行']:
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
            指导文本，如果意图不存在则返回None
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
            指导文本，如果意图不存在则返回None
        """
        intent = self._intents.get(intent_id)
        if intent and intent.guidance:
            return intent.guidance.completion
        return None

    def get_next_actions(self, intent_id: str) -> List[str]:
        """
        获取可执行的下一步操作

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
        """
        获取后置意图列表

        Args:
            intent_id: 当前意图ID

        Returns:
            后置意图ID列表
        """
        return self._reverse_graph.get(intent_id, [])

    def get_pre_intents(self, intent_id: str) -> List[str]:
        """
        获取前置意图列表

        Args:
            intent_id: 当前意图ID

        Returns:
            前置意图ID列表
        """
        return self._intent_graph.get(intent_id, [])

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
            """深度优先搜索"""
            if current in visited:
                return False

            visited.add(current)
            path.insert(0, current)

            pre_intents = self.get_pre_intents(current)
            if not pre_intents:
                return True

            for pre_intent in pre_intents[:1]:  # 只取第一个前置意图
                if dfs(pre_intent):
                    return True

            path.remove(current)
            return False

        dfs(intent_id)
        return path

    def visualize_graph(self) -> str:
        """
        生成意图图谱的可视化文本

        Returns:
            图谱的文本表示
        """
        lines = []
        lines.append("=" * 60)
        lines.append("意图图谱")
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

    def get_workflow_suggestion(self, user_input: str) -> Dict[str, Any]:
        """
        根据用户输入获取工作流建议

        Args:
            user_input: 用户输入

        Returns:
            包含当前意图、路径和指导的字典
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

    def list_all_intents(self) -> List[Dict[str, Any]]:
        """
        列出所有意图

        Returns:
            意图信息列表
        """
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
        """
        获取引擎状态

        Returns:
            状态信息字典
        """
        return {
            "total_intents": len(self._intents),
            "current_intent": self._current_intent,
            "execution_history": self._execution_history.copy(),
            "available_intents": list(self._intents.keys())
        }
