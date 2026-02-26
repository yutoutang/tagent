"""
Simple Options Utilities

Helper functions for building stream options with thinking/reasoning support.
"""

from __future__ import annotations

from typing import Optional, TypedDict, cast

from ..types import (
    Api,
    Model,
    SimpleStreamOptions,
    StreamOptions,
    ThinkingBudgets,
    ThinkingLevel,
)


def build_base_options(
    model: Model,
    options: Optional[SimpleStreamOptions] = None,
    api_key: Optional[str] = None,
) -> StreamOptions:
    """
    Build base stream options from simple stream options.

    Args:
        model: The model to use
        options: Optional simple stream options
        api_key: Optional API key

    Returns:
        Stream options dict
    """
    result: StreamOptions = {
        "temperature": options.get("temperature") if options else None,
        "maxTokens": options.get("maxTokens") if options else min(model.maxTokens, 32000),
        "signal": options.get("signal") if options else None,
        "apiKey": api_key or (options.get("apiKey") if options else None),
        "cacheRetention": options.get("cacheRetention") if options else None,
        "sessionId": options.get("sessionId") if options else None,
        "headers": options.get("headers") if options else None,
        "onPayload": options.get("onPayload") if options else None,
        "maxRetryDelayMs": options.get("maxRetryDelayMs") if options else None,
        "metadata": options.get("metadata") if options else None,
    }
    return result


def clamp_reasoning(effort: Optional[ThinkingLevel]) -> Optional[ThinkingLevel]:
    """
    Clamp reasoning level, converting xhigh to high.

    Args:
        effort: The reasoning level

    Returns:
        The clamped reasoning level
    """
    if effort == "xhigh":
        return "high"
    return effort


def adjust_max_tokens_for_thinking(
    base_max_tokens: int,
    model_max_tokens: int,
    reasoning_level: ThinkingLevel,
    custom_budgets: Optional[ThinkingBudgets] = None,
) -> dict:
    """
    Adjust max tokens to account for thinking budget.

    Args:
        base_max_tokens: The base max tokens
        model_max_tokens: The model's max tokens
        reasoning_level: The reasoning level
        custom_budgets: Optional custom thinking budgets

    Returns:
        Dict with maxTokens and thinkingBudget
    """
    default_budgets: ThinkingBudgets = {
        "minimal": 1024,
        "low": 2048,
        "medium": 8192,
        "high": 16384,
    }

    budgets = {**default_budgets, **(custom_budgets or {})}

    min_output_tokens = 1024
    level = clamp_reasoning(reasoning_level)
    if level is None:
        level = "medium"

    thinking_budget = budgets.get(level, 8192)
    max_tokens = min(base_max_tokens + thinking_budget, model_max_tokens)

    if max_tokens <= thinking_budget:
        thinking_budget = max(0, max_tokens - min_output_tokens)

    return {"maxTokens": max_tokens, "thinkingBudget": thinking_budget}
