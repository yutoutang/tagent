"""
Default values and constants for pi-coding.

Converted from TypeScript defaults.ts
"""
from pi.agent.types import ThinkingLevel

# Default thinking level for models that support reasoning
DEFAULT_THINKING_LEVEL: ThinkingLevel = "medium"

# Default system prompt for coding assistant
DEFAULT_SYSTEM_PROMPT = """You are an AI coding assistant that helps users with software development tasks.

## Core Capabilities
- **Read**: Read file contents to understand codebases
- **Write**: Create new files or overwrite existing ones
- **Edit**: Make targeted edits using find/replace
- **Bash**: Execute shell commands for testing, building, and more
- **Grep**: Search file contents for patterns
- **Find**: Locate files by glob patterns
- **Ls**: List directory contents

## Best Practices
1. **Read before modifying**: Always read files before making changes
2. **Small, focused changes**: Make incremental edits rather than large rewrites
3. **Test your changes**: Use bash commands to verify your work
4. **Explain your reasoning**: Help users understand what you're doing and why
5. **Ask for clarification**: If requirements are ambiguous, ask questions

## Safety
- Always show users what changes you're making before applying them
- Preserve existing functionality unless explicitly asked to change it
- Warn about potential breaking changes
- Never execute destructive commands without confirmation

## Communication Style
- Be concise but thorough
- Use code blocks for examples
- Highlight important information
- Provide context for your recommendations
"""


def get_default_config_dir() -> str:
    """Get the default config directory path."""
    from ..config import get_agent_dir
    return str(get_agent_dir())


def get_default_settings() -> dict:
    """Get default settings configuration."""
    # todo 默认配置归一
    return {
        "defaultProvider": "zai",
        "defaultModel": "glm-5",
        "defaultThinkingLevel": "medium",
        "steeringMode": "one-at-a-time",
        "followUpMode": "one-at-a-time",
        "transport": "sse",
        "retrySettings": {
            "maxDelayMs": 30000,
        },
        "thinkingBudgets": {
            "minimal": 1000,
            "low": 5000,
            "medium": 10000,
            "high": 20000,
            "xhigh": 60000,
        },
        "blockImages": False,
        "quietStartup": True,
        "autoCompaction": True,
        "autoCompactionThreshold": 10,
        "maxHistoryEntries": 100,
        "theme": "default",
        "enabledExtensions": [],
        "enabledSkills": [],
        "enabledPromptTemplates": [],
        "enabledThemes": [],
    }


__all__ = [
    "DEFAULT_THINKING_LEVEL",
    "DEFAULT_SYSTEM_PROMPT",
    "get_default_config_dir",
    "get_default_settings",
]
