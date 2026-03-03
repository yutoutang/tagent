"""Resources for pi-coding (prompts, templates, etc.)."""
from pathlib import Path

RESOURCES_DIR = Path(__file__).parent
PROMPTS_DIR = RESOURCES_DIR / "prompts"


def get_prompts_dir() -> Path:
    """Get the prompts directory path."""
    return PROMPTS_DIR


__all__ = ["RESOURCES_DIR", "PROMPTS_DIR", "get_prompts_dir"]
