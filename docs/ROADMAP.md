# HELIX v4 Roadmap

> Aktuelle Entwicklungs-Roadmap
>
> Stand: 2025-12-23
> Nächstes Update: Nach ADR-017 MVP

---

## Übersicht

```
┌─────────────────────────────────────────────────────────────────┐
│                    ROADMAP ÜBERSICHT                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Phase 0: Bug Fix & Cleanup          [~1 Stunde]    ← JETZT     │
│  ├── BUG-001: _get_search_text() fix                            │
│  ├── ADR-014/015 Status → Implemented                           │
│  └── BACKLOG.md aktualisieren                                   │
│                                                                 │
│  Phase 1: ADR-013 Debug & Observability  [~1 Woche]             │
│  ├── StreamParser für Claude CLI NDJSON                         │
│  ├── ToolTracker für Tool Call Monitoring                       │
│  ├── CostCalculator für Token/Kosten                            │
│  └── LiveDashboard via SSE                                      │
│                                                                 │
│  Phase 2: ADR-017 Orchestrator MVP   [~2 Wochen]                │
│  ├── PhaseRunner (spawnt Claude CLI)                            │
│  ├── GateChecker (prüft Quality Gates)                          │
│  ├── StatusTracker (pause/resume)                               │
│  ├── CLI: helix project create/run/status                       │
│  └── API Integration                                            │
│                                                                 │
│  Phase 3: MaxVP Features             [~4-6 Wochen]              │
│  ├── Domain Consultants                                         │
│  ├── Hardware-Tool Integration                                  │
│  ├── Projekt-Hierarchie                                         │
│  └── Parallele Ausführung                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 0: Bug Fix & Cleanup

**Zeitrahmen:** ~1 Stunde
**Status:** 🔄 In Progress

### Tasks

| Task | Beschreibung | Status |
|------|--------------|--------|
| BUG-001 | `_get_search_text()` muss Sub-Sections einschließen | ⏳ |
| Status Update | ADR-014, ADR-015 → "Implemented" | ⏳ |
| BACKLOG Update | Korrekte Bug-Diagnose dokumentieren | ⏳ |
| Test Fix | BUG-003: ENHANCEMENT → NEW in Tests | ⏳ |

### Deliverables

- [ ] `src/helix/adr/completeness.py` gefixt
- [ ] `adr/014-*.md` Status: Implemented
- [ ] `adr/015-*.md` Status: Implemented
- [ ] `docs/BACKLOG.md` aktualisiert
- [ ] Alle Tests grün

---

## Phase 1: ADR-013 Debug & Observability

**Zeitrahmen:** ~1 Woche
**Status:** ⏳ Pending
**Projekt:** `projects/external/impl-adr-013/`

### Ziel

Live-Sichtbarkeit auf Claude CLI Ausführungen:
- Was passiert gerade?
- Welche Tools werden aufgerufen?
- Was kostet es?

### Neue Dateien

```
src/helix/debug/
├── __init__.py
├── stream_parser.py      # NDJSON Parser für Claude CLI
├── tool_tracker.py       # Tool Call Monitoring
├── cost_calculator.py    # Token/Kosten Tracking
└── live_dashboard.py     # SSE Events für Frontend

tests/debug/
└── test_stream_parser.py

control/
├── helix-debug.sh        # Debug-Wrapper
└── claude-wrapper.sh     # Modified für --stream-json
```

### Phasen

| Phase | Typ | Output | Gate |
|-------|-----|--------|------|
| 1 | development | stream_parser.py, tool_tracker.py | tests_pass |
| 2 | development | cost_calculator.py, live_dashboard.py | tests_pass |
| 3 | integration | claude-wrapper.sh, helix-debug.sh | files_exist |
| 4 | documentation | docs/DEBUGGING.md | docs_complete |

### Akzeptanzkriterien

- [ ] StreamParser parst Claude CLI NDJSON korrekt
- [ ] ToolTracker trackt alle Tool Calls
- [ ] CostCalculator berechnet Kosten pro Phase
- [ ] LiveDashboard sendet SSE Events
- [ ] helix-debug.sh startet Debug-Session
- [ ] Dokumentation in DEBUGGING.md

---

## Phase 2: ADR-017 Orchestrator MVP

**Zeitrahmen:** ~2 Wochen
**Status:** ⏳ Pending
**Projekt:** `projects/external/impl-adr-017/`

### Ziel

Autonome Projekt-Ausführung:
```bash
helix project create my-feature
helix project run my-feature
# → Orchestrator führt alle Phasen aus
# → User kommt später zurück
helix project status my-feature
# → "✅ Completed"
```

### Neue Dateien

```
src/helix/orchestrator/
├── __init__.py
├── runner.py             # Hauptklasse
├── phase_executor.py     # Spawnt Claude CLI
├── data_flow.py          # Kopiert input/output
└── status.py             # Status-Tracking

src/helix/cli/
└── project.py            # CLI Commands

config/
└── phase-types.yaml      # Gate-Defaults pro Phase-Type

tests/orchestrator/
├── test_runner.py
├── test_phase_executor.py
└── test_data_flow.py
```

### Phasen

| Phase | Typ | Output | Gate |
|-------|-----|--------|------|
| 1 | development | runner.py, status.py | tests_pass |
| 2 | development | phase_executor.py, data_flow.py | tests_pass |
| 3 | development | cli/project.py | tests_pass |
| 4 | integration | config/phase-types.yaml, API routes | files_exist |
| 5 | documentation | docs/ORCHESTRATOR-GUIDE.md | docs_complete |
| 6 | testing | E2E Test mit echtem Projekt | e2e_pass |

### Akzeptanzkriterien

- [ ] `helix project create <name>` erstellt Projekt-Struktur
- [ ] `helix project run <name>` führt alle Phasen aus
- [ ] `helix project run --resume` setzt nach Fehler fort
- [ ] `helix project status <name>` zeigt Status
- [ ] Outputs werden automatisch als Inputs kopiert
- [ ] Quality Gates werden nach jeder Phase geprüft
- [ ] Status in status.yaml persistiert
- [ ] API Endpoints funktionieren

---

## Phase 3: MaxVP Features (Future)

**Zeitrahmen:** ~4-6 Wochen
**Status:** 📋 Planned

### Features

| Feature | Aufwand | Dependencies |
|---------|---------|--------------|
| Domain Consultants | 1 Woche | ADR-017 MVP |
| Hardware-Tool Integration | 2 Wochen | ADR-017 MVP |
| Projekt-Hierarchie | 1 Woche | ADR-017 MVP |
| Parallele Ausführung | 2 Wochen | Projekt-Hierarchie |

### Dokumentation

Siehe: `docs/ARCHITECTURE-ORCHESTRATOR-FULL.md`

---

## Projekt-Struktur für Implementation

```
projects/external/
├── impl-adr-013/              # Debug & Observability
│   ├── CLAUDE.md              # Instruktionen
│   ├── phases.yaml            # 4 Phasen
│   ├── input/
│   │   └── ADR-013.md         # Symlink
│   └── output/
│
└── impl-adr-017/              # Orchestrator MVP
    ├── CLAUDE.md
    ├── phases.yaml            # 6 Phasen
    ├── input/
    │   ├── ADR-017.md         # Symlink
    │   └── ARCHITECTURE-*.md  # Symlinks
    └── output/
```

---

## Tracking

### Commits pro Phase

| Phase | Erwartete Commits |
|-------|-------------------|
| Phase 0 | 1-2 |
| Phase 1 (ADR-013) | 4-6 |
| Phase 2 (ADR-017) | 8-12 |

### Metriken

| Metrik | Aktuell | Nach Phase 1 | Nach Phase 2 |
|--------|---------|--------------|--------------|
| ADRs Implemented | 4 | 5 | 6 |
| Code Lines | ~12k | ~14k | ~18k |
| Test Coverage | ~60% | ~70% | ~80% |

---

## Changelog

| Datum | Änderung |
|-------|----------|
| 2025-12-23 | Initial Roadmap erstellt |

