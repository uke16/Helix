# LSP Integration Design for HELIX v4

> **Session:** lsp-integration
> **Stand:** 2024-12-24
> **Autor:** HELIX Consultant

---

## Executive Summary

Diese Analyse untersucht die Integration des Language Server Protocol (LSP) in HELIX v4. Nach Abwägung beider Ansätze empfehlen wir einen **MCP Server als Wrapper (cclsp)** - dieser ermöglicht Multi-Agent-Sharing, ist wartbarer als ein reiner Skill-Ansatz, und integriert sich nahtlos mit der in ADR-017 geplanten parallelen Phase-Ausführung.

---

## 1. Skill vs. MCP Server Analyse

### 1.1 Übersicht

| Kriterium | Skill (Bash) | MCP Server (cclsp) |
|-----------|--------------|-------------------|
| **Setup-Aufwand** | Niedrig (1-2 Tage) | Mittel (3-5 Tage) |
| **Multi-Agent Sharing** | Schwer | Native |
| **Performance** | Gut (direkte Calls) | Sehr gut (Caching, Connection Pooling) |
| **Wartbarkeit** | Mittel | Hoch |
| **State Management** | Keine | LSP Sessions persistent |
| **Error Handling** | Shell-basiert, unstrukturiert | Strukturierte JSON Responses |
| **Debugging** | Log-Analyse | Integrierte Debug-Events (ADR-013) |
| **Parallele Phasen (ADR-017)** | Problematisch | Ideal |

### 1.2 Ansatz A: LSP Navigator Skill

```
┌─────────────────────────────────────────────────────────────┐
│                     SKILL ANSATZ                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Claude Agent                                                │
│      │                                                       │
│      ├── Liest: skills/lsp/SKILL.md                         │
│      │                                                       │
│      └── Bash: python -m helix.tools.lsp find_symbol "Foo"  │
│                    │                                         │
│                    └── LSP Server (pylsp/tsserver)          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Vorteile:**
- Schnelle Implementierung
- Kein zusätzlicher Service
- Einfache Dokumentation im Skill

**Nachteile:**
- Jeder Agent startet eigene LSP-Server -> hoher Overhead
- Kein State zwischen Calls (LSP braucht Session)
- Shell-Escaping Probleme bei komplexen Symbolen
- Keine Synchronisation bei parallelen Agents (ADR-017 MaxVP)

### 1.3 Ansatz B: MCP Server (cclsp)

```
┌─────────────────────────────────────────────────────────────┐
│                     MCP SERVER ANSATZ                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                      │
│  │ Agent 1 │  │ Agent 2 │  │ Agent 3 │                      │
│  └────┬────┘  └────┬────┘  └────┬────┘                      │
│       │            │            │                            │
│       └────────────┼────────────┘                            │
│                    │                                         │
│              ┌─────▼─────┐                                   │
│              │  cclsp    │  MCP Server (Single Instance)     │
│              │           │                                   │
│              │ - Sessions│                                   │
│              │ - Caching │                                   │
│              │ - Pooling │                                   │
│              └─────┬─────┘                                   │
│                    │                                         │
│       ┌────────────┼────────────┐                            │
│       │            │            │                            │
│  ┌────▼────┐  ┌────▼────┐  ┌────▼────┐                      │
│  │  pylsp  │  │tsserver │  │  gopls  │                      │
│  │ Python  │  │  TS/JS  │  │   Go    │                      │
│  └─────────┘  └─────────┘  └─────────┘                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Vorteile:**
- Ein LSP Server pro Sprache für alle Agents
- Session-Management (indexed workspace)
- Strukturierte Responses (JSON-RPC)
- Integriert mit HELIX Debug/Observability (ADR-013)
- Future-proof für MaxVP parallele Agents (ADR-017)

**Nachteile:**
- Höherer initialer Aufwand
- Zusätzlicher Service zu verwalten
- MCP Konfiguration in Claude Code CLI

### 1.4 Vergleich mit ADR-013 Pattern

ADR-013 (Debug & Observability Engine) etabliert ein Pattern für Service-Integration:

```
Claude CLI ──stream-json──► StreamParser ──events──► Dashboard
```

Analoges Pattern für LSP:

```
Claude CLI ──MCP──► cclsp ──LSP──► Language Servers
                      │
                      └──events──► Debug Dashboard (ADR-013)
```

Vorteil: LSP-Events können in das bestehende Observability-System integriert werden.

---

## 2. Use Cases für HELIX

### 2.1 Anti-Halluzination (Primär)

**Problem:** Claude halluziniert manchmal Funktionsnamen oder APIs.

**Lösung mit LSP:**
```python
# Vor dem Schreiben von Code:
# Agent fragt: "Existiert parse_config()?"

response = cclsp.workspace_symbol("parse_config")
# -> [{"name": "parse_config", "location": "src/config.py:42"}]
# -> Bestätigt: Symbol existiert wirklich!
```

**Use Case in phases.yaml:**
```yaml
phases:
  - id: development
    type: development
    pre_check:
      - type: lsp_verify
        symbols: ["from_spec_file"]  # Muss existieren
```

### 2.2 Semantische Navigation

**Problem:** Agent findet Datei, aber nicht die richtige Stelle.

**Lösung mit LSP:**
```python
# "Wo wird OrchestratorRunner.run() definiert?"
definition = cclsp.go_to_definition("OrchestratorRunner", "run")
# -> {"file": "src/helix/orchestrator/runner.py", "line": 356}

# "Wer ruft diese Methode auf?"
references = cclsp.find_references("OrchestratorRunner", "run")
# -> [{"file": "src/helix/cli/project.py", "line": 978}, ...]
```

### 2.3 Refactoring Support

**Problem:** Umbenennung erzeugt inkonsistenten Code.

**Lösung mit LSP:**
```python
# "Benenne run_phase() zu execute_phase() um"
references = cclsp.find_references("PhaseExecutor", "run_phase")
# -> Alle 15 Stellen wo run_phase verwendet wird

# Agent kann jetzt systematisch alle Stellen ändern
```

### 2.4 Code-Verifikation vor Commit

**Integration mit Quality Gates (ADR-017 Pattern):**
```yaml
# phases.yaml
phases:
  - id: development
    quality_gate:
      type: compound
      gates:
        - syntax_check
        - lsp_diagnostics  # NEU: LSP-basierte Prüfung
        - tests_pass
```

```python
# Quality Gate: lsp_diagnostics
diagnostics = cclsp.get_diagnostics("output/src/**/*.py")
# -> [{"severity": "error", "message": "undefined name 'foo'", ...}]

if any(d.severity == "error" for d in diagnostics):
    return GateResult(passed=False, message="LSP errors found")
```

### 2.5 Call-Graph für Impact Analysis

**Problem:** Änderung hat unbeabsichtigte Seiteneffekte.

**Lösung:**
```python
# "Was passiert wenn ich QualityGateRunner.run_gate() ändere?"
callers = cclsp.get_incoming_calls("QualityGateRunner", "run_gate")
# -> Shows all callers in call hierarchy

# Agent kann Impact einschätzen bevor er ändert
```

### 2.6 Integration mit Debug Dashboard (ADR-013)

LSP-Events können in das bestehende Observability-System fließen:

```python
# src/helix/debug/events.py (erweitert)
class DebugEventType(Enum):
    # ... existing ...
    LSP_SYMBOL_LOOKUP = "lsp_symbol_lookup"
    LSP_REFERENCE_SEARCH = "lsp_reference_search"
    LSP_DIAGNOSTICS_CHECK = "lsp_diagnostics_check"
```

---

## 3. Empfohlene Architektur

### 3.1 Entscheidung: MCP Server (cclsp)

Wir empfehlen **Ansatz B: MCP Server** aus folgenden Gründen:

1. **Multi-Agent Ready**: HELIX ADR-017 beschreibt parallele Phase-Ausführung
2. **State Management**: LSP braucht Sessions für Workspace-Index
3. **Observability**: Integration mit ADR-013 Debug Engine möglich
4. **Performance**: Caching und Connection Pooling

### 3.2 Architektur-Übersicht

```
┌─────────────────────────────────────────────────────────────────┐
│                     HELIX v4 + LSP                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    ORCHESTRATOR (ADR-017)                │    │
│  │                                                          │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐               │    │
│  │  │Phase     │  │Phase     │  │Phase     │               │    │
│  │  │Executor  │  │Executor  │  │Executor  │               │    │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘               │    │
│  │       │             │             │                      │    │
│  │       └─────────────┼─────────────┘                      │    │
│  │                     │                                    │    │
│  └─────────────────────┼────────────────────────────────────┘    │
│                        │                                         │
│  ┌─────────────────────▼────────────────────────────────────┐    │
│  │                   Claude Code CLI                         │    │
│  │                                                           │    │
│  │  MCP Config:                                              │    │
│  │  ┌─────────────────────────────────────────────────────┐ │    │
│  │  │ mcpServers:                                         │ │    │
│  │  │   cclsp:                                            │ │    │
│  │  │     command: helix-lsp-server                       │ │    │
│  │  │     args: [--workspace, /project/root]              │ │    │
│  │  └─────────────────────────────────────────────────────┘ │    │
│  │                                                           │    │
│  │  Available MCP Tools:                                     │    │
│  │  - lsp_find_symbol(name, kind?)                          │    │
│  │  - lsp_go_to_definition(file, line, char)                │    │
│  │  - lsp_find_references(file, line, char)                 │    │
│  │  - lsp_get_diagnostics(file_pattern)                     │    │
│  │  - lsp_workspace_symbol(query)                           │    │
│  │  - lsp_hover(file, line, char)                           │    │
│  │  - lsp_incoming_calls(file, line, char)                  │    │
│  │                                                           │    │
│  └─────────────────────┬─────────────────────────────────────┘    │
│                        │                                         │
│  ┌─────────────────────▼────────────────────────────────────┐    │
│  │                 cclsp MCP Server                          │    │
│  │                                                           │    │
│  │  ┌──────────────────────────────────────────────────┐    │    │
│  │  │              LSP Router                           │    │    │
│  │  │                                                   │    │    │
│  │  │  file.py -> pylsp                                 │    │    │
│  │  │  file.ts -> tsserver                              │    │    │
│  │  │  file.go -> gopls                                 │    │    │
│  │  │  file.rs -> rust-analyzer                         │    │    │
│  │  └──────────────────────────────────────────────────┘    │    │
│  │                                                           │    │
│  │  ┌──────────────────────────────────────────────────┐    │    │
│  │  │              LSP Server Pool                      │    │    │
│  │  │                                                   │    │    │
│  │  │  ┌────────┐  ┌────────┐  ┌────────┐              │    │    │
│  │  │  │ pylsp  │  │tsserver│  │ gopls  │              │    │    │
│  │  │  │(cached)│  │(cached)│  │(cached)│              │    │    │
│  │  │  └────────┘  └────────┘  └────────┘              │    │    │
│  │  └──────────────────────────────────────────────────┘    │    │
│  │                                                           │    │
│  │  ┌──────────────────────────────────────────────────┐    │    │
│  │  │         Debug Events -> ADR-013                   │    │    │
│  │  │                                                   │    │    │
│  │  │  LSP operations emit events to Debug Dashboard    │    │    │
│  │  └──────────────────────────────────────────────────┘    │    │
│  │                                                           │    │
│  └───────────────────────────────────────────────────────────┘    │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 3.3 Komponenten

#### 3.3.1 cclsp MCP Server

```python
# src/helix/lsp/mcp_server.py

"""MCP Server wrapper for LSP operations.

Provides Claude Code CLI with semantic code navigation via MCP protocol.
"""

from mcp import MCPServer, Tool
from .lsp_pool import LSPServerPool
from .router import LanguageRouter


class HelixLSPServer(MCPServer):
    """MCP Server exposing LSP functionality to Claude agents."""

    def __init__(self, workspace: Path):
        super().__init__()
        self.workspace = workspace
        self.router = LanguageRouter()
        self.pool = LSPServerPool()

    def get_tools(self) -> list[Tool]:
        """Return available MCP tools."""
        return [
            Tool(
                name="lsp_find_symbol",
                description="Find a symbol by name in the workspace",
                input_schema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Symbol name"},
                        "kind": {"type": "string", "enum": ["function", "class", "variable", "method"]},
                    },
                    "required": ["name"],
                },
            ),
            Tool(
                name="lsp_go_to_definition",
                description="Find where a symbol is defined",
                input_schema={...},
            ),
            Tool(
                name="lsp_find_references",
                description="Find all references to a symbol",
                input_schema={...},
            ),
            Tool(
                name="lsp_get_diagnostics",
                description="Get LSP diagnostics (errors, warnings) for files",
                input_schema={...},
            ),
            Tool(
                name="lsp_workspace_symbol",
                description="Search for symbols across workspace",
                input_schema={...},
            ),
            Tool(
                name="lsp_hover",
                description="Get hover information (type, docs) for a position",
                input_schema={...},
            ),
            Tool(
                name="lsp_incoming_calls",
                description="Find all callers of a function/method",
                input_schema={...},
            ),
        ]

    async def handle_tool(self, name: str, arguments: dict) -> Any:
        """Handle MCP tool call."""
        # Emit debug event (ADR-013 integration)
        await self._emit_debug_event(name, arguments)

        if name == "lsp_find_symbol":
            return await self._find_symbol(arguments["name"], arguments.get("kind"))
        elif name == "lsp_go_to_definition":
            return await self._go_to_definition(...)
        # ... other handlers
```

#### 3.3.2 LSP Server Pool

```python
# src/helix/lsp/lsp_pool.py

"""Pool of LSP servers with caching and lifecycle management."""

from dataclasses import dataclass
import asyncio


@dataclass
class LSPServerConfig:
    """Configuration for an LSP server."""
    language: str
    command: list[str]
    file_extensions: list[str]
    initialization_options: dict | None = None


# Default configurations
DEFAULT_LSP_CONFIGS = {
    "python": LSPServerConfig(
        language="python",
        command=["pylsp"],
        file_extensions=[".py", ".pyi"],
        initialization_options={"pylsp": {"plugins": {"pyflakes": {"enabled": True}}}},
    ),
    "typescript": LSPServerConfig(
        language="typescript",
        command=["typescript-language-server", "--stdio"],
        file_extensions=[".ts", ".tsx", ".js", ".jsx"],
    ),
    "go": LSPServerConfig(
        language="go",
        command=["gopls"],
        file_extensions=[".go"],
    ),
}


class LSPServerPool:
    """Manages a pool of LSP server instances.

    Features:
    - Lazy initialization (start server on first use)
    - Connection pooling (reuse servers across requests)
    - Health checking (restart crashed servers)
    - Graceful shutdown
    """

    def __init__(self, configs: dict[str, LSPServerConfig] | None = None):
        self.configs = configs or DEFAULT_LSP_CONFIGS
        self._servers: dict[str, LSPClient] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def get_server(self, language: str) -> LSPClient:
        """Get or create an LSP server for the language."""
        if language not in self._locks:
            self._locks[language] = asyncio.Lock()

        async with self._locks[language]:
            if language not in self._servers:
                config = self.configs.get(language)
                if not config:
                    raise ValueError(f"No LSP config for language: {language}")

                self._servers[language] = await self._start_server(config)

            return self._servers[language]

    async def shutdown(self):
        """Shutdown all LSP servers."""
        for server in self._servers.values():
            await server.shutdown()
        self._servers.clear()
```

#### 3.3.3 Integration mit PhaseExecutor (ADR-017)

```python
# src/helix/orchestrator/phase_executor.py (erweitert)

class PhaseExecutor:
    """Executes individual phases with optional LSP support."""

    def __init__(
        self,
        claude_runner: ClaudeRunner | None = None,
        gate_runner: QualityGateRunner | None = None,
        lsp_manager: LSPManager | None = None,  # NEU
    ) -> None:
        self.claude = claude_runner or ClaudeRunner()
        self.gates = gate_runner or QualityGateRunner()
        self.lsp = lsp_manager  # Optional LSP Manager

    async def execute(
        self,
        phase_dir: Path,
        phase_config: PhaseConfig,
        timeout: int = 600,
        dry_run: bool = False,
    ) -> PhaseResult:
        """Execute a single phase."""

        # Prepare MCP config if LSP enabled
        mcp_config = None
        if self.lsp and phase_config.lsp_enabled:
            mcp_config = self.lsp.get_mcp_config()

        # Run Claude Code CLI with MCP
        result = await self.claude.run_phase(
            phase_dir=phase_dir,
            mcp_config=mcp_config,
            ...
        )

        return result
```

### 3.4 MCP Configuration in Claude Code CLI

```yaml
# ~/.claude/mcp_servers.yaml (oder in HELIX config)

mcpServers:
  helix-lsp:
    command: python
    args:
      - -m
      - helix.lsp.mcp_server
      - --workspace
      - ${HELIX_PROJECT_ROOT}
    env:
      HELIX_LSP_DEBUG: "true"
```

### 3.5 Quality Gate: lsp_diagnostics

```python
# src/helix/quality_gates/lsp_diagnostics.py

"""LSP Diagnostics Quality Gate for HELIX v4.

Checks for LSP errors before completing a development phase.
"""

from pathlib import Path
from typing import Any

from .base import QualityGate, GateResult


class LspDiagnosticsGate(QualityGate):
    """Check LSP diagnostics before phase completion.

    Usage in phases.yaml:
        quality_gate:
          type: lsp_diagnostics
          severity_threshold: error
          file_pattern: "output/src/**/*.py"
    """

    async def check(
        self,
        phase_dir: Path,
        config: dict[str, Any],
    ) -> GateResult:
        """Run LSP diagnostics check."""

        severity_threshold = config.get("severity_threshold", "error")
        file_pattern = config.get("file_pattern", "output/**/*")

        # Get diagnostics via LSP
        diagnostics = await self._get_diagnostics(phase_dir, file_pattern)

        # Filter by severity
        blocking = [
            d for d in diagnostics
            if self._severity_level(d["severity"]) >= self._severity_level(severity_threshold)
        ]

        if blocking:
            return GateResult(
                passed=False,
                message=f"LSP found {len(blocking)} errors",
                details=blocking[:10],  # Limit output
            )

        return GateResult(
            passed=True,
            message=f"LSP diagnostics passed",
        )

    def _severity_level(self, severity: str) -> int:
        """Convert severity to numeric level for comparison."""
        levels = {"error": 3, "warning": 2, "info": 1, "hint": 0}
        return levels.get(severity, 0)
```

---

## 4. ADR-018 Entwurf

```yaml
---
adr_id: "018"
title: "LSP Integration via MCP Server"
status: Proposed

project_type: helix_internal
component_type: SERVICE
classification: NEW
change_scope: major

domain: helix
language: python
skills:
  - helix
  - lsp

files:
  create:
    - src/helix/lsp/__init__.py
    - src/helix/lsp/mcp_server.py
    - src/helix/lsp/lsp_pool.py
    - src/helix/lsp/lsp_client.py
    - src/helix/lsp/router.py
    - src/helix/lsp/symbol_cache.py
    - src/helix/quality_gates/lsp_diagnostics.py
    - tests/lsp/test_mcp_server.py
    - tests/lsp/test_lsp_pool.py
    - config/lsp-servers.yaml
    - skills/lsp/SKILL.md
  modify:
    - src/helix/orchestrator/phase_executor.py
    - src/helix/quality_gates/__init__.py
    - config/phase-types.yaml
  docs:
    - docs/LSP-INTEGRATION.md
    - CLAUDE.md
    - skills/helix/SKILL.md

depends_on:
  - "013"  # Debug & Observability (für Logging)
  - "017"  # Phase Orchestrator (für Integration)

related_to:
  - "002"  # Quality Gates
---

# ADR-018: LSP Integration via MCP Server

## Status

Proposed

---

## Kontext

### Was ist das Problem?

Claude Code Instanzen in HELIX haben **keine semantische Code-Navigation**:

1. **Symbol-Suche ohne Kontext**: `grep` findet Strings, nicht Definitionen
2. **Halluzination**: Agent glaubt Symbol existiert, obwohl es nicht so heisst
3. **Manuelles Refactoring**: Umbenennung erfordert manuelles Suchen
4. **Kein Call-Graph**: Impact von Aenderungen ist unklar

### Claude Code CLI unterstuetzt LSP

Seit kurzem hat Claude Code CLI native LSP-Unterstuetzung:
- `goToDefinition`
- `findReferences`
- `hover`
- `documentSymbol`
- `workspaceSymbol`
- `incomingCalls`
- `outgoingCalls`

### Warum muss es geloest werden?

1. **Anti-Halluzination**: Verifiziere dass Symbol existiert bevor du es verwendest
2. **Besseres Refactoring**: Finde alle Referenzen systematisch
3. **Impact Analysis**: Verstehe Call-Graph bevor du aenderst
4. **Quality Gates**: LSP-basierte Diagnostics vor Commit

---

## Entscheidung

### Wir entscheiden uns fuer:

Ein **MCP Server (cclsp)** als Wrapper um LSP Server mit:
- Connection Pooling fuer LSP Server
- Symbol Caching fuer haeufige Queries
- Multi-Agent Sharing (ein Server fuer alle Agents)
- Integration mit HELIX Quality Gates
- Debug-Events fuer ADR-013 Dashboard

### Diese Entscheidung beinhaltet:

1. **MCP Server**: `helix-lsp-server` als MCP-konfigurierbarer Service
2. **LSP Server Pool**: Lazy-initialized LSP servers (pylsp, tsserver, gopls)
3. **Symbol Cache**: Workspace-Index fuer schnelle Lookups
4. **Quality Gate**: `lsp_diagnostics` Gate Type
5. **Skill**: `skills/lsp/SKILL.md` fuer Agents
6. **Debug Integration**: LSP-Events fuer ADR-013 Dashboard

### Warum MCP Server statt Skill?

| Kriterium | Skill | MCP Server |
|-----------|-------|------------|
| Multi-Agent | Jeder startet eigenen LSP | Shared Server |
| State | Keine Sessions | Persistent Index |
| Performance | Cold Start bei jedem Call | Warm Cache |
| Integration | Shell-Escaping Probleme | Strukturiertes JSON |
| ADR-017 Parallel | Problematisch | Native Support |

---

## Implementation

### 1. Modul-Struktur

```
src/helix/
├── lsp/                          # NEU: LSP Integration
│   ├── __init__.py
│   ├── mcp_server.py             # MCP Server Entry Point
│   ├── lsp_pool.py               # LSP Server Pool
│   ├── lsp_client.py             # LSP Client (JSON-RPC)
│   ├── router.py                 # Language Router
│   └── symbol_cache.py           # Symbol Caching
│
├── quality_gates/
│   └── lsp_diagnostics.py        # NEU: LSP Gate
│
└── tools/
    └── lsp_verify.py             # CLI Tool fuer Verification
```

### 2. MCP Tools

| Tool | Beschreibung | Verwendung |
|------|--------------|------------|
| `lsp_find_symbol` | Findet Symbol by Name | Anti-Halluzination |
| `lsp_go_to_definition` | Definition finden | Navigation |
| `lsp_find_references` | Alle Referenzen | Refactoring |
| `lsp_get_diagnostics` | Errors/Warnings | Quality Gate |
| `lsp_workspace_symbol` | Suche im Workspace | Exploration |
| `lsp_hover` | Type/Doc Info | Verstaendnis |
| `lsp_incoming_calls` | Wer ruft Funktion? | Impact Analysis |

### 3. Quality Gate: lsp_diagnostics

```yaml
# phases.yaml
quality_gate:
  type: lsp_diagnostics
  severity_threshold: error  # error, warning, info
  file_pattern: "output/src/**/*.py"
```

### 4. Konfiguration

```yaml
# config/lsp-servers.yaml
servers:
  python:
    command: [pylsp]
    extensions: [.py, .pyi]

  typescript:
    command: [typescript-language-server, --stdio]
    extensions: [.ts, .tsx, .js, .jsx]

  go:
    command: [gopls]
    extensions: [.go]
```

---

## Dokumentation

### Zu aktualisierende Dokumente

| Dokument | Aenderung |
|----------|----------|
| `docs/LSP-INTEGRATION.md` | Neue Datei - Vollstaendige Doku |
| `skills/lsp/SKILL.md` | Neuer Skill fuer Agents |
| `CLAUDE.md` | MCP Server Configuration |
| `docs/ARCHITECTURE-MODULES.md` | LSP Modul |
| `config/phase-types.yaml` | lsp_diagnostics Gate |

---

## Akzeptanzkriterien

### 1. MCP Server

- [ ] `helix-lsp-server` startet als MCP Server
- [ ] Alle 7 Tools sind verfuegbar
- [ ] Multi-Agent Requests werden korrekt geroutet
- [ ] Graceful Shutdown funktioniert

### 2. LSP Server Pool

- [ ] pylsp startet bei erstem Python-Request
- [ ] Server bleiben warm zwischen Requests
- [ ] Crashed Server werden automatisch neu gestartet
- [ ] Memory-Limit wird eingehalten

### 3. Quality Gate

- [ ] `lsp_diagnostics` Gate Type registriert
- [ ] Gate blockiert bei LSP Errors
- [ ] Gate passiert bei Warnings (konfigurierbar)
- [ ] Diagnostics werden in Output geloggt

### 4. Integration

- [ ] Claude Code CLI kann MCP Server konfigurieren
- [ ] Agents koennen LSP Tools nutzen
- [ ] Debug Events (ADR-013) fuer LSP Operations
- [ ] PhaseExecutor (ADR-017) integriert LSP
- [ ] Skill dokumentiert Nutzung

### 5. Tests

- [ ] Unit Tests fuer LSP Pool
- [ ] Unit Tests fuer MCP Server
- [ ] Integration Test mit echtem pylsp
- [ ] E2E Test: Phase mit LSP Quality Gate

---

## Konsequenzen

### Vorteile

1. **Anti-Halluzination**: Symbole werden verifiziert
2. **Bessere Code-Qualitaet**: LSP Diagnostics fangen Fehler frueh
3. **Effizientes Refactoring**: Systematische Referenz-Suche
4. **Shared Resources**: Ein LSP Server fuer alle Agents
5. **Future-Ready**: Vorbereitet fuer parallele Ausfuehrung (ADR-017)
6. **Observability**: LSP-Events im Debug Dashboard (ADR-013)

### Nachteile / Risiken

1. **Zusaetzlicher Service**: MCP Server muss laufen
2. **LSP Server Abhaengigkeiten**: pylsp, tsserver muessen installiert sein
3. **Memory Overhead**: LSP Server halten Index im Memory

### Mitigation

| Risiko | Mitigation |
|--------|------------|
| Service-Verfuegbarkeit | Health Checks, Auto-Restart |
| Dependencies | Container mit vorinstallierten LSP Servern |
| Memory | Konfigurierbare Limits, Lazy Loading |

---

## Referenzen

- ADR-013: Debug & Observability Engine
- ADR-017: Phase Orchestrator
- Claude Code CLI: LSP Documentation
- Language Server Protocol Specification
```

---

## 5. Roadmap

### Phase 1: Foundation (3-5 Tage)

```
├── src/helix/lsp/__init__.py
├── src/helix/lsp/mcp_server.py (Basic MCP Server)
├── src/helix/lsp/lsp_client.py (JSON-RPC Client)
├── tests/lsp/test_lsp_client.py
└── config/lsp-servers.yaml
```

**Deliverable:** `lsp_find_symbol` und `lsp_go_to_definition` funktionieren

### Phase 2: Server Pool (2-3 Tage)

```
├── src/helix/lsp/lsp_pool.py
├── src/helix/lsp/router.py
├── tests/lsp/test_lsp_pool.py
└── Installation: pylsp, tsserver
```

**Deliverable:** Multi-Language Support, Connection Pooling

### Phase 3: Quality Gate Integration (2-3 Tage)

```
├── src/helix/quality_gates/lsp_diagnostics.py
├── config/phase-types.yaml (Update)
├── tests/quality_gates/test_lsp_diagnostics.py
└── E2E Test mit echter Phase
```

**Deliverable:** `lsp_diagnostics` Quality Gate funktioniert

### Phase 4: Skill & Documentation (1-2 Tage)

```
├── skills/lsp/SKILL.md
├── docs/LSP-INTEGRATION.md
├── CLAUDE.md (Update)
└── Examples in skills/lsp/examples/
```

**Deliverable:** Agents koennen LSP effektiv nutzen

### Phase 5: ADR-013 Integration (Optional, 1-2 Tage)

```
├── src/helix/debug/events.py (LSP Events)
├── Debug Dashboard Updates
└── LSP Metrics im Dashboard
```

**Deliverable:** LSP-Events im Debug Dashboard sichtbar

### Phase 6: Advanced Features (Optional, 2-3 Tage)

```
├── src/helix/lsp/symbol_cache.py
├── Incoming/Outgoing Calls
├── Call Hierarchy Visualization
└── ADR-017 Parallel Phase Support
```

**Deliverable:** Symbol Caching, Call-Graph Features, Multi-Agent Support

---

## 6. Zusammenfassung

| Aspekt | Empfehlung |
|--------|------------|
| **Ansatz** | MCP Server (cclsp) |
| **Grund** | Multi-Agent, State Management, ADR-Integration |
| **Aufwand** | ~10-14 Tage (Phase 1-4) |
| **Primaerer Use Case** | Anti-Halluzination + Quality Gate |
| **Abhaengigkeiten** | ADR-013 (Debug), ADR-017 (Orchestrator) |

Die LSP-Integration macht HELIX robuster gegen Code-Halluzinationen und ermoeglicht LSP-basierte Quality Gates. Der MCP-Server-Ansatz ist die richtige Wahl fuer HELIX's Multi-Agent-Architektur und integriert sich nahtlos mit dem bestehenden Debug/Observability-System (ADR-013) sowie dem Phase Orchestrator (ADR-017).

---

*Erstellt durch HELIX Consultant*
*Session: lsp-integration*
