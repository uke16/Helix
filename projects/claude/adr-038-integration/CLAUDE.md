# ADR-038 Integration: ResponseEnforcer in Consultant

## Kontext

ADR-038 wurde implementiert (src/helix/enforcement/), aber die **Integration in den Consultant fehlt**.

Aktuell:
- Nur StepMarkerValidator-Fallback nach Streaming (Light-Version)
- Keine Retry-Logic
- Keine anderen Validators aktiv

## Ziel

Vollständige Integration gemäß ADR-038:

```python
enforcer = ResponseEnforcer(
    runner=claude_runner,
    max_retries=2,
    validators=[
        StepMarkerValidator(),
        ADRStructureValidator(),
        FileExistenceValidator(helix_root=HELIX_ROOT),
    ]
)

result = await enforcer.run_with_enforcement(...)
```

## Herausforderung

Der Consultant nutzt **Streaming** (`run_phase_streaming`), aber `ResponseEnforcer.run_with_enforcement()` ist für Non-Streaming designed.

## Lösungsoptionen

### Option A: Post-Streaming Validation (aktuell)
- Validation nach komplettem Response
- Fallback anwenden wenn nötig
- KEIN echter Retry (würde neuen Claude-Aufruf brauchen)

### Option B: Streaming-fähiger Enforcer
- `run_with_enforcement_streaming()` Methode hinzufügen
- Sammelt Response während Streaming
- Validiert am Ende
- Bei Fehler: Retry mit `--continue`

### Option C: Wrapper-Ansatz
- Streaming für User transparent
- Im Hintergrund: Full enforcement mit Retry
- Response erst streamen wenn validiert

## Aufgabe

1. **Lies** `src/helix/enforcement/response_enforcer.py` - verstehe die API
2. **Lies** `src/helix/api/routes/openai.py` - verstehe den Streaming-Flow
3. **Entscheide** welche Option am besten passt
4. **Implementiere** die vollständige Integration:
   - Alle 3 Validators aktiv
   - Retry-Logic wenn Validation fehlschlägt
   - Error-Streaming an Open WebUI wenn Recovery fehlschlägt
5. **Teste** manuell via curl oder Open WebUI

## Dateien

```
src/helix/enforcement/response_enforcer.py  # Evtl. erweitern
src/helix/api/routes/openai.py              # Integration
```

## Akzeptanzkriterien

- [ ] Alle 3 Validators laufen bei jeder Response
- [ ] Bei Validation-Fehler: automatischer Retry (max 2x)
- [ ] Bei max_retries: Fallback-Heuristiken anwenden
- [ ] Bei komplettem Failure: Error an Open WebUI streamen
- [ ] Tests laufen durch: `pytest tests/unit/enforcement/ -v`

## Wichtig

- Streaming-UX beibehalten (User sieht Progress)
- Keine Breaking Changes für bestehende Funktionalität
- Logging für Debugging (wann wurde Retry/Fallback angewandt)
