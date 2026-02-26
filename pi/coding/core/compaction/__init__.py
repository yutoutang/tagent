"""
Compaction and summarization utilities.

Converted from TypeScript core/compaction/index.ts
"""

from .utils import (
    FileOperations,
    create_file_ops,
    extract_file_ops_from_message,
    compute_file_lists,
    format_file_operations,
    serialize_conversation,
    SUMMARIZATION_SYSTEM_PROMPT,
)

__all__ = [
    "FileOperations",
    "create_file_ops",
    "extract_file_ops_from_message",
    "compute_file_lists",
    "format_file_operations",
    "serialize_conversation",
    "SUMMARIZATION_SYSTEM_PROMPT",
]
