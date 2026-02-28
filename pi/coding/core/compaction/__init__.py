"""
Compaction and summarization utilities.

Converted from TypeScript core/compaction/index.ts
"""
import asyncio
from dataclasses import dataclass, field
from typing import Any, Optional, Union
from .utils import (
    FileOperations,
    create_file_ops,
    extract_file_ops_from_message,
    compute_file_lists,
    format_file_operations,
    serialize_conversation,
    SUMMARIZATION_SYSTEM_PROMPT,
)


def _get_model_attr(model: Any, attr: str, default: Any = "") -> Any:
    """Helper to get attribute from Model object or dict."""
    if isinstance(model, dict):
        return model.get(attr, default)
    return getattr(model, attr, default)


@dataclass
class CompactionResult:
    """Result from a compaction operation."""
    summary: str
    first_kept_entry_id: str
    tokens_before: int
    details: Optional[dict] = None


@dataclass
class CompactionPreparation:
    """Preparation data for compaction."""
    total_tokens: int
    context_window: int
    messages_to_compact: list[dict]
    file_ops: FileOperations
    threshold_met: bool
    reason: str  # "threshold" or "overflow"


def prepare_compaction(
    entries: list[Any],
    settings: dict[str, Any],
) -> Optional[CompactionPreparation]:
    """
    Prepare for compaction by analyzing entries and settings.

    Args:
        entries: Session entries to analyze
        settings: Compaction settings (enabled, threshold, etc.)

    Returns:
        CompactionPreparation if compaction is needed, None otherwise
    """
    enabled = settings.get("enabled", True)
    if not enabled:
        return None

    # Get model context window
    context_window = settings.get("context_window", 200000)
    threshold_percent = settings.get("threshold_percent", 80)
    threshold_tokens = int(context_window * threshold_percent / 100)

    # Collect messages and estimate tokens
    messages_to_compact = []
    total_tokens = 0

    for entry in entries:
        if entry.type == "message":
            msg = entry.message
            # Rough token estimation: 1 token ≈ 4 characters
            content = msg.get("content", "")
            if isinstance(content, str):
                tokens = len(content) // 4
            elif isinstance(content, list):
                tokens = sum(len(str(c.get("text", ""))) // 4 for c in content)
            else:
                tokens = 0

            messages_to_compact.append(msg)
            total_tokens += tokens

    if not messages_to_compact:
        return None

    # Check if we should compact
    threshold_met = total_tokens >= threshold_tokens

    # Extract file operations
    file_ops = create_file_ops()
    for msg in messages_to_compact:
        extract_file_ops_from_message(msg, file_ops)

    return CompactionPreparation(
        total_tokens=total_tokens,
        context_window=context_window,
        messages_to_compact=messages_to_compact,
        file_ops=file_ops,
        threshold_met=threshold_met,
        reason="threshold" if threshold_met else "manual",
    )


async def compact(
    preparation: CompactionPreparation,
    model: Union[dict[str, Any], Any],  # Can be dict or Model object
    api_key: str,
    custom_instructions: Optional[str] = None,
    signal: Optional[Any] = None,
) -> CompactionResult:
    """
    Perform compaction with LLM summarization.

    Args:
        preparation: Prepared compaction data
        model: Model dict or Model object with provider, id, etc.
        api_key: API key for the model
        custom_instructions: Optional custom instructions
        signal: Optional abort signal

    Returns:
        CompactionResult with summary and metadata
    """
    # Try to import pi.ai, fallback to simple summarization if not available
    try:
        from pi.ai import create_completion
        use_llm = True
    except ImportError:
        use_llm = False

    # Build summary prompt
    file_lists = compute_file_lists(preparation.file_ops)
    file_ops_xml = format_file_operations(
        file_lists.get("readFiles", []),
        file_lists.get("modifiedFiles", [])
    )

    conversation_text = serialize_conversation(preparation.messages_to_compact)

    if use_llm:
        prompt = f"""{SUMMARIZATION_SYSTEM_PROMPT}

<File operations>
{file_ops_xml}
</File operations>

<Conversation>
{conversation_text}
</Conversation>

{custom_instructions or "Summarize the conversation focusing on key decisions, code changes, and outcomes."}
"""

        # Check for abort
        if signal and signal.aborted:
            raise asyncio.CancelledError("Compaction aborted")

        # Call LLM for summary - support both dict and Model object
        provider = _get_model_attr(model, "provider", "")
        model_id = _get_model_attr(model, "id", "")

        completion = create_completion(
            provider=provider,
            model=model_id,
            api_key=api_key,
            messages=[{"role": "user", "content": prompt}],
            thinking="off",
        )

        # Get summary
        summary = ""
        async for chunk in completion:
            if signal and signal.aborted:
                raise asyncio.CancelledError("Compaction aborted")

            if hasattr(chunk, "content"):
                summary += chunk.content
            elif isinstance(chunk, str):
                summary += chunk

        summary = summary.strip()
    else:
        # Fallback: simple summary without LLM
        summary = f"""Session compaction summary:
- Total tokens before compaction: {preparation.total_tokens}
- Context window: {preparation.context_window}
- Reason: {preparation.reason}

Files affected:
- Read files: {len(file_lists.get("readFiles", []))}
- Modified files: {len(file_lists.get("modifiedFiles", []))}

Messages compacted: {len(preparation.messages_to_compact)}

{custom_instructions or ""}
"""

    # Generate entry ID for first kept message
    import uuid
    first_kept_entry_id = uuid.uuid4().hex[:8]

    details = {
        "readFiles": file_lists.get("readFiles", []),
        "modifiedFiles": file_lists.get("modifiedFiles", []),
    }

    return CompactionResult(
        summary=summary,
        first_kept_entry_id=first_kept_entry_id,
        tokens_before=preparation.total_tokens,
        details=details,
    )


def should_compact(
    current_tokens: int,
    context_window: int,
    settings: dict[str, Any],
) -> bool:
    """
    Check if compaction should be triggered.

    Args:
        current_tokens: Current token count
        context_window: Model context window
        settings: Compaction settings

    Returns:
        True if compaction should be triggered
    """
    enabled = settings.get("enabled", True)
    if not enabled:
        return False

    threshold_percent = settings.get("threshold_percent", 80)
    threshold_tokens = int(context_window * threshold_percent / 100)

    return current_tokens >= threshold_tokens


def calculate_context_tokens(usage: dict[str, Any]) -> int:
    """
    Calculate total context tokens from usage data.

    Args:
        usage: Usage dict from assistant message

    Returns:
        Total token count
    """
    return (
        usage.get("input", 0)
        + usage.get("output", 0)
        + usage.get("cacheRead", 0)
        + usage.get("cacheWrite", 0)
    )


def estimate_context_tokens(messages: list[dict]) -> dict[str, int]:
    """
    Estimate context tokens from messages.

    Args:
        messages: List of messages

    Returns:
        Dict with tokens estimate
    """
    total_chars = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total_chars += len(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    text = block.get("text", "")
                    total_chars += len(text)

    return {"tokens": total_chars // 4}  # Rough estimate


def is_context_overflow(message: dict, context_window: int) -> bool:
    """
    Check if message indicates context overflow.

    Args:
        message: Assistant message dict
        context_window: Model context window

    Returns:
        True if message indicates context overflow
    """
    if message.get("stopReason") != "error":
        return False

    error_msg = message.get("errorMessage", "").lower()
    return "context" in error_msg or "token" in error_msg


def collect_entries_for_branch_summary(
    session_manager: Any,
    old_leaf_id: str,
    target_id: str,
) -> dict:
    """
    Collect entries for branch summarization.

    Args:
        session_manager: SessionManager instance
        old_leaf_id: Old leaf node ID
        target_id: Target entry ID

    Returns:
        Dict with entries and common_ancestor_id
    """
    branch = session_manager.get_branch()
    old_index = -1
    target_index = -1

    for i, entry in enumerate(branch):
        if entry.id == old_leaf_id:
            old_index = i
        if entry.id == target_id:
            target_index = i

    # Find common ancestor
    common_index = min(old_index, target_index)
    common_ancestor_id = branch[common_index].id if common_index >= 0 else None

    # Collect entries between old leaf and target (exclusive of common ancestor)
    entries_to_summarize = branch[min(old_index, target_index) + 1:max(old_index, target_index) + 1]

    return {
        "entries": entries_to_summarize,
        "commonAncestorId": common_ancestor_id,
    }


async def generate_branch_summary(
    entries: list[Any],
    options: dict[str, Any],
) -> dict:
    """
    Generate a summary for branch navigation.

    Args:
        entries: Entries to summarize
        options: Dict with model, apiKey, instructions, etc.

    Returns:
        Dict with summary, details, aborted, error
    """
    # TODO: Implement branch summary generation
    return {
        "summary": "Branch summary not yet implemented",
        "details": {},
        "aborted": False,
        "error": None,
    }


def get_latest_compaction_entry(entries: list[Any]) -> Optional[Any]:
    """
    Get the latest compaction entry from the branch.

    Args:
        entries: Session entries

    Returns:
        Latest compaction entry or None
    """
    for entry in reversed(entries):
        if entry.type == "compaction":
            return entry
    return None


__all__ = [
    "CompactionResult",
    "CompactionPreparation",
    "prepare_compaction",
    "compact",
    "should_compact",
    "calculate_context_tokens",
    "estimate_context_tokens",
    "is_context_overflow",
    "collect_entries_for_branch_summary",
    "generate_branch_summary",
    "get_latest_compaction_entry",
    "FileOperations",
    "create_file_ops",
    "extract_file_ops_from_message",
    "compute_file_lists",
    "format_file_operations",
    "serialize_conversation",
    "SUMMARIZATION_SYSTEM_PROMPT",
]
