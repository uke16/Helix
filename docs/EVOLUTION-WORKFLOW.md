# Evolution Workflow - Step by Step Guide

## Quick Start

```bash
# 1. Start with Consultant to create ADR + phases
./control/helix-control.sh consultant "Add feature X that does Y"

# 2. Execute all phases
./control/helix-async.sh execute projects/evolution/feature-x

# 3. Deploy to test system
./control/helix-async.sh deploy feature-x

# 4. Validate (run tests)
./control/helix-async.sh validate feature-x

# 5. Integrate to production
./control/helix-async.sh integrate feature-x
```

## Detailed Workflow

### Phase 0: Consultant

The Consultant analyzes your request and creates:

| File | Purpose |
|------|---------|
| `ADR-{name}.md` | **Single Source of Truth** - defines what, why, how |
| `phases.yaml` | Execution plan - which phases in which order |

#### ADR Structure

```yaml
---
adr_id: "XXX"
title: "Feature Name"
status: Proposed
component_type: SERVICE    # TOOL|NODE|AGENT|SERVICE|SKILL|...
classification: NEW        # NEW|UPDATE|FIX|REFACTOR|DEPRECATE
change_scope: minor        # major|minor|config|docs|hotfix

files:
  create:
    - src/helix/module.py
    - tests/test_module.py
  modify:
    - src/helix/__init__.py
  docs:
    - docs/ARCHITECTURE-MODULES.md

depends_on: []
---

# ADR-XXX: Feature Name

## Kontext
Why is this needed?

## Entscheidung
What will we build?

## Implementation
How will it work? (Code examples, API design)

## Dokumentation
Which docs to update?

## Akzeptanzkriterien
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Tests pass

## Konsequenzen
What are the implications?
```

#### Quality Gate: ADR Validation

```python
from helix.adr.validator import ADRValidator

validator = ADRValidator()
result = validator.validate_file(Path("ADR-feature.md"))

# Checks:
# - Valid YAML header
# - Required fields present (adr_id, title, status, ...)
# - Required sections present (Kontext, Entscheidung, ...)
# - files.create or files.modify not empty
# - Acceptance criteria present
```

### Phase 1: Concept Development

Creates detailed technical design based on ADR.

**Input:** ADR-{name}.md  
**Output:** CONCEPT.md

CONCEPT.md contains:
- Detailed API design with code examples
- Data structures
- Error handling strategy
- Integration points
- Test strategy

### Phase 2-N: Development

Implements the feature according to CONCEPT.md.

**Input:** CONCEPT.md, previous phase outputs  
**Output:** Code + Tests (as defined in ADR.files)

#### Quality Gate: Post-Phase Verification

After each phase, verify:

```python
# 1. Expected files exist?
for file in adr.files.create:
    assert (phase_dir / "output" / file).exists()

# 2. Syntax valid?
for py_file in phase_dir.glob("**/*.py"):
    compile(py_file.read_text(), py_file, "exec")

# 3. Tests pass?
pytest.main([str(phase_dir / "output" / "tests")])
```

### Deploy → Validate → Integrate

```
┌─────────┐    ┌──────────┐    ┌───────────┐
│ Deploy  │───▶│ Validate │───▶│ Integrate │
└─────────┘    └──────────┘    └───────────┘
     │              │               │
     ▼              ▼               ▼
  Copy to       Run tests       Copy to
  test system   in test        production
```

#### Deploy

```bash
./control/helix-async.sh deploy feature-x
```

- Consolidates phase outputs to `new/` and `modified/`
- Copies files to `/home/aiuser01/helix-v4-test/`
- Restarts test system API
- Health check

#### Validate

```bash
./control/helix-async.sh validate feature-x
```

- Runs full test suite in test system
- Reports pass/fail counts
- Detailed failure output

#### Integrate

```bash
./control/helix-async.sh integrate feature-x
```

- Only proceeds if validation passed
- Copies files to production
- Updates status to "integrated"
- Restarts production API

## File Structure

```
projects/evolution/{name}/
├── ADR-{name}.md              # Single Source of Truth
├── phases.yaml                # Execution plan
├── status.json                # Current state
│
├── phases/
│   ├── 1/
│   │   ├── CLAUDE.md          # Generated instructions
│   │   ├── CONCEPT.md         # Phase 1 output
│   │   └── output/            # Other outputs
│   ├── 2/
│   │   ├── CLAUDE.md
│   │   └── output/
│   │       └── src/...
│   └── ...
│
├── new/                       # Consolidated new files
│   └── src/helix/module.py
│
└── modified/                  # Consolidated modifications
    └── src/helix/__init__.py
```

## Status Transitions

```
created → developing → ready → deployed → validated → integrated
                                  │
                                  └──▶ failed (on validation failure)
```

## Troubleshooting

### Phase stuck or timeout

```bash
# Check job status
./control/helix-async.sh status

# Check logs
tail -f logs/helix-v4.log
```

### Validation failures

```bash
# Run tests manually in test system
cd /home/aiuser01/helix-v4-test
python3 -m pytest tests/ -v
```

### Rollback

```bash
# If integration breaks something
./control/helix-async.sh rollback feature-x
```

## Best Practices

1. **Write complete ADRs** - The ADR drives everything else
2. **Small, focused changes** - One feature per evolution project
3. **Check intermediate outputs** - Verify each phase before continuing
4. **Run validation before integrate** - Don't skip the test step
5. **Update acceptance criteria** - Mark criteria as checked when done
