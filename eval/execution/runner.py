"""
Evaluation runner.

Following intent_system/execution/intent_executor.py pattern with sync/async support.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional

from ..core.config import ConfigLoader
from ..core.evaluator import BaseEvaluator
from ..core.models import EvaluationConfig, EvaluationResult, MetricConfig
from ..datasets.loader import DatasetLoader
from ..llm.client import LLMClient
from ..llm.prompt_provider import PromptProvider
from ..metrics.registry import MetricRegistry


class EvaluationRunner(BaseEvaluator):
    """
    Main evaluation runner.

    Features:
    - Sync and async evaluation
    - Parallel execution support
    - Progress tracking
    - Error handling and retries
    """

    def __init__(self, config: EvaluationConfig):
        """
        Initialize runner.

        Args:
            config: Evaluation configuration
        """
        self.config = config
        self.metric_registry = MetricRegistry()

        # Initialize components
        self.llm_client = LLMClient(config.llm)
        self.prompt_provider = PromptProvider(config.prompt)

        # Load metrics
        self.metrics = self._load_metrics(config.metrics)

    def _load_metrics(self, metric_configs: List[MetricConfig]) -> List[Any]:
        """
        Load metric instances.

        Args:
            metric_configs: List of metric configurations

        Returns:
            List of metric instances
        """
        metrics = []
        for metric_config in metric_configs:
            metric = self.metric_registry.get_metric(
                metric_config.type.value, {**metric_config.params, "threshold": metric_config.threshold}
            )
            metrics.append(metric)
        return metrics

    def evaluate(self, inputs: List[Any], config: Optional[Any] = None) -> List[EvaluationResult]:
        """
        Evaluate inputs (sync).

        Args:
            inputs: List of inputs to evaluate
            config: Optional override config

        Returns:
            List of evaluation results
        """
        results = []

        # Get prompt template
        prompt_template = self.prompt_provider.get_prompt()

        for i, input_data in enumerate(inputs):
            try:
                # Format prompt with input
                prompt = self._format_prompt(prompt_template, input_data)

                # Generate output
                start_time = time.time()
                output = self.llm_client.generate(prompt)
                latency_ms = (time.time() - start_time) * 1000

                # Compute metrics
                scores = {}
                for metric in self.metrics:
                    result = metric.compute(
                        output=output,
                        expected=input_data.get("expected") if isinstance(input_data, dict) else None,
                    )
                    scores[result.name] = result.score

                # Compute overall weighted score
                overall_score = self._compute_overall_score(scores)

                results.append(
                    EvaluationResult(
                        input=input_data,
                        output=output,
                        expected=input_data.get("expected") if isinstance(input_data, dict) else None,
                        scores=scores,
                        overall_score=overall_score,
                        latency_ms=latency_ms,
                    )
                )

            except Exception as e:
                results.append(
                    EvaluationResult(input=input_data, output=None, error=str(e))
                )

        return results

    async def evaluate_async(
        self, inputs: List[Any], config: Optional[Any] = None
    ) -> List[EvaluationResult]:
        """
        Evaluate inputs (async).

        Args:
            inputs: List of inputs to evaluate
            config: Optional override config

        Returns:
            List of evaluation results
        """
        # Get prompt template
        prompt_template = await self.prompt_provider.get_prompt_async()

        if self.config.parallel:
            # Parallel execution
            tasks = [
                self._evaluate_single_async(input_data, prompt_template)
                for input_data in inputs
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle exceptions
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    processed_results.append(
                        EvaluationResult(input=inputs[i], output=None, error=str(result))
                    )
                else:
                    processed_results.append(result)

            return processed_results
        else:
            # Sequential execution
            results = []
            for input_data in inputs:
                result = await self._evaluate_single_async(input_data, prompt_template)
                results.append(result)
            return results

    async def _evaluate_single_async(
        self, input_data: Any, prompt_template: str
    ) -> EvaluationResult:
        """
        Evaluate single input (async).

        Args:
            input_data: Input data
            prompt_template: Prompt template

        Returns:
            EvaluationResult
        """
        try:
            # Format prompt
            prompt = self._format_prompt(prompt_template, input_data)

            # Generate output
            start_time = time.time()
            output = await self.llm_client.generate_async(prompt)
            latency_ms = (time.time() - start_time) * 1000

            # Compute metrics
            scores = {}
            for metric in self.metrics:
                result = metric.compute(
                    output=output,
                    expected=input_data.get("expected") if isinstance(input_data, dict) else None,
                )
                scores[result.name] = result.score

            # Compute overall score
            overall_score = self._compute_overall_score(scores)

            return EvaluationResult(
                input=input_data,
                output=output,
                expected=input_data.get("expected") if isinstance(input_data, dict) else None,
                scores=scores,
                overall_score=overall_score,
                latency_ms=latency_ms,
            )

        except Exception as e:
            return EvaluationResult(input=input_data, output=None, error=str(e))

    def _format_prompt(self, template: str, input_data: Any) -> str:
        """
        Format prompt template with input data.

        Args:
            template: Prompt template
            input_data: Input data

        Returns:
            Formatted prompt
        """
        if isinstance(input_data, dict):
            return template.format(**input_data)
        else:
            return template.format(input=input_data)

    def _compute_overall_score(self, scores: Dict[str, float]) -> float:
        """
        Compute overall weighted score.

        Args:
            scores: Individual metric scores

        Returns:
            Overall weighted score
        """
        if not scores or not self.config.metrics:
            return 0.0

        weighted_sum = 0.0
        total_weight = 0.0

        for metric_config in self.config.metrics:
            metric_name = metric_config.name
            weight = metric_config.weight
            score = scores.get(metric_name, 0.0)

            weighted_sum += score * weight
            total_weight += weight

        return weighted_sum / total_weight if total_weight > 0 else 0.0
