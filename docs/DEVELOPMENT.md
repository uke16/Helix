# HELIX v4 Development Guide

## Setup

```bash
# Clone
git clone <repo>
cd helix-v4

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

## Project Structure

```
helix-v4/
├── src/helix/          # Main package
│   ├── cli/            # CLI commands
│   ├── consultant/     # Meeting system
│   ├── observability/  # Logging/metrics
│   └── api/            # REST API (Phase 12)
├── templates/          # Jinja2 templates
├── config/             # YAML configurations
├── skills/             # Domain knowledge
├── tests/              # Test suite
├── adr/                # Architecture decisions
└── docs/               # Documentation
```

## Running Tests

```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/

# Integration tests
pytest tests/integration/

# With coverage
pytest --cov=helix
```

## Code Style

- **Formatter**: Black
- **Linter**: Ruff
- **Type Checker**: mypy

```bash
# Format
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/helix/
```

## Adding a New Module

1. Create module in `src/helix/`
2. Add type hints and docstrings
3. Export in `__init__.py`
4. Write unit tests
5. Write integration tests
6. Update documentation

## Adding a Domain Expert

1. Add to `config/domain-experts.yaml`
2. Create skills in `skills/<domain>/`
3. Add triggers/keywords

## Creating Templates

Templates use Jinja2:

```markdown
# {{ expert.name }}

{% for skill in expert.skills %}
- {{ skill }}
{% endfor %}
```

See `/templates/` for examples.
