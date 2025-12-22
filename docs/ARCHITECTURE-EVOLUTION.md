# HELIX v4 Evolution System Architecture

## Overview

The Evolution System enables HELIX v4 to modify and extend itself through a structured,
AI-assisted workflow. It uses **ADRs (Architecture Decision Records) as the Single Source
of Truth** for all changes.

## Core Principle: ADR as Single Source of Truth

```
┌─────────────────────────────────────────────────────────────────┐
│                    ADR (Architecture Decision Record)            │
│                                                                 │
│  YAML Header:                    Markdown Sections:             │
│  ─────────────                   ──────────────────             │
│  • title                         • Kontext (Why?)               │
│  • status                        • Entscheidung (What?)         │
│  • component_type                • Implementation (How?)        │
│  • classification                • Dokumentation (Docs?)        │
│  • change_scope                  • Akzeptanzkriterien (Done?)   │
│  • files.create                  • Konsequenzen (Impact?)       │
│  • files.modify                                                 │
│  • files.docs                                                   │
│  • depends_on                                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Derived Artifacts                            │
│                                                                 │
│  • phases.yaml      - Execution plan                            │
│  • Quality Gates    - Verification rules                        │
│  • Templates        - Claude instructions with expected files   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Evolution Workflow

```
┌──────────────────────────────────────────────────────────────────────────┐
│ PHASE 0: CONSULTANT                                                       │
│                                                                          │
│ Input:  User request / Feature idea                                      │
│ Output: ADR-XXX.md, phases.yaml                                          │
│                                                                          │
│ Quality Gate: ADR-System                                                 │
│   → Is ADR valid against template?                                       │
│   → Are files.create/modify defined?                                     │
│   → Are acceptance criteria present?                                     │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: CONCEPT                                                          │
│                                                                          │
│ Input:  ADR-XXX.md                                                       │
│ Output: CONCEPT.md (detailed technical design)                           │
│                                                                          │
│ Quality Gate: File exists + structure check                              │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ PHASE 2-N: DEVELOPMENT                                                    │
│                                                                          │
│ Input:  CONCEPT.md + previous outputs                                    │
│ Output: Code + Tests (as defined in ADR.files)                           │
│                                                                          │
│ Quality Gate: ADR-based verification                                     │
│   → Do all files from ADR.files.create exist?                            │
│   → Do modified files from ADR.files.modify exist?                       │
│   → Syntax check passed?                                                 │
│   → Tests passed?                                                        │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ DEPLOY → VALIDATE → INTEGRATE                                             │
│                                                                          │
│ Deploy:    Copy to test system                                           │
│ Validate:  Run full test suite                                           │
│ Integrate: Copy to production (if tests pass)                            │
│                                                                          │
│ Final Gate:                                                              │
│   → All tests pass?                                                      │
│   → ADR.files.docs updated?                                              │
│   → All acceptance criteria checked?                                     │
└──────────────────────────────────────────────────────────────────────────┘
```

## Components

### 1. ADR System (`src/helix/adr/`)

Parses and validates Architecture Decision Records.

```python
from helix.adr import ADRParser, ADRDocument
from helix.adr.validator import ADRValidator
from helix.adr.gate import ADRQualityGate

# Parse ADR
parser = ADRParser()
adr = parser.parse_file(Path("adr/001-feature.md"))

# Access metadata
print(adr.metadata.title)           # "Feature Name"
print(adr.metadata.files.create)    # ["src/module.py", ...]
print(adr.acceptance_criteria)      # [AcceptanceCriterion(...), ...]

# Validate
validator = ADRValidator()
result = validator.validate_file(Path("adr/001-feature.md"))
if not result.valid:
    for error in result.errors:
        print(f"Error: {error.message}")
```

### 2. Evolution Project Manager (`src/helix/evolution/`)

Manages evolution projects lifecycle.

```
projects/evolution/{name}/
├── ADR-{name}.md          # Single Source of Truth
├── phases.yaml            # Execution plan
├── status.json            # Current state
├── phases/
│   ├── 1/
│   │   ├── CLAUDE.md      # Generated instructions
│   │   └── output/        # Phase output
│   ├── 2/
│   └── ...
├── new/                   # Consolidated new files
└── modified/              # Consolidated modified files
```

### 3. Quality Gates (`src/helix/quality_gates.py`)

Verification at each phase boundary.

| Gate Type | Purpose |
|-----------|---------|
| `adr_valid` | Validate ADR against template |
| `file_exists` | Check if expected files exist |
| `tests_pass` | Run pytest on specified tests |
| `syntax_check` | Python/TypeScript syntax validation |
| `adr_files_exist` | Check if all ADR.files exist |

### 4. Deployer/Validator/Integrator (`src/helix/evolution/`)

```
Deployer   → Copy files to test system, restart
Validator  → Run tests in test system
Integrator → Copy to production if tests pass
```

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/helix/evolution/projects` | GET | List all projects |
| `/helix/evolution/projects/{name}` | GET | Get project details |
| `/helix/evolution/projects/{name}/deploy` | POST | Deploy to test |
| `/helix/evolution/projects/{name}/validate` | POST | Run validation |
| `/helix/evolution/projects/{name}/integrate` | POST | Integrate to prod |
| `/helix/evolution/projects/{name}/run` | POST | Full pipeline |
| `/helix/execute` | POST | Execute phases |

## Configuration

### Test System

```
/home/aiuser01/helix-v4-test/    # Isolated test environment
```

### Paths

```python
EVOLUTION_PROJECTS = Path("/home/aiuser01/helix-v4/projects/evolution")
TEST_SYSTEM = Path("/home/aiuser01/helix-v4-test")
PRODUCTION = Path("/home/aiuser01/helix-v4")
```

## See Also

- [ADR-001: ADR as Single Source of Truth](../adr/001-adr-as-single-source-of-truth.md)
- [EVOLUTION-WORKFLOW.md](EVOLUTION-WORKFLOW.md)
- [ADR Template](ADR-TEMPLATE.md)
