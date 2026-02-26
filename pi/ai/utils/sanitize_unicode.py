"""
Unicode sanitization utilities.
"""

from __future__ import annotations

import re


def sanitize_surrogates(text: str) -> str:
    """
    Removes unpaired Unicode surrogate characters from a string.

    Unpaired surrogates (high surrogates 0xD800-0xDBFF without matching low surrogates 0xDC00-0xDFFF,
    or vice versa) cause JSON serialization errors in many API providers.

    Valid emoji and other characters outside the Basic Multilingual Plane use properly paired
    surrogates and will NOT be affected by this function.

    Args:
        text: The text to sanitize

    Returns:
        The sanitized text with unpaired surrogates removed

    Example:
        # Valid emoji (properly paired surrogates) are preserved
        sanitize_surrogates("Hello World")  # => "Hello World"

        # Unpaired surrogates are removed
        sanitize_surrogates("Text \ud83d here")  # => "Text  here" (if unpaired)
    """
    # Python 3 handles surrogates differently than JavaScript
    # In Python, we can use error handlers to deal with surrogates
    try:
        # Encode and decode with surrogatepass to handle unpaired surrogates
        return text.encode('utf-8', errors='surrogatepass').decode('utf-8', errors='ignore')
    except (UnicodeDecodeError, UnicodeEncodeError):
        # Fallback: remove any remaining surrogate characters
        # High surrogates: U+D800 to U+DBFF
        # Low surrogates: U+DC00 to U+DFFF
        return re.sub(r'[\ud800-\udfff]', '', text)
