---
adr_id: "036"
title: "Streaming Completion Signal - SessionEnd Hook statt Sugar Coating"
status: Proposed

component_type: SERVICE
classification: REFACTOR
change_scope: major

domain: helix
language: python

files:
  create:
    - ~/.claude/hooks/session-end.sh
  modify:
    - src/helix/enforcement/validators/step_marker.py
    - src/helix/api/routes/openai.py
  delete: []
  docs:
    - docs/ARCHITECTURE-MODULES.md
---

# ADR-036: Streaming Completion Signal - SessionEnd Hook statt Sugar Coating

## Status

Proposed

## Kontext

### Das Problem

Beim Streaming von Claude CLI Responses tritt ein kritischer Bug auf:

1. **stdout vom Claude CLI kann vorzeitig schließen** (Ursache unklar - Buffer, Timeout, CLI-Bug)
2. **Die API nutzte stdout-Ende als "fertig"-Signal**
3. **Das führte zu unvollständigen Responses**

### Die Sugar Coating Kette

```
stdout schließt vorzeitig (Bug)
    ↓
API liest unvollständige Response
    ↓
StepMarkerValidator findet keinen <!-- STEP: X --> Marker
    ↓
_infer_step() Fallback wird aufgerufen
    ↓
Default: return "done"  ← SUGAR COATING
    ↓
API schreibt step="done" in status.json
    ↓
Response gilt als "fertig" (obwohl unvollständig!)
```

### Das Mapping-Problem

Der `step` Wert in status.json hat zwei völlig verschiedene Bedeutungen:

| step="done" | Bedeutung |
|-------------|-----------|
| Echtes "done" | Claude hat `<!-- STEP: done -->` geschrieben |
| Fallback "done" | Kein Marker gefunden, _infer_step() hat geraten |

**Zwei Zustände → ein Wert → Information verloren!**

### Wer schreibt was?

```
┌─────────────────┐
│   CLAUDE CLI    │
│                 │
│  Schreibt:      │
│  - stdout       │
│  - response.md  │
│                 │
│  Schreibt NICHT:│
│  - status.json  │  ← Problem!
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   HELIX API     │
│                 │
│  Schreibt:      │
│  - status.json  │  ← API schreibt, nicht Claude!
└─────────────────┘
```

Die API entscheidet basierend auf stdout wann Claude "fertig" ist.
Wenn stdout abbricht, schreibt die API falsches "done".

## Entscheidung

### Lösung: Claude schreibt das Completion-Signal

Claude CLI hat einen `SessionEnd` Hook der ausgeführt wird wenn Claude **wirklich** fertig ist.

**Neuer Datenfluss:**

```
Claude arbeitet...
    ↓
Claude ist fertig
    ↓
SessionEnd Hook wird ausgeführt
    ↓
Hook schreibt: touch output/.done
    ↓
API wartet auf .done Datei (nicht auf stdout!)
    ↓
.done existiert = wirklich fertig
```

### Warum ist das besser?

| Signal | Zuverlässig? | Grund |
|--------|--------------|-------|
| stdout schließt | ❌ Nein | Kann vorzeitig passieren |
| step="done" in status.json | ❌ Nein | Wird von Fallback gesetzt |
| **output/.done existiert** | ✅ Ja | Nur wenn SessionEnd Hook läuft |

### Trennung der Concerns

| Kanal | Zweck | Kann abbrechen? |
|-------|-------|-----------------|
| stdout | Live-Streaming für UX | Ja, egal |
| .done Datei | Completion-Signal | Nein, zuverlässig |

## Implementation

### Phase 1: SessionEnd Hook (bereits erstellt)

```bash
# ~/.claude/hooks/session-end.sh
#!/bin/bash
# Wird ausgeführt wenn Claude WIRKLICH fertig ist

if [ -d "output" ]; then
    touch output/.done
fi
```

### Phase 2: Fallback-Default ändern

```python
# src/helix/enforcement/validators/step_marker.py

def _infer_step(self, response: str) -> str:
    """Infer the conversation step from response content."""
    # ... bestehende Heuristiken ...

    # GEÄNDERT: "unknown" statt "done"
    # "unknown" ist ehrlich - wir wissen nicht wo die Konversation steht
    return "unknown"
```

### Phase 3: Completion-Check umstellen

```python
# src/helix/api/routes/openai.py

# ALT (Sugar Coating):
def check_session_done() -> bool:
    status = json.loads(status_file.read_text())
    return status.get("step") == "done"

# NEU (zuverlässig):
def check_session_done() -> bool:
    done_file = session_path / "output" / ".done"
    return done_file.exists()
```

### Phase 4: .done Datei am Session-Start löschen

```python
# src/helix/api/routes/openai.py

# Am Anfang jeder Session:
done_file = session_path / "output" / ".done"
if done_file.exists():
    done_file.unlink()
```

## Was bleibt, was geht?

### Bleibt (nützlich)

| Code | Grund |
|------|-------|
| StepMarkerValidator | Observability - zeigt wo Konversation steht |
| ResponseEnforcer | Retry-Logik bei fehlenden Markern |
| status.json | Session-State und Debugging |
| `step` Field | Logging (aber nicht mehr für Completion!) |

### Wird geändert

| Code | Änderung |
|------|----------|
| `_infer_step()` Default | "done" → "unknown" |
| `check_session_done()` | status.json → .done Datei |

### Kein Git Revert nötig

ADR-034 und ADR-038 enthalten viel guten Code. Nur ~10 Zeilen müssen geändert werden.

## Akzeptanzkriterien

### Funktional

- [ ] SessionEnd Hook ist konfiguriert und schreibt .done
- [ ] `_infer_step()` gibt "unknown" statt "done" zurück
- [ ] `check_session_done()` prüft .done Datei, nicht status.json
- [ ] .done wird am Session-Start gelöscht
- [ ] Unvollständige Responses werden als Fehler erkannt

### Tests

- [ ] Test: Response ohne STEP-Marker bekommt step="unknown"
- [ ] Test: .done Datei wird von Hook erstellt
- [ ] Test: stdout kann abbrechen ohne Completion zu triggern

## Konsequenzen

### Positiv

1. **Ehrliche Fehlerbehandlung**: Unvollständige Responses werden erkannt
2. **Zuverlässiges Signal**: Basiert auf echtem Claude-Ende
3. **Entkopplung**: stdout für UX, .done für Completion
4. **Einfach**: Ein `touch` Befehl, keine komplexe Logik

### Negativ

1. **Hook-Abhängigkeit**: Erfordert konfiguriertes SessionEnd Hook
2. **Mehr Fehlermeldungen**: User sehen Fehler die vorher versteckt wurden

### Mitigation

- Hook wird bei HELIX-Installation automatisch konfiguriert
- Klare Fehlermeldungen mit Retry-Option

## Referenzen

- ADR-034: Consultant Flow Refactoring (führte LLM-gesteuerte Steps ein)
- ADR-038: Deterministic LLM Response Enforcement (führte Validators ein)
- `~/.claude/hooks/session-end.sh`: SessionEnd Hook
- `src/helix/enforcement/validators/step_marker.py`: Sugar Coating Code
