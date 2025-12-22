# HELIX v4 - Modulare Architektur

## Designprinzipien

1. **Single Responsibility** - Jedes Modul hat EINE Aufgabe
2. **Lose Kopplung** - Module kommunizieren über definierte Interfaces
3. **Dependency Injection** - Abhängigkeiten werden übergeben, nicht hardcoded
4. **Testbarkeit** - Jedes Modul ist einzeln testbar

---

## Modul-Übersicht

```
src/helix/
│
├── __init__.py                 # Package + Version
│
├── ┌─────────────────────────────────────────────────────────┐
│   │  CORE LAYER - Orchestrierung & Workflow                 │
│   ├─────────────────────────────────────────────────────────┤
│   │                                                          │
├── │  orchestrator.py          # Workflow-Steuerung          │
│   │    └── Orchestrator                                     │
│   │        ├── run_project()                                │
│   │        ├── run_phase()                                  │
│   │        └── Nutzt: PhaseLoader, ClaudeRunner, QualityGates│
│   │                                                          │
├── │  phase_loader.py          # Phasen-Definition           │
│   │    └── PhaseLoader                                      │
│   │        ├── load_phases()                                │
│   │        └── Nutzt: SpecValidator                         │
│   │                                                          │
├── │  spec_validator.py        # Schema-Validierung          │
│   │    └── SpecValidator                                    │
│   │        └── validate() → ValidationResult                │
│   │                                                          │
│   └─────────────────────────────────────────────────────────┘
│
├── ┌─────────────────────────────────────────────────────────┐
│   │  EXECUTION LAYER - Claude Code & LLM                    │
│   ├─────────────────────────────────────────────────────────┤
│   │                                                          │
├── │  claude_runner.py         # Claude Code Subprocess      │
│   │    └── ClaudeRunner                                     │
│   │        ├── run_phase()                                  │
│   │        └── get_claude_env()                             │
│   │                                                          │
├── │  llm_client.py            # Multi-Provider LLM          │
│   │    └── LLMClient                                        │
│   │        ├── resolve_model()                              │
│   │        ├── complete()                                   │
│   │        └── Unterstützt: OpenRouter, Anthropic, OpenAI   │
│   │                                                          │
│   └─────────────────────────────────────────────────────────┘
│
├── ┌─────────────────────────────────────────────────────────┐
│   │  CONTEXT LAYER - Templates & Skills                     │
│   ├─────────────────────────────────────────────────────────┤
│   │                                                          │
├── │  template_engine.py       # Jinja2 Templates            │
│   │    └── TemplateEngine                                   │
│   │        ├── render_claude_md()                           │
│   │        └── get_template()                               │
│   │                                                          │
├── │  context_manager.py       # Skill-Verwaltung            │
│   │    └── ContextManager                                   │
│   │        ├── prepare_phase_context()                      │
│   │        ├── get_skills_for_domain()                      │
│   │        └── create_symlinks()                            │
│   │                                                          │
│   └─────────────────────────────────────────────────────────┘
│
├── ┌─────────────────────────────────────────────────────────┐
│   │  QUALITY LAYER - Gates & Escalation                     │
│   ├─────────────────────────────────────────────────────────┤
│   │                                                          │
├── │  quality_gates.py         # Deterministische Prüfungen  │
│   │    └── QualityGateRunner                                │
│   │        ├── check_files_exist()                          │
│   │        ├── check_syntax()                               │
│   │        ├── check_tests_pass()                           │
│   │        └── Returns: GateResult                          │
│   │                                                          │
├── │  escalation.py            # 2-Stufen Escalation         │
│   │    └── EscalationManager                                │
│   │        ├── handle_gate_failure()                        │
│   │        ├── trigger_stufe_1() → Consultant-autonom       │
│   │        └── trigger_stufe_2() → Human-in-Loop            │
│   │                                                          │
│   └─────────────────────────────────────────────────────────┘
│
├── adr/                         # ADR PACKAGE
│   ├── __init__.py              # Exports: ADRParser, ADRValidator, ADRQualityGate
│   ├── parser.py                # ADR Parser
│   │    └── ADRParser
│   │        ├── parse_file()    # Parse from file path
│   │        ├── parse_string()  # Parse from string content
│   │        └── Extracts: ADRDocument, ADRMetadata, ADRSection
│   │
│   ├── validator.py             # ADR Validator
│   │    └── ADRValidator
│   │        ├── validate_file()           # Validate from file
│   │        ├── validate_string()         # Validate from content
│   │        ├── get_completion_status()   # Check acceptance criteria progress
│   │        └── Returns: ValidationResult
│   │
│   └── gate.py                  # ADR Quality Gate
│        └── ADRQualityGate
│            ├── check()           # Validate single ADR
│            ├── check_multiple()  # Validate multiple ADRs
│            └── Returns: GateResult
│
├── consultant/                  # CONSULTANT PACKAGE
│   ├── __init__.py
│   ├── meeting.py              # Agentic Meeting
│   │    └── ConsultantMeeting
│   │        ├── run()
│   │        ├── analyze_request()
│   │        ├── run_expert_analyses()
│   │        └── synthesize()
│   │
│   └── expert_manager.py       # Domain-Experten
│        └── ExpertManager
│            ├── load_experts()
│            ├── select_experts()
│            └── setup_expert_directory()
│
├── observability/               # OBSERVABILITY PACKAGE
│   ├── __init__.py
│   ├── logger.py               # 3-Ebenen Logging
│   │    └── HelixLogger
│   │        ├── log_tool_call()
│   │        ├── log_phase_start/end()
│   │        └── log_error()
│   │
│   └── metrics.py              # Metriken
│        └── MetricsCollector
│            ├── start/end_project()
│            ├── start/end_phase()
│            └── record_tokens/cost()
│
└── cli/                         # CLI PACKAGE
    ├── __init__.py
    ├── main.py                 # Click Entry Point
    │    └── main()
    │
    └── commands.py             # Commands
         ├── cmd_run()
         ├── cmd_status()
         ├── cmd_debug()
         └── cmd_costs()
```

---

## Abhängigkeitsgraph

```
                    CLI (main.py)
                         │
                         ▼
                   Orchestrator
                    /    |    \
                   /     |     \
                  ▼      ▼      ▼
           PhaseLoader  ClaudeRunner  QualityGates
               │            │              │
               ▼            ▼              ▼
         SpecValidator  LLMClient    EscalationManager
                            │              │
                            ▼              ▼
                       (OpenRouter)  ConsultantMeeting
                                          │
                                          ▼
                                    ExpertManager
                                          │
                                          ▼
                                    ContextManager
                                          │
                                          ▼
                                    TemplateEngine
```

---

## Interface-Beispiele

### Orchestrator → QualityGates

```python
# Lose Kopplung durch Interface
class Orchestrator:
    def __init__(self, gate_runner: QualityGateRunner = None):
        self.gates = gate_runner or QualityGateRunner()

    async def run_phase(self, phase_dir: Path, config: PhaseConfig):
        result = await self._execute_phase(phase_dir)

        # Quality Gate prüfen
        gate_result = self.gates.check(
            phase_dir=phase_dir,
            gate_config=config.quality_gate
        )

        if not gate_result.passed:
            return await self.escalation.handle_failure(...)
```

### LLMClient → Provider-Abstraktion

```python
# Provider-unabhängiges Interface
class LLMClient:
    async def complete(self, model_spec: str, messages: list) -> str:
        """Einheitliche API für alle Provider."""
        config = self.resolve_model(model_spec)  # "openrouter:gpt-4o"

        if config.api_format == "openai":
            return await self._complete_openai(config, messages)
        elif config.api_format == "anthropic":
            return await self._complete_anthropic(config, messages)
```

### Testbarkeit durch DI

```python
# Unit Test mit Mock
def test_orchestrator_handles_gate_failure():
    mock_gates = Mock(spec=QualityGateRunner)
    mock_gates.check.return_value = GateResult(passed=False, ...)

    orchestrator = Orchestrator(gate_runner=mock_gates)
    result = await orchestrator.run_phase(...)

    assert mock_gates.check.called
    assert result.escalated
```

---

## Datei-Konventionen

| Typ | Konvention | Beispiel |
|-----|------------|----------|
| Module | `snake_case.py` | `template_engine.py` |
| Klassen | `PascalCase` | `TemplateEngine` |
| Funktionen | `snake_case` | `render_claude_md()` |
| Konstanten | `UPPER_CASE` | `DEFAULT_MODEL` |
| Private | `_prefix` | `_load_config()` |

---

## Package-Struktur Regeln

1. **Ein Package = Ein Concern**
   - `consultant/` = Alles zum Meeting-System
   - `observability/` = Alles zu Logging/Metrics
   - `adr/` = Alles zu Architecture Decision Records

2. **`__init__.py` exportiert Public API**
   ```python
   # consultant/__init__.py
   from .meeting import ConsultantMeeting
   from .expert_manager import ExpertManager

   __all__ = ["ConsultantMeeting", "ExpertManager"]
   ```

3. **Interne Module beginnen mit `_`**
   ```
   consultant/
   ├── meeting.py          # Public
   ├── expert_manager.py   # Public
   └── _utils.py           # Intern
   ```

---

*Erstellt: 2025-12-21*

---

## src/helix/adr/ - ADR (Architecture Decision Records) System

**Purpose:** Parse, validate, and quality-gate Architecture Decision Records following the ADR-086 Template v2 format.

### Modules

| Module | Description |
|--------|-------------|
| `parser.py` | ADRParser - Parses YAML frontmatter and markdown sections from ADR files |
| `validator.py` | ADRValidator - Validates ADRs against template requirements |
| `gate.py` | ADRQualityGate - Quality gate integration for ADR validation |

### Key Classes

```python
from helix.adr import (
    # Parser classes
    ADRParser,
    ADRParseError,
    ADRDocument,
    ADRMetadata,
    ADRSection,
    ADRFiles,
    AcceptanceCriterion,

    # Enums
    ADRStatus,
    ComponentType,
    Classification,
    ChangeScope,

    # Validator classes
    ADRValidator,
    ValidationResult,
    ValidationIssue,
    IssueLevel,
    IssueCategory,

    # Gate classes
    ADRQualityGate,
    register_adr_gate,
)
```

### Usage Examples

```python
from pathlib import Path
from helix.adr import ADRParser, ADRValidator, ADRQualityGate

# Parse an ADR file
parser = ADRParser()
adr = parser.parse_file(Path("adr/086-template.md"))
print(f"ADR-{adr.metadata.adr_id}: {adr.metadata.title}")
print(f"Status: {adr.metadata.status.value}")
print(f"Sections: {list(adr.sections.keys())}")

# Validate an ADR
validator = ADRValidator()
result = validator.validate_file(Path("adr/086-template.md"))
if not result.valid:
    for error in result.errors:
        print(f"ERROR: {error.message}")
    for warning in result.warnings:
        print(f"WARNING: {warning.message}")

# Use as quality gate
gate = ADRQualityGate()
gate_result = gate.check(Path("/project/phases/01"), "output/adr.md")
print(f"Gate passed: {gate_result.passed}")
```

### Quality Gate in phases.yaml

```yaml
phases:
  - id: "3"
    name: ADR Review
    type: review
    quality_gate:
      type: adr_valid
      file: output/feature-adr.md
```

### Template Requirements (ADR-086)

Required YAML header fields:
- `adr_id` - Unique identifier
- `title` - ADR title
- `status` - Proposed|Accepted|Implemented|Superseded|Rejected

Recommended YAML header fields:
- `component_type` - TOOL|NODE|AGENT|PROCESS|SERVICE|SKILL|PROMPT|CONFIG|DOCS|MISC
- `classification` - NEW|UPDATE|FIX|REFACTOR|DEPRECATE
- `change_scope` - major|minor|config|docs|hotfix

Required markdown sections:
1. `## Kontext` - Why is this change needed?
2. `## Entscheidung` - What is the decision?
3. `## Implementation` - Concrete implementation details
4. `## Dokumentation` - Which documentation to update
5. `## Akzeptanzkriterien` - Checkbox list of criteria
6. `## Konsequenzen` - Trade-offs and consequences

See: `docs/ADR-TEMPLATE.md` for the full template.

---

## src/helix/evolution/ - Self-Evolution System

**Purpose:** Enable HELIX to safely evolve itself through an isolated test system.

### Modules

| Module | Description |
|--------|-------------|
| `project.py` | EvolutionProject & EvolutionProjectManager - Manages evolution projects |
| `deployer.py` | Deployer - Deploys changes to test system |
| `validator.py` | Validator - Runs syntax checks, unit tests, E2E tests |
| `integrator.py` | Integrator - Integrates validated changes into production |
| `rag_sync.py` | RAGSync - Syncs Qdrant databases between production and test |

### Key Classes

```python
from helix.evolution import (
    EvolutionProject,
    EvolutionProjectManager,
    EvolutionStatus,
    Deployer,
    Validator,
    Integrator,
    RAGSync,
)
```

### Architecture

```
helix-v4 (Production)        helix-v4-test (Test)
├── src/helix/               ├── src/helix/
├── projects/evolution/      ├── (deployed files)
│   └── {project}/           └── control/helix-control.sh
│       ├── new/
│       └── modified/
```

### Workflow

1. Create evolution project with spec.yaml
2. Development phases generate files in new/ and modified/
3. Deployer copies files to test system
4. Validator runs tests on test system
5. Integrator copies validated files to production
6. RAGSync ensures test system has production data

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/helix/evolution/projects` | GET | List all evolution projects |
| `/helix/evolution/projects/{name}` | GET | Get project details |
| `/helix/evolution/projects/{name}/deploy` | POST | Deploy to test |
| `/helix/evolution/projects/{name}/validate` | POST | Run validation |
| `/helix/evolution/projects/{name}/integrate` | POST | Integrate to production |
| `/helix/evolution/sync-rag` | POST | Sync RAG databases |
| `/helix/evolution/health` | GET | Evolution system health |

---

## ADR System (`src/helix/adr/`)

**Purpose:** Parse and validate Architecture Decision Records (ADRs).

ADRs serve as the **Single Source of Truth** for evolution projects,
defining what files to create, what to modify, and acceptance criteria.

```
src/helix/adr/
├── __init__.py          # Public API exports
├── parser.py            # ADRParser - parse ADR files
├── validator.py         # ADRValidator - validate against template
└── gate.py              # ADRQualityGate - integration with QualityGateRunner
```

### Components

#### ADRParser (`parser.py`)

Parses ADR Markdown files with YAML frontmatter.

```python
from helix.adr import ADRParser, ADRDocument

parser = ADRParser()

# Parse from file
adr = parser.parse_file(Path("adr/001-feature.md"))

# Parse from string
adr = parser.parse_string(content)

# Access parsed data
print(adr.metadata.title)              # "Feature Name"
print(adr.metadata.status)             # ADRStatus.PROPOSED
print(adr.metadata.component_type)     # ComponentType.SERVICE
print(adr.metadata.files.create)       # ["src/module.py", ...]
print(adr.metadata.files.modify)       # ["src/__init__.py", ...]
print(adr.sections["Kontext"].content) # Section content
print(adr.acceptance_criteria)         # [AcceptanceCriterion(...), ...]
```

**Data Classes:**

| Class | Purpose |
|-------|---------|
| `ADRDocument` | Complete parsed ADR |
| `ADRMetadata` | YAML header data |
| `ADRSection` | Markdown section |
| `ADRFiles` | files.create/modify/docs |
| `AcceptanceCriterion` | Checkbox item |

**Enums:**

| Enum | Values |
|------|--------|
| `ADRStatus` | Proposed, Accepted, Implemented, Superseded, Rejected |
| `ComponentType` | TOOL, NODE, AGENT, PROCESS, SERVICE, SKILL, PROMPT, CONFIG, DOCS, MISC |
| `Classification` | NEW, UPDATE, FIX, REFACTOR, DEPRECATE |
| `ChangeScope` | major, minor, config, docs, hotfix |

#### ADRValidator (`validator.py`)

Validates ADRs against template requirements.

```python
from helix.adr.validator import ADRValidator, ValidationResult

validator = ADRValidator()
result = validator.validate_file(Path("adr/001-feature.md"))

if result.valid:
    print("ADR is valid")
else:
    for error in result.errors:
        print(f"Error: {error.message}")
    for warning in result.warnings:
        print(f"Warning: {warning.message}")
```

**Validation Checks:**

| Check | Severity |
|-------|----------|
| Valid YAML frontmatter | Error |
| Required fields (adr_id, title, status) | Error |
| Required sections (Kontext, Entscheidung, ...) | Error |
| Files section not empty | Error |
| Acceptance criteria present | Error |
| Empty sections | Warning |
| Few acceptance criteria (<3) | Warning |

#### ADRQualityGate (`gate.py`)

Integration with HELIX quality gate system.

```python
from helix.adr.gate import ADRQualityGate, register_adr_gate
from helix.quality_gates import QualityGateRunner

# Register with runner
runner = QualityGateRunner()
register_adr_gate(runner)

# Use in quality gate config
# phases.yaml:
#   quality_gate:
#     type: adr_valid
#     adr_path: ADR-feature.md
```

### Integration Points

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Consultant    │────▶│   ADR System    │────▶│  Quality Gates  │
│                 │     │                 │     │                 │
│ Creates ADR     │     │ Validates ADR   │     │ Uses ADR.files  │
│                 │     │ Parses metadata │     │ for verification│
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │    Templates    │
                        │                 │
                        │ Shows expected  │
                        │ files from ADR  │
                        └─────────────────┘
```

### Tests

```bash
# Run ADR system tests
python3 -m pytest tests/adr/ -v

# Test files
tests/adr/
├── conftest.py           # Shared fixtures
├── test_parser.py        # Parser tests (34 tests)
├── test_validator.py     # Validator tests (30 tests)
└── test_gate.py          # Gate integration tests (22 tests)
```

---

## Verification System (`src/helix/evolution/verification.py`)

**Purpose:** Post-phase output verification for Evolution projects.

### Components

#### PhaseVerifier

Verifies that phase outputs match expectations.

```python
from helix.evolution import PhaseVerifier, VerificationResult

verifier = PhaseVerifier(project_path)
result = verifier.verify_phase_output(
    phase_id="2",
    phase_dir=Path("phases/2"),
    expected_files=["src/module.py", "tests/test_module.py"]
)

if not result.success:
    print(result.missing_files)
    print(result.syntax_errors)
```

#### Verification Checks

| Check | Method |
|-------|--------|
| File existence | Searches output/, new/, phase_dir |
| Python syntax | AST parsing |

### Integration

- **streaming.py**: Automatic verification after each phase
- **verify_phase tool**: CLI for Claude to self-verify
- **Templates**: Instructions for verification

### Related

- [ADR-011: Post-Phase Verification](../adr/011-post-phase-verification.md)
- [verify_phase.py](src/helix/tools/verify_phase.py)
