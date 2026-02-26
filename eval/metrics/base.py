"""
Base metric class.

Following intent_system/core/intent_definition.py pattern.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class MetricResult(BaseModel):
    """
    Single metric result.
    """

    name: str = Field(description="Metric name")
    score: float = Field(ge=0.0, le=1.0, description="Metric score (0-1)")
    passed: bool = Field(description="Whether metric passed threshold")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional details")


class BaseMetric(ABC):
    """
    Base metric class.

    All metrics must inherit from this class.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize metric.

        Args:
            config: Metric configuration
        """
        self.config = config
        self.threshold = config.get("threshold", 0.7)

    @abstractmethod
    def compute(
        self, output: Any, expected: Optional[Any] = None, **kwargs
    ) -> MetricResult:
        """
        Compute metric score.

        Args:
            output: Model output
            expected: Expected output (optional)
            **kwargs: Additional parameters

        Returns:
            MetricResult instance
        """
        pass

    def normalize_score(self, raw_score: float) -> float:
        """
        Normalize raw score to 0-1 range.

        Args:
            raw_score: Raw score

        Returns:
            Normalized score (0-1)
        """
        return max(0.0, min(1.0, raw_score))
