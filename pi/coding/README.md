# Pi Coding - AI-Powered Coding CLI Tool

Python implementation of the coding-agent CLI tool, converted from TypeScript.

## Installation

```bash
# Install from source
pip install -e /path/to/tagent
```

## Usage

```bash
# Interactive mode (coming soon)
pi

# Print mode (non-interactive)
pi --print "List all .py files in src/"

# With specific model
pi --print --provider openai --model gpt-4o-mini "Help me refactor this code"

# Continue previous session
pi --continue --print "What did we discuss?"

# With thinking level
pi --print --thinking high "Solve this complex problem"
```

## Project Structure

```
pi/coding/
├── __init__.py          # Main API exports
├── cli.py               # CLI entry point
├── config.py            # Configuration paths
├── pyproject.toml       # Package configuration
├── cli/                 # CLI framework
│   ├── args.py          # Argument parsing
│   ├── config.py        # Config selection
│   ├── file_processor.py
│   ├── list_models.py   # Model listing
│   └── session_picker.py
├── core/                # Core business logic
│   ├── agent_session.py      # Session management
│   ├── auth_storage.py       # Authentication
│   ├── bash_executor.py      # Command execution
│   ├── defaults.py           # Default values
│   ├── event_bus.py          # Event system
│   ├── message_utils.py      # Message conversion
│   ├── model_registry.py     # Model definitions
│   ├── model_resolver.py     # Model resolution
│   ├── prompt_templates.py   # Prompt templates
│   ├── resource_loader.py    # Resource loading
│   ├── sdk.py                # Main SDK
│   ├── session_manager.py    # Session persistence
│   ├── settings_manager.py   # Settings management
│   └── system_prompt.py      # System prompt builder
├── modes/               # Runtime modes
│   ├── print_mode.py    # Non-interactive mode
│   └── interactive/     # Interactive mode (coming soon)
├── tools/               # Built-in tools
│   ├── read.py          # File reading
│   ├── write.py         # File writing
│   ├── edit.py          # File editing
│   ├── bash.py          # Command execution
│   ├── grep.py          # Text search
│   ├── find.py          # File finding
│   └── ls.py            # Directory listing
└── utils/               # Utility functions
```

## Available Tools

| Tool | Description |
|------|-------------|
| `read` | Read file contents |
| `write` | Write/create files |
| `edit` | Edit files with find/replace |
| `bash` | Execute shell commands |
| `grep` | Search file contents |
| `find` | Find files by pattern |
| `ls` | List directory contents |

## Configuration

Configuration is stored in `~/.pi/agent/`:

```
~/.pi/agent/
├── auth.json        # API keys and OAuth tokens
├── models.json      # Custom model definitions
├── settings.json    # User settings
└── sessions/        # Session files
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic Claude API key |
| `OPENAI_API_KEY` | OpenAI API key |
| `GEMINI_API_KEY` | Google Gemini API key |
| `GROQ_API_KEY` | Groq API key |
| `PI_CODING_AGENT_DIR` | Override config directory |

## Development

```bash
# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest pi/coding/tests/

# Format code
black pi/coding/
isort pi/coding/

# Type check
mypy pi/coding/
```

## License

MIT

## Converted From

This package is converted from the TypeScript `@mariozechner/pi-coding-agent` package.
