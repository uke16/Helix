---
adr_id: "027"
title: "Stale Response Bugfix - Open WebUI Integration"
status: Implemented

project_type: helix_internal
component_type: SERVICE
classification: FIX
change_scope: hotfix

domain: helix
language: python
skills:
  - helix

files:
  create: []
  modify:
    - src/helix/api/routes/openai.py
  docs: []

depends_on: []
---

# ADR-027: Stale Response Bugfix - Open WebUI Integration

## Status
✅ Implemented

## Kontext

Bei der Open WebUI Integration wurden 3 zusammenhängende Bugs identifiziert:

### Das Problem

Wenn Claude Code timeout hat oder crasht während einer Session:
1. Die alte `output/response.md` Datei bleibt bestehen
2. HELIX liest die alte Datei und sendet die **veraltete Antwort**
3. Der User sieht immer wieder die gleiche Antwort, egal was er fragt

### Root Cause Analyse

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         WAS PASSIERT                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. Erste Antwort erfolgreich                                                │
│     └─> response.md geschrieben mit "Analyse: Server-Reload..."              │
│                                                                              │
│  2. User fragt: "Funktioniert das Skript?"                                   │
│     └─> Claude startet, aber TIMEOUT bevor response.md aktualisiert          │
│     └─> Open WebUI zeigt: "[Starte Claude Code...]" und nichts weiter        │
│                                                                              │
│  3. User fragt: "Hat es geklappt?"                                           │
│     └─> HELIX liest: output/response.md (die ALTE Antwort!)                 │
│     └─> Streamt die alte Antwort an den User                                 │
│                                                                              │
│  4. Repeat für jede weitere Frage                                            │
│     └─> Immer die alte response.md                                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Die 3 Bugs

| Bug | Location | Beschreibung |
|-----|----------|--------------|
| Bug 1 | `openai.py:222-225` | Stale Response wird wiederverwendet |
| Bug 2 | `openai.py:253-254` | Nach Timeout wird trotzdem alte response.md gelesen |
| Bug 3 | `openai.py:256-257` | Kein Error-Handling für Claude-Crash |

## Entscheidung

Wir fixen alle 3 Bugs in `src/helix/api/routes/openai.py`:

### Fix 1: Alte Response vor Start löschen

Vor dem Claude-Aufruf wird die alte `response.md` gelöscht, damit keine veraltete
Antwort wiederverwendet werden kann.

### Fix 2: Timestamp-Validierung

Nach dem Claude-Aufruf prüfen wir, ob die `response.md` tatsächlich **nach** dem
Start geschrieben wurde. Nur dann verwenden wir sie.

### Fix 3: Explizite Fehlermeldung bei Crash/Error

Wenn Claude crasht oder `result.success == False`, senden wir eine explizite
Fehlermeldung statt die alte response.md zu lesen.

## Implementation

### Geänderte Funktion: `_run_consultant_streaming()`

```python
async def _run_consultant_streaming(
    session_path: Path,
    completion_id: str,
    created: int,
    model: str,
) -> AsyncGenerator[str, None]:
    """Run Claude Code with live streaming to Open WebUI."""

    # === FIX 1: Alte Response VOR dem Start löschen ===
    response_file = session_path / "output" / "response.md"
    if response_file.exists():
        response_file.unlink()

    # Timestamp für spätere Validierung
    start_time = time.time()

    # ... (Runner setup bleibt gleich) ...

    try:
        result = await runner.run_phase_streaming(...)

        # === FIX 2: Timestamp-Validierung ===
        if response_file.exists():
            file_mtime = os.path.getmtime(response_file)
            if file_mtime >= start_time:
                # Datei wurde NACH dem Start geschrieben - OK
                response_text = response_file.read_text()
            else:
                # Datei ist alt - ignorieren
                response_text = "Claude hat keine neue Antwort generiert."
        else:
            # Fallback: Parse stdout
            response_text = _extract_from_stdout(stdout_buffer)

    except asyncio.TimeoutError:
        # === FIX 3a: Bei Timeout keine alte Response verwenden ===
        yield _make_chunk(..., "\n\n**Timeout** - Claude konnte nicht rechtzeitig antworten.\n")
        yield _make_final_chunk(...)
        yield "data: [DONE]\n\n"
        return  # WICHTIG: Hier abbrechen, NICHT response.md lesen!

    except Exception as e:
        # === FIX 3b: Bei Error keine alte Response verwenden ===
        yield _make_chunk(..., f"\n\n**Fehler:** {str(e)}\n")
        yield _make_final_chunk(...)
        yield "data: [DONE]\n\n"
        return  # WICHTIG: Hier abbrechen!
```

### Vollständiger Patch

```python
# Zeile ~215 (vor runner.run_phase_streaming):

# FIX 1: Delete stale response before starting
response_file = session_path / "output" / "response.md"
if response_file.exists():
    response_file.unlink()

# Track start time for timestamp validation
start_time = time.time()

# ... existing runner setup ...

try:
    result = await runner.run_phase_streaming(...)

    # FIX 2: Validate response file timestamp
    if response_file.exists():
        import os
        file_mtime = os.path.getmtime(response_file)
        if file_mtime >= start_time:
            response_text = response_file.read_text()
        else:
            response_text = None
    else:
        response_text = None

    # Fallback to stdout parsing if no valid response file
    if not response_text:
        stdout = "\n".join(stdout_buffer)
        # ... existing stdout parsing ...

except asyncio.TimeoutError:
    # FIX 3a: Don't read stale response after timeout
    yield _make_chunk(completion_id, created, model,
                      "\n\n**Timeout** - Verarbeitung hat zu lange gedauert. "
                      "Bitte versuche es erneut.")
    yield _make_final_chunk(completion_id, created, model)
    yield "data: [DONE]\n\n"
    return  # Exit here, don't continue to read response.md

except Exception as e:
    # FIX 3b: Don't read stale response after error
    yield _make_chunk(completion_id, created, model,
                      f"\n\n**Fehler:** {str(e)}")
    yield _make_final_chunk(completion_id, created, model)
    yield "data: [DONE]\n\n"
    return  # Exit here, don't continue to read response.md
```

## Dokumentation

Keine Dokumentations-Updates erforderlich - dies ist ein interner Bugfix.

## Akzeptanzkriterien

### Funktionalität

- [ ] Alte `response.md` wird vor Claude-Start gelöscht
- [ ] Nach Timeout wird keine alte Response verwendet
- [ ] Nach Error wird keine alte Response verwendet
- [ ] Timestamp-Validierung verhindert Verwendung alter Dateien
- [ ] User erhält klare Fehlermeldung bei Timeout/Error

### Tests

- [ ] Manueller Test: Timeout simulieren, prüfen dass keine alte Antwort kommt
- [ ] Manueller Test: Error simulieren, prüfen dass Fehlermeldung angezeigt wird
- [ ] E2E: Mehrere Anfragen hintereinander, jede bekommt eigene Antwort

### Deployment

- [ ] Fix in Testsystem deployed
- [ ] API neugestartet
- [ ] Validierung bestanden
- [ ] Integration in Production

## Konsequenzen

### Positiv

- User sieht nie mehr wiederholte/alte Antworten
- Klare Fehlermeldungen bei Timeout/Error
- Bessere User Experience in Open WebUI
- Einfacher, minimalinvasiver Fix

### Negativ

- Keine (reiner Bugfix ohne Architektur-Änderung)

### Risiko-Mitigation

- Fix wird zuerst im Testsystem validiert
- Bei Problemen: Einfacher Rollback möglich
- Keine Breaking Changes für andere Komponenten
