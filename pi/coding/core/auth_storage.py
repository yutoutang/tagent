"""
Authentication storage for pi-coding.

Converted from TypeScript core/auth-storage.ts
"""
import json
import os
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, asdict

from ..config import get_auth_path


@dataclass
class AuthEntry:
    """Authentication entry for a provider."""
    provider: str
    api_key: Optional[str] = None
    oauth_token: Optional[str] = None


class AuthStorage:
    """
    Manages authentication credentials storage.

    Stores API keys and OAuth tokens in ~/.pi/agent/auth.json
    """

    def __init__(self, auth_path: Optional[str | Path] = None):
        """
        Initialize auth storage.

        Args:
            auth_path: Path to auth.json file (default: ~/.pi/agent/auth.json)
        """
        self.auth_path = Path(auth_path) if auth_path else get_auth_path()
        self._auth_data: dict[str, dict[str, Any]] = {}

        # Create directory if it doesn't exist
        self.auth_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing auth data
        self._load()

    def _load(self) -> None:
        """Load auth data from file."""
        if self.auth_path.exists():
            try:
                with open(self.auth_path, "r", encoding="utf-8") as f:
                    self._auth_data = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._auth_data = {}

    def _save(self) -> None:
        """Save auth data to file."""
        with open(self.auth_path, "w", encoding="utf-8") as f:
            json.dump(self._auth_data, f, indent=2)

    def get_api_key(self, provider: str) -> Optional[str]:
        """
        Get API key for a provider.

        Args:
            provider: Provider name (e.g., "anthropic", "openai")

        Returns:
            API key or None if not found
        """
        # Check storage first
        if provider in self._auth_data:
            # key: model sk todo api key 和 key 统一
            return self._auth_data[provider].get("key")

        # Check environment variables
        env_var = self._get_env_var(provider)
        if env_var:
            return os.environ.get(env_var)

        return None

    def set_api_key(self, provider: str, api_key: str) -> None:
        """
        Set API key for a provider.

        Args:
            provider: Provider name
            api_key: API key to store
        """
        if provider not in self._auth_data:
            self._auth_data[provider] = {}

        self._auth_data[provider]["apiKey"] = api_key
        self._save()

    def get_oauth_token(self, provider: str) -> Optional[str]:
        """
        Get OAuth token for a provider.

        Args:
            provider: Provider name

        Returns:
            OAuth token or None if not found
        """
        if provider in self._auth_data:
            return self._auth_data[provider].get("oauthToken")
        return None

    def set_oauth_token(self, provider: str, token: str) -> None:
        """
        Set OAuth token for a provider.

        Args:
            provider: Provider name
            token: OAuth token to store
        """
        if provider not in self._auth_data:
            self._auth_data[provider] = {}

        self._auth_data[provider]["oauthToken"] = token
        self._save()

    def remove(self, provider: str) -> None:
        """
        Remove authentication data for a provider.

        Args:
            provider: Provider name
        """
        if provider in self._auth_data:
            del self._auth_data[provider]
            self._save()

    def has(self, provider: str) -> bool:
        """
        Check if provider has auth data.

        Args:
            provider: Provider name

        Returns:
            True if provider has auth data
        """
        return provider in self._auth_data and bool(
            self._auth_data[provider].get("apiKey") or
            self._auth_data[provider].get("oauthToken")
        )

    def list_providers(self) -> list[str]:
        """Get list of providers with auth data."""
        return [
            provider for provider, data in self._auth_data.items()
            if data.get("apiKey") or data.get("oauthToken")
        ]

    def _get_env_var(self, provider: str) -> Optional[str]:
        """
        Get environment variable name for a provider.

        Args:
            provider: Provider name

        Returns:
            Environment variable name or None
        """
        env_vars = {
            "anthropic": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY",
            "google": "GEMINI_API_KEY",
            "groq": "GROQ_API_KEY",
            "cerebras": "CEREBRAS_API_KEY",
            "xai": "XAI_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
            "ai_gateway": "AI_GATEWAY_API_KEY",
            "zai": "ZAI_API_KEY",
            "mistral": "MISTRAL_API_KEY",
            "minimax": "MINIMAX_API_KEY",
            "kimi": "KIMI_API_KEY",
        }
        return env_vars.get(provider.lower())

    @staticmethod
    def create(auth_path: Optional[str | Path] = None) -> "AuthStorage":
        """
        Create an AuthStorage instance.

        Args:
            auth_path: Optional path to auth.json file

        Returns:
            New AuthStorage instance
        """
        return AuthStorage(auth_path)


__all__ = [
    "AuthEntry",
    "AuthStorage",
]
