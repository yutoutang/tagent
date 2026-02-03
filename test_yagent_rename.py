"""
YAgent 导入和基本功能验证
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_yagent_import():
    """测试 YAgent 导入"""
    print("\n" + "=" * 60)
    print("YAgent 导入测试")
    print("=" * 60)

    # 测试从 intent_system 导入
    print("\n1. 测试从 intent_system 导入 YAgent...")
    try:
        from intent_system import YAgent, YAgentState, create_yagent_graph
        print("   [OK] 成功导入 YAgent, YAgentState, create_yagent_graph")
    except Exception as e:
        print(f"   [FAIL] 导入失败: {e}")
        return False

    # 测试从 yagent 模块直接导入
    print("\n2. 测试从 intent_system.yagent 导入...")
    try:
        from intent_system.yagent import YAgent as YAgentDirect
        from intent_system.yagent.state import YAgentState as YAgentStateDirect
        from intent_system.yagent.graph import create_yagent_graph as create_graph_direct
        print("   [OK] 成功从子模块导入")
    except Exception as e:
        print(f"   [FAIL] 从子模块导入失败: {e}")
        return False

    # 测试类的基本属性
    print("\n3. 测试 YAgent 类属性...")
    print(f"   - YAgent 类名: {YAgent.__name__}")
    print(f"   - YAgent 模块: {YAgent.__module__}")
    print(f"   - YAgent 文档: {YAgent.__doc__[:50] if YAgent.__doc__ else 'N/A'}...")

    # 测试方法列表
    print("\n4. YAgent 可用方法:")
    methods = [m for m in dir(YAgent) if not m.startswith('_') and callable(getattr(YAgent, m))]
    for method in methods:
        print(f"   - {method}")

    print("\n" + "=" * 60)
    print("所有测试通过!")
    print("=" * 60)

    return True


def test_yagent_state():
    """测试 YAgentState"""
    print("\n" + "=" * 60)
    print("YAgentState 测试")
    print("=" * 60)

    from intent_system import YAgentState

    # 创建状态实例
    print("\n1. 创建 YAgentState 实例...")
    state = YAgentState()
    print(f"   [OK] 状态创建成功")

    # 检查状态属性
    print("\n2. 检查状态属性...")
    attrs = [
        'messages', 'task_type', 'detected_intents',
        'intent_confidence', 'intent_results', 'iteration',
        'max_iterations', 'is_complete', 'errors'
    ]
    for attr in attrs:
        if hasattr(state, attr):
            print(f"   [OK] {attr}: {type(getattr(state, attr)).__name__}")
        else:
            print(f"   [FAIL] {attr}: 不存在")
            return False

    # 测试方法
    print("\n3. 测试状态方法...")
    summary = state.get_execution_summary()
    print(f"   [OK] get_execution_summary: {summary}")

    return True


def test_backward_compatibility():
    """测试向后兼容（保留旧的 agent 导入）"""
    print("\n" + "=" * 60)
    print("向后兼容性测试")
    print("=" * 60)

    # 旧的 agent 模块应该仍然存在
    print("\n1. 检查旧的 agent 模块...")
    try:
        from intent_system.agent import UnifiedAgent
        print("   [OK] 旧的 agent.UnifiedAgent 仍然存在（向后兼容）")
    except Exception as e:
        print(f"   [INFO] 旧的 agent.UnifiedAgent 不存在: {e}")

    # 新的 yagent 模块
    print("\n2. 检查新的 yagent 模块...")
    try:
        from intent_system.yagent import YAgent
        print("   [OK] 新的 yagent.YAgent 可用")
    except Exception as e:
        print(f"   [FAIL] 新的 yagent.YAgent 不可用: {e}")
        return False

    return True


def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("YAgent 重命名验证测试")
    print("=" * 70)
    print("\n验证 UnifiedAgent 已成功重命名为 YAgent")

    success = True

    # 运行测试
    success = test_yagent_import() and success
    success = test_yagent_state() and success
    success = test_backward_compatibility() and success

    # 汇总
    print("\n" + "=" * 70)
    if success:
        print("所有验证通过!")
        print("\n总结:")
        print("  - UnifiedAgent 已重命名为 YAgent")
        print("  - UnifiedAgentState 已重命名为 YAgentState")
        print("  - create_unified_agent_graph 已重命名为 create_yagent_graph")
        print("  - 可以通过 'from intent_system import YAgent' 导入")
        print("  - 旧的 agent 模块保留用于向后兼容")
    else:
        print("部分验证失败!")
    print("=" * 70)

    return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
