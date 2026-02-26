"""
Accuracy metrics.
"""

from typing import Any, Optional

from .base import BaseMetric, MetricResult


class ExactMatchMetric(BaseMetric):
    """
    Exact match metric.

    Compares output with expected output for exact string match.
    """

    def compute(
        self, output: Any, expected: Optional[Any] = None, **kwargs
    ) -> MetricResult:
        """
        Compute exact match score.

        Args:
            output: Model output
            expected: Expected output

        Returns:
            MetricResult
        """
        if expected is None:
            raise ValueError("Expected output is required for ExactMatchMetric")

        # Convert to strings for comparison
        output_str = str(output).strip().lower()
        expected_str = str(expected).strip().lower()

        # Compute score
        score = 1.0 if output_str == expected_str else 0.0

        return MetricResult(
            name="exact_match",
            score=score,
            passed=score >= self.threshold,
            details={"output": output_str, "expected": expected_str, "match": output_str == expected_str},
        )


class ContainsKeywordMetric(BaseMetric):
    """
    Contains keyword metric.

    Checks if output contains expected keywords.
    """

    def compute(
        self, output: Any, expected: Optional[Any] = None, **kwargs
    ) -> MetricResult:
        """
        Compute keyword containment score.

        Args:
            output: Model output
            expected: Expected keywords (string or list)

        Returns:
            MetricResult
        """
        if expected is None:
            raise ValueError("Expected keywords are required for ContainsKeywordMetric")

        output_str = str(output).lower()

        # Handle both string and list of keywords
        if isinstance(expected, str):
            keywords = [expected.lower()]
        else:
            keywords = [str(k).lower() for k in expected]

        # Count how many keywords are present
        matches = sum(1 for kw in keywords if kw in output_str)
        score = self.normalize_score(matches / len(keywords))

        found_keywords = [kw for kw in keywords if kw in output_str]

        return MetricResult(
            name="contains_keyword",
            score=score,
            passed=score >= self.threshold,
            details={
                "keywords": keywords,
                "found_keywords": found_keywords,
                "matches": matches,
                "total": len(keywords),
            },
        )
