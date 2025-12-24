<!-- AUTO-GENERATED from docs/sources/*.yaml -->
<!-- Template: docs/templates/SKILL.md.j2 -->
<!-- Regenerate: python -m helix.tools.docs_compiler compile -->


# HELIX Core Skill

> Detaillierte Dokumentation des HELIX Orchestration Systems.
>
> Lies diese Datei wenn du an HELIX selbst arbeitest oder die Details verstehen musst.

---

## Übersicht

HELIX v4 ist ein AI Development Orchestration System, das Claude Code Instanzen
koordiniert um Software zu entwickeln. Es organisiert Arbeit in Phasen mit
Quality Gates zur automatischen Validierung.

### Kernkonzepte

1. **Phasen** - Sequentielle Entwicklungsschritte
2. **Quality Gates** - Automatische Validierung von Outputs
3. **Skills** - Domain-spezifisches Wissen
4. **Evolution** - Sichere Selbst-Modifikation

---

## Phase Types

HELIX unterstützt verschiedene Phase-Typen für unterschiedliche Aufgaben:

### Consultant Meeting (`consultant`)

Interactive session to gather requirements and create ADR/spec documents

**Rolle:** Consultant

**Outputs:**
- `adr` - Architecture Decision Record
- `spec` - Project specification (spec.yaml)
- `phases` - Phase configuration (phases.yaml)

**Workflow:**
1. **Read user request**: Parse input/request.md
2. **Load domain skills**: Read relevant skills/*.md
3. **Clarify requirements**: Interactive Q&A with user
4. **Generate outputs**: Create spec.yaml, phases.yaml, ADR

**Quality Gates:** adr_valid, files_exist

**Beispiel:**

```yaml
phases:
  - id: "1"
    name: "Requirements Gathering"
    type: consultant
    quality_gate:
      type: adr_valid
      file: output/feature-adr.md
```

Consultant phase creates an ADR that must be valid

---

### Development (`development`)

Code implementation based on specification and previous phase outputs

**Rolle:** Developer

**Outputs:**
- `code` - Source code files (*.py, *.ts, etc.)
- `tests` - Unit tests (test_*.py)

**Workflow:**
1. **Read specification**: Parse spec.yaml and phase CLAUDE.md
2. **Read previous outputs**: Load input/ from previous phases
3. **Implement**: Write code to output/
4. **Self-verify**: Run syntax checks

**Quality Gates:** files_exist, syntax_check

**Beispiel:**

```yaml
phases:
  - id: "2"
    name: "Implementation"
    type: development
    quality_gate:
      type: syntax_check
      file_patterns:
        - "output/**/*.py"
```

Development phase with syntax validation

---

### Testing (`testing`)

Execute test suites and validate functionality

**Rolle:** Developer

**Outputs:**
- `test_results` - Test execution logs and reports
- `coverage` - Coverage reports (optional)

**Workflow:**
1. **Setup environment**: Install dependencies if needed
2. **Run tests**: Execute pytest/jest
3. **Analyze results**: Check for failures
4. **Fix failures**: Update code if tests fail

**Quality Gates:** tests_pass

**Beispiel:**

```yaml
phases:
  - id: "3"
    name: "Testing"
    type: testing
    quality_gate:
      type: tests_pass
      test_command: "pytest -v"
      timeout: 300
```

Testing phase runs pytest and requires all tests to pass

---

### Review (`review`)

LLM-based or human review of phase outputs

**Rolle:** Reviewer

**Outputs:**
- `review_report` - Review findings and recommendations
- `approval` - Approval status (approved/rejected)

**Workflow:**
1. **Load artifacts**: Read files to be reviewed
2. **Apply criteria**: Check against review criteria
3. **Document findings**: Write review report
4. **Decide**: Approve or reject with reasons

**Quality Gates:** review_approved

**Beispiel:**

```yaml
phases:
  - id: "4"
    name: "Code Review"
    type: review
    quality_gate:
      type: review_approved
      review_type: code
      criteria:
        - "No hardcoded credentials"
        - "Type hints present"
```

Review phase with custom criteria

---

### Documentation (`documentation`)

Create or update technical documentation

**Rolle:** Documentation

**Outputs:**
- `docs` - Markdown documentation files
- `diagrams` - Architecture diagrams (optional)

**Workflow:**
1. **Analyze implementation**: Read code and outputs from previous phases
2. **Update docs**: Write/update documentation files
3. **Validate links**: Check all references are valid
4. **Compile**: Run docs compiler if applicable

**Quality Gates:** files_exist, docs_compiled

**Beispiel:**

```yaml
phases:
  - id: "5"
    name: "Documentation"
    type: documentation
    quality_gate:
      type: files_exist
      required_files:
        - output/SKILL.md
        - output/API.md
```

Documentation phase creates skill and API docs

---

### Integration (`integration`)

Merge changes into main codebase with safety checks

**Rolle:** Developer

**Outputs:**
- `merged_code` - Code integrated into target location
- `backup` - Git tag or backup before integration

**Workflow:**
1. **Validate**: Run full test suite
2. **Backup**: Create git tag
3. **Merge**: Copy files to target locations
4. **Verify**: Run tests again post-merge

**Quality Gates:** tests_pass, files_exist

**Beispiel:**

```yaml
phases:
  - id: "6"
    name: "Integration"
    type: integration
    quality_gate:
      type: tests_pass
      test_command: "pytest tests/ -v"
```

Integration phase with full test validation

---


## Quality Gates

Quality Gates validieren automatisch die Outputs einer Phase.

### Kategorien

- **Deterministic** - Automatisch prüfbar, immer gleiches Ergebnis
- **LLM-based** - Nutzt LLM zur Bewertung

---

### `files_exist` - Files Exist

Checks that all expected output files exist after a phase completes

**Kategorie:** deterministic
**Verwendung:** development, documentation

#### Parameter

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `required_files` | `list[str]` | Yes | List of expected file paths relative to phase output directory |

#### Beispiel

```yaml
quality_gate:
  type: files_exist
  required_files:
    - output/result.md
    - output/schema.py
```

Validates that both files exist after the phase completes



#### Implementation

- Module: `helix.quality_gates`
- Class: `QualityGateRunner`
- Method: `check_files_exist`


---

### `syntax_check` - Syntax Check

Validates Python/TypeScript/Go syntax of source files using AST parsing

**Kategorie:** deterministic
**Verwendung:** development

#### Parameter

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `file_patterns` | `list[str]` | No | Glob patterns for files to check |
| `languages` | `list[str]` | No | Languages to check (python, typescript, go) |

#### Beispiel

```yaml
quality_gate:
  type: syntax_check
  file_patterns:
    - "src/**/*.py"
    - "tests/**/*.py"
```

Validates Python syntax for all .py files in src/ and tests/



#### Implementation

- Module: `helix.quality_gates`
- Class: `QualityGateRunner`
- Method: `check_syntax`


---

### `tests_pass` - Tests Pass

Executes test suite (pytest/jest) and verifies all tests pass

**Kategorie:** deterministic
**Verwendung:** testing

#### Parameter

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `test_command` | `str` | No | Test command to execute |
| `working_dir` | `str` | No | Working directory for test execution |
| `timeout` | `int` | No | Timeout in seconds for test execution |

#### Beispiel

```yaml
quality_gate:
  type: tests_pass
  test_command: "pytest -v --tb=short"
  timeout: 600
```

Runs pytest with verbose output and 10 minute timeout



#### Implementation

- Module: `helix.quality_gates`
- Class: `QualityGateRunner`
- Method: `check_tests_pass`


---

### `review_approved` - Review Approved

LLM-based review of phase output against specified criteria

**Kategorie:** llm_based
**Verwendung:** review

#### Parameter

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `review_type` | `str` | Yes | Type of review to perform |
| `criteria` | `list[str]` | No | Additional review criteria beyond defaults |
| `files` | `list[str]` | No | Specific files to review (defaults to all output files) |

#### Beispiel

```yaml
quality_gate:
  type: review_approved
  review_type: code
  criteria:
    - "No hardcoded credentials"
    - "Type hints present on all functions"
    - "Docstrings for public API"
```

LLM reviews code for security and documentation standards


#### Default Criteria

**Code:**
- Code follows project conventions
- No obvious bugs or logic errors
- Error handling is appropriate

**Architecture:**
- Design aligns with ADR decisions
- No unnecessary complexity
- Interfaces are well-defined

**Documentation:**
- Content is accurate and complete
- Examples are working
- Links are valid


#### Implementation

- Module: `helix.quality_gates`
- Class: `QualityGateRunner`
- Method: `check_review_approved`


---

### `adr_valid` - ADR Valid

Validates Architecture Decision Records against the ADR template (ADR-086 format)

**Kategorie:** deterministic
**Verwendung:** consultant, review

#### Parameter

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `file` | `str` | Yes | Path to the ADR file to validate |

#### Beispiel

```yaml
quality_gate:
  type: adr_valid
  file: output/feature-adr.md
```

Validates that the ADR follows the required template structure

#### Validierung

**Errors (Gate schlägt fehl):**
- YAML frontmatter present and valid
- Required fields: adr_id, title, status
- Required sections: Kontext, Entscheidung, Implementation, Dokumentation, Akzeptanzkriterien, Konsequenzen
- At least one acceptance criterion (checkbox)

**Warnings (Gate besteht):**
- Recommended fields: component_type, classification, change_scope
- Less than 3 acceptance criteria
- Missing depends_on for major changes


#### Implementation

- Module: `helix.adr.gate`
- Class: `ADRQualityGate`
- Method: `check`

**Siehe auch:**
- docs/ADR-TEMPLATE.md
- skills/helix/adr/SKILL.md


---

## Domains

HELIX organisiert Wissen in Domains mit zugehörigen Skills:

### HELIX Core (`helix`)

Core orchestration system, phase management, and self-evolution capabilities

**Skills:**
- [HELIX Core](skills/helix/SKILL.md) - Orchestration, Phases, Quality Gates
- [ADR Writing](skills/helix/adr/SKILL.md) - ADR Template, Validation, Finalization
- [Evolution](skills/helix/evolution/SKILL.md) - Test System, Deployment, Rollback

**Key Concepts:**
- **Phase Orchestration**: Managing sequential development phases with dependencies
- **Quality Gates**: Automated validation of phase outputs
- **Self-Evolution**: Safe modification of HELIX itself via test system

**Wann lesen:** Always read for any HELIX development task

---

### PDM System (`pdm`)

Product Data Management - articles, BOMs, attributes, and catalog structures

**Skills:**
- [PDM Core](skills/pdm/SKILL.md) - Articles, BOMs, Attributes
- [Catalog](skills/pdm/catalog/SKILL.md) - Categories, Navigation, Search

**Key Concepts:**
- **Article**: Product with attributes, variants, and relationships
- **BOM (Bill of Materials)**: Hierarchical structure of components
- **Attributes**: Product properties (technical specs, prices, etc.)

**Wann lesen:** When working with product data, catalogs, or BOMs

---

### POSITAL Encoder (`encoder`)

POSITAL encoder products - specifications, configurations, and integrations

**Skills:**
- [Encoder Basics](skills/encoder/SKILL.md) - Product Types, Specifications, Configurations
- [Integration](skills/encoder/integration/SKILL.md) - APIs, Data Formats, Connectors

**Key Concepts:**
- **Encoder Types**: Absolute, Incremental, Magnetic, Optical
- **Configuration**: Resolution, interface, mechanical options
- **Ordering Code**: Product identification and specification encoding

**Wann lesen:** When working with encoder specifications or configurations

---

### Infrastructure (`infrastructure`)

Docker, PostgreSQL, deployment, and system administration

**Skills:**
- [Infrastructure Core](skills/infrastructure/SKILL.md) - Docker, PostgreSQL, Deployment
- [Docker](skills/infrastructure/docker/SKILL.md) - Containers, Compose, Networks
- [PostgreSQL](skills/infrastructure/postgres/SKILL.md) - Queries, Migrations, Performance

**Key Concepts:**
- **Containerization**: Docker-based deployment and isolation
- **Database Management**: PostgreSQL administration and optimization
- **Service Orchestration**: Docker Compose for multi-service deployments

**Wann lesen:** When working with deployment, databases, or containers

---

### Development Tools (`development-tools`)

Tools and utilities for code development - LSP, debugging, testing

**Skills:**
- [LSP Navigation](skills/lsp/SKILL.md) - goToDefinition, findReferences, hover, Anti-Halluzination

**Key Concepts:**
- **LSP Integration**: Language Server Protocol for code intelligence
- **Anti-Halluzination**: Verify symbols exist before using them

**Wann lesen:** When writing or modifying code

---

### API Layer (`api`)

REST APIs, FastAPI endpoints, authentication, and integrations

**Skills:**
- [API Core](skills/api/SKILL.md) - FastAPI, Endpoints, Authentication
- [REST Patterns](skills/api/rest/SKILL.md) - Resources, Methods, Status Codes

**Key Concepts:**
- **REST API**: RESTful API design patterns
- **FastAPI**: Python web framework for APIs
- **Authentication**: Token-based auth, permissions

**Wann lesen:** When developing or modifying API endpoints

---


---

## Escalation

HELIX hat eine automatische Escalation-Strategie bei Fehlern:

**Max Retries:** 3
**Timeout per Level:** 300s

### Level 1: Phase Retry

Retry the failed phase with enhanced context

**Aktion:** `retry_phase`
**Automatisch:** Ja

**Trigger:**
- Quality gate soft failure
- Transient errors
- Missing file warnings

**Strategie:**
1. **Analyze failure**: Parse error messages and logs
2. **Enhance context**: Add failure info to phase CLAUDE.md
3. **Retry**: Re-run phase with same agent


**Beispiel:** syntax_check fails on one file -> Retry phase, agent sees error and fixes it

---

### Level 2: Domain Expert

Escalate to domain-specific expert agent

**Aktion:** `escalate_to_domain`
**Automatisch:** Ja

**Trigger:**
- Level 1 exhausted
- Domain-specific error patterns
- Complex technical issues

**Strategie:**
1. **Identify domain**: Match error to domain skills
2. **Load expert**: Spawn agent with domain skills
3. **Consult**: Expert reviews and suggests fixes
4. **Apply**: Original agent applies suggestions

**Domain Mapping:**

| Error Pattern | Domain |
|---------------|--------|
| `database|sql|postgres` | infrastructure |
| `api|endpoint|fastapi` | api |
| `article|bom|attribute` | pdm |
| `encoder|sensor` | encoder |
| `phase|gate|orchestrat` | helix |

**Beispiel:** Database migration fails -> Escalate to infrastructure domain expert

---

### Level 3: Architecture Review

Request architectural decision review

**Aktion:** `architecture_review`
**Automatisch:** Nein

**Trigger:**
- Level 2 exhausted
- Fundamental design issues
- Cross-domain conflicts

**Strategie:**
1. **Summarize issue**: Generate problem summary
2. **List options**: Propose alternative approaches
3. **Request decision**: Present to user for decision
4. **Document**: Create ADR if needed


**Beispiel:** Feature conflicts with existing architecture -> Present options to user, create ADR for decision

---

### Level 4: Human Intervention

Pause execution and request human help

**Aktion:** `pause_for_human`
**Automatisch:** Nein

**Trigger:**
- All automatic levels exhausted
- Critical security issue
- Data integrity risk
- External dependency failure

**Strategie:**
1. **Pause**: Stop all phase execution
2. **Notify**: Send notification to user
3. **Document**: Write detailed status report
4. **Wait**: Await user instructions


**Beispiel:** External API permanently unavailable -> Pause and ask user how to proceed

---


### Failure Types

#### Transient

Temporary failures that may resolve on retry

**Beispiele:**
- Network timeout
- Rate limiting
- Temporary file lock

**Default Action:** `retry_phase`
**Retry Count:** 3

#### Fixable

Issues the agent can fix with more context

**Beispiele:**
- Syntax error in generated code
- Missing import statement
- Wrong parameter type

**Default Action:** `retry_phase`
**Retry Count:** 2

#### Domain_specific

Issues requiring domain expertise

**Beispiele:**
- Database schema mismatch
- API contract violation
- Business logic error

**Default Action:** `escalate_to_domain`
**Retry Count:** 1

#### Architectural

Fundamental design issues

**Beispiele:**
- Pattern conflict
- Scalability limitation
- Security architecture flaw

**Default Action:** `architecture_review`
**Retry Count:** 0

#### Critical

Issues requiring immediate human attention

**Beispiele:**
- Data loss risk
- Security breach
- Production impact

**Default Action:** `pause_for_human`
**Retry Count:** 0


### Recovery Procedures

#### Rollback Phase

Restore phase to pre-execution state

**Steps:**
1. Clear output/ directory
2. Reset phase status to pending
3. Log rollback event

#### Checkpoint Restore

Restore project to last successful checkpoint

**Steps:**
1. Identify last successful phase
2. Clear all subsequent outputs
3. Reset phase statuses
4. Log restore event

#### Full Reset

Reset entire project to initial state

**Steps:**
1. Backup all outputs
2. Clear all phase outputs
3. Reset all statuses
4. Notify user



---

## Evolution System

HELIX kann sich selbst sicher modifizieren über das Evolution-System.

### Status Flow

```
PENDING -> DEVELOPING -> READY -> DEPLOYED -> VALIDATED -> INTEGRATED
                               |           |
                            FAILED <- <- ROLLBACK
```

### Project Structure

```
projects/evolution/{name}/
├── spec.yaml        # Project specification
├── phases.yaml      # Development phases
├── status.json      # Current status
├── new/             # New files to create
│   └── src/helix/...
└── modified/        # Modified files
    └── src/helix/...
```

### Evolution API

```bash
# List projects
curl http://localhost:8001/helix/evolution/projects

# Deploy to test
curl -X POST http://localhost:8001/helix/evolution/projects/{name}/deploy

# Validate
curl -X POST http://localhost:8001/helix/evolution/projects/{name}/validate

# Integrate
curl -X POST http://localhost:8001/helix/evolution/projects/{name}/integrate
```

### Safety Guarantees

1. Changes always deploy to test system first
2. Full validation (syntax, unit, E2E) before integration
3. Automatic rollback on failure
4. Git tag backup before integration
5. RAG database 1:1 copy for realistic testing

---

## Documentation Tools

### Docs Compiler

Kompiliert Dokumentation aus YAML-Sources und Code-Docstrings.

```bash
# Generate all docs
python -m helix.tools.docs_compiler compile

# Validate without writing
python -m helix.tools.docs_compiler validate

# List source files
python -m helix.tools.docs_compiler sources

# Show what would change
python -m helix.tools.docs_compiler diff
```

**Python API:**

```python
from helix.tools.docs_compiler import DocCompiler

compiler = DocCompiler()
result = compiler.compile()

if result.success:
    print(f"Generated {len(result.files_written)} files")
else:
    for error in result.errors:
        print(f"ERROR: {error}")
```

### ADR Tool

Validiert und finalisiert Architecture Decision Records.

```bash
# Validate an ADR
python -m helix.tools.adr_tool validate path/to/ADR.md

# Finalize (move to adr/ and update INDEX)
python -m helix.tools.adr_tool finalize path/to/ADR.md

# Get next available ADR number
python -m helix.tools.adr_tool next-number
```

**Python API:**

```python
from helix.tools import validate_adr, finalize_adr, get_next_adr_number

# Validate
result = validate_adr("ADR-feature.md")
if not result.success:
    print(result.errors)

# Finalize
result = finalize_adr("ADR-feature.md")
print(result.final_path)  # -> adr/013-feature.md

# Next number
next_num = get_next_adr_number()  # -> 13
```

---

## Code References

### Key Modules

#### `src/helix/adr/__init__.py`

ADR (Architecture Decision Records) System for HELIX v4.

This package provides tools for parsing and validating Architecture Decision Records
following the ADR-086 Template v2 format.

Modules:
 ...


#### `src/helix/adr/completeness.py`

Contextual completeness validation for ADRs.

Layer 2 of the ADR validation system. Applies context-dependent
rules based on ADR metadata (change_scope, classification, etc.).

This module loads...

- **CompletenessRule** (Line 65): A contextual completeness rule.

Represents a single rule loaded from the YAML...
- **CompletenessResult** (Line 88): Result of completeness validation.

Contains the overall pass/fail status and all issues...
- **CompletenessValidator** (Line 107): Validates ADRs against contextual rules.

Loads rules from YAML configuration and evaluates them...

#### `src/helix/adr/concept_diff.py`

Concept-to-ADR diff for validating completeness.

Layer 3 of the ADR validation system. Compares a source concept
document with the generated ADR to find missing sections.

When an ADR is created...

- **ConceptSection** (Line 45): A section extracted from a concept document.

Attributes:
    name: Section heading text
   ...
- **ConceptDiffResult** (Line 61): Result of concept-ADR comparison.

Contains information about section coverage between...
- **ConceptDiffer** (Line 100): Compares concept document with generated ADR.

Finds missing sections that were in the concept...

#### `src/helix/adr/gate.py`

ADR Quality Gate for HELIX v4.

This module provides quality gate integration for ADR validation.
It integrates the ADRValidator with the QualityGateRunner system,
allowing ADR validation to be...

- **ADRQualityGate** (Line 46): Quality gate for ADR validation.

Integrates ADR validation with the HELIX quality gate...

#### `src/helix/adr/parser.py`

ADR Parser for HELIX v4.

This module provides parsing functionality for Architecture Decision Records
following the ADR-086 Template v2 format. It extracts YAML frontmatter metadata
and parses...

- **ADRStatus** (Line 30): Valid ADR status values per ADR-086 template.

Attributes:
    PROPOSED: Initial draft, under...
- **ComponentType** (Line 47): Valid component types per ADR-069.

Used to classify what type of HELIX component the ADR affects.
- **Classification** (Line 64): Change classification types per ADR-069.

Describes the nature of the change.

#### `src/helix/adr/validator.py`

ADR Validator for HELIX v4.

This module provides validation functionality for Architecture Decision Records
following the ADR-086 Template v2 format. It validates ADR structure,...

- **IssueLevel** (Line 35): Severity level for validation issues.

Attributes:
    ERROR: Critical issue that makes the ADR...
- **IssueCategory** (Line 46): Category of validation issues.

Used to classify and filter validation issues.

Attributes:
   ...
- **ValidationIssue** (Line 74): A single validation issue found during ADR validation.

Attributes:
    level: Severity (error...

#### `src/helix/api/job_manager.py`

Job manager for HELIX API - manages async job execution.

- **Job** (Line 13): Internal job representation.
- **JobManager** (Line 39): Manages HELIX job execution and streaming.

This is an in-memory implementation. For...

#### `src/helix/api/main.py`

HELIX API - FastAPI application.

This API provides:
1. OpenAI-compatible endpoints for Open WebUI integration
2. HELIX-specific endpoints for project execution
3. SSE streaming for real-time...



---

## Best Practices

### Für Consultants

1. **Klärende Fragen stellen** bevor du implementierst
2. **Relevante Skills lesen** für Domain-Wissen
3. **spec.yaml vollständig** mit allen Anforderungen
4. **phases.yaml realistisch** mit passenden Quality Gates

### Für Developers

1. **Phase CLAUDE.md lesen** für spezifische Anweisungen
2. **Input-Dateien analysieren** vor Implementation
3. **Type Hints und Docstrings** für alle Public APIs
4. **Tests schreiben** wo sinnvoll

### Für Reviewers

1. **Kriterien definieren** für Reviews
2. **Konstruktives Feedback** mit konkreten Verbesserungen
3. **Approve oder Reject** mit klarer Begründung

---

## Troubleshooting

### Quality Gate schlägt fehl

1. Lies die Fehlermeldung genau
2. Check die Gate-Konfiguration in phases.yaml
3. Prüfe ob alle erwarteten Dateien existieren
4. Führe Syntax-Check manuell aus

### Phase-Timeout

1. Erhöhe Timeout in phases.yaml
2. Prüfe ob langwierige Operationen nötig sind
3. Consider Breaking in smaller phases

### Escalation zu Human Intervention

1. Lies den Status-Report genau
2. Prüfe alle vorherigen Schritte
3. Entscheide über nächste Aktion
4. Dokumentiere Entscheidung

---

## Weiterführende Links

- [ONBOARDING.md](../../ONBOARDING.md) - Konzept-Erklärung
- [docs/ARCHITECTURE-MODULES.md](../../docs/ARCHITECTURE-MODULES.md) - Technische Architektur
- [docs/ADR-TEMPLATE.md](../../docs/ADR-TEMPLATE.md) - ADR Template
- [docs/SELF-DOCUMENTATION.md](../../docs/SELF-DOCUMENTATION.md) - Dokumentationsprinzipien

---


## Debug & Observability Engine

Live visibility into Claude CLI executions for debugging, 
cost tracking, and monitoring.


### Key Features

- Live Tool Tracking: See which tools are being called in real-time
- Cost Monitoring: Track token usage and costs per phase and project
- Timing Metrics: Measure tool call durations and identify bottlenecks
- SSE Dashboard: Stream events to web dashboards
- Terminal Dashboard: Live CLI monitoring with visual statistics

### Modules

#### `helix.debug.stream_parser`

Parses NDJSON events from Claude CLI --output-format stream-json

**StreamParser**: Main parser class for NDJSON event streams

Methods:
- `parse_line(line: str) -> Event`
- `parse_stream(stream: AsyncIterator) -> AsyncIterator[Event]`
- `get_summary() -> dict`
- `get_tool_calls() -> list[ToolCall]`


```python
from helix.debug import StreamParser

parser = StreamParser()
async for event in parser.parse_stream(process.stdout):
    print(f"{event.type}: {event.data}")
```


#### `helix.debug.tool_tracker`

Tracks all tool calls with timing, input, output, and statistics

**ToolTracker**: Aggregates tool call statistics

Methods:
- `start_tool(tool_id: str, name: str, input: dict)`
- `end_tool(tool_id: str, output: Any, success: bool)`
- `get_stats() -> ToolStats`
- `get_failures() -> list[ToolCall]`


```python
from helix.debug import ToolTracker

tracker = ToolTracker()
tracker.start_tool("123", "bash_tool", {"command": "ls"})
tracker.end_tool("123", output="file.txt", success=True)

stats = tracker.get_stats()
print(f"Total calls: {stats.total_calls}")
print(f"Success rate: {stats.success_rate}%")
```


#### `helix.debug.cost_calculator`

Calculates token usage and costs per model

**CostCalculator**: Tracks and calculates costs

Methods:
- `add_usage(input_tokens: int, output_tokens: int, model: str)`
- `get_total_cost() -> float`
- `get_cost_by_phase() -> dict[str, float]`


```python
from helix.debug import CostCalculator

calc = CostCalculator()
calc.add_usage(1000, 500, model="claude-sonnet")

print(f"Total cost: ${calc.get_total_cost():.4f}")
```


#### `helix.debug.live_dashboard`

SSE endpoints for real-time streaming to web dashboards


```python
from helix.debug import LiveDashboard
from fastapi import FastAPI

app = FastAPI()
dashboard = LiveDashboard()
app.include_router(dashboard.router, prefix="/debug")
```


#### `helix.debug.events`

Event type definitions and dataclasses




### CLI Tools

#### claude-wrapper.sh

Wrapper script for Claude CLI with debug options

```bash
# Basic usage with verbose output
./control/claude-wrapper.sh -v -- --print "Your prompt"

# With cost tracking
./control/claude-wrapper.sh -c -- --print "Your prompt"

# Stream to file
./control/claude-wrapper.sh -o debug.log -- --print "Your prompt"
```


#### helix-debug.sh

Start debug session for a HELIX phase

```bash
# Terminal dashboard
./control/helix-debug.sh -d phases/01-analysis

# Web dashboard on port 8080
./control/helix-debug.sh -w -p 8080 phases/01-analysis

# Just logging, no dashboard
./control/helix-debug.sh -l phases/01-analysis
```





## Phase Orchestrator

Autonomous project execution - the heart of HELIX v4.
Runs projects without manual intervention, handling phases,
quality gates, retries, and status tracking.


### Key Features

- Autonomous Execution: Start a project, come back when it's done
- Quality Gates: Automatic validation after each phase
- Retry Logic: Configurable retries on failure
- Status Tracking: Persistent status in status.yaml
- Resume Support: Continue interrupted projects
- CLI + API: Both interfaces available

### Project Types

#### Simple (Schema F) (`simple`)

Standard feature development workflow

**Phases:** consultant → development → review → documentation → integration

**Use when:** Clear requirements, well-understood scope

#### Complex (`complex`)

Features requiring feasibility study and planning

**Phases:** consultant → feasibility → planning → development → review → documentation → integration

**Use when:** Unclear requirements, technical uncertainty

#### Exploratory (`exploratory`)

Research and discovery projects

**Phases:** consultant → research → decision

**Use when:** No clear direction, need to explore options


### CLI Commands

#### `helix project create`

Create a new project with standard structure

```bash
# Simple project
helix project create my-feature --type simple

# Complex project
helix project create big-refactor --type complex

# Exploratory
helix project create new-idea --type exploratory

# Custom base directory
helix project create my-feature --base-dir projects/internal
```


#### `helix project run`

Execute all phases of a project

```bash
# Normal execution
helix project run my-feature

# Resume after failure
helix project run my-feature --resume

# Dry run (show what would happen)
helix project run my-feature --dry-run

# With debug output
HELIX_DEBUG=1 helix project run my-feature
```


#### `helix project status`

Show current project status

```bash
helix project status my-feature
```


#### `helix project list`

List all projects and their status

```bash
helix project list
helix project list --status running
helix project list --type complex
```



### Python API

#### `helix.orchestrator.runner`

Main orchestration class - runs entire projects

**OrchestratorRunner**: Coordinates phase execution, gates, and status


```python
from helix.orchestrator import OrchestratorRunner

runner = OrchestratorRunner(project_dir=Path("projects/my-feature"))
success = await runner.run()

if not success:
    print(f"Failed at: {runner.get_status().current_phase}")
```


#### `helix.orchestrator.status`

Persistent status tracking with pause/resume support

**StatusTracker**: Manages project and phase status



#### `helix.orchestrator.phase_executor`

Executes individual phases via Claude Code CLI

**PhaseExecutor**: Spawns and manages Claude CLI instances



#### `helix.orchestrator.data_flow`

Manages input/output copying between phases

**DataFlowManager**: Copies outputs as inputs for dependent phases




### API Endpoints

- `POST /project/{name}/run` - Start project execution in background
- `GET /project/{name}/status` - Get current project status
- `GET /projects` - List all projects



## LSP Code Navigation

Native Claude Code LSP-Unterstützung für Code-Intelligence.
Ermöglicht Anti-Halluzination und Echtzeit-Diagnostics.


### Aktivierung

Environment Variable: `ENABLE_LSP_TOOL=1`

Automatisch aktiv für Phasen: development, review, integration

### Verfügbare Operations

#### Go to Definition (`goToDefinition`)

Springt zur Definition eines Symbols

**Use Case:** Wo ist diese Funktion implementiert?

```
LSP goToDefinition: "calculate_total"
→ src/billing/calculator.py:45

```

#### Find References (`findReferences`)

Findet alle Verwendungen eines Symbols

**Use Case:** Wer nutzt diese Klasse? Wo muss ich beim Refactoring ändern?

```
LSP findReferences: "UserService"
→ src/api/routes.py:12
→ src/api/routes.py:89
→ tests/test_api.py:34

```

#### Hover (`hover`)

Zeigt Dokumentation und Type-Information

**Use Case:** Was macht diese Methode? Welche Parameter?

```
LSP hover: "process_request"
→ def process_request(data: dict) -> Response

```

#### Document Symbols (`documentSymbol`)

Listet alle Symbole in einer Datei

**Use Case:** Was ist alles in dieser Datei definiert?


#### Workspace Symbol (`workspaceSymbol`)

Sucht Symbole im gesamten Projekt

**Use Case:** Finde alle Handler-Klassen

```
LSP workspaceSymbol: "*Handler"
→ RequestHandler, ResponseHandler, ErrorHandler

```


### Best Practices

**Anti-Halluzination**

Bevor du eine Funktion aufrufst, prüfe ob sie existiert:
1. LSP goToDefinition → Symbol existiert?
2. LSP hover → Signatur korrekt?
3. Dann erst Code schreiben


**Sichere Refactorings**

1. findReferences auf alten Namen
2. Alle gefundenen Stellen notieren
3. Änderungen durchführen
4. Verifizieren mit findReferences


**Diagnostics beachten**

- Errors immer beheben vor Commit
- Warnings wenn möglich fixen
- Diagnostics erscheinen automatisch nach Edits



### Setup (Python)

```bash
pip install pyright
/plugin install pyright@claude-code-lsps
export ENABLE_LSP_TOOL=1
```

