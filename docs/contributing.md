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
pip install -e "./packages/clipper-core[full]"
pip install -e "./packages/clipper-cli[full]"
pip install -e "./packages/clipper-ui[full]"

# Install development tools
pip install ruff mypy pytest
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=clipper_core --cov=clipper_cli --cov=clipper_ui

# Type checking
mypy packages/clipper-core/clipper_core
mypy packages/clipper-cli/clipper_cli
mypy packages/clipper-ui/backend/clipper_ui
```

## Code Style

```bash
# Format code
ruff format .

# Lint
ruff check .
```

## Adding a New Feature

1. **Core feature** - Add to `clipper-core`
   - New processor goes in `clipper_core/processors/`
   - New model goes in `clipper_core/models/`

2. **CLI command** - Add to `clipper-cli`
   - New command goes in `clipper_cli/commands/`
   - Register in `clipper_cli/main.py`

3. **UI endpoint** - Add to `clipper-ui`
   - New route goes in `clipper_ui/api/`
   - New schema goes in `clipper_ui/schemas/`

## Adding an AI Provider

1. Create `clipper_core/ai/newprovider.py`
2. Inherit from `AIClient`
3. Implement required methods: `is_configured()`, `generate()`, `chat()`
4. Register in `clipper_core/ai/__init__.py`
5. Add to config in `clipper_core/models/config.py`

## Adding a Caption Style

Add to `CaptionStyle.get_default_styles()` in `clipper_core/models/config.py`:

```python
cls(
    id="mystyle",
    name="My Style",
    font_name="Arial",
    font_size=48,
    font_color="white",
)
```
