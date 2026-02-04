"""CLI commands."""

from clipperin_cli.commands.download import download_command
from clipperin_cli.commands.transcribe import transcribe_command
from clipperin_cli.commands.analyze import analyze_command
from clipperin_cli.commands.chapters import chapters_command
from clipperin_cli.commands.render import render_command
from clipperin_cli.commands.config import config_command

__all__ = [
    "download_command",
    "transcribe_command",
    "analyze_command",
    "chapters_command",
    "render_command",
    "config_command",
]
