# HELIX v4 Bootstrap - Phase 02: Consultant Meeting System

Du baust das Consultant Meeting System für HELIX v4.

## WICHTIG: Dateipfade

**Erstelle alle Dateien im HAUPT-Verzeichnis, NICHT im Phase-Verzeichnis!**

- ✅ RICHTIG: `/home/aiuser01/helix-v4/src/helix/consultant/meeting.py`
- ❌ FALSCH: `/home/aiuser01/helix-v4/projects/.../phases/02-consultant/src/...`

## Bereits vorhanden (Phase 01)

Die Core-Module existieren bereits in `/home/aiuser01/helix-v4/src/helix/`:
- `orchestrator.py` - Workflow-Steuerung
- `template_engine.py` - CLAUDE.md Generierung
- `context_manager.py` - Skill-Verwaltung
- `quality_gates.py` - Gate-Prüfungen
- `phase_loader.py` - phases.yaml Loading
- `spec_validator.py` - spec.yaml Validierung
- `llm_client.py` - Multi-Provider LLM
- `claude_runner.py` - Claude Code Subprocess
- `escalation.py` - 2-Stufen Escalation

## Kontext

Das Consultant System orchestriert "Agentic Meetings" mit Domain-Experten:
- **Meta-Consultant**: Analysiert Request, wählt Experten, moderiert, synthetisiert
- **Domain-Experten**: HELIX, PDM, Encoder, ERP, Infrastructure, Database, Webshop
- **Kommunikation**: Über JSON-Dateien (analysis.json, synthesis.json, etc.)

## Deine Aufgabe

Erstelle die Consultant-Module in `/home/aiuser01/helix-v4/src/helix/consultant/`:

### 1. `__init__.py`
```python
from .meeting import ConsultantMeeting, MeetingResult
from .expert_manager import ExpertManager, ExpertConfig
```

### 2. `meeting.py` - Agentic Meeting Orchestrierung

Das Meeting hat 4 Phasen:
1. **Request-Analyse**: Meta-Consultant erkennt Keywords, wählt Experten
2. **Experten-Analyse**: Jeder Experte analysiert (parallel) und schreibt `analysis.json`
3. **Synthese**: Meta-Consultant kombiniert, erkennt Konflikte
4. **Output**: Generiert `spec.yaml`, `phases.yaml`, `quality-gates.yaml`

Kernklasse:
```python
@dataclass
class MeetingResult:
    spec: dict
    phases: dict
    quality_gates: dict
    transcript: str
    experts_consulted: list[str]
    duration_seconds: float

class ConsultantMeeting:
    def __init__(self, llm_client: LLMClient, expert_manager: ExpertManager):
        ...
    
    async def run(self, project_dir: Path, user_request: str) -> MeetingResult
    async def analyze_request(self, request: str) -> ExpertSelection
    async def run_expert_analyses(self, experts: list[str], request: str) -> dict[str, Analysis]
    async def synthesize(self, analyses: dict) -> Synthesis
    async def generate_output(self, synthesis: Synthesis) -> MeetingResult
```

Nutze `LLMClient` aus `helix.llm_client` für LLM-Calls.

### 3. `expert_manager.py` - Domain-Experten Verwaltung

- Lädt Experten-Definitionen aus `/home/aiuser01/helix-v4/config/domain-experts.yaml`
- Erkennt benötigte Experten aus Keywords
- Bereitet Expert-Verzeichnisse vor (CLAUDE.md, Skills)

Kernklasse:
```python
@dataclass
class ExpertConfig:
    id: str
    name: str
    description: str
    skills: list[str]
    triggers: list[str]  # Keywords die diesen Experten triggern

class ExpertManager:
    def __init__(self, config_path: Path = None):
        self.config_path = config_path or Path("/home/aiuser01/helix-v4/config/domain-experts.yaml")
    
    def load_experts(self) -> dict[str, ExpertConfig]
    def select_experts(self, request: str) -> list[str]
    async def setup_expert_directory(self, expert_id: str, phase_dir: Path, question: str) -> Path
    def generate_expert_claude_md(self, expert: ExpertConfig, question: str) -> str
```

## Domain-Experten (FRABA-spezifisch)

Die `domain-experts.yaml` enthält bereits:
- **helix**: HELIX v4 Architektur, ADRs
- **pdm**: Produktdatenmanagement, BOM, Revisionen
- **encoder**: Drehgeber, POSITAL, Encoder-Technologie
- **erp**: SAP-Integration, Aufträge
- **infrastructure**: Docker, Proxmox, CI/CD
- **database**: PostgreSQL, Neo4j, Qdrant
- **webshop**: FRABA Webshop, Konfigurator

## Meeting-Verzeichnis Struktur (zur Laufzeit)

```
projects/external/{project}/phases/01-consultant/
├── input/
│   └── request.md               # Original User-Request
├── meeting/
│   ├── phase-1-selection/
│   │   └── expert-selection.json
│   ├── phase-2-analysis/
│   │   ├── pdm-expert/
│   │   │   ├── CLAUDE.md
│   │   │   └── output/analysis.json
│   │   └── encoder-expert/
│   │       └── ...
│   └── phase-3-synthesis/
│       └── synthesis.json
├── output/
│   ├── spec.yaml
│   ├── phases.yaml
│   └── quality-gates.yaml
└── logs/
    └── meeting-transcript.md
```

## JSON Formate

### expert-selection.json
```json
{
  "experts": ["pdm", "encoder"],
  "questions": {
    "pdm": "Welche BOM-Felder sind für den Export relevant?",
    "encoder": "Welche Encoder-Spezifikationen müssen berücksichtigt werden?"
  },
  "reasoning": "Request enthält Keywords 'Stückliste' und 'Drehgeber'"
}
```

### analysis.json (von jedem Expert)
```json
{
  "domain": "pdm",
  "findings": ["..."],
  "requirements": ["..."],
  "constraints": ["..."],
  "recommendations": ["..."],
  "dependencies": ["..."],
  "open_questions": ["..."]
}
```

### synthesis.json
```json
{
  "combined_requirements": ["..."],
  "conflicts_resolved": ["..."],
  "open_questions": [],
  "recommended_phases": ["..."]
}
```

## Wichtige Regeln

1. **Type Hints** überall (Python 3.10+ Syntax)
2. **Docstrings** im Google-Style
3. **Async/Await** für I/O-Operationen
4. **Nutze bestehende Module** aus `/home/aiuser01/helix-v4/src/helix/`

## Referenz-ADRs

- `/home/aiuser01/helix-v4/adr/005-consultant-topology-agentic-meetings.md`
- `/home/aiuser01/helix-v4/adr/006-dynamic-phase-definition.md`

## Output

Wenn du fertig bist:
1. Erstelle alle 3 Dateien in `/home/aiuser01/helix-v4/src/helix/consultant/`
2. Erstelle `output/result.json` mit Status

```json
{
  "status": "success",
  "files_created": ["__init__.py", "meeting.py", "expert_manager.py"],
  "location": "/home/aiuser01/helix-v4/src/helix/consultant/",
  "notes": "..."
}
```
