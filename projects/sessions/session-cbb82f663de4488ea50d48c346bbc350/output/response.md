# Analyse: Streaming Completion Signal - Sugar Coating Aufräumen

## Zusammenfassung

Ich habe die Codebase analysiert und das Problem identifiziert. Hier sind die Ergebnisse:

---

## 1. Das Problem im Detail

### Die Kette des Sugar Coatings

```
stdout schließt vorzeitig (Bug)
    ↓
StepMarkerValidator findet keinen Marker
    ↓
_infer_step() Fallback → "done" (!)
    ↓
API schreibt step="done" in status.json
    ↓
check_session_done() findet step="done"
    ↓
Response gilt als "fertig" (obwohl unvollständig!)
```

### Die schuldigen Code-Stellen

| Datei | Zeilen | Problem |
|-------|--------|---------|
| `step_marker.py` | 113-161 | `_infer_step()` - Default "done" |
| `step_marker.py` | 85-111 | `apply_fallback()` - nutzt _infer_step() |
| `openai.py` | 343-352 | `check_session_done()` - vertraut auf step="done" |

---

## 2. Zu löschender/ändernder Code

### Minimal-Änderung (Empfohlen)

**1. `_infer_step()` Default ändern:**

```python
# src/helix/enforcement/validators/step_marker.py:161
# ALT:
return "done"

# NEU:
return "unknown"
```

**2. Completion-Check auf `.done` File umstellen:**

```python
# src/helix/api/routes/openai.py:343-352
# ALT:
def check_session_done() -> bool:
    status = json.loads(status_file.read_text())
    return status.get("step") == "done"

# NEU:
def check_session_done() -> bool:
    done_file = session_path / "output" / ".done"
    return done_file.exists()
```

### Was kann bleiben?

| Code | Behalten | Grund |
|------|----------|-------|
| StepMarkerValidator | ✅ Ja | Nützlich für Observability |
| ADRStructureValidator | ✅ Ja | Validiert ADR-Struktur |
| FileExistenceValidator | ✅ Ja | Prüft Datei-Referenzen |
| ResponseEnforcer | ✅ Ja | Retry-Logik ist sinnvoll |
| status.json | ✅ Ja | Für Debugging, nicht Completion |
| `step` Field | ✅ Ja | Observability, nicht Completion |

---

## 3. Git History Analyse

### Relevante Commits

| Commit | ADR | Was wurde eingeführt? |
|--------|-----|----------------------|
| `bd9d144` | ADR-038 | StepMarkerValidator mit Fallback |
| `b638c7e` | ADR-034 | LLM-Native Step Detection |
| `0c70551` | ADR-044 | status.json als Completion Signal |

### Revert Empfehlung: **Nicht reverten!**

**Gründe:**
1. ADR-038 enthält viel guten Code (ResponseEnforcer, andere Validators)
2. ADR-044 ist konzeptionell richtig, nur falsches Signal
3. Nur ~10 Zeilen müssen geändert werden
4. Revert würde funktionierende Features kaputt machen

---

## 4. Wird `step` für etwas Wichtiges gebraucht?

| Verwendung | Wichtig? | Details |
|------------|----------|---------|
| Observability/Logging | Ja | Zeigt wo Konversation steht |
| Session Status API | Nein | Nur für Debugging |
| **Completion Check** | **JA** | Aber **falsch** implementiert! |

**Fazit:** `step` ist für Logging nützlich, aber sollte NICHT für Completion-Detection verwendet werden.

---

## 5. Empfohlene Lösung

### SessionEnd Hook

```bash
# ~/.claude/hooks/session-end.sh
#!/bin/bash
WORKDIR="${1:-$(pwd)}"
OUTPUT_DIR="$WORKDIR/output"

if [ -d "$OUTPUT_DIR" ]; then
    touch "$OUTPUT_DIR/.done"
    echo "Session completed: $(date -Iseconds)" >> "$OUTPUT_DIR/.done"
fi
```

### Code-Änderungen

1. `_infer_step()` → "unknown" statt "done"
2. `check_session_done()` → wartet auf `.done` File
3. Dokumentation aktualisieren

---

## 6. Nächste Schritte

1. **Jetzt:** ADR-045 reviewen und akzeptieren
2. **Phase 1:** Fallback auf "unknown" ändern (5 Min)
3. **Phase 2:** SessionEnd Hook konfigurieren (10 Min)
4. **Phase 3:** Completion-Check umstellen (10 Min)
5. **Phase 4:** Testen und dokumentieren

---

## ADR erstellt

Das ADR wurde erstellt: `output/ADR-045-streaming-completion-cleanup.md`

Bereit zur Finalisierung wenn gewünscht.

<!-- STEP: generate -->
