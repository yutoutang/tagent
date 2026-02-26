"""
Environment API Key Management

Get API keys for providers from environment variables.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from .types import KnownProvider

# Cache for Vertex ADC credentials check
_cached_vertex_adc_credentials_exists: Optional[bool] = None


def _has_vertex_adc_credentials() -> bool:
    """Check if Google Vertex ADC credentials exist."""
    global _cached_vertex_adc_credentials_exists

    if _cached_vertex_adc_credentials_exists is not None:
        return _cached_vertex_adc_credentials_exists

    # Check GOOGLE_APPLICATION_CREDENTIALS env var first (standard way)
    gac_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if gac_path:
        _cached_vertex_adc_credentials_exists = Path(gac_path).exists()
    else:
        # Fall back to default ADC path
        home = Path.home()
        adc_path = home / ".config" / "gcloud" / "application_default_credentials.json"
        _cached_vertex_adc_credentials_exists = adc_path.exists()

    return _cached_vertex_adc_credentials_exists


def get_env_api_key(provider: str) -> Optional[str]:
    """
    Get API key for provider from known environment variables.

    Will not return API keys for providers that require OAuth tokens.

    Args:
        provider: The provider name

    Returns:
        The API key or None if not found
    """
    if provider == "github-copilot":
        return (
            os.environ.get("COPILOT_GITHUB_TOKEN") or
            os.environ.get("GH_TOKEN") or
            os.environ.get("GITHUB_TOKEN")
        )

    # ANTHROPIC_OAUTH_TOKEN takes precedence over ANTHROPIC_API_KEY
    if provider == "anthropic":
        return (
            os.environ.get("ANTHROPIC_OAUTH_TOKEN") or
            os.environ.get("ANTHROPIC_API_KEY")
        )

    # Vertex AI uses Application Default Credentials, not API keys.
    # Auth is configured via `gcloud auth application-default login`.
    if provider == "google-vertex":
        has_credentials = _has_vertex_adc_credentials()
        has_project = bool(
            os.environ.get("GOOGLE_CLOUD_PROJECT") or
            os.environ.get("GCLOUD_PROJECT")
        )
        has_location = bool(os.environ.get("GOOGLE_CLOUD_LOCATION"))

        if has_credentials and has_project and has_location:
            return "<authenticated>"
        return None

    if provider == "amazon-bedrock":
        # Amazon Bedrock supports multiple credential sources:
        # 1. AWS_PROFILE - named profile from ~/.aws/credentials
        # 2. AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY - standard IAM keys
        # 3. AWS_BEARER_TOKEN_BEDROCK - Bedrock API keys (bearer token)
        # 4. AWS_CONTAINER_CREDENTIALS_RELATIVE_URI - ECS task roles
        # 5. AWS_CONTAINER_CREDENTIALS_FULL_URI - ECS task roles (full URI)
        # 6. AWS_WEB_IDENTITY_TOKEN_FILE - IRSA (IAM Roles for Service Accounts)
        if (
            os.environ.get("AWS_PROFILE") or
            (os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY")) or
            os.environ.get("AWS_BEARER_TOKEN_BEDROCK") or
            os.environ.get("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI") or
            os.environ.get("AWS_CONTAINER_CREDENTIALS_FULL_URI") or
            os.environ.get("AWS_WEB_IDENTITY_TOKEN_FILE")
        ):
            return "<authenticated>"
        return None

    # Environment variable mapping for other providers
    env_map: dict[str, str] = {
        "openai": "OPENAI_API_KEY",
        "azure-openai-responses": "AZURE_OPENAI_API_KEY",
        "google": "GEMINI_API_KEY",
        "groq": "GROQ_API_KEY",
        "cerebras": "CEREBRAS_API_KEY",
        "xai": "XAI_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "vercel-ai-gateway": "AI_GATEWAY_API_KEY",
        "zai": "ZAI_API_KEY",
        "mistral": "MISTRAL_API_KEY",
        "minimax": "MINIMAX_API_KEY",
        "minimax-cn": "MINIMAX_CN_API_KEY",
        "huggingface": "HF_TOKEN",
        "opencode": "OPENCODE_API_KEY",
        "kimi-coding": "KIMI_API_KEY",
    }

    env_var = env_map.get(provider)
    return os.environ.get(env_var) if env_var else None
