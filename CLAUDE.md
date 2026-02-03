# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**tagent** is a Python-based dynamic agent framework built on LangGraph, featuring an intent management system inspired by Dify and n8n. It combines LLM-driven task classification, tool registration, and DAG-based intent orchestration.

**Python**: 3.8+ (tested with 3.12.7)
**Package**: `intent-system` (installable via `pip install -e .`)

## Development Commands

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Install intent_system as editable package
pip install -e .

# Configure environment
cp .env.example .env
# Edit .env with OPENAI_API_KEY or ANTHROPIC_API_KEY
```

### Running
```bash
# Interactive menu (recommended for first-time users)
python quickstart.py

# Run tests
python test_agent.py

# Verify intent_system installation
python scripts/test_install.py

# Run examples
python examples/intent_basic_usage.py         # Basic intent system usage
python examples/custom_intent.py              # Custom intent creation
python examples/unified_agent_demo.py          # YAgent usage examples
python examples/sdlc_workflow_y_agent.py # YAgent SDLC workflow
python examples/workflow_with_agent.py        # Agent + workflow integration
python examples/workflow_example.py           # Workflow examples
```

### Testing
No formal pytest setup exists. Tests are run as standalone Python scripts:
- `test_agent.py` - Framework tests (basic, custom tools, multi-turn, streaming, errors)
- `scripts/test_install.py` - Intent system installation verification
- `examples/*.py` - Usage examples that serve as integration tests

## Architecture

### YAgent (`intent_system/yagent/`)

A unified agent framework that combines `dynamic_agent_framework` and the intent system. Now renamed to `YAgent` for brevity.

**Directory Structure**:
```
intent_system/yagent/
├── state.py       # YAgentState - unified state definition
├── nodes.py       # LangGraph nodes (parse, orchestrate, execute, reflect, synthesize)
├── graph.py       # Graph construction with routing logic
└── agent.py       # YAgent class - main interface
```

**Key Components**:
- `YAgent`: Main agent class that replaces `UnifiedAgent`
- `YAgentState`: Unified state combining all features
- `create_yagent_graph()`: Builds the LangGraph workflow

**Quick Start**:
```python
from intent_system import YAgent

agent = YAgent()
result = agent.run("Your query")
```

### Core Framework (`dynamic_agent_framework.py`)

A LangGraph-based agent with a 5-stage execution pipeline:

```
START → Classify → Plan → Decide → Execute/Synthesize → Reflect → END
                    ↑                                    ↑
                    └──────────── Iteration ──────────────┘
```

**Key Components**:
- `TaskType` enum: 5 task types (coding, research, analysis, calculation, general)
- `ToolRegistry`: Dynamic tool registration and task-type-based loading
- `AgentState`: TypedDict state with message history, task info, execution tracking
- **5 Core Nodes**:
  - `task_classifier_node` - LLM-powered task classification
  - `planner_node` - Execution planning
  - `decide_next_action` - Conditional routing
  - `executor_node` - Tool execution
  - `reflector_node` - Result evaluation and iteration decision
  - `synthesizer_node` - Final result synthesis

**Built-in tools**: code_analyzer, web_searcher, data_calculator, document_summarizer, api_client

### Intent System (`intent_system/`)

A separate installable package that provides modular intent management. Design philosophy draws from n8n (node modularization, data mapping expressions) and Dify (graph engine, JSON Schema interfaces).

**Directory Structure**:
```
intent_system/
├── core/
│   ├── intent_definition.py    # IntentMetadata, InputOutputSchema, IntentDefinition
│   ├── intent_registry.py      # Registration, indexing, dependency validation
│   ├── intent_parser.py        # LLM-driven intent recognition
│   └── state.py                # Enhanced state definitions
├── orchestration/
│   └── orchestrator.py         # DAG construction, topological sort, layer-based parallel execution
├── execution/
│   ├── intent_executor.py      # Async execution, parallel within layers
│   └── execution_tracker.py    # Execution tracking
├── data_flow/
│   └── data_flow_engine.py     # n8n-style expression parsing ({{ $json.field }})
├── workflow/
│   ├── workflow_manager.py     # Workflow intent management
│   ├── workflow_intent.py      # Workflow intent definitions
│   └── json_loader.py          # JSON workflow loader
└── builtin_intents/
    └── data_intents.py         # 6 built-in intents (http_request, calculator, web_search, data_analysis, text_processing, file_read)
```

**Core Workflow**:
1. Parse user input with `IntentParser` (LLM-driven, multi-intent detection)
2. Orchestrate with `IntentOrchestrator` (DAG construction, topological sorting)
3. Execute with `IntentExecutor` (layer-based parallel execution)

### Integration Layer (`intent_system_integration.py`)

`IntentEnhancedAgent` extends `DynamicAgent` with intent system support. Fully backward compatible - toggle intent system on/off via `use_intents` parameter.

## Entry Points

**Main entry points**:
- `quickstart.py` - Interactive menu system
- `dynamic_agent_framework.py` - Core framework (runnable directly)
- `test_agent.py` - Test suite

**Programmatic usage**:
```python
# YAgent (recommended)
from intent_system import YAgent
agent = YAgent()
result = agent.run("Your query")

# Basic agent
from dynamic_agent_framework import DynamicAgent
agent = DynamicAgent()
result = agent.chat("Your query")

# Intent-enhanced agent
from intent_system_integration import IntentEnhancedAgent
agent = IntentEnhancedAgent()
result = agent.run_with_intents("Your query", use_intents=True)

# Standalone intent system
from intent_system import IntentRegistry, IntentParser, IntentOrchestrator, IntentExecutor
from intent_system.builtin_intents import register_builtin_data_intents

registry = IntentRegistry()
register_builtin_data_intents(registry)
```

## Important Implementation Notes

### LLM Provider Flexibility
- Supports both OpenAI (`OPENAI_API_KEY`) and Anthropic (`ANTHROPIC_API_KEY`)
- Controlled by `LLM_PROVIDER` env variable (default: "openai")
- Model name via `MODEL_NAME` env variable (default: "gpt-4o")

### State Management
- LangGraph StateGraph with checkpoint memory (MemorySaver)
- Multi-turn conversation support via `thread_id` in config
- Conversation history persisted in `AgentState.messages`

### Tool Registration
Tools are registered with metadata including:
- `task_types`: List of task types that trigger this tool
- `description`: Human-readable description for LLM
- `parameters`: Optional parameter schema

### Intent System Patterns

**Intent Definition** - Use Pydantic models for type safety:
```python
from intent_system.core import IntentDefinition, IntentMetadata, InputOutputSchema

intent = IntentDefinition(
    metadata=IntentMetadata(
        id="my_intent",
        name="My Intent",
        description="Description",
        category="data",
        tags=["api"],
        dependencies=[]  # Empty for standalone
    ),
    schema=InputOutputSchema(
        inputs={"param": {"type": "string", "required": True}},
        outputs={"result": {"type": "object"}}
    ),
    executor=my_function
)
```

**Data Flow Expressions** - n8n-style for intent chaining:
```python
# Reference previous output
mapping = {
    "temperature": "{{ $json.temperature }}",
    "city": "{{ $json.city }}"
}
```

**Dependency Management** - Declare explicitly to enable DAG orchestration:
```python
metadata=IntentMetadata(
    dependencies=["step1", "step2"]  # Must complete first
)
```

## File Relationships

### Must Understand for Modifications
1. `intent_system/yagent/agent.py` - YAgent main class (replaces UnifiedAgent)
2. `intent_system/yagent/state.py` - YAgentState definition
3. `intent_system/yagent/nodes.py` - LangGraph node implementations
4. `intent_system/yagent/graph.py` - Graph construction and routing
5. `dynamic_agent_framework.py` - Core agent execution pipeline
6. `intent_system/core/intent_definition.py` - Intent data model
7. `intent_system/orchestration/orchestrator.py` - DAG orchestration logic
8. `intent_system_integration.py` - Integration layer

### Key Examples
1. `examples/workflow_with_agent.py` - Complete real-world integration
2. `examples/intent_basic_usage.py` - Intent system basics
3. `examples/unified_agent_demo.py` - YAgent usage examples
4. `examples/sdlc_workflow_unified_agent.py` - YAgent SDLC workflow
5. `advanced_examples.py` - Framework advanced features (streaming, batch processing, custom routing)

## Best Practices from Codebase

1. **Keep intents single-responsibility** - One intent should do one thing well
2. **Clear parameter definitions** - Use JSON Schema with descriptions and validation
3. **Explicit dependency declarations** - Enable proper DAG orchestration
4. **Comprehensive error handling** - Return structured error responses from tools/intents
5. **Type safety** - Use TypedDict and Pydantic models throughout

## Code Style

- Chinese comments and documentation throughout codebase
- Comprehensive docstrings
- Type hints required (using `typing` module and Pydantic)
- LangChain `@tool` decorator for tool/intent functions
