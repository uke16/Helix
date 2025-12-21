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
