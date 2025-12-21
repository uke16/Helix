# HELIX v4 Bootstrap - Phase 04: CLI

Du baust das Command Line Interface für HELIX v4.

## WICHTIG: Dateipfade

**Erstelle alle Dateien im HAUPT-Verzeichnis, NICHT im Phase-Verzeichnis!**

- ✅ RICHTIG: `/home/aiuser01/helix-v4/src/helix/cli/main.py`
- ❌ FALSCH: `.../phases/04-cli/src/...`

## Bereits vorhanden

### Phase 01 - Core (`/home/aiuser01/helix-v4/src/helix/`)
- `orchestrator.py` - Workflow-Steuerung
- `template_engine.py` - CLAUDE.md Generierung
- `context_manager.py` - Skill-Verwaltung
- `quality_gates.py` - Gate-Prüfungen
- `phase_loader.py` - phases.yaml Loading
- `spec_validator.py` - spec.yaml Validierung
- `llm_client.py` - Multi-Provider LLM
- `claude_runner.py` - Claude Code Subprocess
- `escalation.py` - 2-Stufen Escalation

### Phase 02 - Consultant (`/home/aiuser01/helix-v4/src/helix/consultant/`)
- `meeting.py` - Agentic Meeting
- `expert_manager.py` - Domain-Experten

### Phase 03 - Observability (`/home/aiuser01/helix-v4/src/helix/observability/`)
- `logger.py` - 3-Ebenen Logging
- `metrics.py` - Token & Cost Tracking

## Deine Aufgabe

Erstelle die CLI-Module in `/home/aiuser01/helix-v4/src/helix/cli/`:

### 1. `__init__.py`
```python
from .main import cli
from .commands import run, status, debug, costs, new
```

### 2. `main.py` - Click Entry Point

```python
import click
from pathlib import Path

@click.group()
@click.version_option(version="4.0.0", prog_name="helix")
def cli():
    """HELIX v4 - AI Development Orchestration System"""
    pass

# Commands werden aus commands.py importiert und registriert
```

### 3. `commands.py` - Alle Commands

```python
import click
import asyncio
from pathlib import Path

@click.command()
@click.argument('project_path', type=click.Path(exists=True))
@click.option('--phase', '-p', help='Start from specific phase')
@click.option('--model', '-m', default='claude-opus-4', help='LLM model to use')
@click.option('--dry-run', is_flag=True, help='Show what would be done')
def run(project_path: str, phase: str, model: str, dry_run: bool):
    """Run a HELIX project workflow."""
    # Nutzt Orchestrator aus helix.orchestrator
    pass

@click.command()
@click.argument('project_path', type=click.Path(exists=True))
def status(project_path: str):
    """Show project status and progress."""
    # Zeigt: aktuelle Phase, Gate-Status, Errors
    pass

@click.command()
@click.argument('project_path', type=click.Path(exists=True))
@click.argument('phase', required=False)
@click.option('--tail', '-n', default=50, help='Number of log lines')
def debug(project_path: str, phase: str, tail: int):
    """Show debug logs for a project or phase."""
    # Nutzt HelixLogger aus helix.observability
    pass

@click.command()
@click.argument('project_path', type=click.Path(exists=True))
@click.option('--detailed', '-d', is_flag=True, help='Show per-phase breakdown')
def costs(project_path: str, detailed: bool):
    """Show token usage and costs."""
    # Nutzt MetricsCollector aus helix.observability
    pass

@click.command()
@click.argument('project_name')
@click.option('--type', '-t', 'project_type', default='feature', 
              type=click.Choice(['feature', 'bugfix', 'documentation', 'research']))
@click.option('--output', '-o', type=click.Path(), help='Output directory')
def new(project_name: str, project_type: str, output: str):
    """Create a new HELIX project from template."""
    # Erstellt Projekt-Verzeichnis mit spec.yaml, phases.yaml
    pass
```

## CLI Ausgabe-Format

Nutze Click's Styling für konsistente Ausgabe:

```python
import click

# Erfolg
click.secho("✓ Phase completed", fg="green")

# Fehler
click.secho("✗ Gate failed", fg="red")

# Info
click.secho("→ Running phase: 02-consultant", fg="blue")

# Warnung
click.secho("⚠ Escalation triggered", fg="yellow")

# Tabellen mit click.echo
click.echo(f"{'Phase':<20} {'Status':<10} {'Duration':<10}")
click.echo("-" * 40)
```

## Entry Point für pyproject.toml

Die CLI soll als `helix` Command verfügbar sein:

```toml
[project.scripts]
helix = "helix.cli.main:cli"
```

## Beispiel-Nutzung

```bash
# Neues Projekt erstellen
helix new my-feature --type feature

# Projekt ausführen
helix run ./projects/my-feature

# Ab bestimmter Phase starten
helix run ./projects/my-feature --phase 03-development

# Status prüfen
helix status ./projects/my-feature

# Logs anzeigen
helix debug ./projects/my-feature 02-consultant --tail 100

# Kosten anzeigen
helix costs ./projects/my-feature --detailed
```

## Wichtige Regeln

1. **Click** für CLI (bereits in pyproject.toml)
2. **Async Support** - Commands die async Code aufrufen nutzen `asyncio.run()`
3. **Error Handling** - Saubere Fehlermeldungen, keine Tracebacks für User
4. **Type Hints** überall

## Output

Wenn du fertig bist:
1. Erstelle alle 3 Dateien in `/home/aiuser01/helix-v4/src/helix/cli/`
2. Erstelle `output/result.json` mit Status

```json
{
  "status": "success",
  "files_created": ["__init__.py", "main.py", "commands.py"],
  "location": "/home/aiuser01/helix-v4/src/helix/cli/"
}
```
