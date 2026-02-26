"""Tests for interactive REPL mode."""
from pathlib import Path

import pytest

from pi.coding.modes.interactive.repl import REPL


class TestREPL:
    """Test cases for the REPL."""

    def test_welcome_message(self) -> None:
        """Test that welcome message can be displayed."""
        repl = REPL()
        # Just ensure it doesn't crash
        repl._print_welcome()

    def test_list_providers(self) -> None:
        """Test listing providers."""
        repl = REPL()
        # Should not crash
        repl._list_providers()

    def test_show_help(self) -> None:
        """Test showing help."""
        repl = REPL()
        # Should not crash
        repl._show_help()

    def test_show_current_thinking(self) -> None:
        """Test showing current thinking level."""
        repl = REPL(thinking="high")
        # Should not crash
        repl._show_current_thinking()

    def test_initialization_with_options(self) -> None:
        """Test REPL initialization with custom options."""
        repl = REPL(
            provider="anthropic",
            model="claude-opus-4-5",
            thinking="high",
        )

        assert repl.provider == "anthropic"
        assert repl.model == "claude-opus-4-5"
        assert repl.thinking == "high"


__all__ = ["TestREPL"]
