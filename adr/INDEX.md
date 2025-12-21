# HELIX v4 - ADR Index

> **Kernprinzip:** Claude Code CLI + CLAUDE.md + Datei-basierte Kommunikation
> 
> Kein SDK, kein LangGraph, kein EventBus - nur Python + Dateien + Claude Code!

---

## Status Legende

| Status | Bedeutung |
|--------|-----------|
| ✅ Akzeptiert | Entschieden, wird implementiert |
| 📋 Proposed | Ausgearbeitet, wartet auf Review |
| 🚧 Draft | In Arbeit |

---

## Übersicht

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
| 008 | [Spec Schema](008-implementation-spec-schema.md) | ✅ | YAML Schema, Validation |
| 009 | [Bootstrap Project](009-bootstrap-project.md) | 📋 | HELIX v4 baut sich selbst |
| 010 | [ADR Migration](010-adr-migration-from-v3.md) | 📋 | v3 → v4 Migration Guide |

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
│   │   • Generiert CLAUDE.md aus Templates (ADR-001)           │    │
│   │   • Führt Phasen sequentiell aus                          │    │
│   │   • Prüft Quality Gates (ADR-002)                         │    │
│   │   • Handled Escalation (ADR-004)                          │    │
│   │   • Multi-Provider LLM (ADR-007)                          │    │
│   └───────────────────────────────┬───────────────────────────┘    │
│                                   │                                 │
│           ┌───────────────────────┼───────────────────────┐        │
│           │                       │                       │        │
│           ▼                       ▼                       ▼        │
│   ┌─────────────┐         ┌─────────────┐         ┌─────────────┐  │
│   │  PHASE 1    │   QG1   │  PHASE 2    │   QG2   │  PHASE 3    │  │
│   │ Consultant  │ ──────▶ │  Developer  │ ──────▶ │  Reviewer   │  │
│   │             │         │             │         │             │  │
│   │ Meta + Exp. │         │ CLAUDE.md   │         │ CLAUDE.md   │  │
│   │ (ADR-005)   │         │ Templates   │         │ Templates   │  │
│   └──────┬──────┘         └──────┬──────┘         └──────┬──────┘  │
│          │                       │                       │         │
│          │                       │                       │         │
│   ┌──────▼──────┐         ┌──────▼──────┐         ┌──────▼──────┐  │
│   │ Claude Code │         │ Claude Code │         │ Claude Code │  │
│   │    CLI      │         │    CLI      │         │    CLI      │  │
│   └──────┬──────┘         └──────┬──────┘         └──────┬──────┘  │
│          │                       │                       │         │
│          ▼                       ▼                       ▼         │
│      spec.yaml              src/*.py               review.json     │
│      phases.yaml           (Code)                (Structured)      │
│      quality-gates.yaml                                            │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                         LOGGING (ADR-003)                           │
│   Phase-Logs → Projekt-Logs → System-Logs                           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Kernkonzepte

### 1. Claude Code macht das Agent-Harness

```
WIR machen:                    CLAUDE CODE macht:
─────────────                  ──────────────────
• Verzeichnisse vorbereiten    • Agent Loop
• CLAUDE.md generieren         • Tool Calling
• Skills verlinken             • Error Handling
• Quality Gates prüfen         • ReAct/CoT
• Orchestrierung               • File Operations
```

### 2. Kommunikation über Dateien

```
Consultant ──▶ spec.yaml ──▶ Developer ──▶ src/*.py ──▶ Reviewer
              phases.yaml
```

### 3. 2-Stufen Escalation (ADR-004)

```
3x Retry Fail
     │
     ▼
STUFE 1: Consultant-Autonom (KEIN HIL)
• Model wechseln
• Plan reverten
• Hints geben
     │
     ▼ (3x Fail)
STUFE 2: Human-in-the-Loop
• User entscheidet
```

### 4. Dynamische Phasen (ADR-006)

Der Consultant definiert den Workflow:
- Feature: Consultant → Dev → Review → Docs
- Doku-Only: Consultant → Writer → Review
- Research: Consultant → Researcher → Summary

---

## Quick Start

```bash
# 1. Repository klonen / wechseln
cd /home/aiuser01/helix-v4

# 2. Dependencies installieren
pip install -e ".[dev]"

# 3. .env von v3 migrieren
cp /home/aiuser01/helix-v3/.env .env

# 4. Projekt erstellen
helix new external/my-feature

# 5. Projekt ausführen
helix run external/my-feature
```

---

## Geplante ADRs

| Nr | Titel | Beschreibung |
|----|-------|--------------|
| 011 | Open WebUI Integration | UI-Anbindung |
| 012 | Skills Library | Skill-Katalog und Verwaltung |
| 013 | Project State Machine | Detailliertes State-Management |

---

## Obsolete v3 Konzepte

Diese v3 ADRs sind durch die neue Architektur ersetzt:

| v3 ADR | Titel | Ersetzt durch |
|--------|-------|---------------|
| 002, 008, 070 | LangGraph Orchestration | Python async |
| 003, 082, 083 | EventBus | Datei-Kommunikation |
| 046, 048, 051 | Tool Calling | Claude Code CLI |
| 039, 115 | Error Handling | Claude Code |
| 111 | Prompt Tooling | Templates |

Vollständige Analyse: [ADR-010](010-adr-migration-from-v3.md)

---

## Statistiken

| Metrik | Wert |
|--------|------|
| Total ADRs | 11 |
| Akzeptiert | 8 |
| Proposed | 3 |
| Zeilen Dokumentation | ~5000 |

---

*Erstellt: 2025-12-21*  
*Letzte Aktualisierung: 2025-12-21*
