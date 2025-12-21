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
