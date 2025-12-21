# ADR-003: Observability & Debugging

**Status:** Proposed  
**Datum:** 2025-12-21  
**Bezug:** ADR-000

---

## Kontext

Jede Claude Code Instanz erzeugt Output. Der Orchestrator macht zusätzliche Arbeit.
Wir brauchen volle Transparenz für Debugging und Analyse.

---

## Entscheidung

### 3-Ebenen Logging-Architektur

```
┌─────────────────────────────────────────────────────────────────┐
│  EBENE 1: Phase-Logs (pro Claude Code Instanz)                  │
├─────────────────────────────────────────────────────────────────┤
│  EBENE 2: Projekt-Logs (Orchestrator)                           │
├─────────────────────────────────────────────────────────────────┤
│  EBENE 3: System-Logs (global, aggregiert)                      │
└─────────────────────────────────────────────────────────────────┘
```

### Ebene 1: Phase-Logs

Jede Phase hat ein `logs/` Verzeichnis:

```
phases/02-developer/logs/
├── claude-stdout.log      # Roher stdout von Claude Code
├── claude-stderr.log      # Roher stderr (Errors, Warnings)
├── claude-output.json     # Strukturierter Output (--output-format json)
├── session-transcript.md  # Lesbare Conversation
├── tool-calls.jsonl       # Alle Tool-Aufrufe
├── files-changed.json     # Was wurde erstellt/geändert
├── metrics.json           # Token-Usage, Duration, Costs
└── errors.json            # Fehler falls aufgetreten
```

#### Claude Code Aufruf mit Logging

```python
# orchestrator.py

async def run_claude_phase(self, phase_dir: Path) -> PhaseResult:
    """Führt Claude Code aus mit vollem Logging."""
    
    logs_dir = phase_dir / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    started_at = datetime.now()
    
    # Claude Code starten
    process = await asyncio.create_subprocess_exec(
        "claude",
        "--print",                      # Non-interactive
        "--output-format", "json",      # Strukturierter Output
        "--verbose",                    # Mehr Details
        cwd=str(phase_dir),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={
            **os.environ,
            "ANTHROPIC_BASE_URL": "https://openrouter.ai/api/v1",
            "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY"),
        }
    )
    
    stdout, stderr = await process.communicate()
    completed_at = datetime.now()
    
    # Rohe Logs speichern
    (logs_dir / "claude-stdout.log").write_bytes(stdout)
    (logs_dir / "claude-stderr.log").write_bytes(stderr)
    
    # JSON Output parsen
    try:
        output = json.loads(stdout.decode())
        (logs_dir / "claude-output.json").write_text(
            json.dumps(output, indent=2)
        )
    except json.JSONDecodeError:
        output = {"raw": stdout.decode(), "parse_error": True}
    
    # Tool Calls extrahieren
    tool_calls = self._extract_tool_calls(output)
    with open(logs_dir / "tool-calls.jsonl", "w") as f:
        for call in tool_calls:
            f.write(json.dumps(call) + "\n")
    
    # Files Changed extrahieren
    files_changed = self._extract_file_changes(tool_calls)
    (logs_dir / "files-changed.json").write_text(
        json.dumps(files_changed, indent=2)
    )
    
    # Metriken berechnen
    metrics = self._calculate_metrics(
        output=output,
        started_at=started_at,
        completed_at=completed_at,
        tool_calls=tool_calls
    )
    (logs_dir / "metrics.json").write_text(
        json.dumps(metrics, indent=2)
    )
    
    # Transcript generieren
    transcript = self._generate_transcript(output)
    (logs_dir / "session-transcript.md").write_text(transcript)
    
    return PhaseResult(
        success=process.returncode == 0,
        output=output,
        metrics=metrics,
        files_changed=files_changed
    )
```

#### Metriken-Schema

```python
@dataclass
class PhaseMetrics:
    # Timing
    started_at: str
    completed_at: str
    duration_seconds: float
    
    # Token Usage
    tokens_input: int
    tokens_output: int
    tokens_total: int
    
    # Kosten (geschätzt)
    cost_usd: float
    model_used: str
    
    # Tool Usage
    tool_calls_total: int
    tool_calls_by_type: dict[str, int]
    # z.B. {"Read": 5, "Write": 3, "Bash": 2}
    
    # Ergebnis
    files_created: int
    files_modified: int
    lines_written: int
    
    # Status
    success: bool
    error_count: int
```

### Ebene 2: Projekt-Logs

Pro Projekt ein Orchestrator-Log:

```
projects/external/bom-export-csv/
├── state.json              # Aktueller State
├── state-history.jsonl     # Alle State-Änderungen
├── orchestrator.log        # Orchestrator Actions
├── quality-gates.log       # Gate Results
└── summary.json            # Projekt-Zusammenfassung
```

#### State History

```python
def update_state(self, project_dir: Path, updates: dict):
    """Aktualisiert State und schreibt History."""
    
    state_file = project_dir / "state.json"
    history_file = project_dir / "state-history.jsonl"
    
    # Aktuellen State laden
    state = json.loads(state_file.read_text())
    
    # Updates anwenden
    old_state = state.copy()
    state.update(updates)
    state["updated_at"] = datetime.now().isoformat()
    
    # State speichern
    state_file.write_text(json.dumps(state, indent=2))
    
    # History Entry
    history_entry = {
        "timestamp": datetime.now().isoformat(),
        "changes": {k: {"old": old_state.get(k), "new": v} 
                   for k, v in updates.items()},
    }
    
    with open(history_file, "a") as f:
        f.write(json.dumps(history_entry) + "\n")
```

#### Quality Gate Logging

```python
def log_quality_gate(self, project_dir: Path, result: GateResult):
    """Loggt Quality Gate Ergebnis."""
    
    log_file = project_dir / "quality-gates.log"
    
    emoji = "✅" if result.passed else "❌"
    
    log_entry = f"""
{datetime.now().isoformat()} | {result.gate} | {emoji} {"PASS" if result.passed else "FAIL"}
  Message: {result.message}
  Details: {json.dumps(result.details) if result.details else "None"}
"""
    
    with open(log_file, "a") as f:
        f.write(log_entry)
```

### Ebene 3: System-Logs

Globale, aggregierte Logs:

```
helix-v4/logs/
├── system.log              # Alle Projekte, alle Phasen
├── errors.jsonl            # Alle Errors (strukturiert)
├── metrics-daily.jsonl     # Tägliche Metriken
└── audit.log               # Wer hat was wann gestartet
```

#### Zentraler Logger

```python
# observability.py

import logging
from pathlib import Path

class HelixLogger:
    """Zentrales Logging für HELIX v4."""
    
    def __init__(self, logs_dir: Path):
        self.logs_dir = logs_dir
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        # System Logger
        self.system_logger = self._setup_logger(
            "helix.system",
            logs_dir / "system.log"
        )
        
        # Audit Logger
        self.audit_logger = self._setup_logger(
            "helix.audit",
            logs_dir / "audit.log"
        )
    
    def _setup_logger(self, name: str, file: Path) -> logging.Logger:
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        
        handler = logging.FileHandler(file)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s'
        ))
        logger.addHandler(handler)
        
        return logger
    
    def log_phase_start(self, project_id: str, phase: str):
        self.system_logger.info(f"[{project_id}] Phase started: {phase}")
    
    def log_phase_complete(self, project_id: str, phase: str, metrics: dict):
        self.system_logger.info(
            f"[{project_id}] Phase completed: {phase} | "
            f"Duration: {metrics['duration_seconds']:.1f}s | "
            f"Tokens: {metrics['tokens_total']} | "
            f"Cost: ${metrics['cost_usd']:.4f}"
        )
    
    def log_error(self, project_id: str, phase: str, error: Exception):
        self.system_logger.error(
            f"[{project_id}] Error in {phase}: {error}"
        )
        
        # Strukturiert in errors.jsonl
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "project_id": project_id,
            "phase": phase,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc()
        }
        
        with open(self.logs_dir / "errors.jsonl", "a") as f:
            f.write(json.dumps(error_entry) + "\n")
    
    def log_audit(self, user: str, action: str, details: dict):
        self.audit_logger.info(
            f"User: {user} | Action: {action} | {json.dumps(details)}"
        )
    
    def aggregate_daily_metrics(self):
        """Aggregiert Metriken aller Projekte für heute."""
        
        today = date.today().isoformat()
        
        total_tokens = 0
        total_cost = 0.0
        total_phases = 0
        projects_active = set()
        
        # Alle Projekte durchgehen
        for project_dir in (PROJECTS_DIR / "external").iterdir():
            if not project_dir.is_dir():
                continue
            
            for phase_dir in (project_dir / "phases").iterdir():
                metrics_file = phase_dir / "logs" / "metrics.json"
                if metrics_file.exists():
                    metrics = json.loads(metrics_file.read_text())
                    
                    # Nur heute
                    if metrics.get("started_at", "").startswith(today):
                        total_tokens += metrics.get("tokens_total", 0)
                        total_cost += metrics.get("cost_usd", 0)
                        total_phases += 1
                        projects_active.add(project_dir.name)
        
        daily_metrics = {
            "date": today,
            "tokens_total": total_tokens,
            "cost_usd_total": total_cost,
            "phases_completed": total_phases,
            "projects_active": len(projects_active)
        }
        
        with open(self.logs_dir / "metrics-daily.jsonl", "a") as f:
            f.write(json.dumps(daily_metrics) + "\n")
        
        return daily_metrics
```

---

## Debug CLI

```python
# helix_debug.py

import click
from pathlib import Path

@click.group()
def cli():
    """HELIX v4 Debug Tools"""
    pass


@cli.command()
@click.argument("project_id")
def status(project_id: str):
    """Zeigt Projekt-Status."""
    
    project_dir = PROJECTS_DIR / "external" / project_id
    state = json.loads((project_dir / "state.json").read_text())
    
    click.echo(f"""
╔══════════════════════════════════════════════════════════╗
║  Project: {project_id:<46} ║
╠══════════════════════════════════════════════════════════╣
║  Phase:     {state['phase']:<44} ║
║  Created:   {state['created']:<44} ║
║  Updated:   {state.get('updated_at', 'N/A'):<44} ║
╠══════════════════════════════════════════════════════════╣
║  Quality Gates:                                          ║
""")
    
    for gate, result in state.get("quality_gates", {}).items():
        status = "✅" if result.get("passed") else "❌"
        click.echo(f"║    {gate}: {status} {result.get('message', ''):<40} ║")
    
    click.echo("╚══════════════════════════════════════════════════════════╝")


@cli.command()
@click.argument("project_id")
@click.argument("phase")
@click.option("-n", "--lines", default=50)
def logs(project_id: str, phase: str, lines: int):
    """Zeigt Phase-Logs."""
    
    phase_dir = PROJECTS_DIR / "external" / project_id / "phases" / phase
    log_file = phase_dir / "logs" / "claude-stdout.log"
    
    if log_file.exists():
        content = log_file.read_text().split("\n")
        for line in content[-lines:]:
            click.echo(line)
    else:
        click.echo(f"No logs found for {phase}")


@cli.command()
@click.argument("project_id")
@click.argument("phase")
def transcript(project_id: str, phase: str):
    """Zeigt Session-Transcript."""
    
    phase_dir = PROJECTS_DIR / "external" / project_id / "phases" / phase
    transcript_file = phase_dir / "logs" / "session-transcript.md"
    
    if transcript_file.exists():
        click.echo(transcript_file.read_text())
    else:
        click.echo("No transcript available")


@cli.command()
@click.argument("project_id")
def costs(project_id: str):
    """Zeigt Kosten-Übersicht."""
    
    project_dir = PROJECTS_DIR / "external" / project_id
    
    click.echo(f"\n  Cost Summary: {project_id}\n")
    click.echo("  Phase                    Tokens      Cost")
    click.echo("  " + "-" * 45)
    
    total_tokens = 0
    total_cost = 0.0
    
    for phase_dir in sorted((project_dir / "phases").iterdir()):
        metrics_file = phase_dir / "logs" / "metrics.json"
        if metrics_file.exists():
            metrics = json.loads(metrics_file.read_text())
            tokens = metrics.get("tokens_total", 0)
            cost = metrics.get("cost_usd", 0)
            
            total_tokens += tokens
            total_cost += cost
            
            click.echo(f"  {phase_dir.name:<22} {tokens:>8}  ${cost:>8.4f}")
    
    click.echo("  " + "-" * 45)
    click.echo(f"  {'TOTAL':<22} {total_tokens:>8}  ${total_cost:>8.4f}")


@cli.command()
@click.argument("project_id")
@click.argument("phase")
def tools(project_id: str, phase: str):
    """Zeigt Tool-Usage."""
    
    phase_dir = PROJECTS_DIR / "external" / project_id / "phases" / phase
    tool_file = phase_dir / "logs" / "tool-calls.jsonl"
    
    if not tool_file.exists():
        click.echo("No tool calls recorded")
        return
    
    tool_counts = {}
    
    with open(tool_file) as f:
        for line in f:
            call = json.loads(line)
            tool = call.get("tool", "unknown")
            tool_counts[tool] = tool_counts.get(tool, 0) + 1
    
    click.echo(f"\n  Tool Usage: {phase}\n")
    for tool, count in sorted(tool_counts.items(), key=lambda x: -x[1]):
        bar = "█" * min(count, 30)
        click.echo(f"  {tool:<15} {count:>4} {bar}")


@cli.command()
def daily():
    """Zeigt tägliche Metriken."""
    
    metrics_file = LOGS_DIR / "metrics-daily.jsonl"
    
    if not metrics_file.exists():
        click.echo("No daily metrics yet")
        return
    
    click.echo("\n  Daily Metrics\n")
    click.echo("  Date         Tokens     Cost    Phases  Projects")
    click.echo("  " + "-" * 55)
    
    with open(metrics_file) as f:
        for line in f:
            m = json.loads(line)
            click.echo(
                f"  {m['date']}  {m['tokens_total']:>8}  "
                f"${m['cost_usd_total']:>7.2f}  {m['phases_completed']:>6}  "
                f"{m['projects_active']:>8}"
            )


if __name__ == "__main__":
    cli()
```

---

## Verwendung

```bash
# Projekt-Status
python helix_debug.py status bom-export-csv

# Phase-Logs (letzte 100 Zeilen)
python helix_debug.py logs bom-export-csv 02-developer -n 100

# Session-Transcript
python helix_debug.py transcript bom-export-csv 02-developer

# Kosten-Übersicht
python helix_debug.py costs bom-export-csv

# Tool-Usage
python helix_debug.py tools bom-export-csv 02-developer

# Tägliche Metriken
python helix_debug.py daily
```

---

## Konsequenzen

### Positiv
- Volle Transparenz über alle Phasen
- Strukturierte Logs für Analyse
- Cost Tracking
- Einfaches CLI für Debugging

### Negativ
- Mehr Disk-Space für Logs
- Log-Rotation nötig

---

## Referenzen

- ADR-000: Vision & Architecture
- HELIX v3 ADR-040a: Prometheus Metrics

