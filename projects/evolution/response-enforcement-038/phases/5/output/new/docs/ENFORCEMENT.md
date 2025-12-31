# Response Enforcement System

> ADR-038: Deterministic LLM Response Enforcement

## Overview

The Response Enforcement System ensures LLM responses meet required formats and constraints. It wraps the ClaudeRunner with automatic validation, retry logic, and fallback mechanisms.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    LLM Response Flow                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ClaudeRunner                                                   │
│       │                                                          │
│       ▼                                                          │
│   ┌───────────────────┐                                          │
│   │ ResponseEnforcer  │◄─── Wrapper um ClaudeRunner              │
│   │                   │                                          │
│   │ • max_retries: 2  │                                          │
│   │ • validators: []  │                                          │
│   └─────────┬─────────┘                                          │
│             │                                                    │
│             ▼                                                    │
│   ┌───────────────────┐                                          │
│   │  Validators       │                                          │
│   │  ─────────────    │                                          │
│   │  • StepMarker     │                                          │
│   │  • ADRStructure   │                                          │
│   │  • FileExistence  │                                          │
│   └─────────┬─────────┘                                          │
│             │                                                    │
│     ┌───────┴───────┐                                            │
│     │               │                                            │
│     ▼               ▼                                            │
│  VALID           INVALID                                         │
│     │               │                                            │
│     ▼               ▼                                            │
│  Return         Retry mit Feedback                               │
│                     │                                            │
│              ┌──────┴──────┐                                     │
│              │             │                                     │
│              ▼             ▼                                     │
│         Success      Max Retries                                 │
│                           │                                      │
│                    ┌──────┴──────┐                               │
│                    │             │                               │
│                    ▼             ▼                               │
│               Fallback      Stream Error                         │
│               anwenden      an Open WebUI                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Package Structure

```
src/helix/enforcement/
├── __init__.py               # Package exports
├── response_enforcer.py      # Main enforcer class
└── validators/
    ├── __init__.py           # Validator exports
    ├── base.py               # ResponseValidator ABC
    ├── step_marker.py        # STEP marker validation
    ├── adr_structure.py      # ADR completeness checks
    └── file_existence.py     # File reference checks
```

## Components

### ResponseEnforcer

The main wrapper around ClaudeRunner that provides:

- Automatic validation of LLM responses
- Retry with feedback prompt on validation failures
- Fallback heuristics when max retries reached
- SSE error streaming for Open WebUI

```python
from helix.enforcement import ResponseEnforcer
from helix.enforcement.validators import StepMarkerValidator

enforcer = ResponseEnforcer(
    runner=claude_runner,
    max_retries=2,
    validators=[StepMarkerValidator()]
)

result = await enforcer.run_with_enforcement(
    session_id="session-123",
    prompt="Create an ADR for...",
    validator_names=["step_marker"]  # Optional: filter validators
)

if result.success:
    print(result.response)
else:
    print(f"Failed: {result.issues}")
```

### Validators

All validators inherit from `ResponseValidator` ABC:

```python
from abc import ABC, abstractmethod
from typing import Optional

class ResponseValidator(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique validator name."""
        pass

    @abstractmethod
    def validate(self, response: str, context: dict) -> list[ValidationIssue]:
        """Return list of issues (empty if valid)."""
        pass

    def apply_fallback(self, response: str, context: dict) -> Optional[str]:
        """Optional: Try to fix the response."""
        return None
```

#### StepMarkerValidator

Ensures responses contain a valid STEP marker:

```python
# Valid: <!-- STEP: what -->
# Valid: <!-- STEP: generate -->
# Invalid: No marker
# Invalid: <!-- STEP: invalid_step -->

validator = StepMarkerValidator()
issues = validator.validate(response, {})
```

**Valid Steps:** `what`, `why`, `constraints`, `generate`, `finalize`, `done`

**Fallback:** Automatically infers step from content:
- ADR generation → `generate`
- Questions at end → `what`
- Constraint keywords → `constraints`
- Default → `done`

#### ADRStructureValidator

Checks ADR completeness when response contains an ADR:

```python
validator = ADRStructureValidator()
issues = validator.validate(adr_response, {})
```

**Checks:**
- YAML frontmatter with `adr_id`, `title`, `status`
- Required sections: `Kontext`, `Entscheidung`, `Akzeptanzkriterien`
- Minimum 3 acceptance criteria (warning)

**No Fallback:** ADR structure issues require manual correction.

#### FileExistenceValidator

Verifies file references in `files.modify` exist:

```python
validator = FileExistenceValidator(helix_root=Path("/path/to/helix"))
issues = validator.validate(adr_response, {})
```

**Fallback:** Moves non-existent files from `files.modify` to `files.create`.

### EnforcementResult

Result dataclass with metadata:

```python
@dataclass
class EnforcementResult:
    success: bool              # Did validation pass (or fallback work)?
    response: str              # Final response text
    attempts: int              # Number of attempts made
    issues: list[ValidationIssue]  # Remaining issues (warnings)
    fallback_applied: bool     # Was a fallback used?
```

### ValidationIssue

Individual validation problem:

```python
@dataclass
class ValidationIssue:
    code: str       # e.g., "MISSING_STEP_MARKER"
    message: str    # Human-readable description
    fix_hint: str   # How to fix it
    severity: str   # "error" or "warning"
```

## Usage Examples

### Basic Enforcement

```python
from helix.enforcement import ResponseEnforcer
from helix.enforcement.validators import (
    StepMarkerValidator,
    ADRStructureValidator,
)

# Create enforcer with validators
enforcer = ResponseEnforcer(
    runner=claude_runner,
    max_retries=2,
    validators=[
        StepMarkerValidator(),
        ADRStructureValidator(),
    ]
)

# Run with enforcement
result = await enforcer.run_with_enforcement(
    session_id=session_id,
    prompt=user_prompt,
)

if result.success:
    process_response(result.response)
elif result.issues:
    for issue in result.issues:
        log.error(f"{issue.code}: {issue.message}")
```

### Selective Validation

Only use specific validators for a call:

```python
# Only enforce step markers for chat
result = await enforcer.run_with_enforcement(
    session_id=session_id,
    prompt=prompt,
    validator_names=["step_marker"]  # Skip ADR and file checks
)
```

### Error Streaming

Stream validation errors to Open WebUI:

```python
if not result.success:
    async for chunk in enforcer.stream_enforcement_error(result.issues):
        yield chunk
```

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `max_retries` | 2 | Maximum retry attempts on validation failure |
| `validators` | [] | List of validators to apply |

## Adding Custom Validators

```python
from helix.enforcement.validators.base import ResponseValidator, ValidationIssue

class MyValidator(ResponseValidator):
    @property
    def name(self) -> str:
        return "my_validator"

    def validate(self, response: str, context: dict) -> list[ValidationIssue]:
        if "required_text" not in response:
            return [ValidationIssue(
                code="MISSING_TEXT",
                message="Required text not found",
                fix_hint="Add required_text to your response"
            )]
        return []

# Use it
enforcer.add_validator(MyValidator())
```

## Testing

Run enforcement tests:

```bash
pytest tests/unit/enforcement/ -v
```

## Related

- [ADR-038: Deterministic LLM Response Enforcement](../adr/038-deterministic-llm-response-enforcement.md)
- [ADR-034: Consultant Flow Refactoring](../adr/034-consultant-flow-refactoring.md)
