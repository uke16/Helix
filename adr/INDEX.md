# HELIX v4 - ADR Index

> **Kernprinzip:** Claude Code CLI + CLAUDE.md + Datei-basierte Kommunikation
> 
> Kein SDK, kein LangGraph, kein EventBus - nur Python + Dateien + Claude Code!

---

## Status Legende

| Status | Bedeutung |
|--------|-----------|
| ✅ Akzeptiert | Entschieden, wird/ist implementiert |
| 📋 Proposed | Ausgearbeitet, wartet auf Review |
| 🚧 Draft | In Arbeit |

---

## Übersicht

### Core Architecture (000-010)

| Nr | ADR | Status | Kurzbeschreibung |
|----|-----|--------|------------------|
| 000 | [Vision & Architecture](000-vision-and-architecture.md) | ✅ | Grundkonzept, Claude Code, Phasen |
| 001 | [Template & Context System](001-template-and-context-system.md) | ✅ | CLAUDE.md Templates, Skills, Jinja2 |
| 002 | [Quality Gate System](002-quality-gate-system.md) | ✅ | Deterministische Prüfungen |
| 003 | [Observability & Debugging](003-observability-and-debugging.md) | ✅ | 3-Ebenen Logging, Debug CLI |
| 004 | [Escalation Meeting System](004-escalation-meeting-system.md) | ✅ | 2-Stufen: Consultant-autonom → HIL |
| 005 | [Consultant Topology](005-consultant-topology-agentic-meetings.md) | ✅ | Meta-Consultant + Domain-Experten |
| 006 | [Dynamic Phase Definition](006-dynamic-phase-definition.md) | ✅ | phases.yaml, Projekt-Typen |
| 007 | [Multi-Provider LLM](007-multi-provider-llm-configuration.md) | ✅ | OpenRouter, Model-Switch |
| 008 | [Spec Schema](008-implementation-spec-schema.md) | ⚠️ | DEPRECATED - Superseded by ADR-012 |
| 009 | [Bootstrap Project](009-bootstrap-project.md) | 📋 | HELIX v4 baut sich selbst |
| 010 | [ADR Migration](010-adr-migration-from-v3.md) | 📋 | v3 → v4 Migration Guide |

### Evolution System (011-015)

| Nr | ADR | Status | Kurzbeschreibung |
|----|-----|--------|------------------|
| 011 | [Post-Phase Verification](011-post-phase-verification.md) | ✅ | Hybrid: Self-Verify + Safety Net, max 2 Retries |
| 012 | [ADR as Single Source of Truth](012-adr-as-single-source-of-truth.md) | ✅ | ADR ersetzt spec.yaml, files.create/modify |
| 013 | [Debug & Observability Engine](013-debug-observability-engine-für-helix-workflows.md) | 📋 | Live Tool Call Tracking, Cost Monitoring, StreamParser |
| 014 | [Documentation Architecture](014-documentation-architecture.md) | 📋 | Generated Docs, Single Source of Truth, Enforcement |
| 015 | [Approval & Validation System](015-approval-validation-system.md) | 📋 | Hybrid Pre-Checks + Sub-Agent, ADR-Completeness |

### Orchestration & API (017-022)

| Nr | ADR | Status | Kurzbeschreibung |
|----|-----|--------|------------------|
| 017 | [Phase Orchestrator](017-phase-orchestrator.md) | ⚠️ | SUPERSEDED by ADR-022 |
| 018 | [LSP Integration](018-lsp-integration.md) | 📋 | Native Claude Code LSP für Code-Intelligence |
| 019 | [Documentation as Code](019-documentation-as-code.md) | 📋 | Validierbare Referenzen, Symbol Extraction |
| 020 | [Intelligent Documentation Discovery](020-intelligent-documentation-discovery.md) | 📋 | Skill Index, Reverse Index für Context |
| 021 | [Async CLI Background Jobs](021-async-cli-background-jobs.md) | 📋 | --background Flag, Jobs überleben SSH-Disconnect |
| 022 | [Unified API Architecture](022-unified-api-architecture.md) | 📋 | Eine API für alles, CLI als thin client |

### Workflow System (023-026)

| Nr | ADR | Status | Kurzbeschreibung |
|----|-----|--------|------------------|
| 023 | [Workflow-Definitionen](023-workflow-definitions.md) | ✅ | 4 Workflow-Templates: intern/extern × simple/complex |
| 024 | [Consultant Workflow-Wissen](024-consultant-workflow-knowledge.md) | ✅ | Workflow-Sektion in session.md.j2, workflow-guide.md |
| 025 | [Sub-Agent Verifikation](025-sub-agent-verification.md) | ✅ | Haiku-basierte Prüfung, 3-Retry-Loop, Feedback |
| 026 | [Dynamische Phasen-Generierung](026-dynamic-phase-generation.md) | ✅ | PlanningAgent generiert 1-5 Phasen dynamisch |

---

## Architektur-Diagramm

```
┌─────────────────────────────────────────────────────────────────────┐
│                         HELIX v4                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   USER                                                              │
│     │                                                               │
│     ▼                                                               │
│   ┌───────────────────────────────────────────────────────────┐    │
│   │              PYTHON ORCHESTRATOR                           │    │
│   │                                                            │    │
│   │   • Lädt phases.yaml (ADR-006)                            │    │
│   │   • Generiert CLAUDE.md (ADR-001)                         │    │
│   │   • Führt Quality Gates aus (ADR-002)                     │    │
│   │   • Post-Phase Verification (ADR-011)                     │    │
│   └───────────────────────────────────────────────────────────┘    │
│                            │                                        │
│                            ▼                                        │
│   ┌───────────────────────────────────────────────────────────┐    │
│   │              CLAUDE CODE INSTANZ                           │    │
│   │                                                            │    │
│   │   • Liest CLAUDE.md                                       │    │
│   │   • Arbeitet in phase/X/                                  │    │
│   │   • Ruft verify_phase_output auf (ADR-011)               │    │
│   │   • Schreibt nach output/ oder new/                      │    │
│   └───────────────────────────────────────────────────────────┘    │
│                            │                                        │
│                            ▼                                        │
│   ┌───────────────────────────────────────────────────────────┐    │
│   │              EVOLUTION SYSTEM                              │    │
│   │                                                            │    │
│   │   • ADR als Single Source of Truth (ADR-012)             │    │
│   │   • Deploy → Validate → Integrate                         │    │
│   │   • ADR-System für Verification                           │    │
│   └───────────────────────────────────────────────────────────┘    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## ADR Lifecycle

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Draft   │───▶│ Proposed │───▶│ Accepted │───▶│Implemented│
│   🚧     │    │    📋    │    │    ✅    │    │    ✅    │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
```

---

## Neue ADRs erstellen

1. Nächste freie Nummer verwenden (aktuell: 039)
2. Format: `NNN-kurzer-name.md`
3. YAML Header mit adr_id, title, status, files, depends_on
4. Sections: Kontext, Entscheidung, Implementation, Akzeptanzkriterien
5. INDEX.md aktualisieren

### Template

```yaml
---
adr_id: "NNN"
title: "Feature Name"
status: Proposed
component_type: TOOL|NODE|AGENT|PROCESS|SERVICE
classification: NEW|UPDATE|FIX|REFACTOR
change_scope: major|minor|config|docs|hotfix

files:
  create: [...]
  modify: [...]
  docs: [...]

depends_on: [...]
---
```

---

## Abhängigkeiten

```
000 Vision
 └── 001 Templates
      ├── 002 Quality Gates ─── 011 Post-Phase Verification
      ├── 003 Observability
      ├── 006 Dynamic Phases
      └── 008 Spec Schema ───── 012 ADR as Single Source
           └── 009 Bootstrap
```

## Aktuelles: Workflow System (ADR-023 bis ADR-026)

Das Workflow System wurde vollständig implementiert und dokumentiert.

**Kernkonzepte:**
- 4 Workflow-Templates: `intern-simple`, `intern-complex`, `extern-simple`, `extern-complex`
- Sub-Agent Verifikation mit 3-Retry-Loop und Feedback-Mechanismus
- Dynamische Phasen-Generierung mit PlanningAgent (1-5 Phasen)
- Consultant weiß über Workflows Bescheid (session.md.j2, workflow-guide.md)

**Dokumentation:**
- [docs/WORKFLOW-SYSTEM.md](../docs/WORKFLOW-SYSTEM.md) - Vollständige Workflow-Dokumentation
- [templates/consultant/workflow-guide.md](../templates/consultant/workflow-guide.md) - Consultant Guide

**Status:** Alle 4 ADRs sind implementiert und die Module existieren:
- `src/helix/verification/` - SubAgentVerifier, FeedbackChannel
- `src/helix/planning/` - PlanningAgent, PhaseGenerator
- `templates/workflows/` - 4 Workflow-Templates

### Integration & Reliability (027-033)

| Nr | ADR | Status | Kurzbeschreibung |
|----|-----|--------|------------------|
| 027 | [Stale Response Bugfix](027-stale-response-bugfix---open-webui-integration.md) | ✅ | Fix für stale response.md in Open WebUI |
| 028 | [Claude Code Launcher Performance](028-claude-code-launcher-performance---pre-warmed-inst.md) | 📋 | Pre-warmed Instance Pool |
| 029 | [Session Persistence](029-open-webui-session-persistence---x-conversation-id.md) | ✅ | X-Conversation-ID für stabile Sessions |
| 030 | [Evolution Pipeline Reliability](030-evolution-pipeline-reliability.md) | ✅ | 10 Fixes für Pipeline-Stabilität |
| 031 | [Pipeline Bugfixes Wave 2](031-pipeline-bugfixes-wave2.md) | ✅ | Weitere Pipeline-Fixes |
| 033 | [MCP Blueprint Server](033-mcp-blueprint-server---modulare-remote-fähige-arch.md) | 📋 | Modulare MCP Architektur für Remote-Clients |
| 034 | [Consultant Flow Refactoring](034-consultant-flow-refactoring-llm-native.md) | 📋 | LLM-Native statt State-Machine für Consultant Flow |
| 035 | [Consultant API Hardening](035-consultant-api-hardening.md) | ✅ | Security & Reliability Fixes |
| 038 | [Deterministic LLM Response Enforcement](038-deterministic-llm-response-enforcement.md) | 📋 | Response Validation, Retry & Fallback, Cleanup |

