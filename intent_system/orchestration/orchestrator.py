"""
意图编排引擎 - 核心编排逻辑

实现意图的动态编排、依赖解析和执行分层
"""

from typing import Any, Dict, List, Optional
from collections import deque

from intent_system.core.intent_registry import IntentRegistry
from intent_system.core.intent_parser import IntentParseResult
from intent_system.core.state import IntentOrchestrationPlan


class IntentOrchestrator:
    """
    意图编排引擎

    核心功能：
    1. 构建依赖图（DAG）
    2. 拓扑排序确定执行顺序
    3. 分层识别可并行执行的意图
    4. 生成数据映射
    """

    def __init__(self, registry: IntentRegistry):
        """
        初始化编排引擎

        Args:
            registry: 意图注册表
        """
        self.registry = registry

    def orchestrate(
        self,
        parse_result: IntentParseResult,
        context: Optional[Dict[str, Any]] = None
    ) -> IntentOrchestrationPlan:
        """
        编排意图执行计划

        Args:
            parse_result: 意图解析结果
            context: 可选的上下文信息

        Returns:
            意图编排计划
        """
        # 1. 收集所有意图
        all_intents = parse_result.get_all_intent_ids()

        if not all_intents:
            return IntentOrchestrationPlan()

        # 2. 构建依赖图
        dependency_graph = self._build_dependency_graph(
            all_intents,
            parse_result.dependencies
        )

        # 3. 拓扑排序 - 确定执行顺序
        try:
            execution_order = self._topological_sort(dependency_graph)
        except ValueError as e:
            # 检测到循环依赖，使用简单顺序
            execution_order = all_intents

        # 4. 分层 - 识别可并行执行的意图
        execution_layers = self._build_execution_layers(
            dependency_graph,
            execution_order
        )

        # 5. 生成数据映射
        data_mappings = self._generate_data_mappings(
            all_intents,
            parse_result,
            context
        )

        return IntentOrchestrationPlan(
            execution_graph=dependency_graph,
            execution_layers=execution_layers,
            data_mappings=data_mappings,
            execution_order=execution_order
        )

    def _build_dependency_graph(
        self,
        intent_ids: List[str],
        additional_dependencies: List[str]
    ) -> Dict[str, List[str]]:
        """
        构建依赖图（DAG）

        Args:
            intent_ids: 所有意图ID列表
            additional_dependencies: 额外的依赖关系

        Returns:
            依赖图，key为意图ID，value为依赖于它的意图列表
        """
        # 初始化图
        graph = {intent_id: [] for intent_id in intent_ids}

        # 添加从意图元数据中定义的依赖
        for intent_id in intent_ids:
            intent_def = self.registry.get(intent_id)
            if intent_def and intent_def.metadata.dependencies:
                for dep_id in intent_def.metadata.dependencies:
                    if dep_id in graph:
                        # dep_id -> intent_id (intent_id 依赖于 dep_id)
                        # 在图中表示为 dep_id 的邻接表包含 intent_id
                        graph[dep_id].append(intent_id)

        # 添加从解析结果中获取的额外依赖
        for dep_relation in additional_dependencies:
            # dep_relation 格式: "A depends on B" 或 ["A", "B"]
            if isinstance(dep_relation, str) and " depends on " in dep_relation:
                parts = dep_relation.split(" depends on ")
                if len(parts) == 2:
                    intent_id, dep_id = parts[0].strip(), parts[1].strip()
                    if intent_id in graph and dep_id in graph:
                        graph[dep_id].append(intent_id)

        return graph

    def _topological_sort(
        self,
        graph: Dict[str, List[str]]
    ) -> List[str]:
        """
        拓扑排序 - Kahn 算法

        Args:
            graph: 依赖图

        Returns:
            拓扑排序后的意图列表

        Raises:
            ValueError: 如果检测到循环依赖
        """
        # 计算入度
        in_degree = {node: 0 for node in graph}

        for node in graph:
            for dependent in graph[node]:
                if dependent in in_degree:
                    in_degree[dependent] += 1

        # 找到入度为0的节点
        queue = deque([node for node in in_degree if in_degree[node] == 0])
        result = []

        while queue:
            node = queue.popleft()
            result.append(node)

            # 减少依赖此节点的节点的入度
            for dependent in graph[node]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        # 检查是否所有节点都被处理
        if len(result) != len(graph):
            raise ValueError("检测到循环依赖")

        return result

    def _build_execution_layers(
        self,
        graph: Dict[str, List[str]],
        execution_order: List[str]
    ) -> List[List[str]]:
        """
        构建执行层级 - 支持并行执行

        同层的意图没有依赖关系，可以并行执行

        Args:
            graph: 依赖图
            execution_order: 执行顺序

        Returns:
            分层列表，每层包含可并行执行的意图
        """
        layers = []
        placed = set()

        # 按拓扑顺序处理
        for node in execution_order:
            # 检查所有依赖是否已放置
            dependencies = self._get_dependencies(node, graph)
            if not all(dep in placed for dep in dependencies):
                # 依赖未全部放置，跳过
                continue

            # 尝试放入现有层
            placed_in_layer = False
            for layer in layers:
                # 检查是否可以加入该层（与层内所有节点无依赖关系）
                can_join = True
                for placed_node in layer:
                    # 检查 node 是否依赖于 placed_node
                    if placed_node in dependencies:
                        can_join = False
                        break
                    # 检查 placed_node 是否依赖于 node
                    if node in self._get_dependencies(placed_node, graph):
                        can_join = False
                        break

                if can_join:
                    layer.append(node)
                    placed.add(node)
                    placed_in_layer = True
                    break

            # 如果无法加入现有层，创建新层
            if not placed_in_layer:
                layers.append([node])
                placed.add(node)

        return layers

    def _get_dependencies(
        self,
        node: str,
        graph: Dict[str, List[str]]
    ) -> List[str]:
        """
        获取节点的所有依赖

        Args:
            node: 节点ID
            graph: 依赖图

        Returns:
            依赖列表
        """
        dependencies = []

        # 在图中，如果 A 在 B 的邻接表中，说明 B 依赖于 A
        # 所以我们需要找出所有包含 node 的邻接表
        for other_node, neighbors in graph.items():
            if node in neighbors:
                dependencies.append(other_node)

        return dependencies

    def _generate_data_mappings(
        self,
        intent_ids: List[str],
        parse_result: IntentParseResult,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Dict[str, str]]:
        """
        生成数据映射

        为每个意图生成输入数据映射，支持引用其他意图的输出

        Args:
            intent_ids: 意图ID列表
            parse_result: 解析结果
            context: 上下文信息

        Returns:
            数据映射字典
        """
        mappings = {}

        for intent_id in intent_ids:
            intent_def = self.registry.get(intent_id)
            if not intent_def:
                continue

            # 获取该意图的参数
            intent_params = parse_result.get_intent_parameters(intent_id)

            # 生成输入数据映射
            input_mapping = {}
            for param_name, param_def in intent_def.schema.inputs.items():
                # 优先使用意图特定的参数
                if param_name in intent_params:
                    input_mapping[param_name] = intent_params[param_name]
                # 其次使用全局参数
                elif param_name in parse_result.parameters:
                    input_mapping[param_name] = parse_result.parameters[param_name]
                # 其次使用上下文
                elif context and param_name in context:
                    # 使用 n8n 风格的表达式
                    input_mapping[param_name] = f"{{{{ $json.{param_name} }}}}"
                # 最后使用默认值
                elif "default" in param_def:
                    input_mapping[param_name] = str(param_def["default"])

            mappings[intent_id] = input_mapping

        return mappings

    def orchestrate_from_intents(
        self,
        intent_ids: List[str],
        parameters: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> IntentOrchestrationPlan:
        """
        直接从意图列表编排（跳过解析步骤）

        Args:
            intent_ids: 意图ID列表
            parameters: 参数字典
            context: 上下文信息

        Returns:
            意图编排计划
        """
        # 创建简化的解析结果
        from intent_system.core.intent_parser import IntentParseResult

        parse_result = IntentParseResult(
            primary_intent=intent_ids[0] if intent_ids else "",
            confidence=1.0,
            sub_intents=[
                {"id": iid, "parameters": parameters or {}}
                for iid in intent_ids[1:]
            ],
            parameters=parameters or {},
            dependencies=[],
            reasoning="直接从意图列表编排"
        )

        return self.orchestrate(parse_result, context)

    def can_execute_in_parallel(
        self,
        intent_ids: List[str]
    ) -> bool:
        """
        检查一组意图是否可以并行执行

        Args:
            intent_ids: 意图ID列表

        Returns:
            是否可以并行执行
        """
        if not intent_ids or len(intent_ids) < 2:
            return True

        # 构建简单的依赖关系检查
        for intent_id in intent_ids:
            intent_def = self.registry.get(intent_id)
            if intent_def:
                # 检查是否依赖于列表中的其他意图
                for dep_id in intent_def.metadata.dependencies:
                    if dep_id in intent_ids:
                        return False

                # 检查是否有冲突
                for conflict_id in intent_def.metadata.conflicts:
                    if conflict_id in intent_ids:
                        return False

        return True
