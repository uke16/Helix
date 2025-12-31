# Phase 1: Base Validator Interface

## Aufgabe

Erstelle das Grundgerüst für das Enforcement-System:

1. **Base Validator Interface** (`src/helix/enforcement/validators/base.py`)
2. **ResponseEnforcer Grundgerüst** (`src/helix/enforcement/response_enforcer.py`)
3. **Package Init Files**

## ADR Referenz

Lies `ADR-038.md` für die vollständige Spezifikation.

## Erwartete Output-Dateien

Erstelle in `output/new/`:

```
output/new/
├── src/helix/enforcement/
│   ├── __init__.py
│   ├── response_enforcer.py
│   └── validators/
│       ├── __init__.py
│       └── base.py
```

## Implementation Details

### base.py

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

@dataclass
class ValidationIssue:
    """Ein Validierungsproblem."""
    code: str
    message: str
    fix_hint: str
    severity: str = "error"  # error, warning

@dataclass
class ValidationResult:
    """Ergebnis einer Validierung."""
    valid: bool
    issues: list[ValidationIssue]

class ResponseValidator(ABC):
    """Base class für Response-Validatoren."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Eindeutiger Name des Validators."""
        pass

    @abstractmethod
    def validate(self, response: str, context: dict) -> list[ValidationIssue]:
        """Validiert eine LLM-Response."""
        pass

    def apply_fallback(self, response: str, context: dict) -> Optional[str]:
        """Wendet Fallback-Heuristik an wenn möglich."""
        return None
```

### response_enforcer.py

Implementiere das EnforcementResult dataclass und die ResponseEnforcer Klasse
gemäß ADR-038 Section "5. Response Enforcer".

## Quality Gate

- Alle Python-Dateien müssen syntaktisch korrekt sein
- Typ-Hints für alle public APIs

## Checkliste

- [ ] `src/helix/enforcement/__init__.py` erstellt
- [ ] `src/helix/enforcement/validators/__init__.py` erstellt
- [ ] `src/helix/enforcement/validators/base.py` mit ValidationIssue, ValidationResult, ResponseValidator
- [ ] `src/helix/enforcement/response_enforcer.py` mit EnforcementResult, ResponseEnforcer
- [ ] Alle Typ-Hints vorhanden
- [ ] Docstrings für alle Klassen und public Methoden
