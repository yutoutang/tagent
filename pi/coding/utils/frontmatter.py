"""YAML frontmatter parser for pi-coding.

Converted from TypeScript utils/frontmatter.ts
"""
import re
from dataclasses import dataclass
from typing import Dict, Any, Generic, TypeVar

import yaml

T = TypeVar('T')


@dataclass
class ParsedFrontmatter(Generic[T]):
    """Result of parsing frontmatter from content."""
    frontmatter: T
    body: str


def _normalize_newlines(value: str) -> str:
    """Normalize line endings to Unix style."""
    return value.replace('\r\n', '\n').replace('\r', '\n')


def _extract_frontmatter(content: str) -> tuple[str | None, str]:
    """
    Extract YAML frontmatter from content.

    Args:
        content: Raw file content

    Returns:
        Tuple of (yaml_string, body) - yaml_string is None if no frontmatter
    """
    normalized = _normalize_newlines(content)

    if not normalized.startswith('---'):
        return None, normalized

    end_index = normalized.find('\n---', 3)
    if end_index == -1:
        return None, normalized

    yaml_string = normalized[4:end_index]
    body = normalized[end_index + 4:].strip()

    return yaml_string, body


def parse_frontmatter(content: str) -> ParsedFrontmatter[Dict[str, Any]]:
    """
    Parse YAML frontmatter from content.

    Args:
        content: Raw file content with optional frontmatter

    Returns:
        ParsedFrontmatter with frontmatter dict and body text

    Example:
        ```python
        content = '''---
        name: my-skill
        description: A skill
        ---
        # My Skill

        Content here.
        '''
        result = parse_frontmatter(content)
        print(result.frontmatter)  # {'name': 'my-skill', 'description': 'A skill'}
        print(result.body)  # '# My Skill\\n\\nContent here.'
        ```
    """
    yaml_string, body = _extract_frontmatter(content)

    if yaml_string is None:
        return ParsedFrontmatter(frontmatter={}, body=body)

    try:
        parsed = yaml.safe_load(yaml_string)
        if parsed is None:
            parsed = {}
        elif not isinstance(parsed, dict):
            # If YAML parsed to a non-dict, treat as empty
            parsed = {}
    except yaml.YAMLError:
        # If YAML parsing fails, return empty frontmatter
        parsed = {}

    return ParsedFrontmatter(frontmatter=parsed, body=body)


def strip_frontmatter(content: str) -> str:
    """
    Remove frontmatter and return only the body.

    Args:
        content: Raw file content with optional frontmatter

    Returns:
        Content with frontmatter removed
    """
    return parse_frontmatter(content).body


__all__ = [
    "ParsedFrontmatter",
    "parse_frontmatter",
    "strip_frontmatter",
]
