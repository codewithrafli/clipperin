"""CLI commands."""

from clipper_cli.commands.download import download_command
from clipper_cli.commands.transcribe import transcribe_command
from clipper_cli.commands.analyze import analyze_command
from clipper_cli.commands.chapters import chapters_command
from clipper_cli.commands.render import render_command
from clipper_cli.commands.config import config_command

__all__ = [
    "download_command",
    "transcribe_command",
    "analyze_command",
    "chapters_command",
    "render_command",
    "config_command",
]
