# Phase 5: OpenAI Route Integration & Documentation

## Aufgabe

1. Integration des ResponseEnforcer in die OpenAI Route
2. Dokumentations-Update

## ADR Referenz

Lies `ADR-038.md` Section "6. Integration in OpenAI Route".

## Input

- Phase 1-4 Output: ResponseEnforcer + alle Validators
- Existierender Code:
  - `src/helix/api/routes/openai.py`
  - `docs/ARCHITECTURE-MODULES.md`

## Erwartete Output-Dateien

```
output/modified/
├── src/helix/api/routes/
│   └── openai.py
└── docs/
    └── ARCHITECTURE-MODULES.md
```

## Implementation Details

### openai.py (Modified)

Integriere ResponseEnforcer in `chat_completion()`:

```python
from helix.enforcement.response_enforcer import ResponseEnforcer
from helix.enforcement.validators.step_marker import StepMarkerValidator
from helix.enforcement.validators.adr_structure import ADRStructureValidator
from helix.enforcement.validators.file_existence import FileExistenceValidator

async def chat_completion(request: ChatCompletionRequest, ...):
    # ... existing setup code ...

    # ResponseEnforcer initialisieren
    enforcer = ResponseEnforcer(
        runner=claude_runner,
        max_retries=2,
        validators=[
            StepMarkerValidator(),
            ADRStructureValidator(),
            FileExistenceValidator(helix_root=Path(HELIX_ROOT)),
        ]
    )

    # Statt direktem runner.run_session:
    result = await enforcer.run_with_enforcement(
        session_id=session_id,
        prompt=prompt,
        validator_names=["step_marker"],  # Für Chat immer Step-Marker
        context={"session_state": session_state}
    )

    if not result.success:
        # Fehler an Open WebUI streamen
        async for chunk in enforcer.stream_enforcement_error(result.issues):
            yield chunk
        return

    # Normale Response verarbeiten
    response = result.response
    # ... rest of existing code ...
```

### ARCHITECTURE-MODULES.md (Modified)

Füge neues Section hinzu:

```markdown
## Response Enforcement

Das `helix.enforcement` Package erzwingt deterministische LLM-Responses.

### Architektur

- **ResponseEnforcer**: Wrapper um ClaudeRunner mit Retry-Logic
- **Validators**: Prüfen Response gegen Regeln
  - StepMarkerValidator: STEP-Marker Pflicht
  - ADRStructureValidator: ADR-Vollständigkeit
  - FileExistenceValidator: Datei-Referenzen

### Verwendung

```python
from helix.enforcement import ResponseEnforcer, StepMarkerValidator

enforcer = ResponseEnforcer(runner, validators=[StepMarkerValidator()])
result = await enforcer.run_with_enforcement(session_id, prompt)
```

### Konfiguration

- `max_retries`: Anzahl Retry-Versuche (default: 2)
- `validators`: Liste aktiver Validators
```

## Cleanup

Lösche `.bak` Dateien:

```bash
rm -f src/helix/api/routes/*.bak
```

## Quality Gate

- Alle Dateien existieren
- Python-Syntax korrekt

## Checkliste

- [ ] `openai.py` importiert enforcement Module
- [ ] `openai.py` erstellt ResponseEnforcer
- [ ] `openai.py` nutzt run_with_enforcement()
- [ ] `openai.py` behandelt Enforcement-Fehler
- [ ] `ARCHITECTURE-MODULES.md` dokumentiert enforcement Package
- [ ] `.bak` Dateien gelöscht
