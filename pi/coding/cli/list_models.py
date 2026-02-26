"""
List available models for pi-coding.

Converted from TypeScript cli/list-models.ts
"""
from typing import Optional


async def list_models(search: Optional[str] = None) -> int:
    """
    List available models, optionally filtering by search pattern.

    Args:
        search: Optional search pattern for fuzzy matching

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # TODO: Implement model listing functionality
    # This requires ModelRegistry and model discovery

    if search:
        print(f"Listing models matching: {search}")
    else:
        print("Listing all available models")

    print("\nNote: Model listing is not yet implemented.")
    print("Available providers: anthropic, openai, google, groq, etc.")
    print("\nUse --provider and --model to specify a model directly.")

    return 0
