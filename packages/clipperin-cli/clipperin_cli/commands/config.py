"""Config command."""

import json
from pathlib import Path

import typer

from clipperin_core import Config, WhisperModel, AIProvider, OutputConfig
from clipperin_cli.config.settings import get_config_path, load_user_config, save_user_config


app = typer.Typer(help="Manage CLI configuration.")


def config_command(
    key: str = typer.Argument(None, help="Config key to set/get"),
    value: str = typer.Argument(None, help="Value to set"),
    list_all: bool = typer.Option(False, "-l", "--list", help="List all config"),
    edit: bool = typer.Option(False, "-e", "--edit", help="Open config in editor"),
) -> None:
    """
    Manage CLI configuration.

    Examples:
        clipperin config                           # Show all config
        clipperin config --list                    # List all config
        clipperin config ai.provider groq          # Set AI provider
        clipperin config ai.groq_api_key sk-xxxx   # Set API key
        clipperin config whisper.model base        # Set Whisper model
    """
    config = load_user_config()

    if edit:
        import subprocess
        config_path = get_config_path()
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.touch(exist_ok=True)
        editor = typer.get_editor() or "vi"
        subprocess.call([editor, str(config_path)])
        return

    if list_all:
        _print_config(config)
        return

    if not key:
        _print_config(config)
        return

    # Parse key (supports dot notation: ai.provider)
    keys = key.split(".")
    obj = config

    # Navigate to the parent object
    for k in keys[:-1]:
        if hasattr(obj, k):
            obj = getattr(obj, k)
        else:
            typer.echo(f"Error: Unknown key '{k}'", err=True)
            raise typer.Exit(1)

    final_key = keys[-1]

    if value is None:
        # Get value
        if hasattr(obj, final_key):
            val = getattr(obj, final_key)
            if isinstance(val, Path):
                typer.echo(str(val))
            elif isinstance(val, list):
                typer.echo(json.dumps([v.__dict__ for v in val], indent=2, default=str))
            else:
                typer.echo(val)
        else:
            typer.echo(f"Error: Unknown key '{final_key}'", err=True)
            raise typer.Exit(1)
    else:
        # Set value
        if hasattr(obj, final_key):
            # Try to parse as JSON for complex types
            try:
                parsed = json.loads(value)
                value = parsed
            except (json.JSONDecodeError, TypeError):
                pass

            # Handle enum types
            if final_key == "model" and isinstance(obj, type(Config().whisper)):
                setattr(obj, final_key, WhisperModel(value))
            elif final_key == "provider" and isinstance(obj, type(Config().ai)):
                setattr(obj, final_key, AIProvider(value))
            elif final_key == "aspect_ratio" and isinstance(obj, type(Config().output)):
                setattr(obj, final_key, value)  # String for aspect ratio
            else:
                setattr(obj, final_key, value)

            save_user_config(config)
            typer.echo(f"Set {key} = {value}")
        else:
            typer.echo(f"Error: Unknown key '{final_key}'", err=True)
            raise typer.Exit(1)


def _print_config(config: Config) -> None:
    """Pretty print configuration."""
    from clipperin_cli.output.table import print_table

    headers = ["Key", "Value"]
    rows = [
        ["Whisper Model", config.whisper.model.value],
        ["Whisper Language", config.whisper.language or "auto"],
        ["AI Provider", config.ai.provider.value],
        ["Gemini Key", "***" if config.ai.gemini_api_key else "(not set)"],
        ["Groq Key", "***" if config.ai.groq_api_key else "(not set)"],
        ["OpenAI Key", "***" if config.ai.openai_api_key else "(not set)"],
        ["Aspect Ratio", config.output.aspect_ratio.value],
        ["Progress Bar", "enabled" if config.output.enable_progress_bar else "disabled"],
        ["Data Dir", str(config.data_dir)],
        ["Jobs Dir", str(config.jobs_dir)],
    ]

    print_table(headers, rows)
