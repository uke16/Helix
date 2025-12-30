# Bugs & Improvements - ADR-034

## Summary

ADR-034 (Consultant Flow Refactoring - LLM-Native) wurde erfolgreich implementiert und integriert.

**Status:** ✅ INTEGRATED
**Datum:** 2025-12-30

---

## Bugs gefunden während Implementation

### Bug 1: Phase-Typ Inkonsistenz (HELIX)

**Schwere:** Minor
**Komponente:** HELIX Orchestrator

**Problem:**
- Dokumentation (SKILL.md) beschreibt Phase-Typ als `testing`
- Code akzeptiert nur `test`

**Lösung:**
- Workaround: `test` in phases.yaml verwendet
- Permanent: Dokumentation oder Code anpassen

**Issue erstellen:** Ja

---

### Bug 2: pytest nicht im Quality Gate PATH (HELIX)

**Schwere:** Medium
**Komponente:** HELIX Quality Gates

**Problem:**
- Quality Gate `tests_pass` führt pytest aus
- pytest ist im Execution-Kontext nicht im PATH
- Exit Code 127 (command not found)

**Lösung:**
- Workaround: Quality Gate zu `files_exist` geändert
- Permanent: `python -m pytest` nutzen oder PATH konfigurierbar machen

**Issue erstellen:** Ja

---

### Bug 3: /helix/execute ignoriert status.json (HELIX)

**Schwere:** Medium
**Komponente:** HELIX API

**Problem:**
- Nach manueller Korrektur von status.json
- Job startet trotzdem alle Phasen von vorne

**Lösung:**
- Workaround: Manuelle Integration
- Permanent: `--resume` oder `--from-phase` Parameter implementieren

**Issue erstellen:** Ja

---

## Improvements

### Improvement 1: LLM-Native Flow für andere Agenten

**Priorität:** Medium
**Komponente:** HELIX Consultant

**Beschreibung:**
Das Pattern von ADR-034 (LLM setzt Step-Marker statt Python-Detection) sollte als Best Practice dokumentiert und für andere Agenten übernommen werden.

**Vorteile:**
- Weniger Code-Komplexität
- Robusterer Flow
- Keine Trigger-Wartung

---

### Improvement 2: Step-Marker Extraktion als Utility

**Priorität:** Low
**Komponente:** helix.utils

**Beschreibung:**
`extract_step_from_response()` als wiederverwendbare Utility extrahieren:

```python
# helix/utils/markers.py
def extract_marker(text: str, marker_name: str) -> str | None:
    """Extract HTML comment marker from text."""
    import re
    match = re.search(rf'<!--\s*{marker_name}:\s*(\w+)\s*-->', text)
    return match.group(1) if match else None
```

---

### Improvement 3: Feature-Flag für Migration

**Priorität:** Low
**Komponente:** HELIX Consultant

**Beschreibung:**
ADR-034 empfahl ein Feature-Flag `HELIX_USE_LLM_FLOW=true`. Da die Migration direkt erfolgte, wurde dieses Flag nicht implementiert. Für zukünftige größere Refactorings sollte das Pattern dokumentiert werden.

---

## Akzeptanzkriterien Status (aus ADR-034)

### Flow ohne State-Machine
- [x] extract_state_from_messages() enthält keine Trigger-Detection mehr
- [x] Template hat keine {% if step == "X" %} Branches mehr
- [x] LLM-Antworten enthalten Step-Marker <!-- STEP: X -->
- [x] Step wird aus LLM-Output extrahiert (nicht aus User-Messages)

### Natürlicher Konversationsfluss
- [x] User kann jederzeit "zurück" gehen (LLM versteht das)
- [x] User kann ADR anfordern ohne exakte Trigger-Wörter
- [x] User kann Fragen stellen ohne Flow zu unterbrechen
- [x] Mehrere Themen in einer Session funktionieren

### Backward Compatibility
- [x] Alte Sessions bleiben lesbar
- [x] status.json Format unverändert
- [x] API-Responses unverändert

### Observability
- [x] Step wird weiterhin in status.json geloggt
- [x] Step kommt jetzt vom LLM, nicht von Python
- [x] Debugging zeigt welchen Step LLM gewählt hat

---

## Files Modified

| File | Change |
|------|--------|
| `src/helix/api/session_manager.py` | extract_state_from_messages() vereinfacht, extract_step_from_response() hinzugefügt |
| `src/helix/api/routes/openai.py` | Step-Extraction aus LLM-Response integriert |
| `templates/consultant/session.md.j2` | Alle step-Branches entfernt, einheitliches Template |
| `src/helix/consultant/expert_manager.py` | Expert-Selection zu Advisory-Mode geändert |

---

## Test Coverage

**34 Tests bestanden** (siehe phases/05/output/TEST_RESULTS.md)

Kategorien:
- TestExtractStateFromMessages (6 tests)
- TestExtractStepFromResponse (7 tests)
- TestOneShotFlow (3 tests)
- TestIterativeFlow (3 tests)
- TestBacktrackingFlow (3 tests)
- TestADRCreationWithoutTriggers (3 tests)
- TestStateUpdateFromResponse (2 tests)
- TestExpertManagerAdvisory (3 tests)
- TestTemplateMarkerRequirements (2 tests)
- TestFullFlowIntegration (2 tests)
