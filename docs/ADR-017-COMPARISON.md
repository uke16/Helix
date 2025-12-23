# ADR-017 Vergleich: Claude Opus vs. Consultant

> Analyse beider Versionen für "best of both worlds"

---

## Übersicht

| Aspekt | Claude Opus | Consultant |
|--------|-------------|------------|
| **Zeilen** | 704 | 1426 |
| **Sections** | 10 | 9 |
| **Akzeptanzkriterien** | 16 | 21 |
| **Code-Beispiele** | 3 Klassen | 5+ Klassen |
| **Validierung** | ❌ FAIL | ✅ PASS |

---

## Was Claude Opus besser macht

### 1. Kompaktheit
- Weniger Text, schneller zu lesen
- Fokussierter auf das Wesentliche

### 2. Architektur-Diagramm
```
┌─────────────────────────────────────────────────────────────┐
│                      ORCHESTRATOR                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ PhaseRunner │  │ GateChecker │  │ Decomposer  │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
```
- Klares visuelles Bild der Architektur

### 3. Aufwandsschätzung
- Konkrete Tabelle mit Tagen pro Phase
- Gesamt: ~2 Wochen

### 4. Pragmatische Migration
- 3 Phasen klar definiert
- Rückwärtskompatibilität explizit

---

## Was Consultant besser macht

### 1. Validität
- `component_type: PROCESS` (valide!)
- Claude Opus hatte `ORCHESTRATOR` (nicht im Enum)

### 2. Mehr Dependencies
```yaml
# Consultant
depends_on:
  - "002"  # Workflow System
  - "015"  # Approval System
related_to:
  - "006"  # Phase Executor
  - "014"  # Documentation
```
vs.
```yaml
# Claude Opus
depends_on:
  - "015"
```

### 3. Test-Dateien im Header
```yaml
files:
  create:
    - tests/test_orchestrator_runner.py
    - tests/test_phase_executor.py
    - tests/test_data_flow.py
```
- Zeigt von Anfang an dass Tests wichtig sind

### 4. Detailliertere Akzeptanzkriterien
- 8 Kategorien statt 4
- Spezifischere Checks (z.B. "Resume funktioniert nach Neustart")

### 5. Projekt-Typen in phase-types.yaml
```yaml
project_types:
  simple:
    default_phases:
      - consultant
      - development
      - review
      - integration
  complex:
    default_phases:
      - consultant
      - feasibility
      - planning
      - ...
```
- Macht Projekt-Templates Teil der Config

### 6. dry_run Option
```python
@dataclass
class RunConfig:
    dry_run: bool = False  # Nützlich für Testing!
```

### 7. DataFlowManager als eigene Klasse
- Bessere Separation of Concerns
- Einfacher zu testen

---

## Best of Both Worlds: Empfehlung

### Von Claude Opus übernehmen:
1. Architektur-Diagramm
2. Aufwandsschätzung
3. Kompakte Prosa

### Von Consultant übernehmen:
1. YAML Header (valide!)
2. depends_on + related_to
3. Test-Dateien im Header
4. Projekt-Typen in Config
5. Detaillierte Akzeptanzkriterien
6. DataFlowManager Klasse
7. dry_run Option

### Zusammenführen:

```yaml
# Kombinierter Header
adr_id: "017"
title: "Phase Orchestrator - Autonome Projekt-Ausführung"
status: Proposed
date: 2025-12-23

project_type: helix_internal
component_type: PROCESS
classification: NEW
change_scope: major

depends_on:
  - "002"
  - "015"
related_to:
  - "006"
  - "014"

files:
  create:
    - src/helix/orchestrator/__init__.py
    - src/helix/orchestrator/runner.py
    - src/helix/orchestrator/phase_executor.py  # Von Consultant
    - src/helix/orchestrator/data_flow.py       # Von Consultant
    - src/helix/orchestrator/status.py
    - src/helix/orchestrator/decompose.py       # Von Opus
    - src/helix/cli/project.py
    - config/phase-types.yaml
    - config/orchestrator.yaml                  # Von Consultant
    - tests/test_orchestrator_runner.py         # Von Consultant
    - tests/test_phase_executor.py
    - tests/test_data_flow.py
```

---

## Nächster Schritt

1. Consultant-Version als Basis nehmen (weil valide)
2. Architektur-Diagramm von Opus einfügen
3. Aufwandsschätzung von Opus hinzufügen
4. Prosa etwas straffen

