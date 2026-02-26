"""
Metric registry implementation.

This module integrates with eval/core/registry.py to provide metric registration.
"""

from typing import Any, Dict, Type

from .accuracy import ContainsKeywordMetric, ExactMatchMetric
from .base import BaseMetric


class MetricRegistry:
    """
    Registry for built-in metrics.
    """

    _metrics: Dict[str, Type[BaseMetric]] = {
        "accuracy": ExactMatchMetric,
        "exact_match": ExactMatchMetric,
        "contains_keyword": ContainsKeywordMetric,
    }

    @classmethod
    def register(cls, name: str, metric_class: Type[BaseMetric]) -> None:
        """
        Register a metric class.

        Args:
            name: Metric name/identifier
            metric_class: Metric class (must be a subclass of BaseMetric)
        """
        if not issubclass(metric_class, BaseMetric):
            raise ValueError(f"Metric must inherit from BaseMetric: {metric_class}")

        cls._metrics[name] = metric_class

    @classmethod
    def get_metric(cls, metric_type: str, config: Dict[str, Any]) -> BaseMetric:
        """
        Get a metric instance by type.

        Args:
            metric_type: Metric type (e.g., "accuracy", "exact_match")
            config: Metric configuration

        Returns:
            Metric instance

        Raises:
            ValueError: If metric type is not found
        """
        # Get metric name from config
        metric_name = config.get("metric_name", metric_type)

        if metric_name in cls._metrics:
            return cls._metrics[metric_name](config)

        # Try to use metric_type directly
        if metric_type in cls._metrics:
            return cls._metrics[metric_type](config)

        raise ValueError(f"Unknown metric type: {metric_type}")

    @classmethod
    def list_metrics(cls) -> Dict[str, Type[BaseMetric]]:
        """
        List all registered metrics.

        Returns:
            Dictionary of metric name to class
        """
        return cls._metrics.copy()
