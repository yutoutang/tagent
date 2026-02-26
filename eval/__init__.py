"""
Evaluation Framework - Public API

Main entry point for the evaluation framework.
"""

from .core.config import ConfigLoader
from .core.evaluator import BaseEvaluator
from .core.models import (
    EvaluationConfig,
    EvaluationResult,
    LLMConfig,
    LLMProvider,
    MetricConfig,
    MetricType,
    PromptConfig,
)
from .datasets.loader import DatasetLoader
from .datasets.models import Dataset, DatasetItem
from .execution.runner import EvaluationRunner


def evaluate_from_config(config_path: str) -> list[EvaluationResult]:
    """
    Quick evaluation from configuration file.

    Args:
        config_path: Path to YAML configuration file

    Returns:
        List of evaluation results

    Example:
        >>> results = evaluate_from_config("eval/config/default.yaml")
        >>> for result in results:
        ...     print(f"Score: {result.overall_score:.2f}")
    """
    # Load configuration
    config = ConfigLoader.load_from_file(config_path)

    # Create runner
    runner = EvaluationRunner(config)

    # Load dataset if provided
    if config.dataset_path:
        dataset = DatasetLoader.load_from_file(config.dataset_path)
        inputs = [item.input for item in dataset.items]
    else:
        raise ValueError("dataset_path must be provided in configuration")

    # Run evaluation
    return runner.evaluate(inputs)


async def evaluate_from_config_async(config_path: str) -> list[EvaluationResult]:
    """
    Async evaluation from configuration file.

    Args:
        config_path: Path to YAML configuration file

    Returns:
        List of evaluation results
    """
    # Load configuration
    config = ConfigLoader.load_from_file(config_path)

    # Create runner
    runner = EvaluationRunner(config)

    # Load dataset if provided
    if config.dataset_path:
        dataset = DatasetLoader.load_from_file(config.dataset_path)
        inputs = [item.input for item in dataset.items]
    else:
        raise ValueError("dataset_path must be provided in configuration")

    # Run evaluation
    return await runner.evaluate_async(inputs)


__all__ = [
    "ConfigLoader",
    "EvaluationConfig",
    "EvaluationResult",
    "EvaluationRunner",
    "LLMConfig",
    "LLMProvider",
    "MetricConfig",
    "MetricType",
    "PromptConfig",
    "Dataset",
    "DatasetItem",
    "DatasetLoader",
    "BaseEvaluator",
    "evaluate_from_config",
    "evaluate_from_config_async",
]

__version__ = "1.0.0"
