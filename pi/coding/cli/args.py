"""
CLI argument parsing for pi-coding.

Converted from TypeScript cli/args.ts
"""
from dataclasses import dataclass, field
from typing import Literal, Optional
from pi.agent.types import ThinkingLevel


Mode = Literal["text", "json", "rpc"]
ToolName = Literal["read", "bash", "edit", "write", "grep", "find", "ls"]

# Valid thinking levels
VALID_THINKING_LEVELS = ["off", "minimal", "low", "medium", "high", "xhigh"]

# All available tools
ALL_TOOLS: dict[str, ToolName] = {
    "read": "read",
    "bash": "bash",
    "edit": "edit",
    "write": "write",
    "grep": "grep",
    "find": "find",
    "ls": "ls",
}


def is_valid_thinking_level(level: str) -> bool:
    """Check if a string is a valid thinking level."""
    return level in VALID_THINKING_LEVELS


@dataclass
class CliArgs:
    """Parsed CLI arguments."""

    # Provider and model options
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None

    # System prompt options
    system_prompt: Optional[str] = None
    append_system_prompt: Optional[str] = None

    # Thinking level
    thinking: Optional[ThinkingLevel] = None

    # Session management
    continue_: bool = False
    resume: bool = False
    no_session: bool = False
    session: Optional[str] = None
    session_dir: Optional[str] = None

    # Model selection
    models: Optional[list[str]] = None

    # Tool options
    no_tools: bool = False
    tools: Optional[list[ToolName]] = None

    # Extension options
    extensions: Optional[list[str]] = None
    no_extensions: bool = False

    # Skill options
    no_skills: bool = False
    skills: Optional[list[str]] = None

    # Prompt template options
    prompt_templates: Optional[list[str]] = None
    no_prompt_templates: bool = False

    # Theme options
    themes: Optional[list[str]] = None
    no_themes: bool = False

    # Output options
    mode: Optional[Mode] = None
    print_: bool = False
    export: Optional[str] = None

    # Utility options
    list_models: Optional[str | bool] = None
    verbose: bool = False
    help: bool = False
    version: bool = False

    # Messages and file arguments
    messages: list[str] = field(default_factory=list)
    file_args: list[str] = field(default_factory=list)

    # Unknown flags (for extension flags)
    unknown_flags: dict[str, bool | str] = field(default_factory=dict)


def parse_args(args: list[str], extension_flags: Optional[dict[str, Literal["boolean", "string"]]] = None) -> CliArgs:
    """
    Parse CLI arguments.

    Args:
        args: List of command-line arguments (excluding program name)
        extension_flags: Optional map of extension flag names to their types

    Returns:
        Parsed arguments as CliArgs dataclass
    """
    result = CliArgs()

    i = 0
    while i < len(args):
        arg = args[i]

        if arg in ("--help", "-h"):
            result.help = True
        elif arg in ("--version", "-v"):
            result.version = True
        elif arg == "--mode" and i + 1 < len(args):
            mode = args[i + 1]
            if mode in ("text", "json", "rpc"):
                result.mode = mode
            i += 1
        elif arg in ("--continue", "-c"):
            result.continue_ = True
        elif arg in ("--resume", "-r"):
            result.resume = True
        elif arg == "--provider" and i + 1 < len(args):
            result.provider = args[i + 1]
            i += 1
        elif arg == "--model" and i + 1 < len(args):
            result.model = args[i + 1]
            i += 1
        elif arg == "--api-key" and i + 1 < len(args):
            result.api_key = args[i + 1]
            i += 1
        elif arg == "--system-prompt" and i + 1 < len(args):
            result.system_prompt = args[i + 1]
            i += 1
        elif arg == "--append-system-prompt" and i + 1 < len(args):
            result.append_system_prompt = args[i + 1]
            i += 1
        elif arg == "--no-session":
            result.no_session = True
        elif arg == "--session" and i + 1 < len(args):
            result.session = args[i + 1]
            i += 1
        elif arg == "--session-dir" and i + 1 < len(args):
            result.session_dir = args[i + 1]
            i += 1
        elif arg == "--models" and i + 1 < len(args):
            result.models = [s.strip() for s in args[i + 1].split(",")]
            i += 1
        elif arg == "--no-tools":
            result.no_tools = True
        elif arg == "--tools" and i + 1 < len(args):
            tool_names = [s.strip() for s in args[i + 1].split(",")]
            valid_tools: list[ToolName] = []
            for name in tool_names:
                if name in ALL_TOOLS:
                    valid_tools.append(ALL_TOOLS[name])
                else:
                    import sys
                    print(f"Warning: Unknown tool '{name}'. Valid tools: {', '.join(ALL_TOOLS.keys())}", file=sys.stderr)
            result.tools = valid_tools
            i += 1
        elif arg == "--thinking" and i + 1 < len(args):
            level = args[i + 1]
            if is_valid_thinking_level(level):
                result.thinking = level
            else:
                import sys
                print(f"Warning: Invalid thinking level '{level}'. Valid values: {', '.join(VALID_THINKING_LEVELS)}", file=sys.stderr)
            i += 1
        elif arg in ("--print", "-p"):
            result.print_ = True
        elif arg == "--export" and i + 1 < len(args):
            result.export = args[i + 1]
            i += 1
        elif arg in ("--extension", "-e") and i + 1 < len(args):
            if result.extensions is None:
                result.extensions = []
            result.extensions.append(args[i + 1])
            i += 1
        elif arg in ("--no-extensions", "-ne"):
            result.no_extensions = True
        elif arg == "--skill" and i + 1 < len(args):
            if result.skills is None:
                result.skills = []
            result.skills.append(args[i + 1])
            i += 1
        elif arg == "--prompt-template" and i + 1 < len(args):
            if result.prompt_templates is None:
                result.prompt_templates = []
            result.prompt_templates.append(args[i + 1])
            i += 1
        elif arg == "--theme" and i + 1 < len(args):
            if result.themes is None:
                result.themes = []
            result.themes.append(args[i + 1])
            i += 1
        elif arg in ("--no-skills", "-ns"):
            result.no_skills = True
        elif arg in ("--no-prompt-templates", "-np"):
            result.no_prompt_templates = True
        elif arg == "--no-themes":
            result.no_themes = True
        elif arg == "--list-models":
            # Check if next arg is a search pattern
            if i + 1 < len(args) and not args[i + 1].startswith("-") and not args[i + 1].startswith("@"):
                result.list_models = args[i + 1]
                i += 1
            else:
                result.list_models = True
        elif arg == "--verbose":
            result.verbose = True
        elif arg.startswith("@"):
            # File argument (remove @ prefix)
            result.file_args.append(arg[1:])
        elif arg.startswith("--") and extension_flags:
            # Check if it's an extension-registered flag
            flag_name = arg[2:]
            ext_flag = extension_flags.get(flag_name)
            if ext_flag:
                if ext_flag == "boolean":
                    result.unknown_flags[flag_name] = True
                elif ext_flag == "string" and i + 1 < len(args):
                    result.unknown_flags[flag_name] = args[i + 1]
                    i += 1
        elif not arg.startswith("-"):
            # Positional message argument
            result.messages.append(arg)

        i += 1

    return result


def print_help() -> None:
    """Print help message."""
    from ..config import APP_NAME, CONFIG_DIR_NAME, ENV_AGENT_DIR, VERSION

    help_text = f"""{APP_NAME} - AI coding assistant with read, bash, edit, write tools v{VERSION}

Usage:
  {APP_NAME} [options] [@files...] [messages...]

Commands:
  {APP_NAME} install <source> [-l]    Install extension source and add to settings
  {APP_NAME} remove <source> [-l]     Remove extension source from settings
  {APP_NAME} update [source]          Update installed extensions (skips pinned sources)
  {APP_NAME} list                     List installed extensions from settings
  {APP_NAME} config                   Open TUI to enable/disable package resources
  {APP_NAME} <command> --help         Show help for install/remove/update/list

Options:
  --provider <name>              Provider name (default: google)
  --model <pattern>              Model pattern or ID (supports "provider/id" and optional ":<thinking>")
  --api-key <key>                API key (defaults to env vars)
  --system-prompt <text>         System prompt (default: coding assistant prompt)
  --append-system-prompt <text>  Append text or file contents to the system prompt
  --mode <mode>                  Output mode: text (default), json, or rpc
  --print, -p                    Non-interactive mode: process prompt and exit
  --continue, -c                 Continue previous session
  --resume, -r                   Select a session to resume
  --session <path>               Use specific session file
  --session-dir <dir>            Directory for session storage and lookup
  --no-session                   Don't save session (ephemeral)
  --models <patterns>            Comma-separated model patterns for Ctrl+P cycling
                                Supports globs (anthropic/*, *sonnet*) and fuzzy matching
  --no-tools                     Disable all built-in tools
  --tools <tools>                Comma-separated list of tools to enable (default: read,bash,edit,write)
                                Available: read, bash, edit, write, grep, find, ls
  --thinking <level>             Set thinking level: off, minimal, low, medium, high, xhigh
  --extension, -e <path>         Load an extension file (can be used multiple times)
  --no-extensions, -ne           Disable extension discovery (explicit -e paths still work)
  --skill <path>                 Load a skill file or directory (can be used multiple times)
  --no-skills, -ns               Disable skills discovery and loading
  --prompt-template <path>       Load a prompt template file or directory (can be used multiple times)
  --no-prompt-templates, -np     Disable prompt template discovery and loading
  --theme <path>                 Load a theme file or directory (can be used multiple times)
  --no-themes                    Disable theme discovery and loading
  --export <file>                Export session file to HTML and exit
  --list-models [search]         List available models (with optional fuzzy search)
  --verbose                      Force verbose startup (overrides quietStartup setting)
  --help, -h                     Show this help
  --version, -v                  Show version number

Examples:
  # Interactive mode
  {APP_NAME}

  # Interactive mode with initial prompt
  {APP_NAME} "List all .py files in src/"

  # Include files in initial message
  {APP_NAME} @prompt.md @image.png "What color is the sky?"

  # Non-interactive mode (process and exit)
  {APP_NAME} -p "List all .py files in src/"

  # Multiple messages (interactive)
  {APP_NAME} "Read pyproject.toml" "What dependencies do we have?"

  # Continue previous session
  {APP_NAME} --continue "What did we discuss?"

  # Use different model
  {APP_NAME} --provider openai --model gpt-4o-mini "Help me refactor this code"

  # Use model with provider prefix (no --provider needed)
  {APP_NAME} --model openai/gpt-4o "Help me refactor this code"

  # Use model with thinking level shorthand
  {APP_NAME} --model sonnet:high "Solve this complex problem"

  # Read-only mode (no file modifications possible)
  {APP_NAME} --tools read,grep,find,ls -p "Review the code in src/"

Available Tools (default: read, bash, edit, write):
  read   - Read file contents
  bash   - Execute bash commands
  edit   - Edit files with find/replace
  write  - Write files (creates/overwrites)
  grep   - Search file contents (read-only, off by default)
  find   - Find files by glob pattern (read-only, off by default)
  ls     - List directory contents (read-only, off by default)

For more information, see: https://github.com/badlogic/pi-mono
"""
    print(help_text)


__all__ = [
    "Mode",
    "ToolName",
    "CliArgs",
    "is_valid_thinking_level",
    "parse_args",
    "print_help",
]
