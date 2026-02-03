"""
意图注册表 - 参考 n8n 的 NodeTypes 管理系统

提供意图的注册、查询和管理功能
"""

from typing import Dict, List, Optional
from collections import defaultdict
from intent_system.core.intent_definition import IntentDefinition


class IntentRegistry:
    """
    意图注册表 - 管理所有已注册的意图

    类似 n8n 的 NodeTypeRegistry，提供：
    - 意图注册与注销
    - 按类别、标签检索
    - 意图验证
    - 注册表导出
    """

    def __init__(self):
        """初始化注册表"""
        self._intents: Dict[str, IntentDefinition] = {}
        self._categories: Dict[str, List[str]] = defaultdict(list)
        self._tags_index: Dict[str, List[str]] = defaultdict(list)

    def register(self, intent: IntentDefinition) -> None:
        """
        注册意图

        Args:
            intent: 意图定义

        Raises:
            ValueError: 如果意图 ID 已存在
        """
        intent_id = intent.metadata.id

        # 验证 ID 唯一性
        if intent_id in self._intents:
            raise ValueError(f"Intent ID '{intent_id}' already registered")

        # 存储意图
        self._intents[intent_id] = intent

        # 更新类别索引
        self._categories[intent.metadata.category].append(intent_id)

        # 更新标签索引
        for tag in intent.metadata.tags:
            self._tags_index[tag].append(intent_id)

    def unregister(self, intent_id: str) -> bool:
        """
        注销意图

        Args:
            intent_id: 意图 ID

        Returns:
            是否成功注销
        """
        if intent_id not in self._intents:
            return False

        # 获取意图定义
        intent = self._intents[intent_id]

        # 从类别索引中移除
        category_list = self._categories[intent.metadata.category]
        if intent_id in category_list:
            category_list.remove(intent_id)

        # 从标签索引中移除
        for tag in intent.metadata.tags:
            tag_list = self._tags_index[tag]
            if intent_id in tag_list:
                tag_list.remove(intent_id)

        # 从主存储中移除
        del self._intents[intent_id]

        return True

    def get(self, intent_id: str) -> Optional[IntentDefinition]:
        """
        获取意图定义

        Args:
            intent_id: 意图 ID

        Returns:
            意图定义，如果不存在则返回 None
        """
        return self._intents.get(intent_id)

    def get_by_category(self, category: str) -> List[IntentDefinition]:
        """
        按类别获取意图

        Args:
            category: 类别名称

        Returns:
            该类别下的所有意图
        """
        return [
            self._intents[intent_id]
            for intent_id in self._categories.get(category, [])
        ]

    def get_by_tags(
        self,
        tags: List[str],
        match_all: bool = False
    ) -> List[IntentDefinition]:
        """
        按标签搜索意图

        Args:
            tags: 标签列表
            match_all: 是否匹配所有标签（AND 逻辑），否则为 OR 逻辑

        Returns:
            匹配的意图列表
        """
        if not tags:
            return []

        intent_ids = set()

        if match_all:
            # AND 逻辑：必须包含所有标签
            intent_ids = set(self._tags_index.get(tags[0], []))
            for tag in tags[1:]:
                intent_ids &= set(self._tags_index.get(tag, []))
        else:
            # OR 逻辑：包含任一标签
            for tag in tags:
                intent_ids.update(self._tags_index.get(tag, []))

        return [self._intents[iid] for iid in intent_ids if iid in self._intents]

    def list_all(self) -> List[IntentDefinition]:
        """
        列出所有意图

        Returns:
            所有已注册的意图
        """
        return list(self._intents.values())

    def list_categories(self) -> List[str]:
        """
        列出所有类别

        Returns:
            类别列表
        """
        return list(self._categories.keys())

    def list_tags(self) -> List[str]:
        """
        列出所有标签

        Returns:
            标签列表
        """
        return list(self._tags_index.keys())

    def count(self) -> int:
        """
        获取已注册意图数量

        Returns:
            意图总数
        """
        return len(self._intents)

    def exists(self, intent_id: str) -> bool:
        """
        检查意图是否存在

        Args:
            intent_id: 意图 ID

        Returns:
            是否存在
        """
        return intent_id in self._intents

    def get_intents_by_dependency(self, dependency_id: str) -> List[IntentDefinition]:
        """
        获取依赖于指定意图的所有意图

        Args:
            dependency_id: 依赖的意图 ID

        Returns:
            依赖于该意图的意图列表
        """
        return [
            intent for intent in self._intents.values()
            if dependency_id in intent.metadata.dependencies
        ]

    def validate_dependencies(self) -> List[str]:
        """
        验证所有意图的依赖关系

        检查：
        1. 依赖的意图是否存在
        2. 是否存在循环依赖

        Returns:
            错误信息列表，空列表表示验证通过
        """
        errors = []

        # 检查依赖的意图是否存在
        for intent_id, intent in self._intents.items():
            for dep_id in intent.metadata.dependencies:
                if dep_id not in self._intents:
                    errors.append(
                        f"Intent '{intent_id}' depends on non-existent intent '{dep_id}'"
                    )

        # 检查循环依赖
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: List[str]) -> bool:
            """深度优先搜索检测循环"""
            if node in rec_stack:
                cycle = " -> ".join(path + [node])
                errors.append(f"Circular dependency detected: {cycle}")
                return True

            if node in visited:
                return False

            visited.add(node)
            rec_stack.add(node)

            if node in self._intents:
                for dep in self._intents[node].metadata.dependencies:
                    if dfs(dep, path + [node]):
                        return True

            rec_stack.remove(node)
            return False

        for intent_id in self._intents:
            if intent_id not in visited:
                dfs(intent_id, [])

        return errors

    def export_registry(self) -> Dict[str, Dict]:
        """
        导出注册表为字典格式

        Returns:
            注册表字典，key 为意图 ID，value 为意图信息的简化版本
        """
        return {
            intent_id: {
                "id": intent.metadata.id,
                "name": intent.metadata.name,
                "description": intent.metadata.description,
                "category": intent.metadata.category,
                "tags": intent.metadata.tags,
                "inputs": list(intent.schema.inputs.keys()),
                "outputs": list(intent.schema.outputs.keys())
            }
            for intent_id, intent in self._intents.items()
        }

    def import_from_dict(self, data: Dict[str, Dict]) -> int:
        """
        从字典导入意图信息（仅元数据，不包含执行器）

        注意：这个方法主要用于注册表信息的查看，实际使用需要
        通过 register() 方法注册完整的 IntentDefinition

        Args:
            data: 意图信息字典

        Returns:
            导入的意图数量
        """
        count = 0
        for intent_id, info in data.items():
            # 这里只做计数，实际注册需要完整的 IntentDefinition
            if intent_id not in self._intents:
                count += 1
        return count

    def __len__(self) -> int:
        """获取意图总数"""
        return len(self._intents)

    def __contains__(self, intent_id: str) -> bool:
        """检查意图是否存在"""
        return intent_id in self._intents

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"IntentRegistry(\n"
            f"  total_intents={len(self._intents)},\n"
            f"  categories={list(self._categories.keys())},\n"
            f"  tags={list(self._tags_index.keys())}\n"
            f")"
        )
