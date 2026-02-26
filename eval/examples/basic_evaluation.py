"""
Basic evaluation example.

Demonstrates how to use the evaluation framework.
"""

import asyncio
from eval import evaluate_from_config, EvaluationResult


def print_section(title: str):
    """Print section header."""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def main():
    """Main function."""
    print_section("Basic Evaluation Example")

    # Run evaluation from config file
    print("\nRunning evaluation from config file...")
    print("Config: eval/config/examples/basic_eval.yaml")

    try:
        results = evaluate_from_config("eval/config/examples/basic_eval.yaml")

        # Print results
        print_section("Evaluation Results")

        for i, result in enumerate(results):
            print(f"\n--- Result {i + 1} ---")
            print(f"Input: {result.input}")
            print(f"Output: {result.output}")
            print(f"Expected: {result.expected}")
            print(f"Overall Score: {result.overall_score:.2f}")
            print(f"Latency: {result.latency_ms:.2f}ms")

            for metric_name, score in result.scores.items():
                print(f"  {metric_name}: {score:.2f}")

            if result.error:
                print(f"Error: {result.error}")

        # Summary
        print_section("Summary")

        total = len(results)
        successful = sum(1 for r in results if not r.error)
        failed = total - successful

        avg_score = sum(r.overall_score for r in results if not r.error) / successful if successful > 0 else 0
        avg_latency = sum(r.latency_ms for r in results if r.latency_ms) / total

        print(f"Total evaluations: {total}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Average score: {avg_score:.2f}")
        print(f"Average latency: {avg_latency:.2f}ms")

    except Exception as e:
        print(f"\n[ERROR] Evaluation failed: {e}")
        import traceback

        traceback.print_exc()


async def async_main():
    """Async main function."""
    print_section("Async Evaluation Example")

    print("\nRunning async evaluation from config file...")

    try:
        results = await evaluate_from_config_async("eval/config/examples/basic_eval.yaml")

        print_section("Async Evaluation Results")

        for i, result in enumerate(results):
            print(f"\n--- Result {i + 1} ---")
            print(f"Input: {result.input}")
            print(f"Output: {result.output}")
            print(f"Overall Score: {result.overall_score:.2f}")

    except Exception as e:
        print(f"\n[ERROR] Async evaluation failed: {e}")


if __name__ == "__main__":
    # Sync example
    main()

    # Uncomment to run async example
    # asyncio.run(async_main())
