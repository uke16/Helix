# HELIX v4 Onboarding Guide

> **Willkommen bei HELIX v4** - Ein AI Development Orchestration System
> 
> Diese Datei erklärt das Konzept und wie man HELIX bedient.

---

## Was ist HELIX?

HELIX ist ein System das **Claude Code Instanzen orchestriert** um Software zu entwickeln. 
Statt eine einzelne AI-Session zu nutzen, unterteilt HELIX Aufgaben in **Phasen** die von 
separaten Claude Code Instanzen bearbeitet werden.

```
┌──────────────────────────────────────────────────────────────────┐
│                         HELIX v4                                 │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│   User: "Erstelle einen BOM Export"                              │
│                    │                                             │
│                    ▼                                             │
│   ┌─────────────────────────────────┐                            │
│   │  Claude Code #0 (Consultant)    │  ← Fragt: Was? Warum?      │
│   │  - Liest Skills (PDM, etc.)     │     Constraints?           │
│   │  - Generiert spec.yaml          │                            │
│   │  - Generiert phases.yaml        │                            │
│   └─────────────────────────────────┘                            │
│                    │                                             │
│                    ▼                                             │
│   ┌─────────────────────────────────┐                            │
│   │  Claude Code #1 (Phase 01)      │  ← Analyse                 │
│   └─────────────────────────────────┘                            │
│                    │                                             │
│                    ▼                                             │
│   ┌─────────────────────────────────┐                            │
│   │  Claude Code #2 (Phase 02)      │  ← Implementation          │
│   └─────────────────────────────────┘                            │
│                    │                                             │
│                    ▼                                             │
│   ┌─────────────────────────────────┐                            │
│   │  Claude Code #3 (Phase 03)      │  ← Testing                 │
│   └─────────────────────────────────┘                            │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Kernkonzepte

### 1. Consultant (Phase 0)

Bevor Code geschrieben wird, führt ein **Consultant** ein "Meeting" mit dem User:

- **Was** soll gebaut werden?
- **Warum** wird es benötigt?
- **Welche Constraints** gibt es?

Der Consultant liest die **Skills** (Domain-Wissen) und generiert:
- `spec.yaml` - Anforderungsspezifikation
- `phases.yaml` - Phasen-Plan für die Umsetzung

→ Siehe: [skills/helix/SKILL.md](skills/helix/SKILL.md)

### 2. Phasen-basierte Ausführung

Jedes Projekt wird in Phasen unterteilt:

| Phase | Typ | Beschreibung |
|-------|-----|--------------|
| 01-analysis | development | Analyse des Problems |
| 02-implementation | development | Code schreiben |
| 03-testing | development | Tests und Validierung |
| 04-documentation | documentation | Dokumentation erstellen |

Jede Phase hat:
- Eigenes Verzeichnis: `phases/01-analysis/`
- Eigene CLAUDE.md mit Anweisungen
- Eigene Input/Output Dateien
- **Quality Gate** zur Validierung

→ Siehe: [docs/ARCHITECTURE-MODULES.md](docs/ARCHITECTURE-MODULES.md)

### 3. Quality Gates

Nach jeder Phase prüft HELIX ob die Arbeit erfolgreich war:

- `files_exist` - Wurden die erwarteten Dateien erstellt?
- `syntax_check` - Ist der Code syntaktisch korrekt?
- `tests_pass` - Laufen die Tests?
- `review_approved` - LLM Review bestanden?

→ Siehe: [config/quality-gates.yaml](config/quality-gates.yaml)

### 4. Skills (Domain-Wissen)

Skills sind strukturiertes Wissen das Claude Code Instanzen lesen können:

```
skills/
├── helix/           # Wie HELIX funktioniert
├── pdm/             # PDM System Domain-Wissen
├── encoder/         # POSITAL Encoder Wissen
└── infrastructure/  # Docker, PostgreSQL, etc.
```

→ Siehe: [skills/](skills/)

---

## Verzeichnisstruktur

```
helix-v4/
├── ONBOARDING.md          ← Du bist hier
├── CLAUDE.md              ← Anweisungen für Claude Code im Root
├── README.md              ← Projekt-Übersicht
│
├── src/helix/             # Python Code
│   ├── orchestrator.py    # Phasen-Orchestrierung
│   ├── claude_runner.py   # Claude Code CLI Wrapper
│   ├── phase_loader.py    # Lädt phases.yaml
│   ├── quality_gates.py   # Gate-Validierung
│   └── api/               # FastAPI REST API
│
├── config/                # Konfigurationsdateien
│   ├── llm-providers.yaml
│   ├── quality-gates.yaml
│   └── escalation.yaml
│
├── templates/             # Jinja2 Templates für CLAUDE.md
│   ├── consultant/
│   ├── developer/
│   └── reviewer/
│
├── skills/                # Domain-Wissen
│   ├── helix/
│   ├── pdm/
│   └── encoder/
│
├── projects/              # Projekt-Verzeichnisse
│   ├── sessions/          # Laufende Consultant Sessions
│   ├── external/          # Externe Projekte (z.B. config-validator)
│   └── internal/          # Interne HELIX Projekte
│
└── docs/                  # Dokumentation
    ├── QUICKSTART.md
    ├── USER-GUIDE.md
    └── ARCHITECTURE-*.md
```

---

## Wie bedient man HELIX?

### Option 1: Open WebUI (Browser)

1. Öffne: https://helix2.duckdns.org:8443
2. Wähle Model: `helix-consultant`
3. Beschreibe was du bauen möchtest
4. Beantworte die Fragen des Consultants
5. Bestätige den Plan mit "Ja, starte!"

### Option 2: API (curl)

```bash
# Projekt ausführen
curl -X POST http://localhost:8001/helix/execute \
  -H "Content-Type: application/json" \
  -d '{"project_path": "/path/to/project"}'

# Job Status prüfen
curl http://localhost:8001/helix/jobs/{job_id}

# Live Stream
curl -N http://localhost:8001/helix/stream/{job_id}
```

### Option 3: CLI

```bash
cd /home/aiuser01/helix-v4

# Consultant starten
python -m helix.cli.main discuss ./projects/external/mein-projekt

# Projekt ausführen
python -m helix.cli.main run ./projects/external/mein-projekt
```

---

## Weitere Dokumentation

| Datei | Beschreibung |
|-------|--------------|
| [docs/QUICKSTART.md](docs/QUICKSTART.md) | Schnellstart-Anleitung |
| [docs/USER-GUIDE.md](docs/USER-GUIDE.md) | Ausführliche Bedienungsanleitung |
| [docs/CLI-REFERENCE.md](docs/CLI-REFERENCE.md) | CLI Kommando-Referenz |
| [docs/CONFIGURATION.md](docs/CONFIGURATION.md) | Konfigurationsoptionen |
| [docs/ARCHITECTURE-MODULES.md](docs/ARCHITECTURE-MODULES.md) | Modul-Architektur |
| [docs/ARCHITECTURE-DECISIONS.md](docs/ARCHITECTURE-DECISIONS.md) | Architektur-Entscheidungen |
| [docs/CONCEPT.md](docs/CONCEPT.md) | Detailliertes Konzept-Dokument |

---

## Für Claude Code Instanzen

Wenn du als Claude Code Instanz in diesem Projekt arbeitest:

1. **Lies zuerst**: [CLAUDE.md](CLAUDE.md) im Root
2. **Verstehe deine Rolle**: Welche Phase bearbeitest du?
3. **Nutze Skills**: Lies relevante Skills in `skills/`
4. **Befolge Quality Gates**: Dein Output wird validiert
5. **Schreibe in output/**: Deine Ergebnisse gehören in `output/`

→ Siehe: [skills/helix/workflows.md](skills/helix/workflows.md)

---

## 7. Self-Evolution System (Phase 14)

HELIX can safely evolve itself through an isolated test system.

### Architecture

```
Production (helix-v4)          Test (helix-v4-test)
Port 8001                      Port 9001
├── projects/evolution/        ├── (deployed changes)
│   └── {project}/             └── Isolated DB ports
│       ├── spec.yaml
│       ├── new/
│       └── modified/
```

### Evolution Workflow

```bash
# 1. Create evolution project
POST /helix/evolution/projects
  {name: "new-feature", spec: {...}}

# 2. Deploy to test system
POST /helix/evolution/projects/{name}/deploy

# 3. Validate (syntax, unit tests, E2E)
POST /helix/evolution/projects/{name}/validate

# 4. Integrate to production (on success)
POST /helix/evolution/projects/{name}/integrate

# 5. Sync RAG databases
POST /helix/evolution/sync-rag
```

### Control Script

```bash
./control/helix-control.sh status    # Check both systems
./control/helix-control.sh start     # Start production
./control/helix-control.sh restart   # Restart after changes
```

### Key Principle: "Zettel statt Telefon"

Claude Code instances are short-lived. Communication happens through files
(spec.yaml, status.json), not real-time dialogue.
