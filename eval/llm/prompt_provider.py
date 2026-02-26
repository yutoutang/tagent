"""
HTTP-based prompt template provider.

Fetches prompt templates from HTTP endpoints.
"""

import asyncio
from typing import Dict

import aiohttp
import requests

from ..core.models import PromptConfig


class PromptProvider:
    """
    HTTP-based prompt template provider.

    Features:
    - Fetch prompts from HTTP endpoints
    - Caching support
    - Async and sync support
    - Custom headers support
    """

    def __init__(self, config: PromptConfig):
        """
        Initialize prompt provider.

        Args:
            config: Prompt configuration
        """
        self.config = config
        self._cache: Dict[str, str] = {}

    def get_prompt(self) -> str:
        """
        Get prompt template (sync).

        Returns:
            Prompt template string

        Raises:
            RuntimeError: If fetch fails
        """
        # If inline template provided, use it
        if self.config.prompt_template:
            return self.config.prompt_template

        # If URL provided, fetch it
        if self.config.prompt_url:
            if self.config.cache_enabled and self.config.prompt_url in self._cache:
                return self._cache[self.config.prompt_url]

            try:
                response = requests.get(
                    self.config.prompt_url,
                    headers=self.config.prompt_headers,
                    timeout=10,
                )
                response.raise_for_status()

                prompt = response.text

                if self.config.cache_enabled:
                    self._cache[self.config.prompt_url] = prompt

                return prompt
            except Exception as e:
                raise RuntimeError(f"Failed to fetch prompt from URL: {e}")

        raise ValueError("Either prompt_url or prompt_template must be provided")

    async def get_prompt_async(self) -> str:
        """
        Get prompt template (async).

        Returns:
            Prompt template string
        """
        # If inline template provided, use it
        if self.config.prompt_template:
            return self.config.prompt_template

        # If URL provided, fetch it
        if self.config.prompt_url:
            if self.config.cache_enabled and self.config.prompt_url in self._cache:
                return self._cache[self.config.prompt_url]

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        self.config.prompt_url,
                        headers=self.config.prompt_headers,
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as response:
                        response.raise_for_status()
                        prompt = await response.text()

                        if self.config.cache_enabled:
                            self._cache[self.config.prompt_url] = prompt

                        return prompt
            except Exception as e:
                raise RuntimeError(f"Failed to fetch prompt from URL: {e}")

        raise ValueError("Either prompt_url or prompt_template must be provided")

    def clear_cache(self) -> None:
        """Clear prompt cache."""
        self._cache.clear()
