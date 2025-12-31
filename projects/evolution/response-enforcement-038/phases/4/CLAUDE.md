# Phase 4: ResponseEnforcer Tests & Integration

## Aufgabe

1. Vollständige Unit Tests für ResponseEnforcer
2. Integration in ClaudeRunner

## ADR Referenz

Lies `ADR-038.md` Section "5. Response Enforcer".

## Input

- Phase 1-3 Output: Alle Validators
- Existierender Code: `src/helix/consultant/claude_runner.py`

## Erwartete Output-Dateien

```
output/new/
└── tests/unit/enforcement/
    ├── conftest.py
    └── test_response_enforcer.py

output/modified/
└── src/helix/consultant/
    └── claude_runner.py
```

## Implementation Details

### test_response_enforcer.py

Teste:
1. **Erfolgreiche Validierung**: Response ohne Issues wird direkt zurückgegeben
2. **Retry bei Fehler**: Bei ValidationIssue wird Retry mit Feedback durchgeführt
3. **Max Retries**: Nach max_retries wird Fallback versucht
4. **Fallback erfolgreich**: Fallback korrigiert Response
5. **Fallback fehlgeschlagen**: EnforcementResult.success = False
6. **Validator-Filterung**: validator_names filtert korrekt
7. **Feedback-Prompt**: _build_feedback_prompt() erzeugt korrektes Format

### conftest.py

Fixtures:
- `mock_runner`: Mock für ClaudeRunner
- `sample_validators`: Liste von Test-Validators
- `sample_response_valid`: Gültige Response
- `sample_response_invalid`: Ungültige Response

### claude_runner.py (Modified)

Füge Unterstützung für `continue_session()` hinzu falls noch nicht vorhanden.
Dies ermöglicht Retry mit `--continue` Flag.

```python
async def continue_session(
    self,
    session_id: str,
    prompt: str,
    **kwargs
) -> RunResult:
    """Setzt eine bestehende Session fort."""
    # Implementation mit --continue Flag
    pass
```

## Quality Gate

- `pytest tests/unit/enforcement/ -v` muss bestehen

## Checkliste

- [ ] `test_response_enforcer.py` testet alle Szenarien
- [ ] `conftest.py` mit Fixtures
- [ ] `claude_runner.py` hat `continue_session()` Methode
- [ ] Alle Tests grün
