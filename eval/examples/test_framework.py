"""
Test framework without actual API calls.

This tests the framework components independently.
"""

import os
from eval.core.config import ConfigLoader
from eval.core.models import LLMConfig, PromptConfig, EvaluationConfig
from eval.datasets.loader import DatasetLoader
from eval.metrics.accuracy import ExactMatchMetric, ContainsKeywordMetric


def test_config_loading():
    """Test configuration loading."""
    print("Testing configuration loading...")

    # Test from dict
    config = ConfigLoader.load_from_dict({
        'name': 'test',
        'llm': {
            'api_key': 'sk-test',
            'model_name': 'gpt-4o'
        },
        'prompt': {
            'prompt_template': 'Test: {input}'
        },
        'metrics': []
    })

    assert config.name == 'test'
    assert config.llm.get_api_key() == 'sk-test'
    assert config.llm.model_name == 'gpt-4o'

    print("  ✓ Dict loading works")

    # Test from file
    config = ConfigLoader.load_from_file('eval/config/default.yaml')
    assert config.name == 'basic_evaluation'
    assert len(config.metrics) > 0

    print("  ✓ YAML file loading works")


def test_dataset_loading():
    """Test dataset loading."""
    print("\nTesting dataset loading...")

    dataset = DatasetLoader.load_from_file('eval/data/evaluation_dataset.json')

    assert dataset.name == 'basic_evaluation'
    assert len(dataset) == 3

    item = dataset[0]
    assert 'input' in item.model_dump()

    print("  ✓ Dataset loading works")


def test_metrics():
    """Test metrics."""
    print("\nTesting metrics...")

    # Test exact match
    metric = ExactMatchMetric({'threshold': 0.8})
    result = metric.compute(output='Paris', expected='Paris')
    assert result.score == 1.0
    assert result.passed is True

    print("  ✓ ExactMatchMetric works")

    # Test keyword match
    metric = ContainsKeywordMetric({'threshold': 0.5})
    result = metric.compute(output='I love this!', expected=['love', 'hate'])
    assert result.score >= 0.5

    print("  ✓ ContainsKeywordMetric works")


def test_prompt_config():
    """Test prompt configuration."""
    print("\nTesting prompt configuration...")

    # Test inline template
    config = PromptConfig(prompt_template='Hello {name}')
    assert config.prompt_template == 'Hello {name}'

    print("  ✓ Inline template works")


def test_llm_config():
    """Test LLM configuration."""
    print("\nTesting LLM configuration...")

    # Test with 'sk' field
    config = LLMConfig(sk='my-secret-key')
    assert config.get_api_key() == 'my-secret-key'

    # Test with 'api_key' field
    config = LLMConfig(api_key='another-key')
    assert config.get_api_key() == 'another-key'

    # Test with both (api_key takes precedence)
    config = LLMConfig(sk='sk-key', api_key='api-key')
    assert config.get_api_key() == 'api-key'

    print("  ✓ LLMConfig supports both 'sk' and 'api_key'")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Eval Framework Component Tests")
    print("=" * 60)

    try:
        test_config_loading()
        test_dataset_loading()
        test_metrics()
        test_prompt_config()
        test_llm_config()

        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)

        print("\nFramework components are working correctly.")
        print("To run a full evaluation with actual LLM API calls:")
        print("1. Set OPENAI_API_KEY environment variable")
        print("2. Run: python eval/examples/basic_evaluation.py")

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
