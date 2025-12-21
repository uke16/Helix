# HELIX v4 Bootstrap - Phase 03: Observability

Du baust das Observability-System für HELIX v4.

## WICHTIG: Dateipfade

**Erstelle alle Dateien im HAUPT-Verzeichnis, NICHT im Phase-Verzeichnis!**

- ✅ RICHTIG: `/home/aiuser01/helix-v4/src/helix/observability/logger.py`
- ❌ FALSCH: `.../phases/03-observability/src/...`

## Bereits vorhanden

### Phase 01 - Core (`/home/aiuser01/helix-v4/src/helix/`)
- `orchestrator.py`, `template_engine.py`, `context_manager.py`
- `quality_gates.py`, `phase_loader.py`, `spec_validator.py`
- `llm_client.py`, `claude_runner.py`, `escalation.py`

### Phase 02 - Consultant (`/home/aiuser01/helix-v4/src/helix/consultant/`)
- `meeting.py`, `expert_manager.py`

## Deine Aufgabe

Erstelle die Observability-Module in `/home/aiuser01/helix-v4/src/helix/observability/`:

### 1. `__init__.py`
```python
from .logger import HelixLogger, LogLevel
from .metrics import MetricsCollector, PhaseMetrics, ProjectMetrics
```

### 2. `logger.py` - 3-Ebenen Logging

Logging auf 3 Ebenen:
- **Phase-Logs**: Tool-Calls, Dateien, Errors pro Phase
- **Projekt-Logs**: Aggregiert über alle Phasen
- **System-Logs**: Globale Events (Startup, Shutdown, Crashes)

```python
from enum import Enum
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
import json

class LogLevel(Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

@dataclass
class LogEntry:
    timestamp: datetime
    level: LogLevel
    phase: str | None
    message: str
    details: dict | None = None

class HelixLogger:
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        
    def log(self, level: LogLevel, message: str, phase: str = None, details: dict = None) -> None
    def log_tool_call(self, phase: str, tool: str, args: dict, result: str) -> None
    def log_file_change(self, phase: str, file_path: Path, change_type: str) -> None
    def log_phase_start(self, phase: str) -> None
    def log_phase_end(self, phase: str, success: bool, duration_seconds: float) -> None
    def log_error(self, phase: str, error: Exception, context: dict = None) -> None
    def get_phase_logs(self, phase: str) -> list[LogEntry]
    def get_project_logs(self) -> list[LogEntry]
```

### Log-Dateien Struktur

```
projects/{project}/
├── logs/
│   └── project.jsonl          # Alle Projekt-Events
└── phases/{phase}/logs/
    ├── phase.jsonl            # Phase-Events
    ├── tool-calls.jsonl       # Tool-Aufrufe
    ├── files-changed.json     # Geänderte Dateien
    ├── claude-stdout.log      # Claude Code stdout
    └── claude-stderr.log      # Claude Code stderr
```

### 3. `metrics.py` - Token & Cost Tracking

```python
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

@dataclass
class PhaseMetrics:
    phase_id: str
    start_time: datetime
    end_time: datetime | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    tool_calls: int = 0
    files_created: int = 0
    files_modified: int = 0
    retries: int = 0
    escalations: int = 0

@dataclass
class ProjectMetrics:
    project_id: str
    start_time: datetime
    end_time: datetime | None = None
    phases: dict[str, PhaseMetrics] = field(default_factory=dict)
    total_cost_usd: float = 0.0
    
    def add_phase(self, phase: PhaseMetrics) -> None
    def get_summary(self) -> dict

class MetricsCollector:
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.current_project: ProjectMetrics | None = None
        self.current_phase: PhaseMetrics | None = None
    
    def start_project(self, project_id: str) -> None
    def end_project(self) -> ProjectMetrics
    def start_phase(self, phase_id: str) -> None
    def end_phase(self, success: bool = True) -> PhaseMetrics
    def record_tokens(self, input_tokens: int, output_tokens: int, model: str) -> None
    def record_tool_call(self, tool_name: str) -> None
    def record_file_change(self, change_type: str) -> None
    def save_metrics(self) -> Path
    def load_metrics(self) -> ProjectMetrics | None
```

### Kosten-Berechnung

```python
# Token-zu-Kosten Mapping (pro 1M Tokens)
COST_PER_1M_TOKENS = {
    "claude-opus-4": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4": {"input": 3.0, "output": 15.0},
    "gpt-4o": {"input": 2.5, "output": 10.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.6},
}
```

## Referenz-ADR

- `/home/aiuser01/helix-v4/adr/003-observability-and-debugging.md`

## Wichtige Regeln

1. **Type Hints** (Python 3.10+ Syntax)
2. **Dataclasses** für strukturierte Daten
3. **JSONL-Format** für Logs (eine JSON-Zeile pro Entry)
4. **Thread-safe** - Logging kann aus verschiedenen Threads kommen

## Output

Wenn du fertig bist:
1. Erstelle alle 3 Dateien in `/home/aiuser01/helix-v4/src/helix/observability/`
2. Erstelle `output/result.json` mit Status

```json
{
  "status": "success",
  "files_created": ["__init__.py", "logger.py", "metrics.py"],
  "location": "/home/aiuser01/helix-v4/src/helix/observability/"
}
```
