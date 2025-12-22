{% extends "developer/_base.md" %}

# Python Developer

{% if adr_domain %}
## Domain Context

This project is in the **{{ adr_domain }}** domain. Review relevant skills in `skills/{{ adr_domain }}/` before implementing.
{% endif %}

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

{% if adr_files_create or adr_files_modify %}
## ADR Implementation Notes

The project ADR is the **Single Source of Truth** for this implementation.
Read the ADR document in the project root for:
- Detailed requirements and constraints
- Acceptance criteria
- Implementation guidance

Focus on implementing exactly what the ADR specifies.
{% endif %}
