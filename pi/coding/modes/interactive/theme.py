"""
Theme system for CLI interface.

Provides Claude Code-inspired styling with clean, minimal design.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class ThemeColors:
    """Color palette for the theme."""
    # Primary colors
    primary: str = "cyan"
    secondary: str = "blue"
    accent: str = "magenta"

    # Status colors
    success: str = "green"
    error: str = "red"
    warning: str = "yellow"
    info: str = "blue"

    # Text colors
    text: str = "white"
    text_dim: str = "dim"
    text_muted: str = "bright_black"

    # Background colors
    bg_primary: str = "cyan"
    bg_secondary: str = "blue"


@dataclass
class ThemeIcons:
    """Icons and symbols for the theme."""
    # Status icons
    success: str = "✓"
    error: str = "✗"
    warning: str = "⚠"
    info: str = "ℹ"
    running: str = "⏳"
    pending: str = "○"

    # Role icons
    user: str = ">"
    assistant: str = ""
    tool: str = "▶"

    # Progress indicators
    spinner_frames: tuple = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")

    # Arrows and pointers
    arrow_right: str = "→"
    arrow_down: str = "↓"
    bullet: str = "•"
    dash: str = "─"


@dataclass
class ThemeSpacing:
    """Spacing and layout settings."""
    # Padding
    panel_padding: tuple = (0, 1)
    message_padding: tuple = (0, 0)

    # Margins
    section_margin: int = 1
    line_margin: int = 0

    # Indentation
    content_indent: int = 2
    nested_indent: int = 4


@dataclass
class Theme:
    """Complete theme configuration."""
    name: str
    colors: ThemeColors
    icons: ThemeIcons
    spacing: ThemeSpacing

    # Display options
    show_thinking: bool = True
    show_tool_args: bool = True
    show_timestamps: bool = False
    show_tokens: bool = True
    compact_mode: bool = False

    # Animation options
    streaming_enabled: bool = True
    animation_speed: float = 0.05


# Claude Code theme - clean, minimal, professional
claude_code_theme = Theme(
    name="claude-code",
    colors=ThemeColors(
        primary="cyan",
        secondary="blue",
        accent="magenta",
        success="green",
        error="red",
        warning="yellow",
        info="blue",
        text="white",
        text_dim="dim",
        text_muted="bright_black",
    ),
    icons=ThemeIcons(
        success="✓",
        error="✗",
        warning="⚠",
        info="ℹ",
        running="⏳",
        pending="○",
        user=">",
        assistant="",
        tool="▶",
        spinner_frames=("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"),
        arrow_right="→",
        arrow_down="↓",
        bullet="•",
        dash="─",
    ),
    spacing=ThemeSpacing(
        panel_padding=(0, 1),
        message_padding=(0, 0),
        section_margin=1,
        line_margin=0,
        content_indent=2,
        nested_indent=4,
    ),
    show_thinking=True,
    show_tool_args=True,
    show_timestamps=False,
    show_tokens=True,
    compact_mode=False,
    streaming_enabled=True,
    animation_speed=0.05,
)


# Default theme instance
current_theme: Optional[Theme] = None


def get_theme() -> Theme:
    """Get the current theme, creating default if needed."""
    global current_theme
    if current_theme is None:
        current_theme = claude_code_theme
    return current_theme


def set_theme(theme: Theme) -> None:
    """Set the current theme."""
    global current_theme
    current_theme = theme


def create_theme(
    name: str = "claude-code",
    show_thinking: bool = True,
    compact_mode: bool = False,
    **kwargs
) -> Theme:
    """Create a customized theme."""
    base = claude_code_theme

    colors = ThemeColors(**{**vars(base.colors), **kwargs.get('colors', {})})
    icons = ThemeIcons(**{**vars(base.icons), **kwargs.get('icons', {})})
    spacing = ThemeSpacing(**{**vars(base.spacing), **kwargs.get('spacing', {})})

    return Theme(
        name=name,
        colors=colors,
        icons=icons,
        spacing=spacing,
        show_thinking=show_thinking,
        show_tool_args=kwargs.get('show_tool_args', base.show_tool_args),
        show_timestamps=kwargs.get('show_timestamps', base.show_timestamps),
        show_tokens=kwargs.get('show_tokens', base.show_tokens),
        compact_mode=compact_mode,
        streaming_enabled=kwargs.get('streaming_enabled', base.streaming_enabled),
        animation_speed=kwargs.get('animation_speed', base.animation_speed),
    )
