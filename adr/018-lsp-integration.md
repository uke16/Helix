---
adr_id: "018"
title: "LSP Integration für Code-Intelligence"
status: Proposed
date: 2024-12-24

project_type: helix_internal
component_type: ENHANCEMENT
classification: NEW
change_scope: minor

domain: helix
language: python
skills:
  - helix

files:
  create:
    - skills/lsp/SKILL.md
    - docs/LSP-INTEGRATION.md
  modify:
    - src/helix/orchestrator/phase_executor.py
    - config/orchestrator.yaml
    - docs/sources/tools.yaml
  docs:
    - skills/helix/SKILL.md

depends_on:
  - "017"  # Phase Orchestrator

related_to:
  - "013"  # Debug & Observability
---

# ADR-018: LSP Integration für Code-Intelligence

## Status

Proposed

---

## Kontext

### Was ist das Problem?

Claude Code Agents in HELIX arbeiten "blind" ohne IDE-typische Code-Intelligence:
- Keine Verifikation ob referenzierte Funktionen existieren
- Keine Echtzeit-Syntax-Fehler-Erkennung
- Refactorings ohne Kenntnis aller Referenzen

### Warum jetzt?

**Claude Code hat seit 20. Dezember 2024 native LSP-Unterstützung!**

Das Feature ist brandneu (4 Tage alt) und macht die Integration trivial:
- `ENABLE_LSP_TOOL=1` aktiviert das LSP Tool
- Offizielle Plugin-Marketplace mit LSP Plugins
- Automatische Diagnostics (Echtzeit-Errors)

### Was hat sich gegenüber der ursprünglichen Analyse geändert?

Der Consultant-Report vom 24.12.2024 basierte auf älteren Informationen.
Die tatsächliche Integration ist **viel einfacher** als angenommen:

| Ursprüngliche Annahme | Realität |
|-----------------------|----------|
| Eigener LSP Plugin Manager | Nicht nötig - Claude Code hat Plugin-System |
| PhaseExecutor LSP Integration | Nur `ENABLE_LSP_TOOL=1` Environment Variable |
| cclsp als Primär-Lösung | Nur für Multi-Agent relevant (MaxVP) |
| ~1 Woche Implementation | ~2 Stunden für MVP |

---

## Entscheidung

### Wir entscheiden uns für:

**Minimale Integration** - Nutze die native Claude Code LSP-Unterstützung:

1. **`ENABLE_LSP_TOOL=1`** in PhaseExecutor setzen
2. **LSP Plugins** als Voraussetzung dokumentieren
3. **LSP Diagnostics Gate** als optionales Quality Gate

### Das ist alles was wir implementieren müssen:

```python
# src/helix/orchestrator/phase_executor.py

async def execute(self, phase_dir: Path, phase_config: PhaseConfig) -> PhaseResult:
    env = os.environ.copy()
    
    # LSP aktivieren für alle Development-Phasen
    if phase_config.type in ("development", "review", "integration"):
        env["ENABLE_LSP_TOOL"] = "1"
    
    # Claude Code CLI starten
    result = await self._run_claude(phase_dir, env)
    return result
```

---

## Native LSP Features (bereits in Claude Code)

### LSP Tool Operations

Claude Code bietet 5 LSP Operations:

| Operation | Beschreibung | Use Case |
|-----------|--------------|----------|
| `goToDefinition` | Springt zur Symbol-Definition | "Wo ist diese Funktion definiert?" |
| `findReferences` | Findet alle Verwendungen | "Wer nutzt diese Klasse?" |
| `hover` | Zeigt Dokumentation + Typen | "Was macht diese Methode?" |
| `documentSymbol` | Listet Symbole in Datei | "Was ist in dieser Datei?" |
| `workspaceSymbol` | Sucht Symbole im Projekt | "Finde alle *Handler Klassen" |

### Automatische Diagnostics

- Echtzeit-Fehler und Warnings
- Erscheinen automatisch nach jedem Edit
- Schneller als manuelle Syntax-Checks

### Verfügbare LSP Plugins

```bash
# Python (empfohlen für HELIX)
/plugin install pyright@claude-code-lsps

# TypeScript/JavaScript
/plugin install vtsls@claude-code-lsps

# Go
/plugin install gopls@claude-code-lsps

# Weitere: jdtls (Java), clangd (C/C++), rust-analyzer, etc.
```

---

## Implementation

### Phase 1: MVP (2 Stunden)

#### 1. PhaseExecutor erweitern

```python
# src/helix/orchestrator/phase_executor.py

# In execute() Methode, vor Claude CLI Start:
if phase_config.lsp_enabled or phase_config.type in LSP_ENABLED_TYPES:
    env["ENABLE_LSP_TOOL"] = "1"
```

#### 2. Config erweitern

```yaml
# config/orchestrator.yaml
lsp:
  enabled: true
  enabled_phase_types:
    - development
    - review
    - integration
```

#### 3. Dokumentation

- `skills/lsp/SKILL.md` - Anleitung für Agents
- `docs/LSP-INTEGRATION.md` - Setup-Guide
- Voraussetzung: pyright Plugin installiert

### Phase 2: LSP Diagnostics Gate (Optional, 4 Stunden)

```python
# src/helix/quality_gates/lsp_diagnostics.py

class LspDiagnosticsGate:
    """Quality Gate das LSP Diagnostics prüft.
    
    Blockiert wenn Errors gefunden werden.
    """
    
    async def check(self, phase_dir: Path, config: dict) -> GateResult:
        # Diagnostics werden von Claude Code automatisch erkannt
        # Wir prüfen nur ob Claude sie gefixt hat
        
        # Option A: Claude CLI mit --check-diagnostics Flag (falls verfügbar)
        # Option B: Eigener LSP Query (komplexer)
        # Option C: Vertraue Claude's Self-Check (pragmatisch)
        
        return GateResult(passed=True, message="LSP check delegated to Claude")
```

### Phase 3: Multi-Agent mit cclsp (MaxVP, 1 Woche)

Nur relevant wenn parallele Agents denselben LSP-State brauchen:

```
Agent 1 ──┐
Agent 2 ──┼── cclsp MCP Server ── pylsp
Agent 3 ──┘
```

**Nicht im MVP-Scope.**

---

## Voraussetzungen für Nutzer

### Einmalige Setup (auf HELIX Server)

```bash
# 1. Python LSP installieren
pip install pyright

# 2. Claude Code Plugin Marketplace hinzufügen
claude /plugin marketplace add boostvolt/claude-code-lsps

# 3. Python LSP Plugin installieren
claude /plugin install pyright@claude-code-lsps
```

### Für andere Sprachen

```bash
# TypeScript
npm install -g @vtsls/language-server typescript
/plugin install vtsls@claude-code-lsps

# Go
go install golang.org/x/tools/gopls@latest
/plugin install gopls@claude-code-lsps
```

---

## Dokumentation

### Zu aktualisierende Dokumente

| Dokument | Änderung |
|----------|----------|
| `docs/sources/tools.yaml` | LSP Tool Section hinzufügen |
| `skills/helix/SKILL.md` | LSP Best Practices (via Regeneration) |
| `config/orchestrator.yaml` | LSP Konfiguration |

### Neue Dokumentation

| Dokument | Inhalt |
|----------|--------|
| `skills/lsp/SKILL.md` | Anleitung für Claude Agents |
| `docs/LSP-INTEGRATION.md` | Setup + Troubleshooting |

---

## Akzeptanzkriterien

### MVP

- [ ] `ENABLE_LSP_TOOL=1` wird für development/review/integration Phasen gesetzt
- [ ] pyright LSP Plugin ist auf HELIX Server installiert
- [ ] `skills/lsp/SKILL.md` dokumentiert LSP-Nutzung für Agents
- [ ] `docs/LSP-INTEGRATION.md` erklärt Setup
- [ ] Ein Test-Projekt nutzt erfolgreich LSP

### Nice-to-Have

- [ ] LSP Diagnostics Quality Gate
- [ ] Automatische Plugin-Installation via SessionStart Hook
- [ ] Multi-Language Support (TypeScript, Go)

### MaxVP (später)

- [ ] cclsp Integration für parallele Agents
- [ ] LSP Metrics im Debug Dashboard

---

## Konsequenzen

### Vorteile

1. **Minimaler Aufwand**: Nur ~20 Zeilen Code ändern
2. **Native Integration**: Nutzt Claude Code's eigenes Feature
3. **Echtzeit-Diagnostics**: Errors werden sofort erkannt
4. **Anti-Halluzination**: Agents können Symbole verifizieren

### Nachteile

1. **Externe Abhängigkeit**: pyright muss installiert sein
2. **Neues Feature**: Möglicherweise noch Bugs in Claude Code
3. **Kein Enforcement**: Agent muss LSP aktiv nutzen

### Risiken

| Risiko | Wahrscheinlichkeit | Mitigation |
|--------|-------------------|------------|
| pyright nicht installiert | Mittel | Klare Doku, SessionStart Hook |
| LSP Tool noch buggy | Niedrig | Graceful degradation |
| Agent ignoriert LSP | Mittel | SKILL.md Best Practices |

---

## Referenzen

- [Claude Code LSP Plugins](https://github.com/boostvolt/claude-code-lsps) - Offizieller Marketplace
- [Claude Code Plugins Reference](https://code.claude.com/docs/en/plugins-reference) - LSP Dokumentation
- [Hacker News Diskussion](https://news.ycombinator.com/item?id=46355165) - Community Feedback
- ADR-013: Debug & Observability
- ADR-017: Phase Orchestrator

---

## Changelog

- 2024-12-24: Initial draft nach Web-Recherche zu aktuellem Claude Code LSP Support
