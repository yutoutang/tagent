"""
Model registry for pi-coding.

Converted from TypeScript core/model-registry.ts
"""
import json
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass

from ..config import get_models_path
from pi.ai.models import get_all_models, get_providers, get_models


@dataclass
class ModelInfo:
    """Information about a model."""
    provider: str
    id: str
    name: str
    reasoning: bool = False
    api: str = ""
    context_window: int = 0
    max_tokens: int = 0
    input: list[str] = None

    def __post_init__(self):
        if self.input is None:
            self.input = ["text"]


class ModelRegistry:
    """
    Registry of available models.

    Uses models from pi.ai and combines with user-defined models from ~/.pi/agent/models.json
    """

    def __init__(
        self,
        auth_storage: Optional[Any] = None,  # AuthStorage
        models_path: Optional[str | Path] = None,
    ):
        """
        Initialize the model registry.

        Args:
            auth_storage: AuthStorage instance for checking credentials
            models_path: Path to models.json file
        """
        self.auth_storage = auth_storage
        self.models_path = Path(models_path) if models_path else get_models_path()
        self._user_models: list[dict[str, Any]] = []

        # Load user models
        self._load_user_models()

    def _load_user_models(self) -> None:
        """Load user-defined models from models.json."""
        if self.models_path.exists():
            try:
                with open(self.models_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self._user_models = data
                    elif isinstance(data, dict) and "models" in data:
                        self._user_models = data["models"]
            except (json.JSONDecodeError, IOError):
                self._user_models = []

    @property
    def _builtin_providers(self) -> list[str]:
        """Get list of providers from pi.ai."""
        return get_providers()

    def list_providers(self) -> list[str]:
        """
        List all available providers.

        Returns:
            List of provider names
        """
        providers = set(self._builtin_providers)

        # Add providers from user models
        for model_dict in self._user_models:
            if "provider" in model_dict:
                providers.add(model_dict["provider"])

        return sorted(providers)

    def list_models(self, provider: Optional[str] = None) -> list[ModelInfo]:
        """
        List all available models.

        Args:
            provider: Optional provider filter

        Returns:
            List of ModelInfo objects
        """
        models = []

        # Add models from pi.ai
        if provider:
            # Get models for specific provider
            ai_models = get_models(provider)
            for model in ai_models:
                models.append(ModelInfo(
                    provider=model.provider,
                    id=model.id,
                    name=model.name,
                    reasoning=model.reasoning,
                    api=model.api,
                    context_window=model.contextWindow,
                    max_tokens=model.maxTokens,
                    input=model.input,
                ))
        else:
            # Get all models from all providers
            for provider_name in self._builtin_providers:
                ai_models = get_models(provider_name)
                for model in ai_models:
                    models.append(ModelInfo(
                        provider=model.provider,
                        id=model.id,
                        name=model.name,
                        reasoning=model.reasoning,
                        api=model.api,
                        context_window=model.contextWindow,
                        max_tokens=model.maxTokens,
                        input=model.input,
                    ))

        # Add user models
        for model_dict in self._user_models:
            if provider is None or model_dict.get("provider") == provider:
                models.append(ModelInfo(
                    provider=model_dict.get("provider", ""),
                    id=model_dict.get("id", ""),
                    name=model_dict.get("name", ""),
                    reasoning=model_dict.get("reasoning", False),
                    api=model_dict.get("api", ""),
                    context_window=model_dict.get("contextWindow", 0),
                    max_tokens=model_dict.get("maxTokens", 0),
                    input=model_dict.get("input", ["text"]),
                ))

        return models

    def find(self, provider: str, model_id: str) -> Optional[dict[str, Any]]:
        """
        Find a model by provider and ID.

        Args:
            provider: Provider name
            model_id: Model ID

        Returns:
            Model dict or None if not found
        """
        # Check pi.ai models first
        from pi.ai.models import get_model as get_ai_model
        ai_model = get_ai_model(provider, model_id)
        if ai_model:
            return {
                "provider": ai_model.provider,
                "id": ai_model.id,
                "name": ai_model.name,
                "api": ai_model.api,
                "baseUrl": ai_model.baseUrl,
                "reasoning": ai_model.reasoning,
                "input": ai_model.input,
                "cost": {
                    "input": ai_model.cost.input,
                    "output": ai_model.cost.output,
                    "cacheRead": ai_model.cost.cacheRead,
                    "cacheWrite": ai_model.cost.cacheWrite,
                },
                "contextWindow": ai_model.contextWindow,
                "maxTokens": ai_model.maxTokens,
            }

        # Check user models
        for model_dict in self._user_models:
            if (model_dict.get("provider") == provider and
                model_dict.get("id") == model_id):
                return model_dict

        return None

    async def get_api_key(self, model: dict[str, Any]) -> Optional[str]:
        """
        Get API key for a model.

        Args:
            model: Model dict

        Returns:
            API key or None if not found
        """
        if not self.auth_storage:
            return None

        provider = model.get("provider", "")
        return self.auth_storage.get_api_key(provider)

    async def get_api_key_for_provider(self, provider: str) -> Optional[str]:
        """
        Get API key for a provider.

        Args:
            provider: Provider name

        Returns:
            API key or None if not found
        """
        if not self.auth_storage:
            return None

        return self.auth_storage.get_api_key(provider)

    def is_using_oauth(self, model: dict[str, Any]) -> bool:
        """
        Check if a model uses OAuth authentication.

        Args:
            model: Model dict

        Returns:
            True if model uses OAuth
        """
        if not self.auth_storage:
            return False

        provider = model.get("provider", "")
        return self.auth_storage.get_oauth_token(provider) is not None

    def search(
        self,
        query: str,
        provider: Optional[str] = None,
    ) -> list[ModelInfo]:
        """
        Search for models by query string.

        Args:
            query: Search query
            provider: Optional provider filter

        Returns:
            List of matching ModelInfo objects
        """
        query_lower = query.lower()
        results = []

        for model_info in self.list_models(provider):
            # Search in name and ID
            if (query_lower in model_info.name.lower() or
                query_lower in model_info.id.lower() or
                query_lower in model_info.provider.lower()):
                results.append(model_info)

        return results


__all__ = [
    "ModelInfo",
    "ModelRegistry",
]
