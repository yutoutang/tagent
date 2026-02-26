"""
Tool framework for agent execution.

Provides a complete tool execution system with:
- Base tool class with validation
- Parameter schema validation
- Streaming update support
- Built-in common tools
"""
from typing import Any, Callable, Optional, Union, Awaitable, Literal, get_type_hints
from typing_extensions import Protocol, runtime_checkable
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
import json
import inspect

from .types import (
    AgentToolResult,
    TextContent,
    ImageContent,
    AgentToolUpdateCallback,
)


# ============================================================================
# Tool Protocol
# ============================================================================

@runtime_checkable
class ToolExecutor(Protocol):
    """
    Protocol for tool executors.
    Any object with an execute method matching this signature can be used as a tool.
    """

    async def execute(
        self,
        tool_call_id: str,
        params: dict[str, Any],
        signal: Any | None = None,
        on_update: Optional[AgentToolUpdateCallback] = None,
    ) -> AgentToolResult:
        """
        Execute the tool with the given parameters.

        Args:
            tool_call_id: Unique identifier for this tool call
            params: Validated parameters for the tool
            signal: Abort signal for cancellation
            on_update: Callback for streaming partial results

        Returns:
            AgentToolResult with content blocks and details
        """
        ...


# ============================================================================
# Parameter Schema
# ============================================================================

class ParameterType(Enum):
    """Supported parameter types for tool validation."""
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


@dataclass
class ParameterProperty:
    """Defines a parameter property for validation."""
    type: ParameterType
    description: str
    required: bool = False
    default: Any = None
    enum: list[Any] | None = None
    format: str | None = None  # For additional validation (e.g., "email", "uri")


@dataclass
class ToolSchema:
    """Schema definition for a tool's parameters."""
    type: Literal["object"] = "object"
    properties: dict[str, ParameterProperty] = field(default_factory=dict)
    required: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict for LLM consumption."""
        return {
            "type": self.type,
            "properties": {
                name: {
                    "type": prop.type.value,
                    "description": prop.description,
                    **({"default": prop.default} if prop.default is not None else {}),
                    **({"enum": prop.enum} if prop.enum else {}),
                    **({"format": prop.format} if prop.format else {}),
                }
                for name, prop in self.properties.items()
            },
            "required": self.required,
        }


# ============================================================================
# Base Tool Class
# ============================================================================

class BaseTool(ABC, ToolExecutor):
    """
    Abstract base class for all tools.

    Subclasses must implement the execute method and can optionally
    override get_schema for parameter validation.
    """

    # Class-level tool definition
    name: str = ""
    description: str = ""
    label: str = ""

    def __init__(self):
        if not self.name:
            raise ValueError(f"{self.__class__.__name__} must define a 'name' attribute")
        if not self.description:
            raise ValueError(f"{self.__class__.__name__} must define a 'description' attribute")
        if not self.label:
            self.label = self.name.replace("_", " ").title()

    def get_schema(self) -> ToolSchema:
        """
        Get the parameter schema for this tool.
        Override this to provide custom validation.
        """
        return ToolSchema()

    def get_parameters(self) -> dict[str, Any]:
        """Get parameters dict for LLM consumption."""
        return self.get_schema().to_dict()

    async def execute(
        self,
        tool_call_id: str,
        params: dict[str, Any],
        signal: Any | None = None,
        on_update: Optional[AgentToolUpdateCallback] = None,
    ) -> AgentToolResult:
        """
        Execute the tool with validation and error handling.
        """
        # Validate parameters
        validated = self._validate_params(params)

        # Check for abort signal
        if signal and hasattr(signal, 'aborted') and signal.aborted:
            raise RuntimeError("Tool execution aborted")

        # Execute the tool
        try:
            result = await self._execute(tool_call_id, validated, signal, on_update)
        except Exception as e:
            # Return error as tool result
            return {
                "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                "details": {"error": str(e), "error_type": type(e).__name__},
            }

        return result

    @abstractmethod
    async def _execute(
        self,
        tool_call_id: str,
        params: dict[str, Any],
        signal: Any | None,
        on_update: Optional[AgentToolUpdateCallback],
    ) -> AgentToolResult:
        """
        Actual tool implementation. Subclasses must implement this.
        """
        ...

    def _validate_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """Validate parameters against the schema."""
        schema = self.get_schema()

        # If schema has no properties, allow any parameters (for decorator-based tools)
        if not schema.properties:
            return params.copy()

        # Check required parameters
        missing = [p for p in schema.required if p not in params]
        if missing:
            raise ValueError(f"Missing required parameters: {', '.join(missing)}")

        # Validate each parameter
        validated = {}
        for name, value in params.items():
            if name not in schema.properties:
                raise ValueError(f"Unknown parameter: {name}")

            prop = schema.properties[name]
            validated[name] = self._validate_value(name, value, prop)

        # Add defaults for missing optional parameters
        for name, prop in schema.properties.items():
            if name not in validated and prop.default is not None:
                validated[name] = prop.default

        return validated

    def _validate_value(self, name: str, value: Any, prop: ParameterProperty) -> Any:
        """Validate a single value against its property definition."""
        # Type validation
        if prop.type == ParameterType.STRING:
            if not isinstance(value, str):
                raise ValueError(f"Parameter '{name}' must be a string")
        elif prop.type == ParameterType.NUMBER:
            if not isinstance(value, (int, float)):
                raise ValueError(f"Parameter '{name}' must be a number")
        elif prop.type == ParameterType.INTEGER:
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValueError(f"Parameter '{name}' must be an integer")
        elif prop.type == ParameterType.BOOLEAN:
            if not isinstance(value, bool):
                raise ValueError(f"Parameter '{name}' must be a boolean")
        elif prop.type == ParameterType.ARRAY:
            if not isinstance(value, list):
                raise ValueError(f"Parameter '{name}' must be an array")
        elif prop.type == ParameterType.OBJECT:
            if not isinstance(value, dict):
                raise ValueError(f"Parameter '{name}' must be an object")

        # Enum validation
        if prop.enum and value not in prop.enum:
            raise ValueError(
                f"Parameter '{name}' must be one of: {', '.join(map(str, prop.enum))}"
            )

        # Format validation (simplified)
        if prop.format and isinstance(value, str):
            if prop.format == "email" and "@" not in value:
                raise ValueError(f"Parameter '{name}' must be a valid email")
            elif prop.format == "uri" and not value.startswith(("http://", "https://", "file://")):
                raise ValueError(f"Parameter '{name}' must be a valid URI")

        return value

    def to_dict(self) -> dict[str, Any]:
        """Convert tool to dict format for LLM consumption."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.get_parameters(),
            "label": self.label,
        }


# ============================================================================
# Synchronous Tool Wrapper
# ============================================================================

class SyncToolWrapper(BaseTool):
    """
    Wrapper for tools with synchronous execute implementations.
    Automatically runs sync methods in an executor.
    """

    @abstractmethod
    def execute_sync(
        self,
        tool_call_id: str,
        params: dict[str, Any],
    ) -> AgentToolResult:
        """
        Synchronous tool implementation.
        """
        ...

    async def _execute(
        self,
        tool_call_id: str,
        params: dict[str, Any],
        signal: Any | None,
        on_update: Optional[AgentToolUpdateCallback],
    ) -> AgentToolResult:
        """Run sync execute in executor."""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.execute_sync(tool_call_id, params),
        )


# ============================================================================
# Function Tool (Decorator-Based)
# ============================================================================

def tool(
    name: str | None = None,
    description: str = "",
    parameters: ToolSchema | None = None,
):
    """
    Decorator to convert a function into a tool.

    @example
    ```python
    @tool(name="calculate", description="Perform a calculation")
    async def calculate_tool(params: dict) -> AgentToolResult:
        a = params["a"]
        b = params["b"]
        result = a + b
        return {
            "content": [{"type": "text", "text": f"Result: {result}"}],
            "details": {"result": result},
        }
    ```
    """

    def decorator(func: Callable):
        # Extract metadata from function if not provided
        tool_name = name or func.__name__
        tool_description = description or func.__doc__ or f"Tool: {tool_name}"

        class FunctionTool(BaseTool):
            name = tool_name
            description = tool_description
            label = tool_name.replace("_", " ").title()

            def __init__(self):
                super().__init__()
                self._func = func
                if parameters:
                    self._schema = parameters
                else:
                    # Try to infer schema from function signature
                    self._schema = self._infer_schema()

            def get_schema(self) -> ToolSchema:
                return self._schema

            async def _execute(
                self,
                tool_call_id: str,
                params: dict[str, Any],
                signal: Any | None,
                on_update: Optional[AgentToolUpdateCallback],
            ) -> AgentToolResult:
                # Call the function
                if inspect.iscoroutinefunction(func):
                    return await func(params)
                else:
                    return func(params)

            def _infer_schema(self) -> ToolSchema:
                """Infer schema from function signature."""
                sig = inspect.signature(func)
                params_schema = ToolSchema()

                # Assume first param is 'params: dict'
                # Try to get type hints
                try:
                    hints = get_type_hints(func)
                except Exception:
                    hints = {}

                # For now, return empty schema
                # A full implementation would inspect the dict structure
                return params_schema

        return FunctionTool()

    return decorator


# ============================================================================
# Built-in Tools
# ============================================================================

class NoOpTool(BaseTool):
    """A tool that does nothing. Useful for testing."""

    name = "noop"
    description = "A tool that does nothing and returns a success message."
    label = "No Operation"

    async def _execute(
        self,
        tool_call_id: str,
        params: dict[str, Any],
        signal: Any | None,
        on_update: Optional[AgentToolUpdateCallback],
    ) -> AgentToolResult:
        return {
            "content": [{"type": "text", "text": "No operation performed successfully."}],
            "details": {"status": "ok", "params": params},
        }


class EchoTool(BaseTool):
    """A tool that echoes back its input. Useful for testing."""

    name = "echo"
    description = "Echoes back the input message."
    label = "Echo"

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            properties={
                "message": ParameterProperty(
                    type=ParameterType.STRING,
                    description="The message to echo back",
                    required=True,
                ),
            },
            required=["message"],
        )

    async def _execute(
        self,
        tool_call_id: str,
        params: dict[str, Any],
        signal: Any | None,
        on_update: Optional[AgentToolUpdateCallback],
    ) -> AgentToolResult:
        message = params.get("message", "")
        return {
            "content": [{"type": "text", "text": f"Echo: {message}"}],
            "details": {"original_message": message},
        }


class CalculatorTool(BaseTool):
    """A simple calculator tool."""

    name = "calculator"
    description = "Perform basic arithmetic operations."
    label = "Calculator"

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            properties={
                "operation": ParameterProperty(
                    type=ParameterType.STRING,
                    description="The operation to perform",
                    required=True,
                    enum=["add", "subtract", "multiply", "divide"],
                ),
                "a": ParameterProperty(
                    type=ParameterType.NUMBER,
                    description="First operand",
                    required=True,
                ),
                "b": ParameterProperty(
                    type=ParameterType.NUMBER,
                    description="Second operand",
                    required=True,
                ),
            },
            required=["operation", "a", "b"],
        )

    async def _execute(
        self,
        tool_call_id: str,
        params: dict[str, Any],
        signal: Any | None,
        on_update: Optional[AgentToolUpdateCallback],
    ) -> AgentToolResult:
        operation = params["operation"]
        a = params["a"]
        b = params["b"]

        if operation == "add":
            result = a + b
        elif operation == "subtract":
            result = a - b
        elif operation == "multiply":
            result = a * b
        elif operation == "divide":
            if b == 0:
                raise ValueError("Division by zero")
            result = a / b
        else:
            raise ValueError(f"Unknown operation: {operation}")

        return {
            "content": [{"type": "text", "text": f"Result: {result}"}],
            "details": {"operation": operation, "operands": [a, b], "result": result},
        }


class GetCurrentTimeTool(BaseTool):
    """Tool to get the current time."""

    name = "get_current_time"
    description = "Get the current date and time."
    label = "Get Current Time"

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            properties={
                "timezone": ParameterProperty(
                    type=ParameterType.STRING,
                    description="Timezone (e.g., 'UTC', 'America/New_York')",
                    required=False,
                    default="UTC",
                ),
                "format": ParameterProperty(
                    type=ParameterType.STRING,
                    description="Format string (default: ISO format)",
                    required=False,
                    default=None,
                ),
            },
            required=[],
        )

    async def _execute(
        self,
        tool_call_id: str,
        params: dict[str, Any],
        signal: Any | None,
        on_update: Optional[AgentToolUpdateCallback],
    ) -> AgentToolResult:
        from datetime import datetime
        import pytz

        timezone = params.get("timezone", "UTC")
        fmt = params.get("format")

        try:
            tz = pytz.timezone(timezone)
            now = datetime.now(tz)

            if fmt:
                time_str = now.strftime(fmt)
            else:
                time_str = now.isoformat()

            return {
                "content": [{"type": "text", "text": f"Current time: {time_str}"}],
                "details": {"timezone": timezone, "time": time_str},
            }
        except Exception as e:
            raise ValueError(f"Invalid timezone: {timezone}")


class WebSearchTool(BaseTool):
    """Tool to perform web searches (placeholder implementation)."""

    name = "web_search"
    description = "Search the web for information."
    label = "Web Search"

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            properties={
                "query": ParameterProperty(
                    type=ParameterType.STRING,
                    description="The search query",
                    required=True,
                ),
                "num_results": ParameterProperty(
                    type=ParameterType.INTEGER,
                    description="Number of results to return",
                    required=False,
                    default=5,
                ),
            },
            required=["query"],
        )

    async def _execute(
        self,
        tool_call_id: str,
        params: dict[str, Any],
        signal: Any | None,
        on_update: Optional[AgentToolUpdateCallback],
    ) -> AgentToolResult:
        # Placeholder implementation
        # In a real implementation, this would call a search API
        query = params["query"]
        num_results = params.get("num_results", 5)

        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Search results for '{query}':\n"
                    f"(This is a placeholder - implement actual search API)\n"
                    f"Requested {num_results} results.",
                }
            ],
            "details": {"query": query, "num_results": num_results},
        }


# ============================================================================
# Tool Registry
# ============================================================================

class ToolRegistry:
    """Registry for managing available tools."""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        """Unregister a tool by name."""
        if name in self._tools:
            del self._tools[name]

    def get(self, name: str) -> BaseTool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def get_all(self) -> list[BaseTool]:
        """Get all registered tools."""
        return list(self._tools.values())

    def to_list(self) -> list[dict[str, Any]]:
        """Convert all tools to dict format for LLM."""
        return [tool.to_dict() for tool in self._tools.values()]


# Default registry with built-in tools
_default_registry = ToolRegistry()
_default_registry.register(NoOpTool())
_default_registry.register(EchoTool())
_default_registry.register(CalculatorTool())
_default_registry.register(GetCurrentTimeTool())
_default_registry.register(WebSearchTool())


def get_default_registry() -> ToolRegistry:
    """Get the default tool registry with built-in tools."""
    return _default_registry


def get_builtin_tools() -> list[BaseTool]:
    """Get all built-in tools as a list."""
    return _default_registry.get_all()
