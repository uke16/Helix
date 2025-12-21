# ADR-010: ADR Migration von HELIX v3

**Status:** Proposed  
**Datum:** 2025-12-21  
**Bezug:** Alle v3 ADRs

---

## Kontext

HELIX v3 hat 126 ADRs. Viele sind durch die neue Architektur obsolet, 
einige müssen migriert werden, wenige können 1:1 übernommen werden.

---

## Entscheidung

### Migrations-Kategorien

```
┌─────────────────────────────────────────────────────────────────┐
│                    ADR MIGRATION                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  OBSOLET ─────────────────────────────────────────────────────  │
│  Konzept wird durch Claude Code / neue Architektur ersetzt      │
│  → Nicht migrieren, Referenz in v4 INDEX                        │
│                                                                  │
│  MIGRIEREN ───────────────────────────────────────────────────  │
│  Konzept ist relevant, Implementation ändert sich               │
│  → Neues v4 ADR mit angepasstem Inhalt                          │
│                                                                  │
│  ÜBERNEHMEN ──────────────────────────────────────────────────  │
│  Konzept ist 1:1 relevant                                       │
│  → Kopieren mit minimalen Anpassungen                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Vorläufige Kategorisierung

#### OBSOLET (Claude Code ersetzt)

| v3 ADR | Titel | Warum obsolet |
|--------|-------|---------------|
| 002 | Dynamic Orchestration | Python async ersetzt LangGraph |
| 003 | Event Bus System | Datei-basierte Kommunikation |
| 008 | Multi-Graph Orchestrierung | Einfache Phasen-Sequenz |
| 039 | LLM Error Handling | Claude Code macht das |
| 046 | Tool Calling Architecture | Claude Code macht das |
| 048 | ReAct Prompts | Claude Code macht das |
| 051 | think Tool | Claude Code macht das |
| 070 | Meta-Planner | phases.yaml ersetzt das |
| 082 | Agent Communication Events | Datei-basiert jetzt |
| 083 | Event-Driven Agent Sync | Nicht mehr nötig |
| 111 | Developer Prompt Tooling | Templates ersetzen das |
| 115 | Tool Execution Error Resilience | Claude Code macht das |
| 118 | File Tool Consolidation | Claude Code Tools |
| 110 | File Tools Erweiterung | Claude Code Tools |
| 127 | FileWrite Tool Wrapper | Claude Code Tools |

#### MIGRIEREN (Konzept relevant, Implementation neu)

| v3 ADR | Titel | v4 ADR | Änderungen |
|--------|-------|--------|------------|
| 021 | Model Selection | 007 | OpenRouter + Multi-Provider Config |
| 023 | Multi-Provider | 007 | Teil von LLM Config |
| 040a | Prometheus Metrics | 003 | Integriert in Observability |
| 047 | Agent Meeting System | 005 | Consultant Topologie |
| 052 | HELIX Self-Knowledge | - | Skills/Domain-Docs |
| 067 | Pre-loaded Context | 001 | Template & Context System |
| 071 | Deterministic Documentation | 006 | Teil von phases.yaml |
| 084 | Bugfix Record System | - | Final Review Output |
| 094 | Validator System | 002 | Quality Gates |
| 095 | Gate Validators | 002 | Quality Gates |
| 119 | Multi-Domain Consultant | 005 | Consultant Topologie |

#### ÜBERNEHMEN (1:1 relevant)

| v3 ADR | Titel | v4 ADR | Anmerkung |
|--------|-------|--------|-----------|
| 043 | Open WebUI Integration | 011 (geplant) | UI Layer bleibt |
| 086 | ADR Template v2 | - | Format übernehmen |
| 124 | Conversation Export | - | Logging |

### Migration-Prompt für neue Chats

```markdown
# ADR Migration: HELIX v3 → v4

Du analysierst ADRs von HELIX v3 und entscheidest über die Migration nach v4.

## HELIX v4 Architektur-Kontext

HELIX v4 hat eine fundamental neue Architektur:

### Was neu ist:
- **Claude Code CLI** als Agent Runtime (statt eigene LangGraph-Agents)
- **CLAUDE.md** für Context-Loading (statt SDK/Gateway)
- **Datei-basierte Kommunikation** zwischen Phasen (JSON/YAML)
- **Python Orchestrator** (async, kein LangGraph StateGraph)
- **Dynamische Phasen** via phases.yaml (Consultant definiert Workflow)
- **2-Stufen Escalation** (Stufe 1: Consultant-autonom, Stufe 2: HIL)
- **Template-System** (Jinja2) für CLAUDE.md Generierung
- **Multi-Provider LLM** via OpenRouter + direkte APIs

### Was bleibt:
- Meeting System (Consultant + User + Domain-Experten)
- Domain Knowledge (PDM, ERP Skills)
- Quality Gates (jetzt Python statt LangGraph)
- 4-Level Documentation
- Lessons Learned / Bugfix Records
- Open WebUI Integration (geplant)

## v3 ADR Verzeichnis
`/home/aiuser01/helix-v3/adr/`

## v4 ADR Verzeichnis
`/home/aiuser01/helix-v4/adr/`

## Deine Aufgabe

Für jedes v3 ADR das ich dir zeige:

1. **Lies das ADR komplett**
2. **Entscheide die Kategorie:**
   - **OBSOLET**: Konzept durch v4 Architektur ersetzt
   - **MIGRIEREN**: Konzept relevant, Implementation neu
   - **ÜBERNEHMEN**: 1:1 kopierbar

3. **Dokumentiere:**

```yaml
migration_decision:
  v3_adr_number: "XXX"
  v3_adr_title: "..."
  category: "OBSOLET" | "MIGRIEREN" | "ÜBERNEHMEN"
  
  # Falls OBSOLET:
  obsolete_reason: "Claude Code ersetzt dies weil..."
  replaced_by_v4_adr: "000" | null
  
  # Falls MIGRIEREN:
  v4_adr_number: "0XX"  # Vorschlag
  key_changes:
    - "Änderung 1"
    - "Änderung 2"
  migration_notes: "..."
  
  # Falls ÜBERNEHMEN:
  v4_adr_number: "0XX"  # Vorschlag
  minor_adjustments:
    - "Pfade anpassen"
    - "Referenzen aktualisieren"
```

4. **Falls MIGRIEREN oder ÜBERNEHMEN:**
   Schreibe das v4 ADR mit angepasstem Inhalt.

## Wichtige v4 ADRs als Referenz

- ADR-000: Vision & Architecture (Grundkonzept)
- ADR-001: Template & Context System
- ADR-002: Quality Gate System
- ADR-003: Observability & Debugging
- ADR-004: Escalation Meeting System
- ADR-005: Consultant Topologie
- ADR-006: Dynamic Phase Definition
- ADR-007: Multi-Provider LLM
- ADR-008: Spec Schema
- ADR-009: Bootstrap Project

## Start

Welches v3 ADR soll ich analysieren? 
Gib mir die ADR-Nummer oder sage "nächstes" für sequentielle Analyse.
```

---

## Durchführung der Migration

### Schritt 1: Batch-Analyse

1. Neuen Claude Chat starten mit obigem Prompt
2. v3 ADR Index laden: `/home/aiuser01/helix-v3/adr/000-adr-index.md`
3. Alle ADRs kategorisieren lassen
4. Ergebnis in `docs/v3-migration-analysis.md` speichern

### Schritt 2: Migration durchführen

Für jedes MIGRIEREN/ÜBERNEHMEN ADR:
1. Neues v4 ADR erstellen
2. Referenzen aktualisieren
3. In v4 INDEX aufnehmen

### Schritt 3: Obsolete dokumentieren

In v4 INDEX einen Abschnitt "Obsolete v3 ADRs" mit Begründungen.

---

## Prioritäten

### Sofort (für Bootstrap benötigt)
- ADR-043: Open WebUI Integration
- ADR-086: ADR Template v2

### Nach Bootstrap
- Alle anderen MIGRIEREN ADRs

### Optional
- ÜBERNEHMEN ADRs nach Bedarf

---

## Konsequenzen

### Positiv
- Klare Dokumentation was übernommen wurde
- Keine verlorenen Konzepte
- v3 Wissen bleibt erhalten

### Negativ
- Aufwand für Migration
- Manche Details gehen verloren

---

## Referenzen

- HELIX v3 ADR Index
- HELIX v4 ADRs 000-009

