---
adr_id: "045"
title: "Streaming Completion Signal Cleanup - Remove Sugar Coating"
status: Proposed

component_type: SERVICE
classification: REFACTOR
change_scope: major

domain: helix
language: python
skills:
  - helix
  - infrastructure

files:
  create: []
  modify:
    - src/helix/enforcement/validators/step_marker.py
    - src/helix/enforcement/response_enforcer.py
    - src/helix/api/routes/openai.py
  docs:
    - docs/ARCHITECTURE-MODULES.md

depends_on:
  - ADR-034
  - ADR-038
  - ADR-044
---

# ADR-045: Streaming Completion Signal Cleanup - Remove Sugar Coating

## Status

Proposed

## Kontext

### Das Problem

Wir haben ein fundamentales Problem mit dem Streaming-System entdeckt:

1. **stdout vom Claude CLI kann vorzeitig schließen** (Bug im Claude CLI)
2. **Die API nutzte stdout-Ende als "fertig"-Signal**
3. **Das führte zu unvollständigen Responses**

### Was ist Sugar Coating?

Der aktuelle Code versteckt das Problem statt es zu lösen:

#### 1. StepMarkerValidator `_infer_step()` Fallback (Zeile 113-161)

```python
def _infer_step(self, response: str) -> str:
    """Infer the conversation step from response content."""
    # ... keyword matching ...

    # Default to done (safe choice - doesn't trigger more actions)
    return "done"  # <-- SUGAR COATING: Setzt "done" wenn kein Marker
```

**Problem:** Wenn Claude abstürzt oder stdout vorzeitig schließt, wird die Response trotzdem als "done" markiert. Der User sieht keine Fehlermeldung - das System tut so, als wäre alles in Ordnung.

#### 2. apply_fallback() in StepMarkerValidator (Zeile 85-111)

```python
def apply_fallback(self, response: str, context: dict) -> Optional[str]:
    """Apply fallback heuristics to add missing STEP marker."""
    step = self._infer_step(response)  # <-- Ruft den Sugar Coating Code auf
    return f"{response.rstrip()}\n\n<!-- STEP: {step} -->"
```

**Problem:** Dieser Fallback wird aufgerufen wenn der STEP-Marker fehlt. Das kann zwei Gründe haben:
1. LLM hat den Marker vergessen (legitim, sollte korrigiert werden)
2. stdout wurde vorzeitig geschlossen (Bug, sollte als Fehler gemeldet werden)

Der Code unterscheidet nicht zwischen diesen Fällen!

### Die wahre Lösung: status.json als Completion-Signal

ADR-044 hat bereits einen besseren Ansatz implementiert:

```python
# ADR-044: Check session completion via status.json (persistent signal)
def check_session_done() -> bool:
    """Check if session is done via status.json."""
    status_file = session_path / "status.json"
    if status_file.exists():
        try:
            status = json.loads(status_file.read_text())
            return status.get("step") == "done"
        except Exception:
            pass
    return False
```

**Aber:** Die API schreibt status.json, NICHT Claude! Das `step` wird vom StepMarkerValidator's Fallback auf "done" gesetzt. Das ist ein Kreislauf von Sugar Coating:

```
stdout schließt vorzeitig
    → StepMarkerValidator kann keinen Marker extrahieren
    → Fallback: _infer_step() setzt "done"
    → API schreibt step="done" in status.json
    → check_session_done() findet step="done"
    → Response gilt als "fertig" (obwohl unvollständig!)
```

### Verwendung von `step` in status.json

Nach Analyse der Codebase:

| Verwendung | Datei | Wichtig? |
|------------|-------|----------|
| Observability | openai.py:200 | Ja - für Logging |
| Status API | session_manager.py:310-326 | Nein - nur Logging |
| Completion Check | openai.py:343-352 | **JA - aber falsch implementiert** |

**Fazit:** `step` wird für Completion-Detection verwendet, aber das ist nur zuverlässig wenn Claude den Marker selbst setzt. Der Fallback auf "done" macht die Completion-Detection unzuverlässig.

## Entscheidung

### Phase 1: Fallback-Verhalten ändern

1. **`_infer_step()` Fallback auf "unknown" ändern statt "done"**
   - "unknown" signalisiert: "Wir wissen nicht wo die Konversation steht"
   - Das ist ehrlicher als "done" zu behaupten

2. **Completion-Check in openai.py anpassen**
   - `step == "done"` UND `step != "unknown"` als Bedingung
   - Oder besser: Eigenes `.done` File als Signal

### Phase 2: Dediziertes Completion-Signal (Empfohlen)

Claude CLI hat einen `SessionEnd` Hook. Wir können:

1. Hook erstellen der `output/.done` schreibt wenn Claude WIRKLICH fertig ist
2. API wartet auf `.done` File statt auf stdout-Ende
3. Sugar Coating Code entfernen

**Hook Implementation:**
```bash
# ~/.claude/hooks/session-end.sh
#!/bin/bash
# Schreibt .done File wenn Claude Session wirklich beendet ist

# Der Hook erhält das Working Directory als Argument
WORKDIR="${1:-$(pwd)}"
OUTPUT_DIR="$WORKDIR/output"

if [ -d "$OUTPUT_DIR" ]; then
    touch "$OUTPUT_DIR/.done"
    echo "Session completed: $(date -Iseconds)" >> "$OUTPUT_DIR/.done"
fi
```

### Phase 3: Code-Bereinigung

**Zu entfernen/ändern:**

| Code | Datei | Aktion |
|------|-------|--------|
| `_infer_step()` Default "done" | step_marker.py:161 | Ändern zu "unknown" |
| `apply_fallback()` | step_marker.py:85-111 | Überdenken ob nötig |
| `check_session_done()` | openai.py:343-352 | Warten auf `.done` statt status.json |

## Implementation

### Schritt 1: Fallback ändern (Minimal-Invasiv)

```python
# src/helix/enforcement/validators/step_marker.py

def _infer_step(self, response: str) -> str:
    """Infer the conversation step from response content."""
    # ... bestehende keyword-Logik ...

    # CHANGED: "unknown" statt "done" wenn keine Heuristik greift
    # Das ist ehrlicher und verhindert false-positive Completion
    return "unknown"
```

### Schritt 2: Completion-Check anpassen

```python
# src/helix/api/routes/openai.py

def check_session_done() -> bool:
    """Check if session is done via .done file (SessionEnd hook)."""
    done_file = session_path / "output" / ".done"
    return done_file.exists()
```

### Schritt 3: SessionEnd Hook konfigurieren

```yaml
# ~/.claude/settings.yaml oder hooks Verzeichnis
hooks:
  session_end:
    - command: "touch output/.done"
```

## Empfehlung: Manuelles Aufräumen vs. Git Revert

### Git History Analyse

| Commit | ADR | Code | Revert möglich? |
|--------|-----|------|-----------------|
| b638c7e | ADR-034 | extract_state_from_messages() cleanup | Ja, aber nicht nötig |
| bd9d144 | ADR-038 | ResponseEnforcer + StepMarkerValidator | **Teilweise** - nur Fallback-Logik |
| 0c70551 | ADR-044 | status.json als Signal | **Nein** - ist richtige Richtung |

### Empfehlung: Manuelles Aufräumen

**Gründe gegen Git Revert:**
1. ADR-038 enthält viel guten Code (Retry-Logik, andere Validators)
2. ADR-044 ist teilweise korrekt, nur das "step=done" Vertrauen ist falsch
3. Die Änderungen sind chirurgisch möglich ohne alles zu reverten

**Gründe für manuelles Aufräumen:**
1. Nur ~10 Zeilen Code müssen geändert werden
2. Kein Risiko andere Funktionalität zu verlieren
3. Einfacher zu reviewen und zu verstehen

## Was kann bleiben?

| Code | Behalten? | Grund |
|------|-----------|-------|
| StepMarkerValidator | Ja | Nützlich für Observability |
| ADRStructureValidator | Ja | Validiert ADR-Struktur |
| FileExistenceValidator | Ja | Prüft Datei-Referenzen |
| ResponseEnforcer | Ja | Retry-Logik ist sinnvoll |
| status.json | Ja | Für Session-State und Debugging |
| `step` Field | Ja | Für Observability, aber nicht für Completion |

## Akzeptanzkriterien

### Funktional

- [ ] `_infer_step()` gibt "unknown" zurück statt "done"
- [ ] Completion-Check basiert auf `.done` File, nicht auf `step == "done"`
- [ ] SessionEnd Hook ist konfiguriert und funktioniert
- [ ] Unvollständige Responses werden als Fehler erkannt, nicht als "done"

### Tests

- [ ] Test: Response ohne STEP-Marker wird als "unknown" markiert
- [ ] Test: `.done` File wird von Hook erstellt
- [ ] Test: API wartet auf `.done` bevor Response als fertig gilt

### Dokumentation

- [ ] ARCHITECTURE-MODULES.md: Completion-Signal-Architektur dokumentiert
- [ ] Docstrings: Alle Änderungen kommentiert

## Konsequenzen

### Positiv

1. **Ehrliche Fehlerbehandlung**: Unvollständige Responses werden erkannt
2. **Zuverlässigeres Completion-Signal**: Basiert auf echtem Claude-Ende, nicht Heuristik
3. **Bessere Debugging**: "unknown" Step zeigt klar an wenn etwas schief ging

### Negativ

1. **Breaking Change**: Responses mit fehlendem Marker werden nicht mehr "geheilt"
2. **Hook-Abhängigkeit**: Erfordert konfiguriertes SessionEnd Hook
3. **Mehr Fehlermeldungen**: User sehen Fehler die vorher versteckt wurden

### Mitigation

- **Breaking Change**: Template-Update mit explizitem Hinweis auf STEP-Marker
- **Hook-Abhängigkeit**: Hook automatisch bei HELIX-Installation konfigurieren
- **Fehlermeldungen**: Klare, hilfreiche Fehlermeldungen mit Retry-Option

## Referenzen

- ADR-034: Consultant Flow Refactoring (führte LLM-gesteuerte Steps ein)
- ADR-038: Deterministic LLM Response Enforcement (führte Validators ein)
- ADR-044: Streaming Completion Signal (führte status.json Check ein)
- `src/helix/enforcement/validators/step_marker.py`: Sugar Coating Code
- `src/helix/api/routes/openai.py:343-352`: Completion Check
