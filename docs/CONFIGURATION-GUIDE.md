# HELIX Configuration Guide

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| HELIX_ROOT | auto-detect | Root directory of HELIX |
| HELIX_VENV | $HELIX_ROOT/.venv | Virtual environment path |
| CLAUDE_MODEL | opus | Default Claude model |
| ENABLE_LSP_TOOL | 0 | Enable LSP diagnostics |

## PathConfig

All paths are centralized in `src/helix/config/paths.py`.

### Available Paths

- `PathConfig.HELIX_ROOT` - Project root
- `PathConfig.VENV_PATH` - Virtual environment
- `PathConfig.CLAUDE_CMD` - Claude CLI wrapper
- `PathConfig.DOMAIN_EXPERTS_CONFIG` - Domain experts YAML
- `PathConfig.LLM_PROVIDERS_CONFIG` - LLM providers YAML
- `PathConfig.TEMPLATES_DIR` - Jinja2 templates
- `PathConfig.SKILLS_DIR` - Skills directory
