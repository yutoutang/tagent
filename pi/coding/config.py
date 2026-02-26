"""
Configuration constants and path utilities for pi-coding.

Converted from TypeScript config.ts
"""
import os
import sys
from pathlib import Path
from typing import Optional

# =============================================================================
# Package Information
# =============================================================================

APP_NAME = "pi"
CONFIG_DIR_NAME = ".pi"
VERSION = "0.1.0"

# e.g., PI_CODING_AGENT_DIR
ENV_AGENT_DIR = f"{APP_NAME.upper()}_CODING_AGENT_DIR"

DEFAULT_SHARE_VIEWER_URL = "https://pi.dev/session/"


# =============================================================================
# Path Utilities
# =============================================================================

def get_package_dir() -> Path:
    """
    Get the base directory for resolving package assets.
    For Python packages, this is the directory containing this file.
    """
    return Path(__file__).parent.parent


def get_agent_dir() -> Path:
    """
    Get the agent config directory (e.g., ~/.pi/agent/)
    Can be overridden via PI_CODING_AGENT_DIR environment variable.
    """
    env_dir = os.environ.get(ENV_AGENT_DIR)
    if env_dir:
        if env_dir == "~":
            return Path.home()
        if env_dir.startswith("~/"):
            return Path.home() / env_dir[2:]
        return Path(env_dir)

    return Path.home() / CONFIG_DIR_NAME / "agent"


def get_themes_dir() -> Path:
    """Get path to built-in themes directory."""
    return get_package_dir() / "resources" / "themes"


def get_custom_themes_dir() -> Path:
    """Get path to user's custom themes directory."""
    return get_agent_dir() / "themes"


def get_export_template_dir() -> Path:
    """Get path to HTML export template directory."""
    return get_package_dir() / "resources" / "templates"


def get_models_path() -> Path:
    """Get path to models.json."""
    return get_agent_dir() / "models.json"


def get_auth_path() -> Path:
    """Get path to auth.json."""
    return get_agent_dir() / "auth.json"


def get_settings_path() -> Path:
    """Get path to settings.json."""
    return get_agent_dir() / "settings.json"


def get_tools_dir() -> Path:
    """Get path to tools directory."""
    return get_agent_dir() / "tools"


def get_bin_dir() -> Path:
    """Get path to managed binaries directory."""
    return get_agent_dir() / "bin"


def get_prompts_dir() -> Path:
    """Get path to prompt templates directory."""
    return get_agent_dir() / "prompts"


def get_sessions_dir() -> Path:
    """Get path to sessions directory."""
    return get_agent_dir() / "sessions"


def get_debug_log_path() -> Path:
    """Get path to debug log file."""
    return get_agent_dir() / f"{APP_NAME}-debug.log"


def get_docs_path() -> Path:
    """Get path to docs directory."""
    return get_package_dir() / "docs"


def get_examples_path() -> Path:
    """Get path to examples directory."""
    return get_package_dir() / "examples"


def get_readme_path() -> Path:
    """Get path to README.md."""
    return get_package_dir() / "README.md"


def get_changelog_path() -> Path:
    """Get path to CHANGELOG.md."""
    return get_package_dir() / "CHANGELOG.md"


def get_share_viewer_url(gist_id: str) -> str:
    """Get the share viewer URL for a gist ID."""
    base_url = os.environ.get("PI_SHARE_VIEWER_URL", DEFAULT_SHARE_VIEWER_URL)
    return f"{base_url}#{gist_id}"


# =============================================================================
# Environment Variables
# =============================================================================

ENV_VARS = {
    "ANTHROPIC_API_KEY": "Anthropic Claude API key",
    "ANTHROPIC_OAUTH_TOKEN": "Anthropic OAuth token (alternative to API key)",
    "OPENAI_API_KEY": "OpenAI GPT API key",
    "AZURE_OPENAI_API_KEY": "Azure OpenAI API key",
    "AZURE_OPENAI_BASE_URL": "Azure OpenAI base URL",
    "AZURE_OPENAI_RESOURCE_NAME": "Azure OpenAI resource name",
    "AZURE_OPENAI_API_VERSION": "Azure OpenAI API version",
    "AZURE_OPENAI_DEPLOYMENT_NAME_MAP": "Azure OpenAI model=deployment map",
    "GEMINI_API_KEY": "Google Gemini API key",
    "GROQ_API_KEY": "Groq API key",
    "CEREBRAS_API_KEY": "Cerebras API key",
    "XAI_API_KEY": "xAI Grok API key",
    "OPENROUTER_API_KEY": "OpenRouter API key",
    "AI_GATEWAY_API_KEY": "Vercel AI Gateway API key",
    "ZAI_API_KEY": "ZAI API key",
    "MISTRAL_API_KEY": "Mistral API key",
    "MINIMAX_API_KEY": "MiniMax API key",
    "KIMI_API_KEY": "Kimi For Coding API key",
    "AWS_PROFILE": "AWS profile for Amazon Bedrock",
    "AWS_ACCESS_KEY_ID": "AWS access key for Amazon Bedrock",
    "AWS_SECRET_ACCESS_KEY": "AWS secret key for Amazon Bedrock",
    "AWS_BEARER_TOKEN_BEDROCK": "Bedrock API key (bearer token)",
    "AWS_REGION": "AWS region for Amazon Bedrock",
    ENV_AGENT_DIR: f"Session storage directory (default: ~/{CONFIG_DIR_NAME}/agent)",
    "PI_PACKAGE_DIR": "Override package directory (for Nix/Guix store paths)",
    "PI_SHARE_VIEWER_URL": "Base URL for /share command",
    "PI_AI_ANTIGRAVITY_VERSION": "Override Antigravity User-Agent version",
}


__all__ = [
    # Package info
    "APP_NAME",
    "CONFIG_DIR_NAME",
    "VERSION",
    "ENV_AGENT_DIR",
    "DEFAULT_SHARE_VIEWER_URL",
    # Path utilities
    "get_package_dir",
    "get_agent_dir",
    "get_themes_dir",
    "get_custom_themes_dir",
    "get_export_template_dir",
    "get_models_path",
    "get_auth_path",
    "get_settings_path",
    "get_tools_dir",
    "get_bin_dir",
    "get_prompts_dir",
    "get_sessions_dir",
    "get_debug_log_path",
    "get_docs_path",
    "get_examples_path",
    "get_readme_path",
    "get_changelog_path",
    "get_share_viewer_url",
    # Environment variables
    "ENV_VARS",
]
