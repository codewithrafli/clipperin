# Contributing

## Development Setup

```bash
# Clone repository
git clone https://github.com/yourname/auto-clipper.git
cd auto-clipper

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e "./packages/clipperin-core[full]"
pip install -e "./packages/clipperin-cli[full]"
pip install -e "./packages/clipperin-ui[full]"

# Install development tools
pip install ruff mypy pytest
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=clipperin_core --cov=clipperin_cli --cov=clipperin_ui

# Type checking
mypy packages/clipperin-core/clipperin_core
mypy packages/clipperin-cli/clipperin_cli
mypy packages/clipperin-ui/backend/clipperin_ui
```

## Code Style

```bash
# Format code
ruff format .

# Lint
ruff check .
```

## Adding a New Feature

1. **Core feature** - Add to `clipperin-core`
   - New processor goes in `clipperin_core/processors/`
   - New model goes in `clipperin_core/models/`

2. **CLI command** - Add to `clipperin-cli`
   - New command goes in `clipperin_cli/commands/`
   - Register in `clipperin_cli/main.py`

3. **UI endpoint** - Add to `clipperin-ui`
   - New route goes in `clipperin_ui/api/`
   - New schema goes in `clipperin_ui/schemas/`

## Adding an AI Provider

1. Create `clipperin_core/ai/newprovider.py`
2. Inherit from `AIClient`
3. Implement required methods: `is_configured()`, `generate()`, `chat()`
4. Register in `clipperin_core/ai/__init__.py`
5. Add to config in `clipperin_core/models/config.py`

## Adding a Caption Style

Add to `CaptionStyle.get_default_styles()` in `clipperin_core/models/config.py`:

```python
cls(
    id="mystyle",
    name="My Style",
    font_name="Arial",
    font_size=48,
    font_color="white",
)
```
