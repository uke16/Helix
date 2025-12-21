# HELIX v4 Bootstrap - Phase 11: Documentation

Create comprehensive documentation and skills for HELIX v4.

## Target Directories

- Skills: `/home/aiuser01/helix-v4/skills/`
- Docs: `/home/aiuser01/helix-v4/docs/`

## 1. Skills (Domain Knowledge for Consultant)

Skills are markdown files that the Consultant reads to understand domains.

### `/home/aiuser01/helix-v4/skills/helix/SKILL.md`

```markdown
# HELIX v4 - AI Development Orchestration System

## Overview

HELIX v4 is an AI-powered development orchestration system that manages multi-phase software development workflows using Claude Code CLI.

## Core Concepts

### Consultant Meeting
Before implementation begins, users discuss their requirements with a Meta-Consultant who:
- Asks clarifying questions
- Consults domain experts (PDM, ERP, Encoder, etc.)
- Creates specification documents (spec.yaml)
- Plans implementation phases (phases.yaml)

### Phase-Based Execution
Projects are divided into phases:
1. **Consultant** - Requirements discussion
2. **Development** - Code implementation
3. **Review** - Code review
4. **Documentation** - Technical docs

### Quality Gates
Each phase has quality gates:
- `files_exist` - Check output files
- `syntax_check` - Validate code syntax
- `tests_pass` - Run test suites
- `review_approved` - LLM review approval

### Escalation
When issues occur:
- **Stufe 1**: Autonomous recovery (model switch, hints)
- **Stufe 2**: Human in the loop

## Architecture

```
User Request
     │
     ▼
┌─────────────────┐
│ Meta-Consultant │ ← Discusses, plans
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Orchestrator   │ ← Manages phases
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌───────┐ ┌───────┐
│Phase 1│ │Phase 2│ ...
└───┬───┘ └───────┘
    │
    ▼
┌─────────────────┐
│  Claude Code    │ ← Executes tasks
└─────────────────┘
```

## Key Files

- `spec.yaml` - Project specification
- `phases.yaml` - Phase definitions
- `CLAUDE.md` - Instructions for Claude Code

## Domains Supported

- **HELIX** - Self-referential (this system)
- **PDM** - Product Data Management
- **Encoder** - Rotary encoders, POSITAL products
- **ERP** - SAP integration
- **Infrastructure** - Docker, CI/CD
- **Database** - PostgreSQL, Neo4j, Qdrant
- **Webshop** - E-commerce, configurator
```

### `/home/aiuser01/helix-v4/skills/helix/architecture.md`

```markdown
# HELIX v4 Architecture

## Module Overview

### Core Layer (`/src/helix/`)

| Module | Responsibility |
|--------|----------------|
| `orchestrator.py` | Workflow control, phase execution |
| `phase_loader.py` | Load phases.yaml |
| `spec_validator.py` | Validate spec.yaml |
| `template_engine.py` | Render CLAUDE.md from Jinja2 |
| `context_manager.py` | Manage skills and context |
| `quality_gates.py` | Check phase outputs |
| `escalation.py` | Handle failures |
| `llm_client.py` | Multi-provider LLM access |
| `claude_runner.py` | Execute Claude Code CLI |

### Consultant Package (`/src/helix/consultant/`)

| Module | Responsibility |
|--------|----------------|
| `meeting.py` | Agentic meeting orchestration |
| `expert_manager.py` | Domain expert selection |

### Observability Package (`/src/helix/observability/`)

| Module | Responsibility |
|--------|----------------|
| `logger.py` | 3-level logging (phase, project, system) |
| `metrics.py` | Token and cost tracking |

### CLI Package (`/src/helix/cli/`)

| Module | Responsibility |
|--------|----------------|
| `main.py` | Entry point |
| `commands.py` | run, status, debug, costs, new |

## Data Flow

1. User invokes `helix run ./project`
2. Orchestrator loads `phases.yaml`
3. For each phase:
   - ContextManager prepares skills
   - TemplateEngine renders CLAUDE.md
   - ClaudeRunner executes Claude Code
   - QualityGates check output
   - On failure: EscalationManager handles
4. MetricsCollector tracks costs
5. HelixLogger records events

## Configuration

- `config/llm-providers.yaml` - Model definitions
- `config/quality-gates.yaml` - Gate configurations
- `config/escalation.yaml` - Escalation rules
- `config/streaming.yaml` - Output streaming
- `config/domain-experts.yaml` - Expert definitions
```

### `/home/aiuser01/helix-v4/skills/helix/workflows.md`

```markdown
# HELIX v4 Workflows

## Feature Development Workflow

```
1. CONSULTANT PHASE
   User: "I want feature X"
   ├── Meta-Consultant asks questions
   ├── Domain experts analyze
   ├── Creates: spec.yaml, phases.yaml
   └── Creates: ADR if needed

2. DEVELOPMENT PHASE(S)
   ├── Claude Code implements
   ├── Quality Gate: syntax_check
   └── On failure: Escalation

3. REVIEW PHASE
   ├── LLM reviews code
   ├── Quality Gate: review_approved
   └── May request changes

4. DOCUMENTATION PHASE
   ├── Claude Code writes docs
   └── Quality Gate: files_exist
```

## Bugfix Workflow

```
1. ANALYSIS
   ├── Understand the bug
   └── Plan fix approach

2. FIX
   ├── Implement fix
   └── Quality Gate: tests_pass

3. REVIEW
   └── Verify fix
```

## Research Workflow

```
1. SCOPE
   └── Define research questions

2. EXPLORATION
   └── Investigate options

3. REPORT
   └── Document findings
```

## Project Types

Defined in `/templates/project-types/`:
- `feature.yaml` - Standard feature
- `bugfix.yaml` - Bug fixes
- `documentation.yaml` - Docs only
- `research.yaml` - Exploration
```

### `/home/aiuser01/helix-v4/skills/pdm/SKILL.md`

```markdown
# PDM - Product Data Management

## Overview

PDM at FRABA manages product lifecycle data including:
- Article master data
- Bill of Materials (BOM/Stücklisten)
- Revisions and versions
- Document management
- Engineering changes

## Key Concepts

### Articles (Artikel)
Products with unique identifiers, descriptions, and attributes.

### Bill of Materials (BOM)
Hierarchical structure showing:
- Parent article
- Child components
- Quantities
- Positions

### Revisions
Version control for articles:
- Revision number (A, B, C...)
- Status (Draft, Released, Obsolete)
- Effective dates

## Integration Points

- **ERP/SAP**: Material master sync
- **Webshop**: Product catalog
- **Engineering**: CAD drawings
- **Production**: Manufacturing orders

## Common Operations

1. Create/modify articles
2. Build/explode BOMs
3. Release revisions
4. Export to SAP
5. Generate reports

## Data Structures

```
Article
├── ID
├── Description
├── Category
├── Status
└── BOM[]
    ├── Position
    ├── Child Article
    ├── Quantity
    └── Unit
```

*Note: FRABA-specific field names and structures to be added.*
```

### `/home/aiuser01/helix-v4/skills/pdm/bom-structure.md`

```markdown
# BOM Structure (Stücklisten)

## Types

### Single-Level BOM
Direct children only:
```
Product A
├── Component B (qty: 2)
├── Component C (qty: 1)
└── Component D (qty: 4)
```

### Multi-Level BOM
Full hierarchy:
```
Product A
├── Assembly B
│   ├── Part B1
│   └── Part B2
├── Component C
└── Assembly D
    ├── Part D1
    └── Part D2
```

## BOM Operations

### Explosion
Top-down: Show all components of a product

### Implosion (Where-Used)
Bottom-up: Show all products using a component

### Comparison
Show differences between BOM revisions

## Export Formats

- CSV (flat)
- XML (hierarchical)
- SAP IDoc (integration)
- JSON (API)
```

### `/home/aiuser01/helix-v4/skills/encoder/SKILL.md`

```markdown
# Encoder Domain - POSITAL/FRABA

## Overview

FRABA manufactures rotary encoders and inclinometers under the POSITAL brand.

## Product Types

### Absolute Encoders
- Know exact position at power-on
- Single-turn or multi-turn
- Interfaces: SSI, BiSS, CANopen, etc.

### Incremental Encoders
- Output pulses per revolution
- Require reference/homing
- A/B/Z signals

### Inclinometers
- Measure tilt angle
- Gravity-based sensing
- Single or dual axis

## Key Specifications

- **Resolution**: Bits or PPR (pulses per revolution)
- **Accuracy**: Angular error
- **Interface**: Communication protocol
- **Housing**: Mechanical form factor
- **Protection**: IP rating
- **Temperature**: Operating range

## Configuration Parameters

```yaml
encoder:
  type: absolute_multiturn
  resolution_singleturn: 16  # bits
  resolution_multiturn: 43   # bits
  interface: biss_c
  housing: 58mm_shaft
  protection: ip67
```

## Common Tasks

1. Configure encoder parameters
2. Generate product codes
3. Create technical documentation
4. Export to webshop
5. Integration with customer systems

*Note: FRABA-specific product codes and options to be added.*
```

### `/home/aiuser01/helix-v4/skills/infrastructure/SKILL.md`

```markdown
# Infrastructure Domain

## Overview

HELIX v4 infrastructure includes:
- Docker containers
- PostgreSQL database
- Vector stores (Qdrant)
- Graph database (Neo4j)
- Redis cache
- Proxmox VMs

## Docker Setup

### HELIX Services
```yaml
services:
  helix-api:     # FastAPI REST API
  helix-postgres: # Job/project state
```

### Supporting Services
```yaml
services:
  qdrant:        # Vector search
  neo4j:         # Graph database
  redis:         # Cache/queue
  minio:         # Object storage
```

## VM Architecture

```
Proxmox Host
├── ai-vm (HELIX development)
│   ├── Docker containers
│   └── Claude Code CLI
└── other VMs...
```

## Networking

- Internal: Docker bridge network
- External: Reverse proxy (nginx/traefik)
- Ports: 8100 (API), 5434 (Postgres)

## Deployment

1. Clone repository
2. Configure `.env`
3. `docker compose up -d`
4. Verify health checks

## Monitoring

- Container logs: `docker logs`
- Metrics: Prometheus/Grafana (optional)
- Health endpoints: `/health`
```

## 2. User Documentation

### `/home/aiuser01/helix-v4/docs/QUICKSTART.md`

```markdown
# HELIX v4 Quickstart

## Prerequisites

- Python 3.11+
- Node.js 20+ (for Claude Code)
- Claude Code CLI installed
- API key (Anthropic or OpenRouter)

## Installation

```bash
# Clone repository
git clone <repo-url>
cd helix-v4

# Install Python dependencies
pip install -e .

# Verify installation
helix --version
```

## Your First Project

### 1. Create a new project

```bash
helix new my-feature --type feature
```

### 2. Describe your feature

Edit `projects/my-feature/input/request.md`:
```markdown
I want to create a feature that exports
product data to a CSV file.
```

### 3. Run the project

```bash
helix run ./projects/my-feature
```

### 4. Monitor progress

```bash
helix status ./projects/my-feature
helix debug ./projects/my-feature --tail 50
```

### 5. Check costs

```bash
helix costs ./projects/my-feature
```

## Next Steps

- Read [User Guide](USER-GUIDE.md) for full documentation
- Check [CLI Reference](CLI-REFERENCE.md) for all commands
- See [Configuration](CONFIGURATION.md) for customization
```

### `/home/aiuser01/helix-v4/docs/USER-GUIDE.md`

```markdown
# HELIX v4 User Guide

## Introduction

HELIX v4 is an AI development orchestration system that helps you build software features through a structured, phase-based workflow.

## Concepts

### Projects
A project is a self-contained feature or task with:
- `spec.yaml` - What to build
- `phases.yaml` - How to build it
- `phases/` - Working directories

### Phases
Projects are divided into phases:
1. **Consultant** - Discuss and plan
2. **Development** - Implement code
3. **Review** - Quality check
4. **Documentation** - Write docs

### The Consultant
Before coding begins, you discuss your requirements with an AI consultant:
- Ask clarifying questions
- Identify implications
- Create specifications
- Plan implementation

## Workflow

### 1. Start a Discussion

```bash
helix new my-feature --type feature
helix run ./projects/my-feature
```

The consultant will:
- Read your request
- Ask clarifying questions
- Consult domain experts
- Propose a plan

### 2. Review the Plan

Check the generated files:
- `spec.yaml` - Verify requirements
- `phases.yaml` - Check phases
- `adr/` - Read decisions

### 3. Execute

```bash
helix run ./projects/my-feature --phase 02-development
```

### 4. Monitor

```bash
# Status
helix status ./projects/my-feature

# Logs
helix debug ./projects/my-feature

# Costs
helix costs ./projects/my-feature --detailed
```

### 5. Handle Issues

If a phase fails:
- Check logs for errors
- HELIX may auto-recover (Stufe 1)
- Or pause for your input (Stufe 2)

## Project Types

| Type | Use Case |
|------|----------|
| `feature` | New functionality |
| `bugfix` | Fix issues |
| `documentation` | Docs only |
| `research` | Exploration |

## Configuration

See [Configuration Guide](CONFIGURATION.md) for:
- LLM providers
- Quality gates
- Streaming options
- Escalation rules

## Best Practices

1. **Be specific** in your requests
2. **Review** consultant output before proceeding
3. **Monitor costs** for large projects
4. **Commit** after each phase
```

### `/home/aiuser01/helix-v4/docs/CLI-REFERENCE.md`

```markdown
# HELIX v4 CLI Reference

## Global Options

```bash
helix --version    # Show version
helix --help       # Show help
```

## Commands

### helix new

Create a new project.

```bash
helix new <name> [OPTIONS]

Options:
  --type, -t    Project type: feature|bugfix|documentation|research
  --output, -o  Output directory
```

Examples:
```bash
helix new bom-export --type feature
helix new fix-login --type bugfix
helix new api-docs --type documentation
```

### helix run

Execute a project workflow.

```bash
helix run <project_path> [OPTIONS]

Options:
  --phase, -p   Start from specific phase
  --model, -m   LLM model to use
  --dry-run     Show what would be done
```

Examples:
```bash
helix run ./projects/my-feature
helix run ./projects/my-feature --phase 02-development
helix run ./projects/my-feature --model opus
```

### helix status

Show project status.

```bash
helix status <project_path>
```

Output includes:
- Current phase
- Phase status (pending/running/completed/failed)
- Quality gate results

### helix debug

Show debug logs.

```bash
helix debug <project_path> [phase] [OPTIONS]

Options:
  --tail, -n    Number of log lines (default: 50)
```

Examples:
```bash
helix debug ./projects/my-feature
helix debug ./projects/my-feature 02-development --tail 100
```

### helix costs

Show token usage and costs.

```bash
helix costs <project_path> [OPTIONS]

Options:
  --detailed, -d  Show per-phase breakdown
```

Output includes:
- Total tokens (input/output)
- Cost in USD
- Per-phase breakdown (with --detailed)
```

### `/home/aiuser01/helix-v4/docs/CONFIGURATION.md`

```markdown
# HELIX v4 Configuration

## Configuration Files

All configuration is in `/config/`:

| File | Purpose |
|------|---------|
| `llm-providers.yaml` | LLM model definitions |
| `quality-gates.yaml` | Gate configurations |
| `escalation.yaml` | Failure handling |
| `streaming.yaml` | Output streaming |
| `domain-experts.yaml` | Expert definitions |

## LLM Providers

### Supported Providers

- **OpenRouter** - Multi-model gateway
- **Anthropic** - Direct Claude access
- **OpenAI** - Direct GPT access

### Model Aliases

```yaml
# Use short names
aliases:
  opus: "openrouter:claude-opus-4"
  sonnet: "openrouter:claude-sonnet-4"
  gpt4: "openrouter:gpt-4o"
  fast: "openrouter:gpt-4o-mini"
```

### Environment Variables

```bash
HELIX_OPENROUTER_API_KEY=sk-or-...
HELIX_ANTHROPIC_API_KEY=sk-ant-...
HELIX_OPENAI_API_KEY=sk-...
```

## Quality Gates

### Gate Types

| Gate | Description |
|------|-------------|
| `files_exist` | Check output files exist |
| `syntax_check` | Validate code syntax |
| `tests_pass` | Run test suite |
| `review_approved` | LLM review approval |

### Customization

```yaml
# config/quality-gates.yaml
gates:
  syntax_check:
    config:
      languages:
        python:
          command: "python3 -m py_compile {file}"
```

## Streaming

### Levels

| Level | What's Streamed |
|-------|-----------------|
| `minimal` | Phase start/end, errors only |
| `normal` | + file changes, costs |
| `verbose` | + all events |
| `debug` | Raw Claude Code output |

### Configuration

```yaml
# config/streaming.yaml
streaming:
  default_level: "normal"
```

## Escalation

### Levels

| Level | Handling |
|-------|----------|
| Stufe 1 | Autonomous (model switch, retry) |
| Stufe 2 | Human intervention required |

### Configuration

```yaml
# config/escalation.yaml
escalation:
  max_retries_per_level: 3
  attempt_timeout: 30  # minutes
```
```

### `/home/aiuser01/helix-v4/docs/DEVELOPMENT.md`

```markdown
# HELIX v4 Development Guide

## Setup

```bash
# Clone
git clone <repo>
cd helix-v4

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

## Project Structure

```
helix-v4/
├── src/helix/          # Main package
│   ├── cli/            # CLI commands
│   ├── consultant/     # Meeting system
│   ├── observability/  # Logging/metrics
│   └── api/            # REST API (Phase 12)
├── templates/          # Jinja2 templates
├── config/             # YAML configurations
├── skills/             # Domain knowledge
├── tests/              # Test suite
├── adr/                # Architecture decisions
└── docs/               # Documentation
```

## Running Tests

```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/

# Integration tests
pytest tests/integration/

# With coverage
pytest --cov=helix
```

## Code Style

- **Formatter**: Black
- **Linter**: Ruff
- **Type Checker**: mypy

```bash
# Format
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/helix/
```

## Adding a New Module

1. Create module in `src/helix/`
2. Add type hints and docstrings
3. Export in `__init__.py`
4. Write unit tests
5. Write integration tests
6. Update documentation

## Adding a Domain Expert

1. Add to `config/domain-experts.yaml`
2. Create skills in `skills/<domain>/`
3. Add triggers/keywords

## Creating Templates

Templates use Jinja2:

```markdown
# {{ expert.name }}

{% for skill in expert.skills %}
- {{ skill }}
{% endfor %}
```

See `/templates/` for examples.
```

## 3. Create Directories

```bash
mkdir -p /home/aiuser01/helix-v4/skills/{helix,pdm,encoder,infrastructure}
```

## Instructions

1. Create all skills in `/home/aiuser01/helix-v4/skills/`
2. Create all docs in `/home/aiuser01/helix-v4/docs/`
3. All content in English
4. Create `output/result.json` when done

## Files to Create

### Skills (~10 files)
- `skills/helix/SKILL.md`
- `skills/helix/architecture.md`
- `skills/helix/workflows.md`
- `skills/pdm/SKILL.md`
- `skills/pdm/bom-structure.md`
- `skills/encoder/SKILL.md`
- `skills/infrastructure/SKILL.md`

### Docs (~6 files)
- `docs/QUICKSTART.md`
- `docs/USER-GUIDE.md`
- `docs/CLI-REFERENCE.md`
- `docs/CONFIGURATION.md`
- `docs/DEVELOPMENT.md`

## Output

```json
{
  "status": "success",
  "files_created": [
    "skills/helix/SKILL.md",
    "skills/helix/architecture.md",
    "skills/helix/workflows.md",
    "skills/pdm/SKILL.md",
    "skills/pdm/bom-structure.md",
    "skills/encoder/SKILL.md",
    "skills/infrastructure/SKILL.md",
    "docs/QUICKSTART.md",
    "docs/USER-GUIDE.md",
    "docs/CLI-REFERENCE.md",
    "docs/CONFIGURATION.md",
    "docs/DEVELOPMENT.md"
  ]
}
```
