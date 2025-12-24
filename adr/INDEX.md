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

### Evolution System (011-020)

| Nr | ADR | Status | Kurzbeschreibung |
|----|-----|--------|------------------|
| 011 | [Post-Phase Verification](011-post-phase-verification.md) | ✅ | Hybrid: Self-Verify + Safety Net, max 2 Retries |
| 012 | [ADR as Single Source of Truth](012-adr-as-single-source-of-truth.md) | ✅ | ADR ersetzt spec.yaml, files.create/modify |
| 013 | [Debug & Observability Engine](013-debug-observability-engine-für-helix-workflows.md) | 📋 | Live Tool Call Tracking, Cost Monitoring, StreamParser |
| 014 | [Documentation Architecture](014-documentation-architecture.md) | 📋 | Generated Docs, Single Source of Truth, Enforcement |
| 015 | [Approval & Validation System](015-approval-validation-system.md) | 📋 | Hybrid Pre-Checks + Sub-Agent, ADR-Completeness |

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

1. Nächste freie Nummer verwenden (aktuell: 016)
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

## ADR-018: LSP Integration für Code-Intelligence

**Status:** Proposed | **Datum:** 2024-12-24

Native Claude Code LSP-Unterstützung für Anti-Halluzination und Code-Intelligence.
Nur `ENABLE_LSP_TOOL=1` Environment Variable nötig (seit Claude Code v2.0.74).

**Kernentscheidung:** Minimale Integration - nutze natives Feature statt eigener Lösung.

**Siehe:** [ADR-018](018-lsp-integration.md)

## ADR-019: Documentation as Code - Validierbare Referenzen

**Status:** Proposed | **Datum:** 2024-12-24

Drei-Schichten Dokumentationssystem mit validierbaren Referenzen (`$ref`, `$uses`, `$file`).
Verhindert veraltete Dokumentation durch Compile-Time Validierung.

**Kernkonzepte:**
- `$ref: helix.debug.StreamParser` → Validierbar, auto-extrahiert Docstrings
- `$uses: StreamParser.parse_line` → Workflow-Steps validieren Methoden
- `$diagram_refs` → Diagramme listen ihre Code-Abhängigkeiten

**Siehe:** [ADR-019](019-documentation-as-code.md)
