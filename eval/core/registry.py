"""
Metric and evaluator registry.

Following intent_system/core/intent_registry.py pattern.
"""

from typing import Any, Callable, Dict, Type, Optional


class MetricRegistry:
    """
    Registry for evaluation metrics.

    Allows dynamic registration and retrieval of metric classes.
    """

    _metrics: Dict[str, Type] = {}
    _custom_metrics: Dict[str, Type] = {}

    @classmethod
    def register(cls, name: str, metric_class: Type) -> None:
        """
        Register a metric class.

        Args:
            name: Metric name/identifier
            metric_class: Metric class (must be a subclass of BaseMetric)
        """
        from .metrics.base import BaseMetric

        if not issubclass(metric_class, BaseMetric):
            raise ValueError(f"Metric must inherit from BaseMetric: {metric_class}")

        cls._metrics[name] = metric_class

    @classmethod
    def register_custom(cls, name: str, metric_class: Type) -> None:
        """
        Register a custom metric class.

        Args:
            name: Metric name/identifier
            metric_class: Custom metric class
        """
        cls._custom_metrics[name] = metric_class

    @classmethod
    def get_metric(cls, metric_type: str, config: Dict[str, Any]) -> Any:
        """
        Get a metric instance by type.

        Args:
            metric_type: Metric type (e.g., "accuracy", "custom")
            config: Metric configuration

        Returns:
            Metric instance

        Raises:
            ValueError: If metric type is not found
        """
        metric_name = config.get("metric_name", "")

        # Check custom metrics first
        if metric_name in cls._custom_metrics:
            return cls._custom_metrics[metric_name](config)

        # Check built-in metrics
        if metric_type in cls._metrics:
            return cls._metrics[metric_type](config)

        raise ValueError(f"Unknown metric type: {metric_type}")

    @classmethod
    def list_metrics(cls) -> Dict[str, Type]:
        """
        List all registered metrics.

        Returns:
            Dictionary of metric name to class
        """
        return {**cls._metrics, **cls._custom_metrics}


def register_metric(name: str) -> Callable:
    """
    Decorator to register a metric.

    Usage:
        @register_metric("my_metric")
        class MyMetric(BaseMetric):
            ...
    """

    def decorator(metric_class: Type) -> Type:
        MetricRegistry.register_custom(name, metric_class)
        return metric_class

    return decorator
