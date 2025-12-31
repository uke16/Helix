# Phase 2: Step Marker Validator

## Aufgabe

Implementiere den StepMarkerValidator mit Fallback-Heuristik.

## ADR Referenz

Lies `ADR-038.md` Section "2. Step Marker Validator".

## Input

- Phase 1 Output: Base Validator Interface

## Erwartete Output-Dateien

Erstelle in `output/new/`:

```
output/new/
├── src/helix/enforcement/validators/
│   └── step_marker.py
└── tests/unit/enforcement/
    ├── __init__.py
    └── test_step_marker.py
```

## Implementation Details

### step_marker.py

```python
import re
from typing import Optional
from .base import ResponseValidator, ValidationIssue

class StepMarkerValidator(ResponseValidator):
    """Validiert dass STEP-Marker vorhanden ist."""

    PATTERN = r'<!--\s*STEP:\s*(\w+)\s*-->'
    VALID_STEPS = {"what", "why", "constraints", "generate", "finalize", "done"}

    @property
    def name(self) -> str:
        return "step_marker"

    def validate(self, response: str, context: dict) -> list[ValidationIssue]:
        # Implementiere Validierung gemäß ADR
        pass

    def apply_fallback(self, response: str, context: dict) -> Optional[str]:
        # Implementiere Heuristik-basierte Step-Zuweisung gemäß ADR
        pass
```

### test_step_marker.py

Teste:
1. Gültiger Step-Marker wird akzeptiert
2. Fehlender Step-Marker wird erkannt
3. Ungültiger Step wird erkannt
4. Fallback fügt korrekten Step hinzu
5. Fallback-Heuristik für verschiedene Response-Typen

## Quality Gate

- `pytest tests/unit/enforcement/test_step_marker.py -v` muss bestehen

## Checkliste

- [ ] `step_marker.py` implementiert validate()
- [ ] `step_marker.py` implementiert apply_fallback() mit Heuristik
- [ ] Tests für alle VALID_STEPS
- [ ] Tests für Fehlerfälle
- [ ] Tests für Fallback-Heuristik
