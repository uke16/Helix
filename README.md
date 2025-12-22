# HELIX v4

> **Multi-Agent AI System für Enterprise Software Development**
> 
> Claude Code SDK + OpenRouter + Python Orchestration

## Vision

HELIX v4 ist die nächste Evolution unseres AI-gestützten Entwicklungssystems.
Statt eigene LLM-Agents von Grund auf zu bauen, nutzen wir **Claude Code SDK** 
als bewährtes Agent-Harness und fokussieren uns auf das, was HELIX einzigartig macht:

- **Domain-Wissen** (PDM, ERP, Legacy-Systeme)
- **Quality Gates** (deterministische Prüfungen)
- **Meeting-System** (Consultant-User Kollaboration)
- **Workflow-Orchestrierung** (Phasen, Transitions, Escalation)

## Key Features

- **Multi-Agent Orchestration** - Consultant, Developer, Reviewer workflow
- **Claude Code SDK Integration** - Proven agent harness
- **OpenAI-Compatible API** - Easy integration with any client
- **Self-Evolution System** - HELIX can safely evolve itself through isolated test validation
- **Quality Gates** - Deterministic checks between phases
- **RAG Integration** - Vector search with Qdrant

## Kernprinzip

```
┌─────────────────────────────────────────────────────────────────┐
│  "Claude Code macht das Agent-Harness.                         │
│   Wir machen das Drumherum."                                    │
└─────────────────────────────────────────────────────────────────┘
```

## Architektur-Überblick

```
                         ┌─────────────────┐
                         │    Open WebUI   │
                         └────────┬────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                     HELIX v4 Orchestrator                        │
│                        (Python + FastAPI)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Phase 1          Phase 2          Phase 3          Phase 4    │
│  ┌─────────┐      ┌─────────┐      ┌─────────┐      ┌─────────┐ │
│  │Consultant│      │Developer│      │Reviewer │      │  Docs   │ │
│  │ Meeting │──QG1─▶│  Code   │──QG2─▶│ Review  │──QG3─▶│  Agent  │ │
│  └─────────┘      └─────────┘      └─────────┘      └─────────┘ │
│       │                │                │                │      │
│       ▼                ▼                ▼                ▼      │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              Claude Code SDK Instances                      ││
│  │                    (via OpenRouter)                         ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │   Final Consultant      │
                    │   Review & Lessons      │
                    └─────────────────────────┘
```

## Quality Gates

| Gate | Nach Phase | Prüfung | Typ |
|------|------------|---------|-----|
| QG1 | Consultant Meeting | Spec vollständig? Files definiert? | Deterministisch |
| QG2 | Developer | Alle Files erstellt? Syntax OK? | Deterministisch |
| QG3 | Reviewer | Review passed? Tests grün? | Deterministisch |
| QG4 | Documentation | Alle Docs geschrieben? | Deterministisch |

## Was von HELIX v3 übernommen wird

| Konzept | ADR | Warum relevant |
|---------|-----|----------------|
| Open WebUI Integration | ADR-043 | UI-Layer bleibt |
| Meeting System | ADR-047 | Kern-Feature |
| Multi-Domain Consultant | ADR-119 | Round-Table Meetings |
| Deterministic Documentation | ADR-071 | 4-Ebenen Doku-System |
| Bugfix Records | ADR-084 | Lessons Learned |
| Plan/Completion Validators | ADR-094/095 | Quality Gates |
| ADR Template v2 | ADR-086 | Spec-Format |
| Pre-loaded Context | ADR-067 | Domain-Wissen |

## Was NEU ist in v4

| Konzept | Beschreibung |
|---------|--------------|
| Claude Code SDK | Ersetzt eigene Agent-Implementierung |
| OpenRouter | Vendor-unabhängiges LLM-Routing |
| Python Orchestrator | Ersetzt LangGraph für Workflow |
| SDK Hooks | Ersetzt EventBus für Agent-Kommunikation |
| Simpler State | Python dict statt TypedDict-Magie |

## Quick Start

```bash
# Prerequisites
npm install -g @anthropic-ai/claude-code
pip install claude-agent-sdk

# OpenRouter Config
export ANTHROPIC_BASE_URL="https://openrouter.ai/api/v1"
export ANTHROPIC_API_KEY=""  # Muss leer sein!
export OPENROUTER_API_KEY="sk-or-..."

# Start HELIX v4
cd /home/aiuser01/helix-v4
python -m helix.main
```

## Projekt-Struktur

```
helix-v4/
├── README.md              # Diese Datei
├── adr/                   # Architecture Decision Records
│   ├── 000-vision.md      # Vision & Grundkonzept
│   ├── 001-sdk-integration.md
│   └── ...
├── docs/                  # Architektur-Dokumentation
│   ├── architecture/
│   └── skills/           # Von v3 migriert
├── src/                  # Python Source
│   └── helix/
│       ├── orchestrator.py
│       ├── quality_gates.py
│       ├── meetings.py
│       └── agents/       # SDK-basierte Agents
├── config/               # Konfiguration
│   ├── domains/          # Domain-Wissen (PDM, ERP, ...)
│   └── openrouter.yaml
└── projects/             # Laufende Projekte
```

## Status

🚧 **In Planung** - Konzeptphase

---

*Erstellt: 2025-12-21*
*Migration von: HELIX v3*
