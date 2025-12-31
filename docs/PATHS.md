# PathConfig API Reference

## Overview

`PathConfig` provides centralized path management for HELIX.

## Usage

```python
from helix.config.paths import PathConfig

# Get paths
root = PathConfig.HELIX_ROOT
config = PathConfig.DOMAIN_EXPERTS_CONFIG

# Validate all paths exist
PathConfig.validate()

# Show path info
PathConfig.info()
```

## Properties

| Property | Type | Description |
|----------|------|-------------|
| HELIX_ROOT | Path | Project root directory |
| VENV_PATH | Path | Virtual environment |
| CLAUDE_CMD | Path | Claude CLI wrapper script |
| NVM_PATH | Path | Node.js via NVM |
| DOMAIN_EXPERTS_CONFIG | Path | config/domain-experts.yaml |
| LLM_PROVIDERS_CONFIG | Path | config/llm-providers.yaml |
| TEMPLATES_DIR | Path | templates/ directory |
| TEMPLATES_PHASES | Path | templates/phases/ |
| SKILLS_DIR | Path | skills/ directory |
