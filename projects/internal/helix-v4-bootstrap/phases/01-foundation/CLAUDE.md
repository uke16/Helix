# HELIX v4 Bootstrap - Phase 01: Foundation

Du baust das Core-Framework für HELIX v4.

## Kontext

HELIX v4 ist ein AI-Entwicklungssystem das:
- Claude Code CLI als Agent-Runtime nutzt (nicht eigene Agents)
- CLAUDE.md + Jinja2 Templates für Context-Loading verwendet
- Datei-basierte Kommunikation zwischen Phasen hat (JSON/YAML)
- Python async für Orchestrierung nutzt (kein LangGraph)

## Deine Aufgabe

Erstelle die Core-Module in `/home/aiuser01/helix-v4/src/helix/`:

### 1. `__init__.py`
```python
__version__ = "4.0.0"
```

### 2. `orchestrator.py` - Workflow-Steuerung
- Lädt `phases.yaml` aus Projekt-Verzeichnis
- Führt Phasen sequentiell aus
- Ruft Quality Gates nach jeder Phase auf
- Handled Escalation bei Gate-Failures
- Nutzt `asyncio` für async Ausführung

Kernklasse:
```python
class Orchestrator:
    async def run_project(self, project_dir: Path) -> ProjectResult
    async def run_phase(self, phase_dir: Path, phase_config: PhaseConfig) -> PhaseResult
    async def check_quality_gate(self, phase_dir: Path, gate_config: dict) -> GateResult
```

### 3. `template_engine.py` - CLAUDE.md Generierung
- Jinja2-basiert
- Lädt Templates aus `/home/aiuser01/helix-v4/templates/`
- Unterstützt Template-Vererbung (2 Ebenen: `_base.md` → `python.md`)
- Generiert CLAUDE.md basierend auf `spec.yaml`

Kernklasse:
```python
class TemplateEngine:
    def render_claude_md(self, template_name: str, context: dict) -> str
    def get_template(self, name: str) -> Template
```

### 4. `context_manager.py` - Skill-Verwaltung
- Verwaltet Skills in `/home/aiuser01/helix-v4/skills/`
- Erstellt Symlinks in Phase-Verzeichnissen
- Erkennt benötigte Skills aus `spec.yaml`

Kernklasse:
```python
class ContextManager:
    def prepare_phase_context(self, phase_dir: Path, spec: dict) -> None
    def get_skills_for_domain(self, domain: str) -> list[Path]
    def get_skills_for_language(self, language: str) -> list[Path]
```

### 5. `quality_gates.py` - Deterministische Prüfungen
- Gate-Typen: `files_exist`, `syntax_check`, `tests_pass`, `review_approved`
- Gibt strukturiertes `GateResult` zurück
- Sammelt Feedback für Retry

Kernklasse:
```python
@dataclass
class GateResult:
    passed: bool
    gate_type: str
    message: str
    details: dict
    
class QualityGateRunner:
    def check_files_exist(self, phase_dir: Path, expected: list[str]) -> GateResult
    def check_syntax(self, phase_dir: Path, language: str) -> GateResult
    def check_tests_pass(self, phase_dir: Path, command: str) -> GateResult
```

### 6. `phase_loader.py` - Phasen-Definition laden
- Lädt und validiert `phases.yaml`
- Unterstützt Projekt-Typ Templates
- Gibt `PhaseConfig` Objekte zurück

Kernklasse:
```python
@dataclass
class PhaseConfig:
    id: str
    name: str
    type: str  # meeting | development | review | documentation | test
    config: dict
    input: dict
    output: dict
    quality_gate: dict

class PhaseLoader:
    def load_phases(self, project_dir: Path) -> list[PhaseConfig]
```

### 7. `spec_validator.py` - Spec-Schema Validierung
- Validiert `spec.yaml` gegen Schema
- Prüft required fields: `meta.id`, `meta.domain`, `implementation.summary`, etc.
- Gibt `ValidationResult` mit Errors/Warnings zurück

Kernklasse:
```python
@dataclass
class ValidationResult:
    valid: bool
    errors: list[ValidationError]
    warnings: list[ValidationError]

class SpecValidator:
    def validate(self, spec_path: Path) -> ValidationResult
```

### 8. `llm_client.py` - Multi-Provider LLM
- Unterstützt: OpenRouter, Anthropic, OpenAI, xAI
- Lädt Config aus `/home/aiuser01/helix-v4/config/llm-providers.yaml`
- Unified Interface für alle Provider

Kernklasse:
```python
@dataclass
class ModelConfig:
    provider: str
    model_id: str
    base_url: str
    api_format: str  # openai | anthropic

class LLMClient:
    def resolve_model(self, model_spec: str) -> ModelConfig
    async def complete(self, model_spec: str, messages: list[dict]) -> str
```

### 9. `claude_runner.py` - Claude Code Subprocess
- Startet Claude Code CLI als Subprocess
- Setzt Environment (API Keys, Model)
- Sammelt Output (stdout, stderr, JSON)

Kernklasse:
```python
class ClaudeRunner:
    async def run_phase(self, phase_dir: Path, model: str = None) -> ClaudeResult
    def get_claude_env(self, model_spec: str) -> dict
```

### 10. `escalation.py` - 2-Stufen Escalation
- Stufe 1: Consultant-autonom (Model-Switch, Plan-Revert, Hints)
- Stufe 2: Human-in-the-Loop
- JSON-basierte Kommunikation

Kernklasse:
```python
class EscalationManager:
    async def handle_gate_failure(self, phase_dir: Path, gate_result: GateResult, state: EscalationState) -> EscalationAction
    async def trigger_stufe_1(self, phase_dir: Path, state: EscalationState) -> EscalationAction
    async def trigger_stufe_2(self, phase_dir: Path, state: EscalationState) -> EscalationAction
```

## Wichtige Regeln

1. **Type Hints** überall (Python 3.10+ Syntax)
2. **Docstrings** im Google-Style
3. **Async/Await** für I/O-Operationen
4. **Dataclasses** für strukturierte Daten
5. **Path** aus pathlib für Dateipfade
6. **Keine externen Dependencies** außer: `jinja2`, `pyyaml`, `httpx`, `pydantic`

## Referenz-ADRs

Die vollständigen Spezifikationen findest du in:
- `/home/aiuser01/helix-v4/adr/000-vision-and-architecture.md`
- `/home/aiuser01/helix-v4/adr/001-template-and-context-system.md`
- `/home/aiuser01/helix-v4/adr/002-quality-gate-system.md`
- `/home/aiuser01/helix-v4/adr/003-observability-and-debugging.md`
- `/home/aiuser01/helix-v4/adr/004-escalation-meeting-system.md`
- `/home/aiuser01/helix-v4/adr/007-multi-provider-llm-configuration.md`

## Output

Wenn du fertig bist, erstelle:
- Alle 10 Python-Dateien in `/home/aiuser01/helix-v4/src/helix/`
- `output/result.json` mit Status

```json
{
  "status": "success",
  "files_created": ["__init__.py", "orchestrator.py", ...],
  "notes": "..."
}
```
