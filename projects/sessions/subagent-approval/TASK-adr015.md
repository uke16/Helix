# Aufgabe: ADR-015 erstellen - Approval & Validation System

Du bist der HELIX Meta-Consultant. Erstelle ADR-015 basierend auf den Konzepten.

## Quellen

Lies diese Dateien für den vollständigen Kontext:
1. `output/subagent-approval.md` - Sub-Agent Konzept
2. `../adr-completeness/output/adr-completeness.md` - Completeness Rules
3. `../adr-completeness/output/semantic-validation-design.md` - Layer 4 Design
4. `../../adr/014-documentation-architecture.md` - Referenz für Format

## Das ADR soll enthalten

### Kernkonzept: Hybrid Validation + Sub-Agent

```
PHASE 1: Pre-Checks (deterministisch, kostenlos)
├── Layer 1: Structural (Sections vorhanden?)
├── Layer 2: Contextual Rules (major → Migration?)
└── Layer 3: Concept Diff (Konzept übernommen?)

→ Wenn FAILED: Sofort abbrechen
→ Wenn PASSED: Weiter zu Phase 2

PHASE 2: Sub-Agent Approval (LLM, ~$0.02)
└── Layer 4: Semantic + Tiefenprüfung
    ├── Frischer Context (kein Ersteller-Bias)
    ├── Kann Codebase lesen
    └── Kann Skills laden
```

### Inhalt

1. **Kontext**
   - Problem: Selbstprüfung = Bestätigungsbias
   - Problem: Vergessene Sections (wie bei ADR-014 Migration)
   - Lösung: Hybrid aus Pre-Checks + Sub-Agent

2. **Entscheidung**
   - Hybrid-Ansatz (nicht nur API-Call, nicht nur Sub-Agent)
   - Sub-Agent als neue Claude CLI Instanz
   - Approval-Verzeichnis-Pattern

3. **Implementation**
   - Verzeichnis-Struktur (approvals/, checks/)
   - Pre-Check Engine (completeness.py)
   - ApprovalRunner (runner.py)
   - Quality Gate Integration

4. **Approval-Typen**
   - adr (MVP)
   - code (Phase 2)
   - docs (Phase 2)
   - security (Phase 3)

5. **Workflow-Integration**
   - phases.yaml mit type: approval
   - on_rejection Handler

6. **Implementierungsreihenfolge**
   - Was von ADR-014 zuerst?
   - Was von ADR-015 zuerst?
   - Abhängigkeiten zwischen beiden

7. **Akzeptanzkriterien** (Checkboxen)

8. **Konsequenzen**

## YAML Header

```yaml
---
adr_id: "015"
title: "Approval & Validation System - Hybrid Pre-Checks + Sub-Agent"
status: Proposed

component_type: COMPONENT
classification: NEW
change_scope: major

domain: helix
language: python
skills:
  - helix

files:
  create:
    - approvals/adr/CLAUDE.md
    - approvals/adr/checks/completeness.md
    - approvals/adr/checks/migration.md
    - approvals/code/CLAUDE.md
    - config/adr-completeness-rules.yaml
    - config/approvals.yaml
    - src/helix/adr/completeness.py
    - src/helix/adr/concept_diff.py
    - src/helix/approval/__init__.py
    - src/helix/approval/runner.py
    - src/helix/approval/result.py
  modify:
    - src/helix/adr/validator.py
    - src/helix/adr/gate.py
    - src/helix/quality_gates/__init__.py
    - src/helix/tools/adr_tool.py

depends_on: ["002", "003", "012"]
related_to: ["014"]
---
```

## Output

Schreibe nach: output/ADR-015-approval-validation-system.md

Das ADR soll ~500-700 Zeilen sein und ALLE wichtigen Details aus den Konzepten konsolidieren.
