"""
Shared utilities for compaction and branch summarization.

Converted from TypeScript core/compaction/utils.ts
"""
from dataclasses import dataclass, field
from typing import Any, Set, List


@dataclass
class FileOperations:
    """Track file operations during a session."""
    read: Set[str] = field(default_factory=set)
    written: Set[str] = field(default_factory=set)
    edited: Set[str] = field(default_factory=set)


def create_file_ops() -> FileOperations:
    """Create a new FileOperations instance."""
    return FileOperations()


def extract_file_ops_from_message(message: dict[str, Any], file_ops: FileOperations) -> None:
    """
    Extract file operations from tool calls in an assistant message.

    Args:
        message: Agent message dict
        file_ops: FileOperations to update
    """
    if message.get("role") != "assistant":
        return

    content = message.get("content")
    if not isinstance(content, list):
        return

    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") != "toolCall":
            continue

        args = block.get("arguments", {})
        if not isinstance(args, dict):
            continue

        path = args.get("path")
        if not isinstance(path, str):
            continue

        tool_name = block.get("name", "")
        if tool_name == "read":
            file_ops.read.add(path)
        elif tool_name == "write":
            file_ops.written.add(path)
        elif tool_name == "edit":
            file_ops.edited.add(path)


def compute_file_lists(file_ops: FileOperations) -> dict[str, List[str]]:
    """
    Compute final file lists from file operations.

    Args:
        file_ops: FileOperations instance

    Returns:
        Dict with readFiles (files only read, not modified) and modifiedFiles
    """
    modified = set(file_ops.edited) | set(file_ops.written)
    read_only = sorted([f for f in file_ops.read if f not in modified])
    modified_files = sorted(list(modified))

    return {
        "readFiles": read_only,
        "modifiedFiles": modified_files,
    }


def format_file_operations(read_files: List[str], modified_files: List[str]) -> str:
    """
    Format file operations as XML tags for summary.

    Args:
        read_files: List of files that were only read
        modified_files: List of files that were modified

    Returns:
        Formatted XML string
    """
    sections: List[str] = []

    if read_files:
        sections.append(f"<read-files>\n{chr(10).join(read_files)}\n</read-files>")

    if modified_files:
        sections.append(f"<modified-files>\n{chr(10).join(modified_files)}\n</modified-files>")

    if not sections:
        return ""

    return f"\n\n{chr(10).join(sections)}"


def serialize_conversation(messages: List[dict[str, Any]]) -> str:
    """
    Serialize LLM messages to text for summarization.

    This prevents the model from treating it as a conversation to continue.

    Args:
        messages: List of Message dicts

    Returns:
        Serialized conversation string
    """
    parts: List[str] = []

    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content")

        if role == "user":
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                text = "".join(
                    block.get("text", "")
                    for block in content
                    if isinstance(block, dict) and block.get("type") == "text"
                )
            else:
                text = ""

            if text:
                parts.append(f"[User]: {text}")

        elif role == "assistant":
            text_parts: List[str] = []
            thinking_parts: List[str] = []
            tool_calls: List[str] = []

            if isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        continue

                    block_type = block.get("type", "")

                    if block_type == "text":
                        text_parts.append(block.get("text", ""))
                    elif block_type == "thinking":
                        thinking_parts.append(block.get("thinking", ""))
                    elif block_type == "toolCall":
                        args = block.get("arguments", {})
                        if isinstance(args, dict):
                            args_str = ", ".join(
                                f"{k}={repr(v)}"
                                for k, v in args.items()
                            )
                        else:
                            args_str = ""
                        tool_calls.append(f"{block.get('name', '')}({args_str})")

            if thinking_parts:
                parts.append(f"[Assistant thinking]: {chr(10).join(thinking_parts)}")
            if text_parts:
                parts.append(f"[Assistant]: {chr(10).join(text_parts)}")
            if tool_calls:
                parts.append(f"[Assistant tool calls]: {'; '.join(tool_calls)}")

        elif role == "toolResult":
            if isinstance(content, list):
                text = "".join(
                    block.get("text", "")
                    for block in content
                    if isinstance(block, dict) and block.get("type") == "text"
                )
            else:
                text = ""

            if text:
                parts.append(f"[Tool result]: {text}")

    return "\n\n".join(parts)


# Summarization system prompt
SUMMARIZATION_SYSTEM_PROMPT = """You are a context summarization assistant. Your task is to read a conversation between a user and an AI coding assistant, then produce a structured summary following the exact format specified.

Do NOT continue the conversation. Do NOT respond to any questions in the conversation. ONLY output the structured summary."""


__all__ = [
    "FileOperations",
    "create_file_ops",
    "extract_file_ops_from_message",
    "compute_file_lists",
    "format_file_operations",
    "serialize_conversation",
    "SUMMARIZATION_SYSTEM_PROMPT",
]
