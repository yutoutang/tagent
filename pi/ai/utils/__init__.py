"""Utility functions for AI abstraction layer."""

from .event_stream import EventStream, AssistantMessageEventStream, create_assistant_message_event_stream
from .json_parse import parse_streaming_json
from .overflow import is_context_overflow, get_overflow_patterns
from .sanitize_unicode import sanitize_surrogates
from .validation import validate_tool_call, validate_tool_arguments
from .typebox_helpers import (
    string_enum,
    object_schema,
    array_schema,
    string_schema,
    number_schema,
    boolean_schema,
    optional,
    nullable,
)

__all__ = [
    "EventStream",
    "AssistantMessageEventStream",
    "create_assistant_message_event_stream",
    "parse_streaming_json",
    "is_context_overflow",
    "get_overflow_patterns",
    "sanitize_surrogates",
    "validate_tool_call",
    "validate_tool_arguments",
    "string_enum",
    "object_schema",
    "array_schema",
    "string_schema",
    "number_schema",
    "boolean_schema",
    "optional",
    "nullable",
]
