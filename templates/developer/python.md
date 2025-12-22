{% extends "developer/_base.md" %}

# Python Developer

## Additional Python Rules

- Use `pathlib.Path` for file paths
- Use `dataclasses` or `pydantic` for data structures
- Use `async/await` for I/O operations
- Format with `black`, lint with `ruff`
- Dependencies only from pyproject.toml

## Import Structure

```python
# Standard library
from pathlib import Path
from dataclasses import dataclass

# Third party
import httpx
import yaml

# Local
from helix.observability import HelixLogger
```
