"""
Base evaluator interface.

Following intent_system/core/intent_definition.py pattern.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional

from .models import EvaluationResult


class BaseEvaluator(ABC):
    """
    Base evaluator interface.

    All evaluators must implement this interface.
    """

    @abstractmethod
    def evaluate(
        self, inputs: List[Any], config: Optional[Any] = None
    ) -> List[EvaluationResult]:
        """
        Evaluate inputs.

        Args:
            inputs: List of inputs to evaluate
            config: Optional configuration

        Returns:
            List of evaluation results
        """
        pass

    @abstractmethod
    async def evaluate_async(
        self, inputs: List[Any], config: Optional[Any] = None
    ) -> List[EvaluationResult]:
        """
        Evaluate inputs asynchronously.

        Args:
            inputs: List of inputs to evaluate
            config: Optional configuration

        Returns:
            List of evaluation results
        """
        pass
