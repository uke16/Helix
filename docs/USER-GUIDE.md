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
