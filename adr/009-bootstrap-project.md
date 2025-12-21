# ADR-009: Bootstrap-Projekt - HELIX v4 baut sich selbst

**Status:** Proposed  
**Datum:** 2025-12-21  
**Bezug:** Alle vorherigen ADRs

---

## Kontext

Wir haben die Architektur entschieden. Jetzt soll Claude Code HELIX v4 
basierend auf unseren ADRs implementieren. Das ist das "Ur-Projekt".

---

## Entscheidung

### Bootstrap-Projekt Spec

```yaml
# projects/internal/helix-v4-bootstrap/spec.yaml

meta:
  id: "helix-v4-bootstrap"
  domain: "helix"
  language: "python"
  type: "feature"
  priority: "p0"
  tags: ["bootstrap", "meta", "core"]

implementation:
  summary: "HELIX v4 Core-System Implementation basierend auf ADR-000 bis ADR-008"
  
  description: |
    Implementiert das HELIX v4 System das sich selbst für weitere Projekte nutzt.
    
    Kernkomponenten:
    1. Orchestrator - Steuert den Workflow
    2. Template Engine - Generiert CLAUDE.md
    3. Context Manager - Verwaltet Skills/Context
    4. Quality Gates - Prüft Phase-Ergebnisse
    5. LLM Client - Multi-Provider Support
    6. Escalation System - Consultant-autonome Intervention
    
  files_to_create:
    # ═══ Core ═══
    - path: "src/helix/__init__.py"
      description: "Package Init mit Version"
      
    - path: "src/helix/orchestrator.py"
      description: "Hauptsteuerung des Workflows (ADR-000, ADR-006)"
      
    - path: "src/helix/template_engine.py"
      description: "Jinja2-basierte CLAUDE.md Generierung (ADR-001)"
      
    - path: "src/helix/context_manager.py"
      description: "Skill-Verwaltung und Symlink-Erstellung (ADR-001)"
      
    - path: "src/helix/quality_gates.py"
      description: "Gate-Implementierungen (ADR-002)"
      
    - path: "src/helix/phase_loader.py"
      description: "Lädt und validiert phases.yaml (ADR-006)"
      
    - path: "src/helix/spec_validator.py"
      description: "Spec-Schema Validierung (ADR-008)"
      
    - path: "src/helix/llm_client.py"
      description: "Multi-Provider LLM Client (ADR-007)"
      
    - path: "src/helix/claude_runner.py"
      description: "Claude Code Subprocess-Steuerung"
      
    - path: "src/helix/escalation.py"
      description: "2-Stufen Escalation System (ADR-004)"
      
    # ═══ Consultant Meeting ═══
    - path: "src/helix/consultant/__init__.py"
      description: "Consultant Package"
      
    - path: "src/helix/consultant/meeting.py"
      description: "Agentic Meeting Orchestrierung (ADR-005)"
      
    - path: "src/helix/consultant/expert_manager.py"
      description: "Domain-Experten Verwaltung (ADR-005)"
      
    # ═══ Observability ═══
    - path: "src/helix/observability/__init__.py"
      description: "Observability Package"
      
    - path: "src/helix/observability/logger.py"
      description: "3-Ebenen Logging (ADR-003)"
      
    - path: "src/helix/observability/metrics.py"
      description: "Metriken-Erfassung (ADR-003)"
      
    # ═══ CLI ═══
    - path: "src/helix/cli/__init__.py"
      description: "CLI Package"
      
    - path: "src/helix/cli/main.py"
      description: "Haupteinstiegspunkt"
      
    - path: "src/helix/cli/commands.py"
      description: "CLI Commands (run, status, debug)"
      
    # ═══ Config ═══
    - path: "config/llm-providers.yaml"
      description: "LLM Provider Konfiguration (ADR-007)"
      
    - path: "config/domain-experts.yaml"
      description: "Domain-Experten Definition (ADR-005)"
      
    # ═══ Templates ═══
    - path: "templates/consultant/default.md"
      description: "Meta-Consultant Template"
      
    - path: "templates/consultant/expert-base.md"
      description: "Domain-Expert Basis-Template"
      
    - path: "templates/developer/_base.md"
      description: "Developer Basis-Template (ADR-001)"
      
    - path: "templates/developer/python.md"
      description: "Python Developer Template"
      
    - path: "templates/reviewer/code.md"
      description: "Code Reviewer Template"
      
    - path: "templates/documentation/technical.md"
      description: "Technical Docs Template"
      
    - path: "templates/project-types/feature.yaml"
      description: "Feature Projekt-Typ (ADR-006)"
      
    - path: "templates/project-types/documentation.yaml"
      description: "Doku Projekt-Typ (ADR-006)"
      
    # ═══ Tests ═══
    - path: "tests/__init__.py"
      description: "Test Package"
      
    - path: "tests/unit/test_template_engine.py"
      description: "Template Engine Tests"
      
    - path: "tests/unit/test_quality_gates.py"
      description: "Quality Gate Tests"
      
    - path: "tests/unit/test_spec_validator.py"
      description: "Spec Validator Tests"
      
    - path: "tests/unit/test_phase_loader.py"
      description: "Phase Loader Tests"
      
    - path: "tests/integration/test_orchestrator.py"
      description: "Orchestrator Integration Tests"
      
    - path: "tests/e2e/test_mini_project.py"
      description: "E2E Test mit Mini-Projekt"
      
  acceptance_criteria:
    # Core Functionality
    - "Orchestrator kann phases.yaml laden und ausführen"
    - "Template Engine generiert korrektes CLAUDE.md aus spec.yaml"
    - "Context Manager erstellt Skill-Symlinks"
    - "Quality Gates validieren Phase-Output"
    - "Spec Validator erkennt invalide Specs"
    
    # LLM Integration
    - "LLM Client unterstützt OpenRouter, Anthropic, OpenAI"
    - "Model-Switch in Escalation funktioniert"
    
    # Escalation
    - "Stufe 1: Consultant kann autonom Model wechseln"
    - "Stufe 1: Consultant kann Plan reverten"
    - "Stufe 2: HIL Request wird generiert"
    
    # Consultant Meeting
    - "Meta-Consultant wählt Domain-Experten"
    - "Experten-Analysen werden synthetisiert"
    - "phases.yaml wird dynamisch generiert"
    
    # Tests
    - "Unit Tests haben >80% Coverage"
    - "E2E Test durchläuft Mini-Projekt erfolgreich"
    
    # CLI
    - "helix run <project> startet Workflow"
    - "helix status <project> zeigt State"
    - "helix debug <project> zeigt Logs"

context:
  relevant_docs:
    - path: "adr/000-vision-and-architecture.md"
      relevance: "Grundarchitektur"
    - path: "adr/001-template-and-context-system.md"
      relevance: "Template-System"
    - path: "adr/002-quality-gate-system.md"
      relevance: "Quality Gates"
    - path: "adr/003-observability-and-debugging.md"
      relevance: "Logging"
    - path: "adr/004-escalation-meeting-system.md"
      relevance: "Escalation"
    - path: "adr/005-consultant-topology-agentic-meetings.md"
      relevance: "Consultant Meetings"
    - path: "adr/006-dynamic-phase-definition.md"
      relevance: "Dynamische Phasen"
    - path: "adr/007-multi-provider-llm-configuration.md"
      relevance: "LLM Config"
    - path: "adr/008-implementation-spec-schema.md"
      relevance: "Spec Schema"

  dependencies:
    - name: "jinja2"
      version: ">=3.0"
      reason: "Template Engine"
    - name: "pyyaml"
      version: ">=6.0"
      reason: "YAML Parsing"
    - name: "click"
      version: ">=8.0"
      reason: "CLI Framework"
    - name: "httpx"
      version: ">=0.24"
      reason: "Async HTTP Client"
    - name: "pydantic"
      version: ">=2.0"
      reason: "Data Validation"

testing:
  unit_tests:
    required: true
    coverage_target: 80
  integration_tests:
    required: true
    scenarios:
      - "Orchestrator führt 2-Phase Workflow aus"
      - "LLM Client wechselt Provider"
  e2e_tests:
    required: true
    scenarios:
      - "Vollständiger Mini-Projekt Durchlauf"

documentation:
  required_docs:
    - type: "architecture"
      path: "docs/architecture.md"
    - type: "user"
      path: "docs/getting-started.md"
    - type: "api"
      path: "docs/api/index.md"
```

### Bootstrap Phasen

```yaml
# projects/internal/helix-v4-bootstrap/phases.yaml

project:
  name: "helix-v4-bootstrap"
  type: "feature"
  description: "HELIX v4 baut sich selbst"

phases:
  # ═══ PHASE 1: Core Foundation ═══
  - id: "01-foundation"
    name: "Core Framework"
    type: "development"
    config:
      template: "developer/python"
      skills:
        - "python-async"
        - "python-patterns"
        - "helix-conventions"
      model: "openrouter:claude-sonnet"
    input:
      from_phase: null
      files:
        - "spec.yaml"
        - "adr/*.md"
    output:
      directory: "src/helix"
      expected_files:
        - "__init__.py"
        - "orchestrator.py"
        - "template_engine.py"
        - "context_manager.py"
        - "quality_gates.py"
        - "phase_loader.py"
        - "spec_validator.py"
        - "llm_client.py"
        - "claude_runner.py"
        - "escalation.py"
    quality_gate:
      type: "syntax_check"
      checks:
        - "all_files_exist"
        - "python_syntax_valid"
        - "no_import_errors"
      on_failure: "retry"
      max_retries: 3

  # ═══ PHASE 2: Consultant System ═══
  - id: "02-consultant"
    name: "Consultant Meeting System"
    type: "development"
    config:
      template: "developer/python"
      skills:
        - "python-async"
        - "helix-conventions"
      model: "openrouter:claude-sonnet"
    input:
      from_phase: "01-foundation"
      files:
        - "src/helix/*.py"
        - "adr/005-*.md"
    output:
      directory: "src/helix/consultant"
      expected_files:
        - "__init__.py"
        - "meeting.py"
        - "expert_manager.py"
    quality_gate:
      type: "syntax_check"
      on_failure: "retry"

  # ═══ PHASE 3: Observability ═══
  - id: "03-observability"
    name: "Logging & Metrics"
    type: "development"
    config:
      template: "developer/python"
      model: "openrouter:gpt-4o"
    input:
      from_phase: "01-foundation"
      files:
        - "adr/003-*.md"
    output:
      directory: "src/helix/observability"
      expected_files:
        - "__init__.py"
        - "logger.py"
        - "metrics.py"
    quality_gate:
      type: "syntax_check"
      on_failure: "retry"

  # ═══ PHASE 4: CLI ═══
  - id: "04-cli"
    name: "Command Line Interface"
    type: "development"
    config:
      template: "developer/python"
      skills:
        - "python-click"
      model: "openrouter:gpt-4o"
    input:
      from_phase: "01-foundation"
      files:
        - "src/helix/*.py"
    output:
      directory: "src/helix/cli"
      expected_files:
        - "__init__.py"
        - "main.py"
        - "commands.py"
    quality_gate:
      type: "syntax_check"
      on_failure: "retry"

  # ═══ PHASE 5: Templates ═══
  - id: "05-templates"
    name: "Template Collection"
    type: "development"
    config:
      template: "developer/markdown"
    input:
      from_phase: null
      files:
        - "adr/001-*.md"
        - "adr/005-*.md"
        - "adr/006-*.md"
    output:
      directory: "templates"
      expected_files:
        - "consultant/default.md"
        - "consultant/expert-base.md"
        - "developer/_base.md"
        - "developer/python.md"
        - "reviewer/code.md"
        - "documentation/technical.md"
        - "project-types/feature.yaml"
        - "project-types/documentation.yaml"
    quality_gate:
      type: "files_exist"
      on_failure: "retry"

  # ═══ PHASE 6: Config ═══
  - id: "06-config"
    name: "Configuration Files"
    type: "development"
    config:
      template: "developer/yaml"
    input:
      from_phase: null
      files:
        - "adr/005-*.md"
        - "adr/007-*.md"
    output:
      directory: "config"
      expected_files:
        - "llm-providers.yaml"
        - "domain-experts.yaml"
    quality_gate:
      type: "files_exist"
      on_failure: "retry"

  # ═══ PHASE 7: Unit Tests ═══
  - id: "07-unit-tests"
    name: "Unit Tests"
    type: "development"
    config:
      template: "developer/python-tests"
      skills:
        - "pytest"
      model: "openrouter:claude-sonnet"
    input:
      from_phase: "01-foundation"
      files:
        - "src/helix/*.py"
    output:
      directory: "tests/unit"
      expected_files:
        - "__init__.py"
        - "test_template_engine.py"
        - "test_quality_gates.py"
        - "test_spec_validator.py"
        - "test_phase_loader.py"
    quality_gate:
      type: "tests_pass"
      checks:
        - "pytest tests/unit/"
      on_failure: "escalation"

  # ═══ PHASE 8: Integration Tests ═══
  - id: "08-integration-tests"
    name: "Integration Tests"
    type: "development"
    config:
      template: "developer/python-tests"
    input:
      from_phase: "07-unit-tests"
      files:
        - "src/helix/**/*.py"
        - "tests/unit/*.py"
    output:
      directory: "tests/integration"
      expected_files:
        - "test_orchestrator.py"
    quality_gate:
      type: "tests_pass"
      on_failure: "escalation"

  # ═══ PHASE 9: Code Review ═══
  - id: "09-review"
    name: "Architecture Review"
    type: "review"
    config:
      template: "reviewer/architecture"
      model: "openrouter:claude-opus"   # Opus für tiefes Review
    input:
      from_phase: "08-integration-tests"
      files:
        - "src/**/*.py"
        - "tests/**/*.py"
    output:
      directory: "review"
      expected_files:
        - "review.json"
    quality_gate:
      type: "review_approved"
      on_failure: "escalation"

  # ═══ PHASE 10: E2E Test ═══
  - id: "10-e2e-test"
    name: "E2E Self-Test"
    type: "test"
    config:
      test_types: ["e2e"]
      description: "HELIX v4 führt ein Mini-Projekt mit sich selbst durch"
    input:
      from_phase: "09-review"
      files:
        - "src/**/*.py"
    output:
      directory: "tests/e2e"
      expected_files:
        - "test_mini_project.py"
    quality_gate:
      type: "tests_pass"
      checks:
        - "pytest tests/e2e/ -v"
      on_failure: "escalation"

  # ═══ PHASE 11: Documentation ═══
  - id: "11-documentation"
    name: "Finale Dokumentation"
    type: "documentation"
    config:
      template: "documentation/technical"
      doc_types: ["architecture", "api", "user"]
    input:
      from_phase: "10-e2e-test"
      files:
        - "src/**/*.py"
        - "spec.yaml"
        - "adr/*.md"
    output:
      directory: "docs"
      expected_files:
        - "architecture.md"
        - "getting-started.md"
        - "api/index.md"
    quality_gate:
      type: "files_exist"
      on_failure: "retry"
```

### Verzeichnis-Struktur nach Bootstrap

```
helix-v4/
├── adr/                          # Architecture Decisions
│   ├── INDEX.md
│   ├── 000-vision-and-architecture.md
│   └── ...
│
├── config/                       # Konfiguration
│   ├── llm-providers.yaml
│   └── domain-experts.yaml
│
├── docs/                         # Dokumentation
│   ├── architecture.md
│   ├── getting-started.md
│   └── api/
│
├── projects/                     # Projekte
│   ├── internal/
│   │   └── helix-v4-bootstrap/   # Das Bootstrap-Projekt
│   └── external/
│
├── skills/                       # Wiederverwendbare Skills
│   ├── languages/
│   ├── tools/
│   ├── domains/
│   └── helix/
│
├── src/                          # Source Code
│   └── helix/
│       ├── __init__.py
│       ├── orchestrator.py
│       ├── template_engine.py
│       ├── context_manager.py
│       ├── quality_gates.py
│       ├── phase_loader.py
│       ├── spec_validator.py
│       ├── llm_client.py
│       ├── claude_runner.py
│       ├── escalation.py
│       ├── consultant/
│       │   ├── __init__.py
│       │   ├── meeting.py
│       │   └── expert_manager.py
│       ├── observability/
│       │   ├── __init__.py
│       │   ├── logger.py
│       │   └── metrics.py
│       └── cli/
│           ├── __init__.py
│           ├── main.py
│           └── commands.py
│
├── templates/                    # CLAUDE.md Templates
│   ├── consultant/
│   ├── developer/
│   ├── reviewer/
│   ├── documentation/
│   └── project-types/
│
├── tests/                        # Tests
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── .env                          # API Keys (migriert von v3)
├── pyproject.toml                # Python Projekt Config
└── README.md
```

---

## Durchführung

### Schritt 1: Manuelles Setup

```bash
# Verzeichnisse erstellen
mkdir -p /home/aiuser01/helix-v4/{src/helix,templates,config,skills,tests}

# .env migrieren
cp /home/aiuser01/helix-v3/.env /home/aiuser01/helix-v4/.env

# pyproject.toml erstellen
cat > /home/aiuser01/helix-v4/pyproject.toml << 'PY'
[project]
name = "helix"
version = "4.0.0"
requires-python = ">=3.10"
dependencies = [
    "jinja2>=3.0",
    "pyyaml>=6.0",
    "click>=8.0",
    "httpx>=0.24",
    "pydantic>=2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "pytest-cov>=4.0",
]

[project.scripts]
helix = "helix.cli.main:main"
PY
```

### Schritt 2: Claude Code starten

```bash
cd /home/aiuser01/helix-v4/projects/internal/helix-v4-bootstrap/phases/01-foundation

# CLAUDE.md sollte bereit sein (generiert aus template + spec)
claude
```

### Schritt 3: Phasen durchlaufen

Der Orchestrator (sobald er existiert) führt die Phasen automatisch durch.
Bis dahin: Manuelles Wechseln in jede Phase und `claude` starten.

---

## Konsequenzen

### Positiv
- HELIX v4 wird durch seine eigene Architektur validiert
- Alle ADRs werden praktisch getestet
- Dokumentation entsteht automatisch

### Negativ
- Bootstrapping manuell starten
- Erste Phasen ohne Orchestrator

---

## Referenzen

- Alle ADRs 000-008

