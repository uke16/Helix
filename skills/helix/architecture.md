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
