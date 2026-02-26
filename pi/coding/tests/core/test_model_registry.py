"""Tests for ModelRegistry."""
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from pi.coding.core.model_registry import (
    ModelRegistry,
    ModelInfo,
)


class TestModelRegistry:
    """Test cases for ModelRegistry."""

    def test_init_without_auth_storage(self, tmp_path: Path) -> None:
        """Test initialization without auth storage."""
        models_path = tmp_path / "models.json"
        registry = ModelRegistry(auth_storage=None, models_path=models_path)

        assert registry.models_path == models_path
        assert registry.auth_storage is None

    def test_list_all_models(self, tmp_path: Path) -> None:
        """Test listing all available models."""
        registry = ModelRegistry(auth_storage=None, models_path=tmp_path / "models.json")

        models = registry.list_models()

        # Should have models from pi.ai (749 total)
        assert len(models) > 100
        assert all(isinstance(m, ModelInfo) for m in models)

    def test_list_models_by_provider(self, tmp_path: Path) -> None:
        """Test listing models filtered by provider."""
        registry = ModelRegistry(auth_storage=None, models_path=tmp_path / "models.json")

        anthropic_models = registry.list_models(provider="anthropic")

        assert all(m.provider == "anthropic" for m in anthropic_models)
        assert len(anthropic_models) > 0

    def test_find_builtin_model(self, tmp_path: Path) -> None:
        """Test finding a built-in model."""
        registry = ModelRegistry(auth_storage=None, models_path=tmp_path / "models.json")

        # Try to find a common model that should exist
        model = registry.find("anthropic", "claude-3-5-sonnet-20240620")

        # The model might exist under a different ID format
        if model:
            assert model["provider"] == "anthropic"
        else:
            # Try another common model
            model = registry.find("openai", "gpt-4o")
            assert model is not None
            assert model["provider"] == "openai"

    def test_find_nonexistent_model(self, tmp_path: Path) -> None:
        """Test finding a non-existent model."""
        registry = ModelRegistry(auth_storage=None, models_path=tmp_path / "models.json")

        model = registry.find("nonexistent", "nonexistent-model")

        assert model is None

    def test_search_models(self, tmp_path: Path) -> None:
        """Test searching models by query."""
        registry = ModelRegistry(auth_storage=None, models_path=tmp_path / "models.json")

        # Search for "claude"
        results = registry.search("claude")

        assert len(results) > 0
        assert all("claude" in m.name.lower() or "claude" in m.id.lower()
                   for m in results)

    def test_search_models_by_provider(self, tmp_path: Path) -> None:
        """Test searching models within a provider."""
        registry = ModelRegistry(auth_storage=None, models_path=tmp_path / "models.json")

        results = registry.search("gpt", provider="openai")

        assert all(m.provider == "openai" for m in results)

    def test_search_no_results(self, tmp_path: Path) -> None:
        """Test search with no results."""
        registry = ModelRegistry(auth_storage=None, models_path=tmp_path / "models.json")

        results = registry.search("nonexistent-model-xyz-123")

        assert results == []

    @pytest.mark.asyncio
    async def test_get_api_key_with_auth_storage(self, tmp_path: Path) -> None:
        """Test getting API key with auth storage."""
        auth_storage = MagicMock()
        auth_storage.get_api_key = MagicMock(return_value="sk-test-key")

        registry = ModelRegistry(
            auth_storage=auth_storage,
            models_path=tmp_path / "models.json"
        )

        model = {"provider": "anthropic", "id": "claude-opus-4-5"}
        api_key = await registry.get_api_key(model)

        assert api_key == "sk-test-key"
        auth_storage.get_api_key.assert_called_once_with("anthropic")

    @pytest.mark.asyncio
    async def test_get_api_key_without_auth_storage(self, tmp_path: Path) -> None:
        """Test getting API key without auth storage."""
        registry = ModelRegistry(
            auth_storage=None,
            models_path=tmp_path / "models.json"
        )

        model = {"provider": "anthropic", "id": "claude-opus-4-5"}
        api_key = await registry.get_api_key(model)

        assert api_key is None

    @pytest.mark.asyncio
    async def test_get_api_key_for_provider(self, tmp_path: Path) -> None:
        """Test getting API key for provider."""
        auth_storage = MagicMock()
        auth_storage.get_api_key = MagicMock(return_value="sk-provider-key")

        registry = ModelRegistry(
            auth_storage=auth_storage,
            models_path=tmp_path / "models.json"
        )

        api_key = await registry.get_api_key_for_provider("openai")

        assert api_key == "sk-provider-key"
        auth_storage.get_api_key.assert_called_once_with("openai")

    def test_is_using_oauth(self, tmp_path: Path) -> None:
        """Test checking if model uses OAuth."""
        auth_storage = MagicMock()
        auth_storage.get_oauth_token = MagicMock(return_value="oauth-token-123")

        registry = ModelRegistry(
            auth_storage=auth_storage,
            models_path=tmp_path / "models.json"
        )

        model = {"provider": "anthropic", "id": "claude-opus-4-5"}
        result = registry.is_using_oauth(model)

        assert result is True
        auth_storage.get_oauth_token.assert_called_once_with("anthropic")

    def test_is_using_oauth_no_token(self, tmp_path: Path) -> None:
        """Test OAuth check when no token exists."""
        auth_storage = MagicMock()
        auth_storage.get_oauth_token = MagicMock(return_value=None)

        registry = ModelRegistry(
            auth_storage=auth_storage,
            models_path=tmp_path / "models.json"
        )

        model = {"provider": "openai", "id": "gpt-4o"}
        result = registry.is_using_oauth(model)

        assert result is False

    def test_is_using_oauth_without_auth_storage(self, tmp_path: Path) -> None:
        """Test OAuth check without auth storage."""
        registry = ModelRegistry(
            auth_storage=None,
            models_path=tmp_path / "models.json"
        )

        model = {"provider": "anthropic", "id": "claude-opus-4-5"}
        result = registry.is_using_oauth(model)

        assert result is False


class TestUserModels:
    """Test cases for user-defined models."""

    def test_load_user_models(self, tmp_path: Path) -> None:
        """Test loading user models from file."""
        models_path = tmp_path / "models.json"
        user_models = [
            {
                "provider": "custom",
                "id": "custom-model-1",
                "name": "Custom Model 1",
                "reasoning": False,
            },
            {
                "provider": "custom",
                "id": "custom-model-2",
                "name": "Custom Model 2",
                "reasoning": True,
            },
        ]
        models_path.write_text(json.dumps(user_models))

        registry = ModelRegistry(auth_storage=None, models_path=models_path)

        # Should include both built-in and user models
        all_models = registry.list_models()
        custom_models = [m for m in all_models if m.provider == "custom"]

        assert len(custom_models) == 2
        assert custom_models[0].name == "Custom Model 1"
        assert custom_models[1].reasoning is True

    def test_load_user_models_dict_format(self, tmp_path: Path) -> None:
        """Test loading user models in dict format."""
        models_path = tmp_path / "models.json"
        user_models = {
            "models": [
                {
                    "provider": "custom",
                    "id": "custom-model",
                    "name": "Custom",
                }
            ]
        }
        models_path.write_text(json.dumps(user_models))

        registry = ModelRegistry(auth_storage=None, models_path=models_path)

        custom_models = [m for m in registry.list_models() if m.provider == "custom"]
        assert len(custom_models) == 1

    def test_find_user_model(self, tmp_path: Path) -> None:
        """Test finding a user-defined model."""
        models_path = tmp_path / "models.json"
        user_models = [
            {
                "provider": "custom",
                "id": "my-custom-model",
                "name": "My Custom Model",
            }
        ]
        models_path.write_text(json.dumps(user_models))

        registry = ModelRegistry(auth_storage=None, models_path=models_path)

        model = registry.find("custom", "my-custom-model")

        assert model is not None
        assert model["id"] == "my-custom-model"
        assert model["name"] == "My Custom Model"

    def test_search_user_models(self, tmp_path: Path) -> None:
        """Test searching includes user models."""
        models_path = tmp_path / "models.json"
        user_models = [
            {
                "provider": "custom",
                "id": "my-ai-model",
                "name": "My AI Model",
            }
        ]
        models_path.write_text(json.dumps(user_models))

        registry = ModelRegistry(auth_storage=None, models_path=models_path)

        results = registry.search("my ai")

        assert any(m.provider == "custom" for m in results)


class TestBuiltinModels:
    """Test cases for built-in models from pi.ai."""

    def test_builtin_models_structure(self, tmp_path: Path) -> None:
        """Test that built-in models have required fields."""
        registry = ModelRegistry(auth_storage=None, models_path=tmp_path / "models.json")
        models = registry.list_models()

        for model in models[:10]:  # Test first 10 models
            assert model.provider is not None
            assert model.id is not None
            assert model.name is not None
            assert isinstance(model.reasoning, bool)

    def test_builtin_anthropic_models(self, tmp_path: Path) -> None:
        """Test Anthropic built-in models from pi.ai."""
        registry = ModelRegistry(auth_storage=None, models_path=tmp_path / "models.json")
        anthropic_models = registry.list_models(provider="anthropic")

        assert len(anthropic_models) > 0
        # Check that we have Claude models
        model_ids = [m.id for m in anthropic_models]
        assert any("claude" in m_id.lower() for m_id in model_ids)

    def test_builtin_openai_models(self, tmp_path: Path) -> None:
        """Test OpenAI built-in models from pi.ai."""
        registry = ModelRegistry(auth_storage=None, models_path=tmp_path / "models.json")
        openai_models = registry.list_models(provider="openai")

        assert len(openai_models) > 0
        # Check that we have GPT models
        model_ids = [m.id for m in openai_models]
        assert any("gpt" in m_id.lower() for m_id in model_ids)

    def test_reasoning_models(self, tmp_path: Path) -> None:
        """Test models marked as reasoning models."""
        registry = ModelRegistry(auth_storage=None, models_path=tmp_path / "models.json")

        # Get all models and filter for reasoning
        all_models = registry.list_models()
        reasoning_models = [m for m in all_models if m.reasoning is True]

        # There should be some reasoning models (o1, o1-mini, etc.)
        assert len(reasoning_models) > 0
        # At least one should be from OpenAI
        reasoning_providers = {m.provider for m in reasoning_models}
        assert "openai" in reasoning_providers or "amazon-bedrock" in reasoning_providers

    def test_total_model_count(self, tmp_path: Path) -> None:
        """Test that we have a reasonable number of models."""
        registry = ModelRegistry(auth_storage=None, models_path=tmp_path / "models.json")
        all_models = registry.list_models()

        # Should have 749 models from pi.ai
        assert len(all_models) > 700

    def test_provider_count(self, tmp_path: Path) -> None:
        """Test that we have all expected providers."""
        registry = ModelRegistry(auth_storage=None, models_path=tmp_path / "models.json")
        providers = registry.list_providers()

        # Should have at least these major providers
        assert "anthropic" in providers
        assert "openai" in providers
        assert "google" in providers
        assert "groq" in providers


class TestModelInfo:
    """Test cases for ModelInfo dataclass."""

    def test_model_info_creation(self) -> None:
        """Test creating ModelInfo."""
        info = ModelInfo(
            provider="anthropic",
            id="claude-opus-4-5",
            name="Claude Opus 4.5",
            reasoning=False,
        )

        assert info.provider == "anthropic"
        assert info.id == "claude-opus-4-5"
        assert info.name == "Claude Opus 4.5"
        assert info.reasoning is False

    def test_model_info_default_reasoning(self) -> None:
        """Test ModelInfo with default reasoning value."""
        info = ModelInfo(
            provider="openai",
            id="gpt-4o",
            name="GPT-4o",
        )

        assert info.reasoning is False


class TestModelRegistryEdgeCases:
    """Edge case tests for ModelRegistry."""

    def test_malformed_user_models(self, tmp_path: Path) -> None:
        """Test handling of malformed user models file."""
        models_path = tmp_path / "models.json"
        models_path.write_text("invalid json")

        registry = ModelRegistry(auth_storage=None, models_path=models_path)

        # Should not error, just skip user models
        models = registry.list_models()
        # Should still have built-in models
        assert len(models) > 0

    def test_empty_user_models(self, tmp_path: Path) -> None:
        """Test handling of empty user models file."""
        models_path = tmp_path / "models.json"
        models_path.write_text("[]")

        registry = ModelRegistry(auth_storage=None, models_path=models_path)

        models = registry.list_models()
        # Should have all models from pi.ai (749 models)
        assert len(models) > 700

    def test_user_model_missing_fields(self, tmp_path: Path) -> None:
        """Test handling of user models with missing fields."""
        models_path = tmp_path / "models.json"
        user_models = [
            {
                "provider": "custom",
                # Missing id
                "name": "Custom",
            }
        ]
        models_path.write_text(json.dumps(user_models))

        registry = ModelRegistry(auth_storage=None, models_path=models_path)

        # Should handle gracefully
        model = registry.find("custom", "")
        # Model won't be found due to missing id
        assert model is None or model.get("id") == ""

    def test_case_sensitive_search(self, tmp_path: Path) -> None:
        """Test that search is case-insensitive."""
        registry = ModelRegistry(auth_storage=None, models_path=tmp_path / "models.json")

        results_lower = registry.search("claude")
        results_upper = registry.search("CLAUDE")
        results_mixed = registry.search("ClAuDe")

        # All should return results
        assert len(results_lower) > 0
        assert len(results_upper) > 0
        assert len(results_mixed) > 0

        # Should return same models
        assert {m.id for m in results_lower} == {m.id for m in results_upper}
