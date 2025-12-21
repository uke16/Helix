# HELIX v4 Bootstrap - Phasen-Übersicht

## Übersicht aller 11 Phasen

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Phase 01: Foundation        → Core-Module (orchestrator, templates)   │
│  Phase 02: Consultant        → Meeting System (Meta + Experten)        │
│  Phase 03: Observability     → Logging & Metrics                       │
│  Phase 04: CLI               → Command Line Interface                  │
│  Phase 05: Templates         → CLAUDE.md Templates (Jinja2)            │
│  Phase 06: Config            → Konfigurationsdateien (YAML)            │
│  Phase 07: Unit Tests        → pytest für alle Module                  │
│  Phase 08: Integration Tests → Orchestrator + LLM Tests                │
│  Phase 09: Review            → Architecture Review (Claude Opus)       │
│  Phase 10: E2E Test          → HELIX testet sich selbst!               │
│  Phase 11: Documentation     → Finale Doku (API, User, Architecture)   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 01: Foundation (Core Framework) 🔴

**Status:** Bereit zum Start

**Erstellt:**
```
src/helix/
├── __init__.py           # Version
├── orchestrator.py       # Workflow-Steuerung
├── template_engine.py    # Jinja2 CLAUDE.md Generierung
├── context_manager.py    # Skill-Verwaltung & Symlinks
├── quality_gates.py      # Gate-Prüfungen
├── phase_loader.py       # phases.yaml Loading
├── spec_validator.py     # spec.yaml Validierung
├── llm_client.py         # Multi-Provider LLM (OpenRouter, etc.)
├── claude_runner.py      # Claude Code Subprocess
└── escalation.py         # 2-Stufen Escalation
```

**ADR-Referenzen:** 000, 001, 002, 003, 004, 007

**Quality Gate:** `syntax_check` (Python Syntax, keine Import-Fehler)

---

## Phase 02: Consultant (Meeting System) 🟡

**Status:** Wartet auf Phase 01

**Erstellt:**
```
src/helix/consultant/
├── __init__.py
├── meeting.py            # Agentic Meeting Orchestrierung
│                         # 4 Phasen: Selection → Analysis → Synthesis → Output
└── expert_manager.py     # Domain-Experten Verwaltung
                          # PDM, ERP, Infrastructure, Database, Frontend
```

**ADR-Referenzen:** 005, 006

**Quality Gate:** `syntax_check`

---

## Phase 03: Observability (Logging & Metrics) 🟡

**Status:** Wartet auf Phase 01

**Erstellt:**
```
src/helix/observability/
├── __init__.py
├── logger.py             # 3-Ebenen Logging
│                         # Phase-Logs, Projekt-Logs, System-Logs
└── metrics.py            # Token/Cost Tracking
                          # PhaseMetrics, ProjectMetrics, Aggregation
```

**ADR-Referenzen:** 003

**Quality Gate:** `syntax_check`

---

## Phase 04: CLI (Command Line Interface) 🟡

**Status:** Wartet auf Phase 01-03

**Erstellt:**
```
src/helix/cli/
├── __init__.py
├── main.py               # Click Einstiegspunkt
└── commands.py           # Commands: run, status, debug, costs
```

**Commands:**
- `helix run <project>` - Workflow starten
- `helix status <project>` - State anzeigen
- `helix debug <project> <phase>` - Logs anzeigen
- `helix costs <project>` - Kosten anzeigen
- `helix new <project>` - Neues Projekt erstellen

**Quality Gate:** `syntax_check`

---

## Phase 05: Templates (CLAUDE.md Templates) 🟡

**Status:** Wartet auf Phase 01

**Erstellt:**
```
templates/
├── consultant/
│   ├── default.md        # Meta-Consultant
│   └── expert-base.md    # Domain-Expert Basis
├── developer/
│   ├── _base.md          # Basis für alle Developer
│   ├── python.md         # Python-spezifisch
│   ├── cpp.md            # C++-spezifisch
│   └── typescript.md     # TypeScript-spezifisch
├── reviewer/
│   ├── code.md           # Code Review
│   └── architecture.md   # Architecture Review
├── documentation/
│   └── technical.md      # Technical Docs
└── project-types/
    ├── feature.yaml      # Standard Feature
    ├── documentation.yaml
    ├── research.yaml
    └── bugfix.yaml
```

**Quality Gate:** `files_exist`

---

## Phase 06: Config (Konfiguration) 🟡

**Status:** Wartet auf Phase 01

**Erstellt:**
```
config/
├── llm-providers.yaml    # OpenRouter, Anthropic, OpenAI, xAI
└── domain-experts.yaml   # PDM, ERP, Infra, DB, Frontend Experten
```

**Quality Gate:** `files_exist`

---

## Phase 07: Unit Tests 🟡

**Status:** Wartet auf Phase 01-06

**Erstellt:**
```
tests/unit/
├── __init__.py
├── test_template_engine.py
├── test_quality_gates.py
├── test_spec_validator.py
└── test_phase_loader.py
```

**Quality Gate:** `tests_pass` (`pytest tests/unit/`)

---

## Phase 08: Integration Tests 🟡

**Status:** Wartet auf Phase 07

**Erstellt:**
```
tests/integration/
└── test_orchestrator.py  # Orchestrator mit Mock-LLM
```

**Quality Gate:** `tests_pass`

---

## Phase 09: Architecture Review 🟡

**Status:** Wartet auf Phase 08

**Model:** Claude Opus (für tiefes Review)

**Prüft:**
- Code-Qualität
- ADR-Konformität
- Konsistenz zwischen Modulen
- Edge Cases

**Output:**
```
review/
└── review.json           # Strukturiertes Review-Ergebnis
```

**Quality Gate:** `review_approved`

---

## Phase 10: E2E Test (Self-Test!) 🟡

**Status:** Wartet auf Phase 09

**Testet:**
HELIX v4 führt ein Mini-Projekt mit sich selbst durch!

```
tests/e2e/
└── test_mini_project.py
    # 1. Erstellt Mini-Projekt
    # 2. Startet HELIX Orchestrator
    # 3. Durchläuft alle Phasen
    # 4. Prüft Output
```

**Quality Gate:** `tests_pass`

---

## Phase 11: Documentation 🟡

**Status:** Wartet auf Phase 10

**Erstellt:**
```
docs/
├── architecture.md       # System-Architektur
├── getting-started.md    # Quick Start Guide
└── api/
    └── index.md          # API Dokumentation
```

**Quality Gate:** `files_exist`

---

## Start-Anleitung

```bash
# Phase 01 starten
./start-phase.sh 01-foundation

# Oder manuell
cd /home/aiuser01/helix-v4/projects/internal/helix-v4-bootstrap/phases/01-foundation
claude --permission-mode acceptEdits
```

---

## Abhängigkeiten

```
01-foundation ──┬──▶ 02-consultant
                ├──▶ 03-observability
                ├──▶ 05-templates
                └──▶ 06-config
                          │
                          ▼
             04-cli ◀────┴────────────┐
                                      │
                                      ▼
                              07-unit-tests
                                      │
                                      ▼
                          08-integration-tests
                                      │
                                      ▼
                                 09-review
                                      │
                                      ▼
                               10-e2e-test
                                      │
                                      ▼
                             11-documentation
```

---

*Erstellt: 2025-12-21*

---

## Phase 12: REST API 🟡

**Status:** Added (after Phase 11)

**Creates:**
```
src/helix/api/
├── __init__.py
├── main.py              # FastAPI app
├── models.py            # Pydantic schemas
├── config.py            # Settings
├── database.py          # SQLAlchemy async
├── auth.py              # Open WebUI JWT
├── queue.py             # Job queue
└── routes/
    ├── __init__.py
    ├── discuss.py       # POST /discuss (Meta-Consultant chat)
    ├── projects.py      # CRUD projects
    ├── execute.py       # Start workflow
    └── stream.py        # SSE streaming

docker/helix-api/
├── Dockerfile
├── docker-compose.yaml
└── requirements.txt

config/
└── api.yaml             # API configuration
```

**Features:**
- FastAPI with async support
- PostgreSQL for jobs/projects state
- SSE streaming for live output
- Open WebUI authentication
- 10 projects per user limit
- 5 concurrent jobs limit

**Endpoints:**
- `POST /api/v1/discuss` - Chat with Meta-Consultant
- `POST /api/v1/projects` - Create project
- `GET  /api/v1/projects` - List projects
- `GET  /api/v1/projects/{id}` - Get project
- `POST /api/v1/projects/{id}/execute` - Start workflow
- `GET  /api/v1/stream/{id}` - SSE streaming

**Quality Gate:** `syntax_check`

---

## Updated Dependency Graph

```
01-foundation ──┬──▶ 02-consultant
                ├──▶ 03-observability
                ├──▶ 05-templates
                └──▶ 06-config
                          │
             04-cli ◀────┴────────────┐
                                      │
                                      ▼
                              07-unit-tests
                                      │
                                      ▼
                          08-integration-tests
                                      │
                                      ▼
                                 09-review
                                      │
                                      ▼
                               10-e2e-test
                                      │
                                      ▼
                             11-documentation
                                      │
                                      ▼
                               12-api ◀──── NEW!
```
