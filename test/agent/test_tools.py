"""
Tests for the pi.agent tool framework.
"""
import pytest
import asyncio
from pi.agent import (
    BaseTool,
    CalculatorTool,
    EchoTool,
    NoOpTool,
    ToolRegistry,
    ToolSchema,
    ParameterType,
    ParameterProperty,
    tool,
    get_builtin_tools,
)


class TestParameterTypes:
    """Test parameter type definitions."""

    def test_parameter_type_enum(self):
        """Test ParameterType enum values."""
        assert ParameterType.STRING.value == "string"
        assert ParameterType.NUMBER.value == "number"
        assert ParameterType.INTEGER.value == "integer"
        assert ParameterType.BOOLEAN.value == "boolean"
        assert ParameterType.ARRAY.value == "array"
        assert ParameterType.OBJECT.value == "object"

    def test_parameter_property(self):
        """Test ParameterProperty dataclass."""
        prop = ParameterProperty(
            type=ParameterType.STRING,
            description="Test parameter",
            required=True,
            default="default_value",
        )
        assert prop.type == ParameterType.STRING
        assert prop.description == "Test parameter"
        assert prop.required is True
        assert prop.default == "default_value"


class TestToolSchema:
    """Test ToolSchema functionality."""

    def test_empty_schema(self):
        """Test empty schema."""
        schema = ToolSchema()
        assert schema.type == "object"
        assert len(schema.properties) == 0
        assert len(schema.required) == 0

    def test_schema_with_properties(self):
        """Test schema with properties."""
        schema = ToolSchema(
            properties={
                "name": ParameterProperty(
                    type=ParameterType.STRING,
                    description="Name parameter",
                    required=True,
                ),
                "age": ParameterProperty(
                    type=ParameterType.INTEGER,
                    description="Age parameter",
                    required=False,
                ),
            },
            required=["name"],
        )
        assert len(schema.properties) == 2
        assert "name" in schema.required
        assert "age" not in schema.required

    def test_schema_to_dict(self):
        """Test converting schema to dict."""
        schema = ToolSchema(
            properties={
                "message": ParameterProperty(
                    type=ParameterType.STRING,
                    description="A message",
                    required=True,
                ),
            },
            required=["message"],
        )
        result = schema.to_dict()
        assert result["type"] == "object"
        assert "message" in result["properties"]
        assert result["properties"]["message"]["type"] == "string"
        assert "message" in result["required"]


class TestBaseTool:
    """Test BaseTool functionality."""

    def test_base_tool_requires_name_and_description(self):
        """Test that BaseTool requires name and description."""
        with pytest.raises(ValueError, match="must define a 'name' attribute"):
            class InvalidTool(BaseTool):
                name = ""
                description = "Test"

                async def _execute(self, tool_call_id, params, signal, on_update):
                    return {"content": [], "details": {}}

            InvalidTool()

    def test_base_tool_default_label(self):
        """Test default label generation."""
        class TestTool(BaseTool):
            name = "test_tool_name"
            description = "Test tool"

            async def _execute(self, tool_call_id, params, signal, on_update):
                return {
                    "content": [{"type": "text", "text": "OK"}],
                    "details": {},
                }

        tool = TestTool()
        assert tool.label == "Test Tool Name"

    def test_tool_to_dict(self):
        """Test converting tool to dict format."""
        class SimpleTool(BaseTool):
            name = "simple"
            description = "A simple tool"

            def get_schema(self) -> ToolSchema:
                return ToolSchema(
                    properties={
                        "input": ParameterProperty(
                            type=ParameterType.STRING,
                            description="Input value",
                            required=True,
                        ),
                    },
                    required=["input"],
                )

            async def _execute(self, tool_call_id, params, signal, on_update):
                return {
                    "content": [{"type": "text", "text": f"Got: {params['input']}"}],
                    "details": {"input": params["input"]},
                }

        tool = SimpleTool()
        result = tool.to_dict()
        assert result["name"] == "simple"
        assert result["description"] == "A simple tool"
        assert "parameters" in result
        assert result["parameters"]["type"] == "object"

    @pytest.mark.asyncio
    async def test_tool_parameter_validation(self):
        """Test parameter validation."""
        class ValidatedTool(BaseTool):
            name = "validated"
            description = "Tool with validation"

            def get_schema(self) -> ToolSchema:
                return ToolSchema(
                    properties={
                        "required_param": ParameterProperty(
                            type=ParameterType.STRING,
                            description="Required parameter",
                            required=True,
                        ),
                        "optional_param": ParameterProperty(
                            type=ParameterType.STRING,
                            description="Optional parameter",
                            required=False,
                            default="default",
                        ),
                    },
                    required=["required_param"],
                )

            async def _execute(self, tool_call_id, params, signal, on_update):
                return {
                    "content": [{"type": "text", "text": "OK"}],
                    "details": params,
                }

        tool = ValidatedTool()

        # Valid parameters
        result = await tool.execute("call-1", {"required_param": "value"})
        assert "required_param" in result["details"]

        # Missing required parameter
        with pytest.raises(ValueError, match="Missing required parameters"):
            await tool.execute("call-2", {})

        # Unknown parameter
        with pytest.raises(ValueError, match="Unknown parameter"):
            await tool.execute("call-3", {"required_param": "value", "unknown": "value"})

    @pytest.mark.asyncio
    async def test_tool_type_validation(self):
        """Test type validation for parameters."""
        class TypedTool(BaseTool):
            name = "typed"
            description = "Tool with type validation"

            def get_schema(self) -> ToolSchema:
                return ToolSchema(
                    properties={
                        "string_param": ParameterProperty(
                            type=ParameterType.STRING,
                            description="String parameter",
                            required=True,
                        ),
                        "int_param": ParameterProperty(
                            type=ParameterType.INTEGER,
                            description="Integer parameter",
                            required=True,
                        ),
                        "bool_param": ParameterProperty(
                            type=ParameterType.BOOLEAN,
                            description="Boolean parameter",
                            required=True,
                        ),
                    },
                    required=["string_param", "int_param", "bool_param"],
                )

            async def _execute(self, tool_call_id, params, signal, on_update):
                return {
                    "content": [{"type": "text", "text": "OK"}],
                    "details": params,
                }

        tool = TypedTool()

        # Correct types
        result = await tool.execute("call-1", {
            "string_param": "hello",
            "int_param": 42,
            "bool_param": True,
        })
        assert result["details"]["string_param"] == "hello"
        assert result["details"]["int_param"] == 42
        assert result["details"]["bool_param"] is True

        # Wrong types
        with pytest.raises(ValueError, match="must be a string"):
            await tool.execute("call-2", {
                "string_param": 123,
                "int_param": 42,
                "bool_param": True,
            })

        with pytest.raises(ValueError, match="must be an integer"):
            await tool.execute("call-3", {
                "string_param": "hello",
                "int_param": "not_an_int",
                "bool_param": True,
            })

    @pytest.mark.asyncio
    async def test_tool_enum_validation(self):
        """Test enum validation for parameters."""
        class EnumTool(BaseTool):
            name = "enum_test"
            description = "Tool with enum validation"

            def get_schema(self) -> ToolSchema:
                return ToolSchema(
                    properties={
                        "choice": ParameterProperty(
                            type=ParameterType.STRING,
                            description="Choice parameter",
                            required=True,
                            enum=["option1", "option2", "option3"],
                        ),
                    },
                    required=["choice"],
                )

            async def _execute(self, tool_call_id, params, signal, on_update):
                return {
                    "content": [{"type": "text", "text": "OK"}],
                    "details": params,
                }

        tool = EnumTool()

        # Valid enum value
        result = await tool.execute("call-1", {"choice": "option1"})
        assert result["details"]["choice"] == "option1"

        # Invalid enum value
        with pytest.raises(ValueError, match="must be one of"):
            await tool.execute("call-2", {"choice": "invalid_option"})


class TestBuiltinTools:
    """Test built-in tools."""

    @pytest.mark.asyncio
    async def test_noop_tool(self):
        """Test NoOpTool."""
        tool = NoOpTool()
        assert tool.name == "noop"

        result = await tool.execute("call-1", {"any": "params"})
        assert "content" in result
        assert len(result["content"]) > 0
        assert result["details"]["status"] == "ok"

    @pytest.mark.asyncio
    async def test_echo_tool(self):
        """Test EchoTool."""
        tool = EchoTool()
        assert tool.name == "echo"

        result = await tool.execute("call-1", {"message": "Hello!"})
        assert "content" in result
        assert "Echo: Hello!" in result["content"][0]["text"]
        assert result["details"]["original_message"] == "Hello!"

    @pytest.mark.asyncio
    async def test_calculator_tool(self):
        """Test CalculatorTool."""
        tool = CalculatorTool()
        assert tool.name == "calculator"

        # Addition
        result = await tool.execute("call-1", {
            "operation": "add",
            "a": 5,
            "b": 3,
        })
        assert result["details"]["result"] == 8

        # Subtraction
        result = await tool.execute("call-2", {
            "operation": "subtract",
            "a": 10,
            "b": 4,
        })
        assert result["details"]["result"] == 6

        # Multiplication
        result = await tool.execute("call-3", {
            "operation": "multiply",
            "a": 7,
            "b": 6,
        })
        assert result["details"]["result"] == 42

        # Division
        result = await tool.execute("call-4", {
            "operation": "divide",
            "a": 20,
            "b": 4,
        })
        assert result["details"]["result"] == 5.0

        # Division by zero - error is caught and returned in result
        result = await tool.execute("call-5", {
            "operation": "divide",
            "a": 10,
            "b": 0,
        })
        # Should return error result, not raise
        assert "error" in result["content"][0]["text"].lower() or "error" in result.get("details", {})

        # Invalid operation - parameter validation fails first
        with pytest.raises(ValueError, match="must be one of"):
            await tool.execute("call-6", {
                "operation": "modulo",
                "a": 10,
                "b": 3,
            })


class TestDecoratorTool:
    """Test decorator-based tool creation."""

    @pytest.mark.asyncio
    async def test_tool_decorator(self):
        """Test @tool decorator."""
        @tool(name="test_decorator", description="Test decorator tool")
        async def test_tool_func(params: dict) -> dict:
            name = params.get("name", "World")
            return {
                "content": [{"type": "text", "text": f"Hello, {name}!"}],
                "details": {"name": name},
            }

        assert test_tool_func.name == "test_decorator"
        assert test_tool_func.description == "Test decorator tool"

        result = await test_tool_func.execute("call-1", {"name": "Claude"})
        assert "Hello, Claude!" in result["content"][0]["text"]
        assert result["details"]["name"] == "Claude"

    @pytest.mark.asyncio
    async def test_tool_decorator_with_schema(self):
        """Test @tool decorator with custom schema."""
        schema = ToolSchema(
            properties={
                "value": ParameterProperty(
                    type=ParameterType.INTEGER,
                    description="Integer value",
                    required=True,
                ),
            },
            required=["value"],
        )

        @tool(name="schema_tool", description="Tool with schema", parameters=schema)
        async def schema_tool_func(params: dict) -> dict:
            return {
                "content": [{"type": "text", "text": f"Value: {params['value']}"}],
                "details": params,
            }

        # Valid parameters
        result = await schema_tool_func.execute("call-1", {"value": 42})
        assert result["details"]["value"] == 42

        # Invalid type
        with pytest.raises(ValueError):
            await schema_tool_func.execute("call-2", {"value": "not_an_int"})


class TestToolRegistry:
    """Test ToolRegistry functionality."""

    def test_tool_registry_registration(self):
        """Test registering and unregistering tools."""
        registry = ToolRegistry()
        tool = NoOpTool()

        registry.register(tool)
        assert "noop" in registry.list_tools()
        assert registry.get("noop") is tool

        registry.unregister("noop")
        assert "noop" not in registry.list_tools()
        assert registry.get("noop") is None

    def test_tool_registry_get_all(self):
        """Test getting all tools from registry."""
        registry = ToolRegistry()
        registry.register(NoOpTool())
        registry.register(EchoTool())
        registry.register(CalculatorTool())

        tools = registry.get_all()
        assert len(tools) == 3
        tool_names = [t.name for t in tools]
        assert "noop" in tool_names
        assert "echo" in tool_names
        assert "calculator" in tool_names

    def test_tool_registry_to_list(self):
        """Test converting registry to list of dicts."""
        registry = ToolRegistry()
        registry.register(NoOpTool())

        tool_list = registry.to_list()
        assert len(tool_list) == 1
        assert tool_list[0]["name"] == "noop"
        assert "parameters" in tool_list[0]

    def test_get_builtin_tools(self):
        """Test getting built-in tools."""
        tools = get_builtin_tools()
        assert len(tools) >= 5  # At least 5 built-in tools
        tool_names = [t.name for t in tools]
        assert "noop" in tool_names
        assert "echo" in tool_names
        assert "calculator" in tool_names


class TestCustomTool:
    """Test custom tool implementations."""

    @pytest.mark.asyncio
    async def test_custom_string_reverse_tool(self):
        """Test a custom tool that reverses strings."""

        class StringReverseTool(BaseTool):
            name = "string_reverse"
            description = "Reverse a string"

            def get_schema(self) -> ToolSchema:
                return ToolSchema(
                    properties={
                        "text": ParameterProperty(
                            type=ParameterType.STRING,
                            description="Text to reverse",
                            required=True,
                        ),
                    },
                    required=["text"],
                )

            async def _execute(self, tool_call_id, params, signal, on_update):
                text = params["text"]
                reversed_text = text[::-1]
                return {
                    "content": [{"type": "text", "text": reversed_text}],
                    "details": {"original": text, "reversed": reversed_text},
                }

        tool = StringReverseTool()
        result = await tool.execute("call-1", {"text": "Hello"})
        assert result["content"][0]["text"] == "olleH"
        assert result["details"]["original"] == "Hello"
        assert result["details"]["reversed"] == "olleH"

    @pytest.mark.asyncio
    async def test_tool_with_update_callback(self):
        """Test tool with streaming update callback."""

        class ProgressTool(BaseTool):
            name = "progress"
            description = "Tool with progress updates"

            def get_schema(self) -> ToolSchema:
                return ToolSchema(
                    properties={
                        "steps": ParameterProperty(
                            type=ParameterType.INTEGER,
                            description="Number of steps",
                            required=True,
                        ),
                    },
                    required=["steps"],
                )

            async def _execute(self, tool_call_id, params, signal, on_update):
                steps = params["steps"]
                result = 0

                for i in range(steps):
                    # Simulate work
                    await asyncio.sleep(0.01)
                    result += i

                    # Send update
                    if on_update:
                        on_update({
                            "content": [{"type": "text", "text": f"Step {i+1}/{steps}"}],
                            "details": {"progress": (i + 1) / steps, "current_result": result},
                        })

                return {
                    "content": [{"type": "text", "text": f"Final result: {result}"}],
                    "details": {"result": result},
                }

        tool = ProgressTool()
        updates = []

        def capture_update(update):
            updates.append(update)

        result = await tool.execute("call-1", {"steps": 3}, None, capture_update)

        # Should have received updates
        assert len(updates) == 3
        assert updates[0]["details"]["progress"] == pytest.approx(1/3)
        assert updates[2]["details"]["progress"] == pytest.approx(1.0)

        # Should have final result
        assert "Final result:" in result["content"][0]["text"]
