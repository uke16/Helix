# HELIX Bugs & Technical Debt

Gesammelt aus Controller-Workflows und Audits.

---

## Quellen

| Datei | Quelle | Datum |
|-------|--------|-------|
| [from-controller-adr-032.md](from-controller-adr-032.md) | Controller ADR-032 | 2025-12-30 |
| [from-controller-adr-034.md](from-controller-adr-034.md) | Controller ADR-034 | 2025-12-30 |
| [from-audit-orchestrator.md](from-audit-orchestrator.md) | Audit-Orchestrator | 2025-12-30 |

---

## Übersicht nach Priorität

### KRITISCH (ADR erstellt)

| Bug | Ort | Status |
|-----|-----|--------|
| Consultant State-Machine | session_manager.py | ✅ ADR-034 DONE |

### HOCH

| Bug | Ort | Quelle | Status |
|-----|-----|--------|--------|
| EvolutionStatus Case-Sensitivity | evolution/project.py | ADR-032 | Offen |
| Fehlende Phase-Typen (deployment/integration) | Phase-Parser | ADR-032 | Offen |
| Fehlender Gate-Typ `manual` | Quality Gate Runner | ADR-032 | Offen |
| Status nicht auf Ready nach Job | Job-Manager | ADR-032 | Offen |
| Integration kopiert nicht nach final | Evolution Workflow | ADR-032 | Offen |
| Keyword-basierte Skill-Selection | skill_selector.py | Audit | → ADR-035 |
| Error-Pattern-Listen | retry_handler.py | Audit | → ADR-036 |

### MITTEL

| Bug | Ort | Quelle | Status |
|-----|-----|--------|--------|
| pytest nicht im Quality Gate PATH | Quality Gates | ADR-034 | Offen |
| /helix/execute ignoriert status.json | Job Manager | ADR-034 | Offen |
| Statische Domain/Skill Mappings | context_manager.py | Audit | Offen |
| Hardkodierte CLAUDE.md Templates | phase_generator.py | Audit | Offen |
| Quality Gate if-else Kette | quality_gates.py | Audit | → ADR-037 |

### NIEDRIG

| Bug | Ort | Quelle | Status |
|-----|-----|--------|--------|
| Phase-Typ testing vs test | SKILL.md/Code | ADR-034 | Offen |
| Description-Truncation Magic Number | skill_index.py | Audit | Offen |
| Feedback String-Parsing | feedback.py | Audit | Offen |

### FEHLENDE FEATURES

| Feature | Quelle | Impact | Status |
|---------|--------|--------|--------|
| POST /helix/evolution/projects | ADR-032 | Manuelle Projekt-Erstellung | Offen |
| Separate Test-API | ADR-032 | Test-Projekte nicht sichtbar | Offen |
| Phase Resume (--from-phase) | ADR-032/034 | Keine Resume nach Fehler | Offen |
| Step-Marker Enforcement | ADR-034 | Keine Validierung | Offen |

### IMPROVEMENTS

| Improvement | Quelle | Priorität |
|-------------|--------|-----------|
| LLM-Native Flow als Best Practice | ADR-034 | Medium |
| Step-Marker Utility | ADR-034 | Low |
| Step-Marker Enforcement (Gate/Hook) | ADR-034 | Medium |

---

## Statistiken

| Metrik | Wert |
|--------|------|
| Controller-Workflows abgeschlossen | 2 (ADR-032, ADR-034) |
| Bugs gefunden | 11 |
| Features fehlend | 4 |
| Improvements vorgeschlagen | 3 |
| Bugs gefixt | 1 (ADR-034 State-Machine) |

---

## Workflow

1. Controller findet Bug → dokumentiert in BUGS_AND_IMPROVEMENTS.md
2. Nach Controller-Abschluss → Bug nach `bugs/` kopieren
3. Bei nächstem Refactoring → Bug fixen oder ADR erstellen
4. Bug gefixt → Status auf "✅ DONE" setzen


---

## NEU GEFUNDEN (2025-12-30 14:30)

### Bug 6: Chat-History wird nicht an Claude übergeben
**Schwere:** KRITISCH
**Ort:** `src/helix/api/routes/openai.py`, `templates/consultant/session.md.j2`
**Symptom:** Bei Multi-Turn Konversationen antwortet Claude 2x mit der gleichen Antwort
**Root Cause:** 
- `messages` werden in `messages.json` gespeichert
- Aber CLAUDE.md enthält nur `original_request` (erste Nachricht)
- Claude Code sieht Folge-Nachrichten nie
**Fix:** Chat-History in CLAUDE.md Template einbetten
**Status:** ✅ DONE (Commit c93c1ad, 2025-12-30)


---

## BUG-007: ResponseEnforcer Retry nutzt nicht --continue (2025-12-31)

**Schwere:** KRITISCH
**ADR:** ADR-038
**Status:** 🟢 GEFIXT

### Problem

ADR-038 spezifiziert:
```python
result = await self.runner.continue_session(
    session_id=session_id,
    prompt=feedback_prompt,
)
```

Aber implementiert wurde:
```python
result = await runner.run_phase(
    phase_dir=phase_dir,
    prompt=feedback_prompt,
)
```

### Impact

- `run_phase` startet eine **NEUE** Claude Session
- Claude hat keinen Kontext was die "letzte Antwort" war
- Retry-Feedback "Deine letzte Antwort hatte Fehler" macht keinen Sinn
- Claude generiert wirres Zeug (z.B. Follow-up Fragen statt Korrektur)

### Root Cause

`ClaudeRunner.continue_session()` wurde **nie implementiert**.

Claude CLI hat:
- `--continue`: Continue most recent conversation
- `--resume <session-id>`: Resume specific session

### FIX IMPLEMENTIERT (2025-12-31)

1. `ClaudeRunner.continue_session()` implementiert mit `--resume <session_id>`
2. `ResponseEnforcer.run_retry_phase()` nutzt jetzt `continue_session`
3. Session-ID wird aus JSONL extrahiert und durch Retry-Chain weitergegeben
4. Für simple Issues (MISSING_STEP_MARKER) → direkter Fallback statt Retry

### Ursprünglicher Workaround (vor Fix)

Für fallback-fixable Issues (MISSING_STEP_MARKER) wird sofort Fallback angewandt, keine Retries.

### Echter Fix (jetzt implementiert)

1. Session-ID aus erster Claude-Ausführung extrahieren (aus JSONL)
2. `ClaudeRunner.continue_session(session_id, prompt)` implementieren
3. ResponseEnforcer anpassen um continue_session zu nutzen

### Betroffene Dateien

- `src/helix/claude_runner.py` - continue_session fehlt
- `src/helix/enforcement/response_enforcer.py` - nutzt run_phase statt continue_session

