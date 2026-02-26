"""Tests for AuthStorage."""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from pi.coding.core.auth_storage import AuthStorage, AuthEntry


class TestAuthStorage:
    """Test cases for AuthStorage."""

    def test_init_creates_directory(self, tmp_path: Path) -> None:
        """Test that auth file directory is created."""
        auth_path = tmp_path / "auth.json"
        storage = AuthStorage(auth_path=auth_path)

        assert auth_path.parent.exists()
        assert storage.auth_path == auth_path

    def test_get_api_key_not_found(self, tmp_path: Path) -> None:
        """Test getting API key when none exists."""
        storage = AuthStorage(auth_path=tmp_path / "auth.json")

        result = storage.get_api_key("anthropic")
        assert result is None

    def test_set_and_get_api_key(self, tmp_path: Path) -> None:
        """Test setting and getting API key."""
        storage = AuthStorage(auth_path=tmp_path / "auth.json")

        storage.set_api_key("anthropic", "sk-test-key-123")

        result = storage.get_api_key("anthropic")
        assert result == "sk-test-key-123"

    def test_api_key_persistence(self, tmp_path: Path) -> None:
        """Test that API keys persist across instances."""
        auth_path = tmp_path / "auth.json"

        storage1 = AuthStorage(auth_path=auth_path)
        storage1.set_api_key("openai", "sk-openai-key")

        storage2 = AuthStorage(auth_path=auth_path)
        result = storage2.get_api_key("openai")
        assert result == "sk-openai-key"

    def test_get_api_key_from_env(self, tmp_path: Path) -> None:
        """Test getting API key from environment variable."""
        storage = AuthStorage(auth_path=tmp_path / "auth.json")

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-env-key"}):
            result = storage.get_api_key("anthropic")
            assert result == "sk-env-key"

    def test_storage_takes_precedence_over_env(self, tmp_path: Path) -> None:
        """Test that stored key takes precedence over env var."""
        storage = AuthStorage(auth_path=tmp_path / "auth.json")
        storage.set_api_key("anthropic", "sk-stored-key")

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-env-key"}):
            result = storage.get_api_key("anthropic")
            assert result == "sk-stored-key"

    def test_set_oauth_token(self, tmp_path: Path) -> None:
        """Test setting OAuth token."""
        storage = AuthStorage(auth_path=tmp_path / "auth.json")

        storage.set_oauth_token("anthropic", "oauth-token-123")

        result = storage.get_oauth_token("anthropic")
        assert result == "oauth-token-123"

    def test_get_oauth_token_not_found(self, tmp_path: Path) -> None:
        """Test getting OAuth token when none exists."""
        storage = AuthStorage(auth_path=tmp_path / "auth.json")

        result = storage.get_oauth_token("anthropic")
        assert result is None

    def test_has_credentials(self, tmp_path: Path) -> None:
        """Test checking if provider has credentials."""
        storage = AuthStorage(auth_path=tmp_path / "auth.json")

        assert storage.has("anthropic") is False

        storage.set_api_key("anthropic", "sk-key")
        assert storage.has("anthropic") is True

    def test_has_with_oauth_token(self, tmp_path: Path) -> None:
        """Test has with OAuth token."""
        storage = AuthStorage(auth_path=tmp_path / "auth.json")

        storage.set_oauth_token("openai", "oauth-token")
        assert storage.has("openai") is True

    def test_remove_provider(self, tmp_path: Path) -> None:
        """Test removing provider credentials."""
        storage = AuthStorage(auth_path=tmp_path / "auth.json")
        storage.set_api_key("anthropic", "sk-key")

        storage.remove("anthropic")

        assert storage.has("anthropic") is False
        assert storage.get_api_key("anthropic") is None

    def test_remove_nonexistent_provider(self, tmp_path: Path) -> None:
        """Test removing provider that doesn't exist (should not error)."""
        storage = AuthStorage(auth_path=tmp_path / "auth.json")

        storage.remove("nonexistent")  # Should not raise

    def test_list_providers(self, tmp_path: Path) -> None:
        """Test listing providers with credentials."""
        storage = AuthStorage(auth_path=tmp_path / "auth.json")

        storage.set_api_key("anthropic", "sk-key1")
        storage.set_api_key("openai", "sk-key2")
        storage.set_oauth_token("google", "oauth-token")

        providers = storage.list_providers()

        assert set(providers) == {"anthropic", "openai", "google"}

    def test_list_providers_empty(self, tmp_path: Path) -> None:
        """Test listing providers when none exist."""
        storage = AuthStorage(auth_path=tmp_path / "auth.json")

        providers = storage.list_providers()
        assert providers == []

    def test_multiple_providers(self, tmp_path: Path) -> None:
        """Test storing credentials for multiple providers."""
        storage = AuthStorage(auth_path=tmp_path / "auth.json")

        storage.set_api_key("anthropic", "sk-anthropic")
        storage.set_api_key("openai", "sk-openai")
        storage.set_api_key("google", "sk-google")

        assert storage.get_api_key("anthropic") == "sk-anthropic"
        assert storage.get_api_key("openai") == "sk-openai"
        assert storage.get_api_key("google") == "sk-google"

    def test_env_var_mapping(self, tmp_path: Path) -> None:
        """Test environment variable name mapping."""
        storage = AuthStorage(auth_path=tmp_path / "auth.json")

        with patch.dict("os.environ", {
            "ANTHROPIC_API_KEY": "sk-1",
            "OPENAI_API_KEY": "sk-2",
            "GEMINI_API_KEY": "sk-3",
            "GROQ_API_KEY": "sk-4",
        }):
            assert storage.get_api_key("anthropic") == "sk-1"
            assert storage.get_api_key("openai") == "sk-2"
            assert storage.get_api_key("google") == "sk-3"
            assert storage.get_api_key("groq") == "sk-4"

    def test_static_create(self, tmp_path: Path) -> None:
        """Test static create method."""
        storage = AuthStorage.create(auth_path=tmp_path / "auth.json")
        assert storage.auth_path == tmp_path / "auth.json"


class TestAuthEntry:
    """Test cases for AuthEntry dataclass."""

    def test_auth_entry(self) -> None:
        """Test AuthEntry dataclass."""
        entry = AuthEntry(
            provider="anthropic",
            api_key="sk-test-key",
            oauth_token=None,
        )
        assert entry.provider == "anthropic"
        assert entry.api_key == "sk-test-key"
        assert entry.oauth_token is None

    def test_auth_entry_with_oauth(self) -> None:
        """Test AuthEntry with OAuth token."""
        entry = AuthEntry(
            provider="openai",
            api_key=None,
            oauth_token="oauth-token-123",
        )
        assert entry.provider == "openai"
        assert entry.api_key is None
        assert entry.oauth_token == "oauth-token-123"


class TestAuthStorageEdgeCases:
    """Edge case tests for AuthStorage."""

    def test_malformed_json_file(self, tmp_path: Path) -> None:
        """Test handling of malformed JSON file."""
        auth_path = tmp_path / "auth.json"
        auth_path.write_text("invalid json {")

        storage = AuthStorage(auth_path=auth_path)
        # Should not error, just start fresh
        result = storage.get_api_key("anthropic")
        assert result is None

    def test_empty_json_file(self, tmp_path: Path) -> None:
        """Test handling of empty JSON file."""
        auth_path = tmp_path / "auth.json"
        auth_path.write_text("{}")

        storage = AuthStorage(auth_path=auth_path)
        result = storage.get_api_key("anthropic")
        assert result is None

    def test_overwrite_existing_key(self, tmp_path: Path) -> None:
        """Test overwriting existing API key."""
        storage = AuthStorage(auth_path=tmp_path / "auth.json")

        storage.set_api_key("anthropic", "sk-old-key")
        storage.set_api_key("anthropic", "sk-new-key")

        result = storage.get_api_key("anthropic")
        assert result == "sk-new-key"

    def test_case_sensitive_provider(self, tmp_path: Path) -> None:
        """Test that provider names are case-sensitive."""
        storage = AuthStorage(auth_path=tmp_path / "auth.json")

        storage.set_api_key("Anthropic", "sk-1")
        storage.set_api_key("anthropic", "sk-2")

        assert storage.get_api_key("Anthropic") == "sk-1"
        assert storage.get_api_key("anthropic") == "sk-2"
