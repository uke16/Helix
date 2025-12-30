# Technical Debt aus Audit-Orchestrator

**Quelle**: `/home/aiuser01/claude-memory/audit-orchestrator/phase-2-result.md`
**Datum**: 2025-12-30

---

## ADR-034 (KRITISCH) - Bereits erstellt

Consultant State-Machine ist fundamental kaputt:
- Index-basierte Message-Logik
- Keyword-Matching für Intent
- Template-driven Flow

→ ADR-034 erstellt, wartet auf Implementation

---

## Weitere Findings (Phase 2 Audit)

### HOCH: Keyword-basierte Skill-Selection
**Datei:** `src/helix/docs/skill_selector.py:82-88`
**Problem:** Hardkodierte Score-Gewichtungen, Substring-Matching
**Empfehlung:** ADR-035 - LLM-Native Skill Selection

### HOCH: Hartkodierte Error-Pattern-Listen
**Datei:** `src/helix/pipeline/retry_handler.py:30-65`
**Problem:** String-Pattern-Matching für Retry-Entscheidungen
**Empfehlung:** ADR-036 - Exception-Handling Modernisierung

### MITTEL: Domain/Language-zu-Skill Mappings
**Datei:** `src/helix/context_manager.py:34-58`
**Problem:** Statische Mappings, manuell gepflegt

### MITTEL: Template-basierte CLAUDE.md-Generierung
**Datei:** `src/helix/planning/phase_generator.py:28-72`
**Problem:** Hardkodierte, unflexible Templates

### MITTEL: Hardkodierte Quality Gate Typen
**Datei:** `src/helix/quality_gates.py:449-473`
**Problem:** if-else Kette statt Plugin-System
**Empfehlung:** ADR-037 - Plugin-basierte Quality Gates

### NIEDRIG: Description-Truncation
**Datei:** `src/helix/docs/skill_index.py:251-252`
**Problem:** Magische Zahl 200 ohne Dokumentation

### NIEDRIG: Feedback-Parsing mit String-Suche
**Datei:** `src/helix/verification/feedback.py:143-154`
**Problem:** Parst strukturierte Daten durch String-Manipulation

---

## Saubere Module (keine Findings)

- `src/helix/claude_runner.py`
- `src/helix/api/streaming.py`
- `src/helix/verification/sub_agent.py`
- `src/helix/gates/adr_complete.py`
- `src/helix/adr/completeness.py`
- `src/helix/consultant/meeting.py`

