"""
Custom metric example.

Demonstrates how to create and register custom metrics.
"""

from eval.core.metrics.base import BaseMetric, MetricResult
from eval.core.registry import register_metric


# Register a custom metric using the decorator
@register_metric("length_check")
class LengthCheckMetric(BaseMetric):
    """
    Custom metric that checks if output length is within range.
    """

    def compute(self, output, expected=None, **kwargs):
        """Compute length check score."""
        min_length = self.config.get("min_length", 10)
        max_length = self.config.get("max_length", 1000)

        output_length = len(str(output))

        # Score based on how close to target range
        if min_length <= output_length <= max_length:
            score = 1.0
        else:
            # Partial score if outside range
            if output_length < min_length:
                score = output_length / min_length
            else:
                score = max_length / output_length

        return MetricResult(
            name="length_check",
            score=min(1.0, score),
            passed=score >= self.threshold,
            details={"length": output_length, "min": min_length, "max": max_length},
        )


# Example usage:
# In your YAML config:
# metrics:
#   - name: "length_check"
#     type: "custom"
#     weight: 0.5
#     threshold: 0.8
#     params:
#       metric_name: "length_check"
#       min_length: 50
#       max_length: 500


if __name__ == "__main__":
    # Test the custom metric
    config = {"threshold": 0.8, "min_length": 10, "max_length": 100}

    metric = LengthCheckMetric(config)

    # Test with valid length
    result1 = metric.compute(output="This is a valid response with appropriate length.")
    print(f"Test 1 - Score: {result1.score:.2f}, Passed: {result1.passed}")

    # Test with too short
    result2 = metric.compute(output="Short")
    print(f"Test 2 - Score: {result2.score:.2f}, Passed: {result2.passed}")

    # Test with too long
    result3 = metric.compute(output="x" * 200)
    print(f"Test 3 - Score: {result3.score:.2f}, Passed: {result3.passed}")
