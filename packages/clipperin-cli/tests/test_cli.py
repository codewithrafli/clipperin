"""Empty test file to establish test structure for clipperin-cli."""

import pytest


def test_cli_imports():
    """Test that CLI modules can be imported."""
    from clipperin_cli import __version__
    assert __version__ is not None
