---
adr_id: "017"
title: "Phase Orchestrator - Automatische Projekt-Ausführung"
status: Proposed

project_type: helix_internal
component_type: PROCESS
classification: NEW
change_scope: major

domain: helix
language: python
skills:
  - helix

files:
  create:
    - src/helix/orchestrator/runner.py
    - src/helix/orchestrator/phase_executor.py
    - src/helix/orchestrator/data_flow.py
    - src/helix/orchestrator/status.py
    - src/helix/orchestrator/__init__.py
    - src/helix/cli/project.py
    - config/phase-types.yaml
    - config/orchestrator.yaml
    - tests/test_orchestrator_runner.py
    - tests/test_phase_executor.py
    - tests/test_data_flow.py
  modify:
    - src/helix/orchestrator.py
    - src/helix/cli/__init__.py
    - src/helix/api/routes/__init__.py
  docs:
    - docs/ARCHITECTURE-ORCHESTRATOR.md
    - docs/ARCHITECTURE-MODULES.md
    - CLAUDE.md
    - skills/helix/SKILL.md

depends_on:
  - "002"
  - "015"

related_to:
  - "006"
  - "014"
---

# ADR-017: Phase Orchestrator - Automatische Projekt-Ausführung

## Status

📋 Proposed

---

## Kontext

### Was ist das Problem?

HELIX v4 hat aktuell **keinen automatischen Orchestrator**. Die Projekt-Ausführung erfolgt manuell:

```
┌─────────────────────────────────────────────────────────────┐
│  AKTUELLER ZUSTAND: Manueller Orchestrator                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. User startet Claude Code CLI manuell                    │
│     $ claude -p "Führe Phase 1 aus"                         │
│                                                             │
│  2. User wartet und beobachtet                              │
│     → Polling: "Ist die Phase fertig?"                      │
│                                                             │
│  3. User prüft Output manuell                               │
│     → Existieren Dateien?                                   │
│     → Syntax OK?                                            │
│     → Tests grün?                                           │
│                                                             │
│  4. User kopiert Outputs als Inputs für nächste Phase       │
│     $ cp phases/01/output/* phases/02/input/                │
│                                                             │
│  5. User startet nächste Phase manuell                      │
│     ... und so weiter ...                                   │
│                                                             │
│  6. User integriert und committed                           │
│     $ cp output/* ziel/ && git add -A && git commit         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Warum muss es gelöst werden?

1. **Skalierbarkeit**: Manuelles Orchestrieren skaliert nicht
2. **Fehleranfälligkeit**: Vergessene Kopier-Schritte, falsche Input-Verknüpfungen
3. **Zeitaufwand**: Jede Phase erfordert manuelle Intervention
4. **Inkonsistenz**: Jeder macht es anders
5. **Kern-Feature**: HELIX soll autonom entwickeln können

### Was passiert wenn wir nichts tun?

- HELIX bleibt ein "Framework ohne Motor"
- Jedes Projekt erfordert manuellen Aufwand
- Die Adoption wird blockiert
- Die Vision von autonomer Entwicklung bleibt unerfüllt

### Bestehendes: Was existiert bereits?

```python
# src/helix/orchestrator.py - 418 Zeilen
class Orchestrator:
    """Orchestrates the execution of HELIX v4 project workflows."""

    async def run_project(self, project_dir: Path) -> ProjectResult
    async def run_phase(self, phase_dir, phase_config, spec) -> PhaseResult
    async def check_quality_gate(self, phase_dir, gate_config) -> GateResult
```

Der existierende Code ist eine solide Basis, aber:
- ❌ Kein automatischer Datenfluss zwischen Phasen
- ❌ Keine CLI-Integration (`helix project run`)
- ❌ Kein Status-Tracking in Datei
- ❌ Keine Unterstützung für Projekt-Typen
- ❌ Kein Decompose-Mechanismus

---

## Entscheidung

### Wir entscheiden uns für:

Eine **modulare Orchestrator-Architektur** die den existierenden Code erweitert und um drei neue Kernkomponenten ergänzt:

1. **PhaseExecutor** - Führt einzelne Phasen aus (inkl. Claude CLI)
2. **DataFlowManager** - Kopiert Outputs → Inputs automatisch
3. **StatusTracker** - Persistenter Status in `status.yaml`

### Diese Entscheidung beinhaltet:

1. **Projekt-Typen** (simple, complex, exploratory) bestimmen den Workflow
2. **Consultant bestimmt Typ** bei Projekt-Erstellung
3. **Automatischer Datenfluss** zwischen Phasen
4. **Feste Quality Gates pro Phase-Type**, überschreibbar in phases.yaml
5. **CLI Integration**: `helix project run <name>`
6. **API Integration**: `POST /project/{name}/run`

### Warum diese Lösung?

| Kriterium | Monolithisch | Event-basiert | Modular (gewählt) |
|-----------|--------------|---------------|-------------------|
| **Komplexität** | Niedrig | Hoch | Mittel |
| **Erweiterbarkeit** | Schwer | Sehr gut | Gut |
| **Debugging** | Schwer | Mittel | Einfach |
| **Implementierung** | Schnell | Langsam | Mittel |
| **Testbarkeit** | Schwer | Gut | Sehr gut |

Der modulare Ansatz bietet die beste Balance zwischen Einfachheit und Erweiterbarkeit.

### Welche Alternativen wurden betrachtet?

1. **Monolithischer Orchestrator** (500+ Zeilen in einer Datei)
   - Nicht gewählt: Schwer zu testen und zu erweitern

2. **Event-basierte Pipeline** (Pub/Sub mit Event-Handlern)
   - Nicht gewählt: Zu komplex für MVP, später möglich

3. **Externes Workflow-Tool** (Airflow, Prefect, etc.)
   - Nicht gewählt: Zu schwergewichtig, Vendor-Lock-in

---

## Implementation

### 1. Modul-Struktur

```
src/helix/
├── orchestrator/                    # NEU: Orchestrator-Paket
│   ├── __init__.py                  # Exports
│   ├── runner.py                    # OrchestratorRunner (Hauptklasse)
│   ├── phase_executor.py            # PhaseExecutor
│   ├── data_flow.py                 # DataFlowManager
│   └── status.py                    # StatusTracker
│
├── orchestrator.py                  # BEHALTEN: Existierende Orchestrator-Klasse
│                                    # → Wird zu Basis-Klasse
│
└── cli/
    ├── __init__.py                  # ERWEITERN
    └── project.py                   # NEU: project-Subcommands
```

### 2. Projekt-Typen Konfiguration

**`config/phase-types.yaml`:**

```yaml
_meta:
  version: "1.0"
  description: "Feste Quality Gates pro Phase-Type"

phase_types:
  consultant:
    description: "ADR und Spezifikation erstellen"
    default_gates:
      - adr_valid
    output_pattern: "output/ADR-*.md"

  development:
    description: "Code implementieren"
    default_gates:
      - files_exist
      - syntax_check
      - tests_pass
    output_pattern: "output/src/**/*.py"

  review:
    description: "Code und ADR reviewen"
    default_gates:
      - review_approved
    requires_input_from: [development, consultant]

  testing:
    description: "Tests ausführen"
    default_gates:
      - tests_pass
    output_pattern: "output/tests/**/*.py"

  integration:
    description: "In Hauptprojekt integrieren"
    default_gates:
      - all_tests_pass
      - docs_current
    requires_input_from: [development, review]

  feasibility:
    description: "Proof of Concept erstellen"
    default_gates:
      - poc_working
    output_pattern: "output/poc/**"

  planning:
    description: "Phasen planen (decompose)"
    default_gates:
      - plan_valid
    can_decompose: true
    max_sub_phases: 4
    output_pattern: "output/plan.yaml"

# Projekt-Typen
project_types:
  simple:
    description: "Standard-Feature (Schema F)"
    default_phases:
      - consultant
      - development
      - review
      - integration
    auto_approve: false

  complex:
    description: "Komplexes Feature mit Feasibility"
    default_phases:
      - consultant
      - feasibility
      - planning
      - development
      - review
      - integration
    auto_approve: false

  exploratory:
    description: "Exploration ohne festen Plan"
    default_phases:
      - consultant
      - research
      - decision
    auto_approve: false
```

### 3. OrchestratorRunner (Hauptklasse)

```python
# src/helix/orchestrator/runner.py

"""Phase Orchestrator Runner for HELIX v4.

Manages the automatic execution of project phases including:
- Phase execution via Claude Code CLI
- Quality gate checking
- Data flow between phases
- Status tracking
"""

import asyncio
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .phase_executor import PhaseExecutor, PhaseResult
from .data_flow import DataFlowManager
from .status import StatusTracker, ProjectStatus, PhaseStatus
from ..orchestrator import Orchestrator  # Basis-Klasse
from ..phase_loader import PhaseConfig, PhaseLoader
from ..quality_gates import GateResult


@dataclass
class RunConfig:
    """Configuration for an orchestrator run."""
    project_dir: Path
    resume: bool = False
    parallel: bool = False
    dry_run: bool = False
    timeout_per_phase: int = 600  # 10 Minuten pro Phase


class OrchestratorRunner:
    """Runs projects automatically.

    The OrchestratorRunner extends the base Orchestrator with:
    - Automatic data flow between phases
    - Persistent status tracking
    - Resume capability
    - CLI integration

    Example:
        >>> runner = OrchestratorRunner()
        >>> result = await runner.run("my-project")
        >>> print(f"Status: {result.status}")
        >>> print(f"Completed: {result.completed_phases}/{result.total_phases}")
    """

    def __init__(
        self,
        base_orchestrator: Orchestrator | None = None,
        phase_executor: PhaseExecutor | None = None,
        data_flow: DataFlowManager | None = None,
        status_tracker: StatusTracker | None = None,
    ) -> None:
        """Initialize the OrchestratorRunner.

        Args:
            base_orchestrator: Base Orchestrator instance.
            phase_executor: Phase executor for running phases.
            data_flow: Data flow manager for copying outputs.
            status_tracker: Status tracker for persistence.
        """
        self.base = base_orchestrator or Orchestrator()
        self.executor = phase_executor or PhaseExecutor()
        self.data_flow = data_flow or DataFlowManager()
        self.status = status_tracker or StatusTracker()

    async def run(
        self,
        project_name: str,
        config: RunConfig | None = None,
    ) -> ProjectStatus:
        """Run a project to completion.

        Args:
            project_name: Name of the project to run.
            config: Optional run configuration.

        Returns:
            ProjectStatus with final status.
        """
        config = config or RunConfig(
            project_dir=Path(f"projects/external/{project_name}")
        )

        # Load or resume status
        status = self.status.load_or_create(config.project_dir)

        if not config.resume and status.status == "completed":
            return status

        # Load phases
        phases = self.base.phase_loader.load_phases(config.project_dir)
        phase_queue = deque(phases)

        status.status = "running"
        status.total_phases = len(phases)
        status.started_at = datetime.now()
        self.status.save(status)

        while phase_queue:
            phase = phase_queue.popleft()

            # Skip completed phases on resume
            if config.resume and status.is_phase_complete(phase.id):
                continue

            # Prepare inputs from previous phases
            await self.data_flow.prepare_phase_inputs(
                config.project_dir,
                phase,
                status,
            )

            # Execute phase
            phase_dir = self.base.phase_loader.get_phase_dir(
                config.project_dir,
                phase,
            )

            result = await self.executor.execute(
                phase_dir=phase_dir,
                phase_config=phase,
                timeout=config.timeout_per_phase,
                dry_run=config.dry_run,
            )

            # Update status
            status.update_phase(phase.id, result)
            self.status.save(status)

            if not result.success:
                status.status = "failed"
                status.error = result.error
                self.status.save(status)
                return status

            # Handle decompose phases
            if phase.config.get("decompose") and result.has_plan:
                new_phases = self._parse_plan(result.plan_path)
                for new_phase in reversed(new_phases):
                    phase_queue.appendleft(new_phase)
                status.total_phases += len(new_phases)

            status.completed_phases += 1

        status.status = "completed"
        status.completed_at = datetime.now()
        self.status.save(status)

        return status

    def _parse_plan(self, plan_path: Path) -> list[PhaseConfig]:
        """Parse plan.yaml into phase configs."""
        with open(plan_path) as f:
            plan = yaml.safe_load(f)

        phases = []
        for phase_def in plan.get("decomposed_phases", []):
            phases.append(PhaseConfig(
                id=phase_def["id"],
                name=phase_def.get("description", phase_def["id"]),
                type=phase_def.get("type", "development"),
                config=phase_def,
                quality_gate=phase_def.get("gate"),
            ))

        return phases
```

### 4. PhaseExecutor

```python
# src/helix/orchestrator/phase_executor.py

"""Phase Executor for HELIX v4.

Executes individual phases using Claude Code CLI.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from ..claude_runner import ClaudeRunner, ClaudeResult
from ..quality_gates import QualityGateRunner, GateResult
from ..phase_loader import PhaseConfig


@dataclass
class PhaseResult:
    """Result of executing a single phase."""
    phase_id: str
    success: bool
    started_at: datetime
    completed_at: datetime | None = None
    claude_result: ClaudeResult | None = None
    gate_result: GateResult | None = None
    error: str | None = None
    has_plan: bool = False
    plan_path: Path | None = None
    retries: int = 0


class PhaseExecutor:
    """Executes individual phases.

    Handles:
    - Claude Code CLI invocation
    - Quality gate checking
    - Retry logic
    - Timeout handling

    Example:
        >>> executor = PhaseExecutor()
        >>> result = await executor.execute(
        ...     phase_dir=Path("phases/01-consultant"),
        ...     phase_config=config,
        ... )
        >>> if result.success:
        ...     print("Phase completed!")
    """

    MAX_RETRIES = 3

    def __init__(
        self,
        claude_runner: ClaudeRunner | None = None,
        gate_runner: QualityGateRunner | None = None,
    ) -> None:
        """Initialize the PhaseExecutor.

        Args:
            claude_runner: Claude Code CLI runner.
            gate_runner: Quality gate runner.
        """
        self.claude = claude_runner or ClaudeRunner()
        self.gates = gate_runner or QualityGateRunner()

    async def execute(
        self,
        phase_dir: Path,
        phase_config: PhaseConfig,
        timeout: int = 600,
        dry_run: bool = False,
    ) -> PhaseResult:
        """Execute a single phase.

        Args:
            phase_dir: Directory for phase execution.
            phase_config: Phase configuration.
            timeout: Maximum execution time in seconds.
            dry_run: If True, don't actually run Claude.

        Returns:
            PhaseResult with execution details.
        """
        result = PhaseResult(
            phase_id=phase_config.id,
            success=False,
            started_at=datetime.now(),
        )

        phase_dir.mkdir(parents=True, exist_ok=True)

        for attempt in range(self.MAX_RETRIES):
            result.retries = attempt

            try:
                # Run Claude Code CLI
                if not dry_run:
                    claude_result = await asyncio.wait_for(
                        self.claude.run_phase(
                            phase_dir,
                            model=phase_config.config.get("model"),
                        ),
                        timeout=timeout,
                    )
                    result.claude_result = claude_result

                    if not claude_result.success:
                        result.error = claude_result.error
                        continue
                else:
                    result.claude_result = ClaudeResult(
                        success=True,
                        output="[DRY RUN]",
                    )

                # Check quality gate
                if phase_config.quality_gate:
                    gate_result = await self.gates.run_gate(
                        phase_dir,
                        phase_config.quality_gate,
                    )
                    result.gate_result = gate_result

                    if not gate_result.passed:
                        result.error = gate_result.message
                        continue

                # Check for plan output (decompose phases)
                plan_path = phase_dir / "output" / "plan.yaml"
                if plan_path.exists():
                    result.has_plan = True
                    result.plan_path = plan_path

                result.success = True
                result.completed_at = datetime.now()
                return result

            except asyncio.TimeoutError:
                result.error = f"Phase timed out after {timeout}s"
            except Exception as e:
                result.error = str(e)

        result.completed_at = datetime.now()
        return result
```

### 5. DataFlowManager

```python
# src/helix/orchestrator/data_flow.py

"""Data Flow Manager for HELIX v4.

Handles the automatic copying of outputs from one phase
to inputs of the next phase.
"""

import shutil
from pathlib import Path
from typing import Any

from ..phase_loader import PhaseConfig


class DataFlowManager:
    """Manages data flow between phases.

    Automatically copies outputs from completed phases
    to the input directories of dependent phases.

    Example:
        >>> manager = DataFlowManager()
        >>> await manager.prepare_phase_inputs(
        ...     project_dir,
        ...     phase_config,
        ...     status,
        ... )
    """

    def __init__(self) -> None:
        """Initialize the DataFlowManager."""
        pass

    async def prepare_phase_inputs(
        self,
        project_dir: Path,
        phase: PhaseConfig,
        status: "ProjectStatus",
    ) -> None:
        """Prepare inputs for a phase from previous outputs.

        Args:
            project_dir: Project root directory.
            phase: Phase configuration with input_from.
            status: Current project status.
        """
        input_from = phase.config.get("input_from", [])
        if isinstance(input_from, str):
            input_from = [input_from]

        phase_dir = project_dir / "phases" / phase.id
        input_dir = phase_dir / "input"
        input_dir.mkdir(parents=True, exist_ok=True)

        for source_phase_id in input_from:
            source_dir = project_dir / "phases" / source_phase_id / "output"

            if not source_dir.exists():
                continue

            # Copy all outputs to input
            self._copy_outputs(source_dir, input_dir)

        # Also copy project-level files (spec.yaml, ADRs)
        self._copy_project_files(project_dir, input_dir)

    def _copy_outputs(self, source: Path, dest: Path) -> None:
        """Copy all files from source to destination."""
        for item in source.iterdir():
            dest_path = dest / item.name

            if item.is_file():
                shutil.copy2(item, dest_path)
            elif item.is_dir():
                if dest_path.exists():
                    shutil.rmtree(dest_path)
                shutil.copytree(item, dest_path)

    def _copy_project_files(self, project_dir: Path, input_dir: Path) -> None:
        """Copy project-level files to phase input."""
        # Copy spec.yaml if exists
        spec_path = project_dir / "spec.yaml"
        if spec_path.exists():
            shutil.copy2(spec_path, input_dir / "spec.yaml")

        # Copy ADR files
        for adr in project_dir.glob("ADR-*.md"):
            shutil.copy2(adr, input_dir / adr.name)

        # Copy phases.yaml for reference
        phases_path = project_dir / "phases.yaml"
        if phases_path.exists():
            shutil.copy2(phases_path, input_dir / "phases.yaml")
```

### 6. StatusTracker

```python
# src/helix/orchestrator/status.py

"""Status Tracker for HELIX v4.

Persists project and phase status to status.yaml.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .phase_executor import PhaseResult


@dataclass
class PhaseStatus:
    """Status of a single phase."""
    phase_id: str
    status: str  # pending, running, completed, failed
    started_at: datetime | None = None
    completed_at: datetime | None = None
    retries: int = 0
    error: str | None = None


@dataclass
class ProjectStatus:
    """Status of an entire project."""
    project_id: str
    status: str  # pending, running, completed, failed
    total_phases: int = 0
    completed_phases: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    phases: dict[str, PhaseStatus] = field(default_factory=dict)

    def is_phase_complete(self, phase_id: str) -> bool:
        """Check if a phase is completed."""
        phase = self.phases.get(phase_id)
        return phase is not None and phase.status == "completed"

    def update_phase(self, phase_id: str, result: PhaseResult) -> None:
        """Update phase status from result."""
        self.phases[phase_id] = PhaseStatus(
            phase_id=phase_id,
            status="completed" if result.success else "failed",
            started_at=result.started_at,
            completed_at=result.completed_at,
            retries=result.retries,
            error=result.error,
        )


class StatusTracker:
    """Tracks and persists project status.

    Example:
        >>> tracker = StatusTracker()
        >>> status = tracker.load_or_create(project_dir)
        >>> status.status = "running"
        >>> tracker.save(status)
    """

    STATUS_FILE = "status.yaml"

    def load_or_create(self, project_dir: Path) -> ProjectStatus:
        """Load existing status or create new one.

        Args:
            project_dir: Project directory.

        Returns:
            ProjectStatus instance.
        """
        status_path = project_dir / self.STATUS_FILE

        if status_path.exists():
            return self._load(status_path)

        return ProjectStatus(
            project_id=project_dir.name,
            status="pending",
        )

    def save(self, status: ProjectStatus) -> None:
        """Save status to file.

        Args:
            status: Status to save.
        """
        project_dir = Path(f"projects/external/{status.project_id}")
        status_path = project_dir / self.STATUS_FILE

        data = {
            "project_id": status.project_id,
            "status": status.status,
            "total_phases": status.total_phases,
            "completed_phases": status.completed_phases,
            "started_at": status.started_at.isoformat() if status.started_at else None,
            "completed_at": status.completed_at.isoformat() if status.completed_at else None,
            "error": status.error,
            "phases": {
                pid: {
                    "status": p.status,
                    "started_at": p.started_at.isoformat() if p.started_at else None,
                    "completed_at": p.completed_at.isoformat() if p.completed_at else None,
                    "retries": p.retries,
                    "error": p.error,
                }
                for pid, p in status.phases.items()
            },
        }

        with open(status_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

    def _load(self, path: Path) -> ProjectStatus:
        """Load status from file."""
        with open(path) as f:
            data = yaml.safe_load(f)

        phases = {}
        for pid, pdata in data.get("phases", {}).items():
            phases[pid] = PhaseStatus(
                phase_id=pid,
                status=pdata["status"],
                started_at=datetime.fromisoformat(pdata["started_at"]) if pdata.get("started_at") else None,
                completed_at=datetime.fromisoformat(pdata["completed_at"]) if pdata.get("completed_at") else None,
                retries=pdata.get("retries", 0),
                error=pdata.get("error"),
            )

        return ProjectStatus(
            project_id=data["project_id"],
            status=data["status"],
            total_phases=data.get("total_phases", 0),
            completed_phases=data.get("completed_phases", 0),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            error=data.get("error"),
            phases=phases,
        )
```

### 7. CLI Integration

```python
# src/helix/cli/project.py

"""Project management CLI commands for HELIX v4.

Usage:
    helix project create <name> [--type simple|complex|exploratory]
    helix project run <name> [--resume] [--dry-run]
    helix project status <name>
    helix project list
"""

import asyncio
from pathlib import Path

import click
import yaml

from ..orchestrator.runner import OrchestratorRunner, RunConfig
from ..orchestrator.status import StatusTracker


@click.group()
def project():
    """Project management commands."""
    pass


@project.command()
@click.argument("name")
@click.option(
    "--type",
    "project_type",
    default="simple",
    type=click.Choice(["simple", "complex", "exploratory"]),
    help="Project type (determines default phases).",
)
def create(name: str, project_type: str):
    """Create a new project.

    Example:
        helix project create my-feature --type simple
    """
    project_dir = Path(f"projects/external/{name}")

    if project_dir.exists():
        click.echo(f"Error: Project '{name}' already exists.", err=True)
        raise SystemExit(1)

    project_dir.mkdir(parents=True)

    # Load phase types config
    config_path = Path("config/phase-types.yaml")
    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f)
        default_phases = config["project_types"][project_type]["default_phases"]
    else:
        default_phases = ["consultant", "development", "review"]

    # Create phases.yaml
    phases_yaml = {
        "project": {
            "name": name,
            "type": project_type,
        },
        "phases": [
            {"id": phase, "type": phase}
            for phase in default_phases
        ],
    }

    with open(project_dir / "phases.yaml", "w") as f:
        yaml.dump(phases_yaml, f, default_flow_style=False)

    # Create phase directories
    for phase in default_phases:
        phase_dir = project_dir / "phases" / phase
        (phase_dir / "input").mkdir(parents=True)
        (phase_dir / "output").mkdir(parents=True)

    click.echo(f"Created project '{name}' with type '{project_type}'")
    click.echo(f"Phases: {', '.join(default_phases)}")
    click.echo(f"Location: {project_dir}")


@project.command()
@click.argument("name")
@click.option("--resume", is_flag=True, help="Resume from last completed phase.")
@click.option("--dry-run", is_flag=True, help="Don't execute, just show what would happen.")
def run(name: str, resume: bool, dry_run: bool):
    """Run a project.

    Example:
        helix project run my-feature
        helix project run my-feature --resume
    """
    project_dir = Path(f"projects/external/{name}")

    if not project_dir.exists():
        click.echo(f"Error: Project '{name}' not found.", err=True)
        raise SystemExit(1)

    config = RunConfig(
        project_dir=project_dir,
        resume=resume,
        dry_run=dry_run,
    )

    runner = OrchestratorRunner()

    click.echo(f"Running project '{name}'...")
    if dry_run:
        click.echo("[DRY RUN MODE]")

    result = asyncio.run(runner.run(name, config))

    if result.status == "completed":
        click.echo(f"✅ Project completed! ({result.completed_phases}/{result.total_phases} phases)")
    elif result.status == "failed":
        click.echo(f"❌ Project failed at phase: {result.error}")
        raise SystemExit(1)
    else:
        click.echo(f"⚠️ Project status: {result.status}")


@project.command()
@click.argument("name")
def status(name: str):
    """Show project status.

    Example:
        helix project status my-feature
    """
    project_dir = Path(f"projects/external/{name}")

    if not project_dir.exists():
        click.echo(f"Error: Project '{name}' not found.", err=True)
        raise SystemExit(1)

    tracker = StatusTracker()
    project_status = tracker.load_or_create(project_dir)

    click.echo(f"Project: {name}")
    click.echo(f"Status: {project_status.status}")
    click.echo(f"Progress: {project_status.completed_phases}/{project_status.total_phases}")

    if project_status.phases:
        click.echo("\nPhases:")
        for pid, phase in project_status.phases.items():
            icon = "✅" if phase.status == "completed" else "❌" if phase.status == "failed" else "⏳"
            click.echo(f"  {icon} {pid}: {phase.status}")
            if phase.error:
                click.echo(f"      Error: {phase.error}")


@project.command("list")
def list_projects():
    """List all projects.

    Example:
        helix project list
    """
    projects_dir = Path("projects/external")

    if not projects_dir.exists():
        click.echo("No projects found.")
        return

    tracker = StatusTracker()

    click.echo("Projects:")
    for project_dir in sorted(projects_dir.iterdir()):
        if project_dir.is_dir():
            status = tracker.load_or_create(project_dir)
            icon = {
                "completed": "✅",
                "failed": "❌",
                "running": "🔄",
                "pending": "⏳",
            }.get(status.status, "❓")
            click.echo(f"  {icon} {project_dir.name}: {status.status}")
```

### 8. API Integration

```python
# src/helix/api/routes/project.py

"""Project API routes for HELIX v4.

Endpoints:
    POST /project/{name}/run - Start project execution
    GET /project/{name}/status - Get project status
    GET /projects - List all projects
"""

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from ...orchestrator.runner import OrchestratorRunner, RunConfig
from ...orchestrator.status import StatusTracker, ProjectStatus

router = APIRouter(prefix="/project", tags=["project"])


class RunRequest(BaseModel):
    """Request body for project run."""
    resume: bool = False
    dry_run: bool = False


class RunResponse(BaseModel):
    """Response for project run."""
    status: str
    message: str
    project: str


async def run_project_background(name: str, config: RunConfig):
    """Background task to run a project."""
    runner = OrchestratorRunner()
    await runner.run(name, config)


@router.post("/{name}/run")
async def run_project(
    name: str,
    request: RunRequest,
    background_tasks: BackgroundTasks,
) -> RunResponse:
    """Start project execution.

    Runs the project in the background and returns immediately.

    Args:
        name: Project name.
        request: Run configuration.
        background_tasks: FastAPI background tasks.

    Returns:
        RunResponse with status.
    """
    project_dir = Path(f"projects/external/{name}")

    if not project_dir.exists():
        raise HTTPException(status_code=404, detail=f"Project not found: {name}")

    config = RunConfig(
        project_dir=project_dir,
        resume=request.resume,
        dry_run=request.dry_run,
    )

    background_tasks.add_task(run_project_background, name, config)

    return RunResponse(
        status="started",
        message=f"Project '{name}' execution started in background.",
        project=name,
    )


@router.get("/{name}/status")
async def get_status(name: str) -> dict:
    """Get project status.

    Args:
        name: Project name.

    Returns:
        Project status dictionary.
    """
    project_dir = Path(f"projects/external/{name}")

    if not project_dir.exists():
        raise HTTPException(status_code=404, detail=f"Project not found: {name}")

    tracker = StatusTracker()
    status = tracker.load_or_create(project_dir)

    return {
        "project_id": status.project_id,
        "status": status.status,
        "total_phases": status.total_phases,
        "completed_phases": status.completed_phases,
        "started_at": status.started_at.isoformat() if status.started_at else None,
        "completed_at": status.completed_at.isoformat() if status.completed_at else None,
        "error": status.error,
        "phases": {
            pid: {
                "status": p.status,
                "retries": p.retries,
                "error": p.error,
            }
            for pid, p in status.phases.items()
        },
    }


@router.get("s")
async def list_projects() -> list[dict]:
    """List all projects.

    Returns:
        List of project summaries.
    """
    projects_dir = Path("projects/external")

    if not projects_dir.exists():
        return []

    tracker = StatusTracker()
    projects = []

    for project_dir in sorted(projects_dir.iterdir()):
        if project_dir.is_dir():
            status = tracker.load_or_create(project_dir)
            projects.append({
                "name": project_dir.name,
                "status": status.status,
                "progress": f"{status.completed_phases}/{status.total_phases}",
            })

    return projects
```

### 9. Beispiel: Vollständiger Workflow

```yaml
# projects/external/my-feature/phases.yaml
project:
  name: my-feature
  type: simple

phases:
  - id: consultant
    type: consultant
    output:
      - output/ADR-my-feature.md
    quality_gate:
      type: adr_valid

  - id: development
    type: development
    input_from: consultant
    output:
      - output/src/*.py
      - output/tests/*.py
    quality_gate:
      type: compound
      gates:
        - syntax_check
        - tests_pass

  - id: review
    type: review
    input_from: [consultant, development]
    quality_gate:
      type: review_approved
    on_rejection:
      action: retry_phase
      target_phase: development
      max_retries: 2

  - id: integration
    type: integration
    input_from: [development, review]
    quality_gate:
      type: all_tests_pass
```

```bash
# Projekt erstellen
helix project create my-feature --type simple

# Projekt ausführen (automatisch alle Phasen)
helix project run my-feature

# Status prüfen
helix project status my-feature

# Bei Fehler: Resume nach Fix
helix project run my-feature --resume
```

---

## Dokumentation

### Zu aktualisierende Dokumente

| Dokument | Änderung |
|----------|----------|
| `docs/ARCHITECTURE-ORCHESTRATOR.md` | Orchestrator-Architektur dokumentieren |
| `docs/ARCHITECTURE-MODULES.md` | Neue Module beschreiben |
| `CLAUDE.md` | CLI-Commands und Workflow hinzufügen |
| `skills/helix/SKILL.md` | Orchestrator-Nutzung für Agents |

### Neue Dokumentation

- [ ] `docs/ORCHESTRATOR-USAGE.md` - Benutzerhandbuch
- [ ] `config/phase-types.yaml` - Inline-Dokumentation
- [ ] CLI `--help` Texte

---

## Migration

### Phase 1: Vorbereitung (Tag 1)

1. **Neue Paketstruktur erstellen**
   ```bash
   mkdir -p src/helix/orchestrator
   touch src/helix/orchestrator/__init__.py
   ```

2. **Konfigurationsdateien erstellen**
   - `config/phase-types.yaml`
   - `config/orchestrator.yaml`

3. **Existierende Tests sicherstellen**
   ```bash
   pytest tests/test_orchestrator.py -v
   ```

### Phase 2: Kernimplementierung (Tage 2-4)

1. **StatusTracker implementieren** (`status.py`)
2. **DataFlowManager implementieren** (`data_flow.py`)
3. **PhaseExecutor implementieren** (`phase_executor.py`)
4. **OrchestratorRunner implementieren** (`runner.py`)

### Phase 3: CLI & API Integration (Tage 5-6)

1. **CLI-Commands implementieren** (`cli/project.py`)
2. **API-Endpoints implementieren** (`api/routes/project.py`)
3. **Integration mit existierender CLI/API**

### Phase 4: Testing & Dokumentation (Tage 7-8)

1. **Unit Tests für alle neuen Module**
2. **E2E-Test: Komplettes Projekt durchlaufen**
3. **Dokumentation aktualisieren**

### Rollback-Strategie

Der existierende `src/helix/orchestrator.py` bleibt unverändert als Basis-Klasse. Bei Problemen kann auf die alte manuelle Methode zurückgegriffen werden.

```bash
# Bei Rollback: Alte Methode nutzen
python -c "from helix.orchestrator import Orchestrator; ..."
```

---

## Akzeptanzkriterien

### 1. Kernfunktionalität

- [ ] `helix project create <name>` erstellt Projekt-Struktur
- [ ] `helix project run <name>` führt alle Phasen automatisch aus
- [ ] `helix project status <name>` zeigt aktuellen Status
- [ ] `helix project run --resume` setzt nach Fehler fort
- [ ] Outputs werden automatisch als Inputs kopiert

### 2. Projekt-Typen

- [ ] `simple` Typ funktioniert (consultant → development → review)
- [ ] `complex` Typ funktioniert (inkl. feasibility)
- [ ] Consultant kann Projekt-Typ in spec.yaml setzen

### 3. Quality Gates

- [ ] Gates werden pro Phase-Type aus Config geladen
- [ ] Gates können in phases.yaml überschrieben werden
- [ ] Gate-Failures führen zu Retry (max 3x)
- [ ] Nach 3 Retries: Fehler und Abbruch

### 4. Status-Tracking

- [ ] `status.yaml` wird bei jeder Phase aktualisiert
- [ ] Resume funktioniert nach Neustart
- [ ] Phase-Historie wird gespeichert

### 5. API Integration

- [ ] `POST /project/{name}/run` startet Projekt
- [ ] `GET /project/{name}/status` gibt Status zurück
- [ ] `GET /projects` listet alle Projekte

### 6. Dokumentation

- [ ] CLAUDE.md aktualisiert mit CLI-Commands
- [ ] ARCHITECTURE-MODULES.md beschreibt Orchestrator-Paket
- [ ] Inline-Dokumentation in config/phase-types.yaml

### 7. Testing

- [ ] Unit Tests für alle neuen Klassen (>80% Coverage)
- [ ] E2E-Test: `helix project run` mit echtem Projekt
- [ ] Retry-Logik getestet

### 8. Integration

- [ ] Funktioniert mit ADR-015 Approval-System
- [ ] Funktioniert mit existierendem Escalation-System
- [ ] Keine Regression in bestehenden Tests

---

## Konsequenzen

### Vorteile

1. **Automatisierung** - Projekte laufen ohne manuelle Intervention
2. **Konsistenz** - Jedes Projekt durchläuft den gleichen Workflow
3. **Persistenz** - Status überlebt Neustarts
4. **Erweiterbarkeit** - Modulare Architektur für zukünftige Features
5. **CLI & API** - Flexible Nutzung (interaktiv und automatisiert)
6. **Resume** - Fehler können behoben und fortgesetzt werden

### Nachteile / Risiken

1. **Komplexität** - Mehr Code zu verstehen und zu warten
2. **Abhängigkeit** - Orchestrator wird zum kritischen Pfad
3. **Debugging** - Automatische Ausführung kann schwerer zu debuggen sein
4. **Kosten** - Jede Phase spawnt Claude CLI → Token-Kosten

### Mitigation

| Risiko | Mitigation |
|--------|------------|
| Komplexität | Modulare Architektur, gute Dokumentation |
| Kritischer Pfad | Fallback auf manuelle Ausführung möglich |
| Debugging | Ausführliches Logging, status.yaml für Forensik |
| Kosten | Dry-Run Option, Gate-First (Early-Exit bei Fehler) |

### Metriken nach Implementation

| Metrik | Ziel | Messung |
|--------|------|---------|
| Zeit pro Projekt | 50% schneller als manuell | Timer |
| Erfolgsrate | >90% | completed/total |
| Retry-Rate | <20% | retries/phases |
| Kosten pro Projekt | <$2 | Token-Tracking |

---

## Referenzen

- ADR-002: Quality Gate System
- ADR-006: Dynamic Phase Definition
- ADR-015: Approval & Validation System
- [VISION.md](../../docs/VISION.md) - Langfristige Architektur-Vision
- [ARCHITECTURE-ORCHESTRATOR.md](../../docs/ARCHITECTURE-ORCHESTRATOR.md) - Design-Dokument
- [BACKLOG.md](../../docs/BACKLOG.md) - FEATURE-001: Phase Orchestrator

---

*ADR erstellt vom HELIX Consultant*
*Session: adr-017-orchestrator*

---

## Aufwandsschätzung

| Phase | Aufwand | Abhängigkeiten |
|-------|---------|----------------|
| MVP (Orchestrator Core) | 3-4 Tage | BACKLOG Bug Fixes |
| CLI Integration | 1 Tag | MVP |
| API Integration | 1 Tag | MVP |
| Phase-Type Defaults | 0.5 Tage | MVP |
| Dokumentation | 1 Tag | Alles andere |
| Tests | 2 Tage | Parallel |
| **Gesamt** | **~2 Wochen** | |

