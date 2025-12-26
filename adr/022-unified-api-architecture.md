---
adr_id: "022"
title: "Unified API Architecture - Eine API für alles"
status: Implemented
date: 2024-12-24

project_type: helix_internal
component_type: SERVICE
classification: REFACTOR
change_scope: major

domain: helix
language: python

skills:
  - helix

files:
  create:
    - src/helix/api/orchestrator.py
    - src/helix/cli/api_client.py
    - scripts/helix
  delete:
    - src/helix/orchestrator_legacy.py
    - src/helix/orchestrator/__init__.py
    - src/helix/orchestrator/runner.py
    - src/helix/orchestrator/phase_executor.py
    - src/helix/orchestrator/data_flow.py
    - src/helix/orchestrator/status.py
  modify:
    - src/helix/api/main.py
    - src/helix/api/streaming.py
    - src/helix/cli/main.py
    - src/helix/cli/commands.py
  docs:
    - docs/sources/api.yaml
    - docs/sources/cli.yaml
    - skills/helix/SKILL.md
    - CLAUDE.md

depends_on:
  - "011"
  - "017"
---

# ADR-022: Unified API Architecture - Eine API für alles

## Status

Implemented (2025-12-26)

---

## Kontext

### Das Problem: Architektur-Chaos

Aktuell existieren **drei verschiedene Orchestrator-Implementierungen**:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    AKTUELLER ZUSTAND (CHAOS)                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. orchestrator_legacy.py (417 Zeilen)                                 │
│     ├── Genutzt von: CLI (helix run)                                    │
│     ├── Quality Gates: ✅                                               │
│     ├── Escalation: ✅                                                  │
│     └── Verification (ADR-011): ❌ FEHLT                                │
│                                                                         │
│  2. streaming.py (400+ Zeilen)                                          │
│     ├── Genutzt von: API (/helix/execute)                               │
│     ├── Verification: ✅                                                │
│     ├── SSE Events: ✅                                                  │
│     └── Quality Gates: ⚠️ Eigene Implementierung                        │
│                                                                         │
│  3. orchestrator/ package (~2000 Zeilen)                                │
│     ├── Genutzt von: NIEMAND                                            │
│     ├── ADR-017 Design: ✅                                              │
│     └── Status: Tot, nie integriert                                     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Konkrete Probleme

1. **Duplizierter Code**: Gleiche Logik in 3 Dateien
2. **Inkonsistentes Verhalten**: CLI vs API haben unterschiedliche Features
3. **Maintenance-Last**: Änderungen müssen an 3 Stellen gemacht werden
4. **Toter Code**: orchestrator/ package wird nie genutzt (2000 Zeilen Ballast)
5. **ADR-011 nur halb umgesetzt**: Verification nur in API, nicht in CLI

### Warum ist das passiert?

1. CLI kam zuerst → `orchestrator.py`
2. API brauchte Streaming → Eigene Logik in `streaming.py`
3. ADR-017 definierte neues Design → `orchestrator/` package
4. Package shadowed Module → Renamed zu `orchestrator_legacy.py`
5. Niemand hat aufgeräumt

---

## Entscheidung

### Eine API als Single Source of Truth

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    NEUE ARCHITEKTUR                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│                         ┌─────────────────┐                             │
│                         │   HELIX API     │                             │
│                         │   (FastAPI)     │                             │
│                         │   :8001         │                             │
│                         └────────┬────────┘                             │
│                                  │                                      │
│                    ┌─────────────┼─────────────┐                        │
│                    │             │             │                        │
│                    ▼             ▼             ▼                        │
│              ┌──────────┐ ┌──────────┐ ┌──────────┐                     │
│              │   CLI    │ │  WebUI   │ │  Other   │                     │
│              │  Client  │ │  Client  │ │ Clients  │                     │
│              │ (async)  │ │(OpenAI)  │ │          │                     │
│              └──────────┘ └──────────┘ └──────────┘                     │
│                                                                         │
│  API Features (EINE Implementierung):                                   │
│  ✅ Phase Orchestration                                                 │
│  ✅ Quality Gates                                                       │
│  ✅ Escalation                                                          │
│  ✅ Verification (ADR-011)                                              │
│  ✅ SSE Streaming                                                       │
│  ✅ OpenAI-kompatibel (für Open WebUI)                                  │
│  ✅ Job Management                                                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### CLI wird Thin Client

```python
# VORHER: CLI hat eigene Orchestrator-Logik
$ helix run project
→ orchestrator_legacy.py
→ ClaudeRunner
→ (keine Verification)

# NACHHER: CLI ruft API auf
$ helix run project
→ POST http://localhost:8001/helix/execute
→ SSE Stream empfangen
→ Progress anzeigen
```

### Was wird gelöscht

| Datei | Zeilen | Grund |
|-------|--------|-------|
| `orchestrator_legacy.py` | 417 | Ersetzt durch API |
| `orchestrator/__init__.py` | 50 | Nie genutzt |
| `orchestrator/runner.py` | 500 | Nie genutzt |
| `orchestrator/phase_executor.py` | 300 | Nie genutzt |
| `orchestrator/data_flow.py` | 400 | Nie genutzt |
| `orchestrator/status.py` | 400 | Nie genutzt |
| **TOTAL** | **~2067** | Toter Code |

### Was wird konsolidiert

Die beste Logik aus allen drei Quellen wird in `api/orchestrator.py` vereint:

```python
# src/helix/api/orchestrator.py - NEUE ZENTRALE LOGIK

class UnifiedOrchestrator:
    """Single orchestrator for all entry points."""
    
    def __init__(self):
        self.claude_runner = ClaudeRunner()
        self.gate_runner = QualityGateRunner()
        self.verifier = PhaseVerifier()  # ADR-011
        self.escalation = EscalationManager()  # ADR-004
    
    async def run_project(
        self,
        project_path: Path,
        event_callback: Callable | None = None,  # Für SSE
    ) -> ProjectResult:
        """Run project with all features."""
        
        for phase in phases:
            # 1. Execute phase
            result = await self.claude_runner.run_phase(phase_dir)
            
            # 2. Verify output (ADR-011)
            verify = await self.verifier.verify_phase_output(...)
            if not verify.success:
                # Emit event
                if event_callback:
                    await event_callback("verification_failed", verify)
                # Retry or escalate
                ...
            
            # 3. Quality Gate
            gate = await self.gate_runner.check(...)
            if not gate.passed:
                # Escalation (ADR-004)
                ...
            
            # 4. Emit progress
            if event_callback:
                await event_callback("phase_complete", result)
```

---

## Implementation

### 1. API Orchestrator (`src/helix/api/orchestrator.py`)

Neue zentrale Datei die ALLE Logik enthält:

```python
"""Unified Orchestrator for HELIX API.

This is the SINGLE source of truth for project execution.
All entry points (CLI, WebUI, API) use this orchestrator.
"""

from pathlib import Path
from typing import AsyncGenerator, Callable
from dataclasses import dataclass

from helix.claude_runner import ClaudeRunner
from helix.quality_gates import QualityGateRunner, GateResult
from helix.evolution.verification import PhaseVerifier, VerificationResult
from helix.escalation import EscalationManager
from helix.phase_loader import PhaseLoader, PhaseConfig


@dataclass
class PhaseEvent:
    """Event emitted during phase execution."""
    event_type: str  # phase_start, phase_complete, verification_failed, etc.
    phase_id: str
    data: dict


@dataclass
class ProjectResult:
    """Result of project execution."""
    success: bool
    phases_completed: int
    phases_total: int
    errors: list[str]
    

class UnifiedOrchestrator:
    """The one and only orchestrator."""
    
    MAX_RETRIES = 2
    
    def __init__(self):
        self.claude_runner = ClaudeRunner()
        self.gate_runner = QualityGateRunner()
        self.verifier = PhaseVerifier()
        self.escalation = EscalationManager()
        self.phase_loader = PhaseLoader()
    
    async def run_project(
        self,
        project_path: Path,
        on_event: Callable[[PhaseEvent], None] | None = None,
    ) -> ProjectResult:
        """Execute a project with full feature set.
        
        Features:
        - Phase execution via ClaudeRunner
        - Post-phase verification (ADR-011)
        - Quality gates with escalation (ADR-004)
        - Event streaming for progress updates
        
        Args:
            project_path: Path to project directory
            on_event: Optional callback for progress events
            
        Returns:
            ProjectResult with execution details
        """
        phases = self.phase_loader.load_phases(project_path)
        errors = []
        completed = 0
        
        for phase in phases:
            # Emit start event
            if on_event:
                await on_event(PhaseEvent(
                    event_type="phase_start",
                    phase_id=phase.id,
                    data={"name": phase.name}
                ))
            
            phase_dir = project_path / "phases" / phase.id
            
            # Execute with retry loop
            for attempt in range(self.MAX_RETRIES + 1):
                # 1. Run Claude
                claude_result = await self.claude_runner.run_phase(phase_dir)
                
                if not claude_result.success:
                    errors.append(f"Phase {phase.id}: Claude failed")
                    break
                
                # 2. Verify output (ADR-011)
                verify_result = self.verifier.verify_phase_output(
                    phase_id=phase.id,
                    phase_dir=phase_dir,
                    expected_files=phase.output,
                )
                
                if not verify_result.success:
                    if on_event:
                        await on_event(PhaseEvent(
                            event_type="verification_failed",
                            phase_id=phase.id,
                            data={"missing": verify_result.missing_files}
                        ))
                    
                    if attempt < self.MAX_RETRIES:
                        # Write error context for retry
                        (phase_dir / "RETRY_CONTEXT.md").write_text(
                            self.verifier.format_retry_prompt(verify_result)
                        )
                        continue
                    else:
                        errors.append(f"Phase {phase.id}: Verification failed")
                        break
                
                # 3. Quality Gate (if defined)
                if phase.quality_gate:
                    gate_result = await self.gate_runner.check(
                        phase_dir, phase.quality_gate
                    )
                    
                    if not gate_result.passed:
                        if on_event:
                            await on_event(PhaseEvent(
                                event_type="gate_failed",
                                phase_id=phase.id,
                                data={"message": gate_result.message}
                            ))
                        
                        # Escalation logic (ADR-004)
                        action = await self.escalation.handle_failure(...)
                        if action.requires_human:
                            errors.append(f"Phase {phase.id}: Requires human")
                            break
                        continue
                
                # Success!
                completed += 1
                if on_event:
                    await on_event(PhaseEvent(
                        event_type="phase_complete",
                        phase_id=phase.id,
                        data={"attempt": attempt + 1}
                    ))
                break
            
            # If phase failed, stop project
            if errors:
                break
        
        return ProjectResult(
            success=len(errors) == 0,
            phases_completed=completed,
            phases_total=len(phases),
            errors=errors,
        )
    
    async def run_project_streaming(
        self,
        project_path: Path,
    ) -> AsyncGenerator[PhaseEvent, None]:
        """Run project and yield events as SSE stream."""
        events = []
        
        async def collect_event(event: PhaseEvent):
            events.append(event)
        
        # Start execution in background
        result_future = asyncio.create_task(
            self.run_project(project_path, on_event=collect_event)
        )
        
        # Yield events as they come
        while not result_future.done() or events:
            if events:
                yield events.pop(0)
            else:
                await asyncio.sleep(0.1)
        
        # Final result event
        result = await result_future
        yield PhaseEvent(
            event_type="project_complete",
            phase_id="",
            data={"success": result.success, "completed": result.phases_completed}
        )
```

### 2. CLI als API Client (`src/helix/cli/api_client.py`)

```python
"""CLI client that calls HELIX API."""

import asyncio
import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

API_BASE = "http://localhost:8001"


async def run_project(project_path: str, background: bool = False) -> bool:
    """Run a project via API."""
    
    async with httpx.AsyncClient(timeout=None) as client:
        # Start job
        response = await client.post(
            f"{API_BASE}/helix/execute",
            json={"project_path": project_path, "background": background}
        )
        job = response.json()
        job_id = job["job_id"]
        
        if background:
            console.print(f"[green]✅ Job gestartet: {job_id}[/green]")
            console.print(f"   Status: helix jobs")
            console.print(f"   Logs:   helix logs {job_id}")
            return True
        
        # Stream events
        console.print(f"[blue]→ Running project: {project_path}[/blue]")
        
        async with client.stream(
            "GET",
            f"{API_BASE}/helix/stream/{job_id}"
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    event = json.loads(line[5:])
                    _handle_event(event)
        
        return True


def _handle_event(event: dict):
    """Handle SSE event and print progress."""
    event_type = event.get("event_type")
    
    if event_type == "phase_start":
        console.print(f"[blue]→ Phase {event['phase_id']}: {event['data']['name']}[/blue]")
    
    elif event_type == "phase_complete":
        console.print(f"[green]✓ Phase {event['phase_id']} complete[/green]")
    
    elif event_type == "verification_failed":
        console.print(f"[yellow]⚠ Verification failed: {event['data']['missing']}[/yellow]")
    
    elif event_type == "gate_failed":
        console.print(f"[red]✗ Gate failed: {event['data']['message']}[/red]")
    
    elif event_type == "project_complete":
        if event["data"]["success"]:
            console.print(f"[green]✅ Project complete ({event['data']['completed']} phases)[/green]")
        else:
            console.print(f"[red]❌ Project failed[/red]")


async def list_jobs() -> list:
    """List all jobs from API."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/helix/jobs")
        return response.json()


async def get_logs(job_id: str, follow: bool = False):
    """Get job logs from API."""
    async with httpx.AsyncClient(timeout=None) as client:
        if follow:
            async with client.stream("GET", f"{API_BASE}/helix/logs/{job_id}?follow=true") as r:
                async for line in r.aiter_lines():
                    console.print(line)
        else:
            response = await client.get(f"{API_BASE}/helix/logs/{job_id}")
            console.print(response.text)
```

### 3. CLI Commands Update (`src/helix/cli/commands.py`)

```python
"""CLI commands - thin wrapper around API."""

import asyncio
import click
from .api_client import run_project, list_jobs, get_logs


@click.command()
@click.argument("project_path")
@click.option("--background", "-bg", is_flag=True)
def run(project_path: str, background: bool):
    """Run a HELIX project via API."""
    asyncio.run(run_project(project_path, background))


@click.command()
def jobs():
    """List running jobs."""
    jobs = asyncio.run(list_jobs())
    for job in jobs:
        click.echo(f"{job['job_id']}  {job['project']}  {job['status']}")


@click.command()
@click.argument("job_id")
@click.option("--follow", "-f", is_flag=True)
def logs(job_id: str, follow: bool):
    """Show job logs."""
    asyncio.run(get_logs(job_id, follow))
```

### 4. Standalone Script (`scripts/helix`)

```bash
#!/bin/bash
# Standalone helix CLI that ensures API is running

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Source environment
source "$PROJECT_ROOT/config/env.sh" 2>/dev/null

# Check if API is running
if ! curl -s http://localhost:8001/ > /dev/null 2>&1; then
    echo "Starting HELIX API..."
    cd "$PROJECT_ROOT"
    PYTHONPATH=src python3 -m uvicorn helix.api.main:app --host 0.0.0.0 --port 8001 &
    sleep 2
fi

# Run CLI command
cd "$PROJECT_ROOT"
PYTHONPATH=src python3 -m helix.cli.main "$@"
```

---

## Migration

### Phase 1: Neuen Orchestrator erstellen

```bash
# 1. Neue Datei mit konsolidierter Logik
touch src/helix/api/orchestrator.py

# 2. Beste Features aus allen 3 Quellen übernehmen:
#    - Quality Gates aus orchestrator_legacy.py
#    - Verification aus streaming.py  
#    - Event System neu designed
```

### Phase 2: API Endpoints aktualisieren

```bash
# streaming.py wird thin wrapper um UnifiedOrchestrator
# Keine eigene Logik mehr, nur SSE formatting
```

### Phase 3: CLI auf API umstellen

```bash
# 1. api_client.py erstellen
# 2. commands.py aktualisieren
# 3. Testen dass CLI via API funktioniert
```

### Phase 4: Aufräumen

```bash
# Löschen (nach Backup):
rm src/helix/orchestrator_legacy.py
rm -rf src/helix/orchestrator/

# ~2067 Zeilen toter Code entfernt
```

### Phase 5: Dokumentation

```bash
# Aktualisieren:
# - docs/sources/api.yaml
# - docs/sources/cli.yaml
# - skills/helix/SKILL.md
# - CLAUDE.md
```

---

## Akzeptanzkriterien

### API

- [ ] `POST /helix/execute` startet Projekt mit allen Features
- [ ] `GET /helix/stream/{job_id}` liefert SSE Events
- [ ] `GET /helix/jobs` listet alle Jobs
- [ ] `GET /helix/logs/{job_id}` liefert Logs
- [ ] Verification (ADR-011) ist integriert
- [ ] Quality Gates funktionieren
- [ ] Escalation (ADR-004) funktioniert

### CLI

- [ ] `helix run project` funktioniert via API
- [ ] `helix run project --background` startet im Hintergrund
- [ ] `helix jobs` zeigt Jobs
- [ ] `helix logs job-id` zeigt Logs
- [ ] Progress wird im Terminal angezeigt

### Open WebUI

- [ ] `/v1/models` listet helix-consultant, helix-developer
- [ ] `/v1/chat/completions` funktioniert
- [ ] Streaming funktioniert

### Cleanup

- [ ] orchestrator_legacy.py gelöscht
- [ ] orchestrator/ package gelöscht
- [ ] Keine Duplikate mehr in streaming.py
- [ ] ~2000 Zeilen Code entfernt

---

## Dokumentation

### Zu aktualisieren

- **docs/sources/api.yaml**: API Endpoints dokumentieren
- **docs/sources/cli.yaml**: CLI nutzt jetzt API
- **skills/helix/SKILL.md**: Architektur-Diagramm aktualisieren
- **CLAUDE.md**: Entry Points aktualisieren

### Zu entfernen

- Alle Referenzen zu orchestrator_legacy.py
- Alle Referenzen zu orchestrator/ package
- ADR-017 Status auf "Superseded by ADR-022" setzen

---

## Konsequenzen

### Vorteile

1. **Eine Implementierung**: Alle Features an einem Ort
2. **Konsistentes Verhalten**: CLI und API haben gleiche Features
3. **Weniger Code**: ~2000 Zeilen entfernt
4. **Einfacher zu maintainen**: Änderungen nur an einer Stelle
5. **Open WebUI ready**: API ist bereits OpenAI-kompatibel

### Nachteile

1. **API muss laufen**: CLI braucht laufende API
2. **Refactoring-Aufwand**: Einmalig ~1-2 Tage Arbeit
3. **Breaking Change**: Alte CLI funktioniert nicht mehr direkt

### Risiken

1. **API Downtime**: CLI funktioniert nicht wenn API down
   - Mitigation: scripts/helix startet API automatisch
   
2. **Netzwerk-Latenz**: Lokaler HTTP Call statt direkter Aufruf
   - Mitigation: Minimal bei localhost, <1ms

---

## Referenzen

- ADR-004: Escalation System
- ADR-011: Post-Phase Verification
- ADR-017: Phase Orchestrator (wird superseded)
- ADR-021: Async CLI Background Jobs
