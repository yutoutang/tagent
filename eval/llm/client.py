"""
LLM client wrapper.

Reuses existing LangChain client pattern from intent_system/yagent/graph.py.
"""

import os
import time
from typing import Any, Dict, List, Optional, Union

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from ..core.models import LLMConfig, LLMProvider


class LLMClient:
    """
    LLM client wrapper.

    Reuses create_default_components pattern from graph.py.
    """

    def __init__(self, config: LLMConfig):
        """
        Initialize LLM client.

        Args:
            config: LLM configuration
        """
        self.config = config
        self._client = self._create_client()

    def _create_client(self) -> Union[ChatOpenAI, ChatAnthropic]:
        """
        Create LangChain LLM client.

        Follows pattern from intent_system/yagent/graph.py:create_default_components().
        """
        api_key = self.config.get_api_key()

        if not api_key:
            # Try to get from environment variable
            if self.config.provider == LLMProvider.ANTHROPIC:
                api_key = os.getenv("ANTHROPIC_API_KEY")
            else:
                api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise ValueError(
                "API key not configured. Set either 'api_key' or 'sk' in config, "
                "or set OPENAI_API_KEY/ANTHROPIC_API_KEY environment variable"
            )

        # Create client based on provider
        if self.config.provider == LLMProvider.ANTHROPIC:
            return ChatAnthropic(
                model=self.config.model_name,
                api_key=api_key,
                timeout=self.config.timeout,
            )
        else:  # OPENAI or CUSTOM
            llm_kwargs = {
                "model": self.config.model_name,
                "api_key": api_key,
                "temperature": self.config.temperature,
                "timeout": self.config.timeout,
            }

            if self.config.base_url:
                llm_kwargs["base_url"] = self.config.base_url

            if self.config.max_tokens:
                llm_kwargs["max_tokens"] = self.config.max_tokens

            return ChatOpenAI(**llm_kwargs)

    def generate(
        self, prompt: str, system_prompt: Optional[str] = None, **kwargs
    ) -> str:
        """
        Generate completion.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            **kwargs: Additional parameters

        Returns:
            Generated text
        """
        messages: List[BaseMessage] = []

        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))

        messages.append(HumanMessage(content=prompt))

        start_time = time.time()

        try:
            response = self._client.invoke(messages, **kwargs)
            return response.content
        except Exception as e:
            raise RuntimeError(f"LLM generation failed: {e}")

    async def generate_async(
        self, prompt: str, system_prompt: Optional[str] = None, **kwargs
    ) -> str:
        """
        Generate completion asynchronously.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            **kwargs: Additional parameters

        Returns:
            Generated text
        """
        messages: List[BaseMessage] = []

        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))

        messages.append(HumanMessage(content=prompt))

        start_time = time.time()

        try:
            response = await self._client.ainvoke(messages, **kwargs)
            return response.content
        except Exception as e:
            raise RuntimeError(f"Async LLM generation failed: {e}")

    def batch_generate(
        self, prompts: List[str], system_prompt: Optional[str] = None, **kwargs
    ) -> List[str]:
        """
        Generate completions for multiple prompts.

        Args:
            prompts: List of user prompts
            system_prompt: Optional system prompt
            **kwargs: Additional parameters

        Returns:
            List of generated texts
        """
        results = []
        for prompt in prompts:
            result = self.generate(prompt, system_prompt, **kwargs)
            results.append(result)
        return results
