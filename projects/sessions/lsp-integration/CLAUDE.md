# Consultant Session: LSP Integration für HELIX

Du entwirfst die Integration des Language Server Protocol (LSP) in HELIX v4.

## Kontext

Claude Code CLI unterstützt seit neuestem LSP. Das ermöglicht:
- Semantische Code-Navigation
- Symbol-Suche ohne genaue Zeilen/Spalten zu kennen
- Call-Graph Analyse
- Weniger Syntax-Errors durch besseres Code-Verständnis

## Die Vision

```
┌─────────────────────────────────────────────────────────────┐
│                      HELIX v4 Orchestrator                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Agent 1     │  │ Agent 2     │  │ Agent 3     │         │
│  │ (Claude CC) │  │ (Claude CC) │  │ (Claude CC) │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                 │
│         └────────────────┼────────────────┘                 │
│                          │                                  │
│                    ┌─────▼─────┐                            │
│                    │  cclsp    │  ← Shared MCP Server       │
│                    │  (MCP)    │                            │
│                    └─────┬─────┘                            │
│                          │                                  │
│         ┌────────────────┼────────────────┐                 │
│         │                │                │                 │
│    ┌────▼────┐     ┌─────▼────┐    ┌─────▼────┐            │
│    │ pylsp   │     │ tsserver │    │ gopls    │            │
│    │ (Python)│     │ (TS/JS)  │    │ (Go)     │            │
│    └─────────┘     └──────────┘    └──────────┘            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Zwei Ansätze zu analysieren

### Ansatz A: LSP Navigator Skill

```markdown
# skills/lsp/SKILL.md

## Purpose
Semantische Code-Navigation für Anti-Halluzination

## Tools (via Bash)
- find_symbol(name, kind) → Findet Symbol ohne Zeile/Spalte zu kennen
- verify_exists(function_name, file) → Boolean ob Funktion existiert
- get_call_graph(function_name) → Wer ruft diese Funktion auf?
- get_references(symbol) → Wo wird dieses Symbol verwendet?

## Implementation
Python-Script das LSP-Queries abstrahiert
```

### Ansatz B: MCP Server als Wrapper (cclsp)

```
Agent: "Finde die Definition von processRequest"
       ↓
cclsp MCP: find_definition(symbol_name="processRequest", symbol_kind="function")
       ↓
LSP:   textDocument/definition für alle Matches
       ↓
Ergebnis: "src/handlers/request.ts:127:1"
```

## Deine Aufgaben

### 1. Analyse: Skill vs. MCP Server

| Kriterium | Skill (Bash) | MCP Server |
|-----------|--------------|------------|
| Setup-Aufwand | ? | ? |
| Multi-Agent Sharing | ? | ? |
| Performance | ? | ? |
| Wartbarkeit | ? | ? |

### 2. Use Cases für HELIX

Welche konkreten Probleme löst LSP in HELIX?
- Weniger Syntax-Errors?
- Bessere Refactoring?
- Code-Verifikation vor Commit?
- Anti-Halluzination (Symbol existiert wirklich)?

### 3. Implementation Design

Für die empfohlene Variante:
- Welche LSP Server brauchen wir? (pylsp, tsserver, ...)
- Wie wird der MCP Server/Skill strukturiert?
- Wie integriert es sich in phases.yaml?
- Wie konfiguriert Claude Code CLI die MCP Connection?

### 4. ADR Entwurf

Skizziere ADR-018: LSP Integration
- Problem
- Entscheidung
- Implementation outline
- Akzeptanzkriterien

## Relevante Dateien

Lies für Kontext:
- `input/ADR-017.md` - Phase Orchestrator (wie Agents gespawnt werden)
- `input/ARCHITECTURE-ORCHESTRATOR-FULL.md` - Multi-Agent Vision
- `input/ADR-013.md` - Debug System (ähnliches Pattern)

## Output

Schreibe nach `output/LSP-INTEGRATION-DESIGN.md`:
1. Skill vs. MCP Server Analyse
2. Use Cases für HELIX
3. Empfohlene Architektur
4. ADR-018 Entwurf
5. Roadmap (was zuerst implementieren?)
