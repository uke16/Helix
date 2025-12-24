---
adr_id: "021"
title: "Async CLI mit Background Jobs"
status: Proposed
date: 2024-12-24

project_type: helix_internal
component_type: TOOL
classification: NEW
change_scope: minor

domain: helix
language: python

skills:
  - helix

files:
  create:
    - src/helix/cli/job_manager.py
    - src/helix/cli/async_runner.py
  modify:
    - src/helix/cli/commands.py
    - src/helix/cli/main.py
  docs:
    - skills/helix/SKILL.md

depends_on:
  - "017"  # Phase Orchestrator
---

# ADR-021: Async CLI mit Background Jobs

## Kontext

### Problem

Die aktuelle CLI blockiert komplett während ein Projekt läuft:

```bash
$ helix run projects/my-feature
→ Loading project...
→ Using model: claude-opus-4
# ... hängt hier 5-10 Minuten ...
```

**Probleme:**
1. Terminal ist blockiert - keine andere Arbeit möglich
2. SSH-Timeout kann Session killen
3. Kein Monitoring während Ausführung
4. Keine Möglichkeit mehrere Projekte parallel zu starten

### Gewünschtes Verhalten

```bash
$ helix run projects/my-feature --background
✅ Job gestartet: job-a1b2c3
   Status: helix jobs
   Logs:   helix logs job-a1b2c3
   Stop:   helix stop job-a1b2c3

$ helix run projects/other-feature --background
✅ Job gestartet: job-d4e5f6

$ helix jobs
JOB-ID      PROJECT              STATUS      PHASE       DURATION
job-a1b2c3  my-feature          running     2/4         2m 34s
job-d4e5f6  other-feature       running     1/3         0m 12s

$ helix logs job-a1b2c3 --follow
[Phase 2] Creating src/helix/new_module.py...
[Phase 2] Running tests...
```

## Entscheidung

### Minimale Async CLI mit Job Manager

```
┌──────────────────────────────────────────────────────────────┐
│                         CLI                                  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  helix run project --background                              │
│       │                                                      │
│       ▼                                                      │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐    │
│  │ JobManager  │────▶│ Background  │────▶│ Orchestrator│    │
│  │             │     │ Process     │     │             │    │
│  └─────────────┘     └─────────────┘     └─────────────┘    │
│       │                    │                                 │
│       │              writes to                               │
│       │                    ▼                                 │
│       │              ~/.helix/jobs/{id}/                     │
│       │              ├── status.json                         │
│       │              ├── output.log                          │
│       │              └── pid                                 │
│       │                                                      │
│  helix jobs ◀────────────┘                                   │
│  helix logs {id}                                             │
│  helix stop {id}                                             │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Neue CLI Commands

```bash
# Starte im Hintergrund
helix run projects/x --background
helix run projects/x -bg

# Starte im Vordergrund (default, wie jetzt)
helix run projects/x

# Job Management
helix jobs                    # Liste aller Jobs
helix jobs --running          # Nur laufende
helix logs <job-id>           # Logs anzeigen
helix logs <job-id> --follow  # Live Logs
helix stop <job-id>           # Job stoppen
helix result <job-id>         # Ergebnis anzeigen
```

### Job Status File

```json
// ~/.helix/jobs/job-a1b2c3/status.json
{
  "job_id": "job-a1b2c3",
  "project": "projects/my-feature",
  "started_at": "2024-12-24T11:30:00Z",
  "status": "running",
  "current_phase": "2",
  "total_phases": 4,
  "pid": 12345,
  "model": "claude-opus-4"
}
```

## Implementation

### 1. Job Manager (`src/helix/cli/job_manager.py`)

```python
"""Background job management for HELIX CLI."""

import json
import os
import signal
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
import uuid


@dataclass
class Job:
    job_id: str
    project: str
    status: str  # pending, running, completed, failed, stopped
    started_at: datetime
    pid: Optional[int] = None
    current_phase: Optional[str] = None
    total_phases: Optional[int] = None
    completed_at: Optional[datetime] = None
    exit_code: Optional[int] = None


class JobManager:
    """Manages background HELIX jobs."""
    
    JOBS_DIR = Path.home() / ".helix" / "jobs"
    
    def __init__(self):
        self.JOBS_DIR.mkdir(parents=True, exist_ok=True)
    
    def start_background(self, project: str, model: str = "claude-opus-4") -> Job:
        """Start a project in background."""
        job_id = f"job-{uuid.uuid4().hex[:6]}"
        job_dir = self.JOBS_DIR / job_id
        job_dir.mkdir(parents=True)
        
        # Start subprocess
        cmd = [
            "python3", "-m", "helix.cli.async_runner",
            "--project", project,
            "--model", model,
            "--job-id", job_id,
        ]
        
        log_file = job_dir / "output.log"
        with open(log_file, "w") as log:
            process = subprocess.Popen(
                cmd,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,  # Detach from terminal
                env={**os.environ, "PYTHONPATH": "src"}
            )
        
        job = Job(
            job_id=job_id,
            project=project,
            status="running",
            started_at=datetime.now(),
            pid=process.pid,
        )
        
        self._save_status(job)
        return job
    
    def list_jobs(self, status_filter: Optional[str] = None) -> list[Job]:
        """List all jobs."""
        jobs = []
        for job_dir in self.JOBS_DIR.iterdir():
            if job_dir.is_dir():
                job = self._load_status(job_dir.name)
                if job and (status_filter is None or job.status == status_filter):
                    jobs.append(job)
        return sorted(jobs, key=lambda j: j.started_at, reverse=True)
    
    def stop_job(self, job_id: str) -> bool:
        """Stop a running job."""
        job = self._load_status(job_id)
        if job and job.pid:
            try:
                os.killpg(os.getpgid(job.pid), signal.SIGTERM)
                job.status = "stopped"
                self._save_status(job)
                return True
            except ProcessLookupError:
                pass
        return False
    
    def get_logs(self, job_id: str, follow: bool = False) -> str:
        """Get job logs."""
        log_file = self.JOBS_DIR / job_id / "output.log"
        if not log_file.exists():
            return ""
        if follow:
            # Return generator for tail -f style
            pass
        return log_file.read_text()
    
    def _save_status(self, job: Job):
        status_file = self.JOBS_DIR / job.job_id / "status.json"
        with open(status_file, "w") as f:
            json.dump({
                "job_id": job.job_id,
                "project": job.project,
                "status": job.status,
                "started_at": job.started_at.isoformat(),
                "pid": job.pid,
                "current_phase": job.current_phase,
                "total_phases": job.total_phases,
            }, f, indent=2)
    
    def _load_status(self, job_id: str) -> Optional[Job]:
        status_file = self.JOBS_DIR / job_id / "status.json"
        if not status_file.exists():
            return None
        with open(status_file) as f:
            data = json.load(f)
        return Job(
            job_id=data["job_id"],
            project=data["project"],
            status=data["status"],
            started_at=datetime.fromisoformat(data["started_at"]),
            pid=data.get("pid"),
            current_phase=data.get("current_phase"),
            total_phases=data.get("total_phases"),
        )
```

### 2. CLI Commands Update

```python
# In src/helix/cli/commands.py

@click.command()
@click.argument("project_path")
@click.option("--background", "-bg", is_flag=True, help="Run in background")
@click.option("--model", "-m", default="claude-opus-4")
def run(project_path: str, background: bool, model: str):
    """Run a HELIX project."""
    if background:
        from helix.cli.job_manager import JobManager
        manager = JobManager()
        job = manager.start_background(project_path, model)
        click.secho(f"✅ Job gestartet: {job.job_id}", fg="green")
        click.echo(f"   Status: helix jobs")
        click.echo(f"   Logs:   helix logs {job.job_id}")
        click.echo(f"   Stop:   helix stop {job.job_id}")
    else:
        # Existing foreground logic
        ...


@click.command()
@click.option("--running", is_flag=True, help="Show only running jobs")
def jobs(running: bool):
    """List background jobs."""
    from helix.cli.job_manager import JobManager
    manager = JobManager()
    
    status_filter = "running" if running else None
    job_list = manager.list_jobs(status_filter)
    
    if not job_list:
        click.echo("No jobs found.")
        return
    
    click.echo(f"{'JOB-ID':<12} {'PROJECT':<20} {'STATUS':<10} {'PHASE':<8} {'DURATION'}")
    click.echo("-" * 70)
    for job in job_list:
        duration = datetime.now() - job.started_at
        phase = f"{job.current_phase}/{job.total_phases}" if job.current_phase else "-"
        click.echo(f"{job.job_id:<12} {job.project:<20} {job.status:<10} {phase:<8} {duration}")


@click.command()
@click.argument("job_id")
@click.option("--follow", "-f", is_flag=True, help="Follow log output")
def logs(job_id: str, follow: bool):
    """Show job logs."""
    from helix.cli.job_manager import JobManager
    manager = JobManager()
    click.echo(manager.get_logs(job_id, follow))


@click.command()
@click.argument("job_id")
def stop(job_id: str):
    """Stop a running job."""
    from helix.cli.job_manager import JobManager
    manager = JobManager()
    if manager.stop_job(job_id):
        click.secho(f"✅ Job {job_id} stopped", fg="green")
    else:
        click.secho(f"❌ Could not stop job {job_id}", fg="red")
```

## Akzeptanzkriterien

- [ ] `helix run project --background` startet Job und gibt sofort Kontrolle zurück
- [ ] `helix jobs` zeigt alle Jobs mit Status
- [ ] `helix logs <job-id>` zeigt Logs
- [ ] `helix logs <job-id> --follow` zeigt Live-Logs
- [ ] `helix stop <job-id>` stoppt laufenden Job
- [ ] Jobs überleben SSH-Disconnect
- [ ] Status wird in ~/.helix/jobs/ persistiert

## Konsequenzen

### Vorteile
- Terminal nicht mehr blockiert
- Mehrere Projekte parallel möglich
- SSH-Timeout kein Problem mehr
- Besseres Monitoring

### Nachteile
- Mehr Komplexität (Job Management)
- Logs müssen explizit abgerufen werden

### Risiken
- Zombie-Prozesse bei unsauberem Shutdown → Mitigation: PID-Tracking + Cleanup

## Dokumentation

### Zu aktualisieren

- docs/sources/cli.yaml - Neue Commands dokumentieren
- skills/helix/SKILL.md - CLI Reference erweitern
- CLAUDE.md - Quick Reference aktualisieren
