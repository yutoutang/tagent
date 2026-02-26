"""Performance timing utilities for pi-coding.

Converted from TypeScript core/timings.ts
"""
import time as _time
from typing import Dict, Optional


# Simple timing store
_timings: Dict[str, list[float]] = {}


def time(label: str, elapsed: Optional[float] = None) -> None:
    """
    Record a timing measurement.

    Args:
        label: Label for the timing
        elapsed: Optional elapsed time in seconds (if not provided, uses current time delta)
    """
    if label not in _timings:
        _timings[label] = []

    _timings[label].append(elapsed or _time.time())


def get_timings() -> Dict[str, list[float]]:
    """
    Get all recorded timings.

    Returns:
        Dict mapping labels to lists of elapsed times
    """
    return _timings.copy()


def clear_timings() -> None:
    """Clear all recorded timings."""
    _timings.clear()


__all__ = ["time", "get_timings", "clear_timings"]
