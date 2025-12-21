# ADR-006: Dynamische Phasen-Definition

**Status:** Akzeptiert  
**Datum:** 2025-12-21  
**Bezug:** ADR-000, ADR-005

---

## Kontext

Nicht jedes Projekt braucht die gleichen Phasen. Ein Feature-Projekt ist anders 
als ein Dokumentations-Projekt oder ein Research-Projekt. Der Consultant soll 
die Phasen dynamisch definieren können.

---

## Entscheidung

### Der Consultant definiert den Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│  CONSULTANT OUTPUT:                                              │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌───────────────────┐        │
│  │  spec.yaml  │  │ phases.yaml │  │ quality-gates.yaml│        │
│  │             │  │             │  │                   │        │
│  │  WAS        │  │  WIE        │  │  WANN             │        │
│  │  gebaut     │  │  der        │  │  ist eine         │        │
│  │  wird       │  │  Workflow   │  │  Phase fertig     │        │
│  │             │  │  aussieht   │  │                   │        │
│  └─────────────┘  └─────────────┘  └───────────────────┘        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### phases.yaml Schema

```yaml
# phases.yaml - Vollständiges Schema

project:
  name: string                    # Projekt-ID
  type: string                    # feature | documentation | research | bugfix | migration
  description: string             # Kurzbeschreibung
  
phases:
  - id: string                    # z.B. "01-consultant", "02-developer"
    name: string                  # Anzeigename
    type: string                  # meeting | development | review | documentation | research | test
    
    # Konfiguration je nach Type
    config:
      # Für type: meeting
      experts: [string]           # Welche Domain-Experten
      max_iterations: int         # Max Rückfragen mit User
      
      # Für type: development
      template: string            # z.B. "developer/python"
      skills: [string]            # Zusätzliche Skills
      model: string               # Optional: Spezifisches Model
      
      # Für type: review
      template: string            # z.B. "reviewer/code"
      review_scope: string        # code | security | architecture | documentation
      
      # Für type: documentation
      template: string            # z.B. "documentation/technical"
      doc_types: [string]         # api | user | architecture
      
      # Für type: test
      test_types: [string]        # unit | integration | e2e
      
    # Input/Output
    input:
      from_phase: string          # Welche Phase liefert Input
      files: [string]             # Welche Dateien
    output:
      directory: string           # Wohin Output
      expected_files: [string]    # Welche Dateien erwartet
      
    # Quality Gate für diese Phase
    quality_gate:
      type: string                # files_exist | syntax_check | tests_pass | review_approved | custom
      checks: [string]            # Spezifische Checks
      on_failure: string          # retry | escalation | abort
      max_retries: int            # Default: 3
```

### Projekt-Typ Templates

```yaml
# templates/project-types/feature.yaml
# Standard Feature-Entwicklung

project:
  type: "feature"
  
phases:
  - id: "01-consultant"
    name: "Anforderungsanalyse"
    type: "meeting"
    config:
      experts: ["auto"]           # Automatisch basierend auf Request
      max_iterations: 10
    output:
      directory: "output"
      expected_files: ["spec.yaml", "phases.yaml", "quality-gates.yaml"]
      
  - id: "02-developer"
    name: "Implementation"
    type: "development"
    config:
      template: "auto"            # Basierend auf spec.language
      skills: ["auto"]            # Basierend auf spec.domain
    input:
      from_phase: "01-consultant"
      files: ["spec.yaml"]
    output:
      directory: "src"
    quality_gate:
      type: "files_exist_and_syntax"
      on_failure: "retry"
      max_retries: 3
      
  - id: "03-reviewer"
    name: "Code Review"
    type: "review"
    config:
      template: "reviewer/code"
      review_scope: "code"
    input:
      from_phase: "02-developer"
      files: ["src/**/*"]
    output:
      directory: "review"
      expected_files: ["review.json"]
    quality_gate:
      type: "review_approved"
      on_failure: "escalation"
      
  - id: "04-documentation"
    name: "Dokumentation"
    type: "documentation"
    config:
      template: "documentation/technical"
      doc_types: ["api", "user"]
    input:
      from_phase: "02-developer"
      files: ["src/**/*", "spec.yaml"]
    output:
      directory: "docs"
    quality_gate:
      type: "files_exist"
      on_failure: "retry"
```

```yaml
# templates/project-types/documentation.yaml
# Nur Dokumentation

project:
  type: "documentation"
  
phases:
  - id: "01-consultant"
    name: "Doku-Planung"
    type: "meeting"
    config:
      experts: ["documentation"]
      max_iterations: 5
      
  - id: "02-writer"
    name: "Dokumentation schreiben"
    type: "documentation"
    config:
      template: "documentation/user"
    quality_gate:
      type: "files_exist"
      on_failure: "retry"
      
  - id: "03-reviewer"
    name: "Doku Review"
    type: "review"
    config:
      template: "reviewer/documentation"
    quality_gate:
      type: "review_approved"
      on_failure: "retry"
```

```yaml
# templates/project-types/research.yaml
# Research/Analyse

project:
  type: "research"
  
phases:
  - id: "01-consultant"
    name: "Research-Planung"
    type: "meeting"
    config:
      experts: ["auto"]
      
  - id: "02-researcher"
    name: "Research durchführen"
    type: "research"
    config:
      template: "researcher/analysis"
      tools: ["web_search", "file_analysis"]
    output:
      expected_files: ["findings.md", "sources.json"]
    quality_gate:
      type: "files_exist"
      
  - id: "03-summary"
    name: "Zusammenfassung"
    type: "documentation"
    config:
      template: "documentation/research-summary"
```

```yaml
# templates/project-types/bugfix.yaml
# Bugfix

project:
  type: "bugfix"
  
phases:
  - id: "01-analysis"
    name: "Bug-Analyse"
    type: "meeting"
    config:
      experts: ["auto"]
      focus: "root_cause_analysis"
      
  - id: "02-fix"
    name: "Fix implementieren"
    type: "development"
    config:
      template: "developer/bugfix"
    quality_gate:
      type: "tests_pass"
      on_failure: "escalation"
      
  - id: "03-verify"
    name: "Fix verifizieren"
    type: "test"
    config:
      test_types: ["regression", "unit"]
    quality_gate:
      type: "tests_pass"
      
  - id: "04-document"
    name: "Bugfix dokumentieren"
    type: "documentation"
    config:
      template: "documentation/bugfix-record"
```

### Orchestrator: Phase-Loading

```python
# phase_loader.py

from pathlib import Path
import yaml

class PhaseLoader:
    """Lädt und validiert Phasen-Definitionen."""
    
    def __init__(self, templates_dir: Path):
        self.templates_dir = templates_dir
        self.project_type_templates = self._load_project_type_templates()
    
    def _load_project_type_templates(self) -> dict:
        """Lädt alle Projekt-Typ Templates."""
        templates = {}
        template_dir = self.templates_dir / "project-types"
        
        for template_file in template_dir.glob("*.yaml"):
            name = template_file.stem
            templates[name] = yaml.safe_load(template_file.read_text())
        
        return templates
    
    def load_phases(self, project_dir: Path) -> list[PhaseConfig]:
        """Lädt Phasen für ein Projekt."""
        
        phases_file = project_dir / "phases" / "01-consultant" / "output" / "phases.yaml"
        
        if phases_file.exists():
            # Custom Phasen vom Consultant
            phases_data = yaml.safe_load(phases_file.read_text())
        else:
            # Fallback auf Template
            project_type = self._detect_project_type(project_dir)
            phases_data = self.project_type_templates.get(project_type, 
                          self.project_type_templates["feature"])
        
        return [PhaseConfig(**phase) for phase in phases_data["phases"]]
    
    def _detect_project_type(self, project_dir: Path) -> str:
        """Erkennt Projekt-Typ aus vorhandenen Dateien."""
        
        state_file = project_dir / "state.json"
        if state_file.exists():
            state = json.loads(state_file.read_text())
            return state.get("project_type", "feature")
        
        return "feature"


@dataclass
class PhaseConfig:
    id: str
    name: str
    type: str
    config: dict = field(default_factory=dict)
    input: dict = field(default_factory=dict)
    output: dict = field(default_factory=dict)
    quality_gate: dict = field(default_factory=dict)
    
    def get_template(self) -> str:
        """Gibt Template-Pfad zurück."""
        return self.config.get("template", f"{self.type}/default")
    
    def get_model(self) -> str | None:
        """Gibt spezifisches Model zurück falls definiert."""
        return self.config.get("model")
    
    def get_quality_gate_config(self) -> dict:
        """Gibt Quality Gate Konfiguration zurück."""
        return {
            "type": self.quality_gate.get("type", "files_exist"),
            "checks": self.quality_gate.get("checks", []),
            "on_failure": self.quality_gate.get("on_failure", "retry"),
            "max_retries": self.quality_gate.get("max_retries", 3)
        }
```

### Workflow-Ausführung

```python
# workflow_executor.py

async def execute_workflow(project_dir: Path):
    """Führt den gesamten Workflow eines Projekts aus."""
    
    loader = PhaseLoader(TEMPLATES_DIR)
    phases = loader.load_phases(project_dir)
    
    state = ProjectState.load(project_dir)
    
    for phase in phases:
        if state.is_phase_completed(phase.id):
            logger.info(f"Phase {phase.id} bereits abgeschlossen, überspringe")
            continue
        
        logger.info(f"Starte Phase: {phase.id} ({phase.name})")
        
        # Phase vorbereiten
        phase_dir = project_dir / "phases" / phase.id
        await prepare_phase(phase_dir, phase, state)
        
        # Phase ausführen
        result = await execute_phase(phase_dir, phase)
        
        # Quality Gate prüfen
        gate_config = phase.get_quality_gate_config()
        gate_result = await check_quality_gate(phase_dir, gate_config)
        
        if gate_result.passed:
            state.mark_phase_completed(phase.id, result)
            state.save()
        else:
            # Escalation Handling (siehe ADR-004)
            await handle_gate_failure(phase_dir, gate_result, phase, state)
    
    # Workflow abgeschlossen
    await finalize_project(project_dir, state)
```

---

## Beispiel: HELIX v4 Bootstrap-Projekt

```yaml
# projects/internal/helix-v4-bootstrap/phases.yaml

project:
  name: "helix-v4-bootstrap"
  type: "feature"
  description: "HELIX v4 baut sich selbst"
  
phases:
  - id: "01-consultant"
    name: "Architektur-Planung"
    type: "meeting"
    config:
      experts: ["helix-architecture", "python"]
      max_iterations: 20          # Viel Diskussion erwartet
    output:
      expected_files: ["spec.yaml", "phases.yaml"]
      
  - id: "02-foundation"
    name: "Core Framework"
    type: "development"
    config:
      template: "developer/python"
      skills: ["python-async", "python-patterns"]
    output:
      directory: "src/helix"
      expected_files:
        - "orchestrator.py"
        - "template_engine.py"
        - "context_manager.py"
        - "quality_gates.py"
        - "phase_loader.py"
    quality_gate:
      type: "syntax_check"
      on_failure: "retry"
      
  - id: "03-templates"
    name: "Template Collection"
    type: "development"
    config:
      template: "developer/markdown"
    output:
      directory: "templates"
    quality_gate:
      type: "files_exist"
      
  - id: "04-unit-tests"
    name: "Unit Tests"
    type: "development"
    config:
      template: "developer/python-tests"
      skills: ["pytest"]
    output:
      directory: "tests/unit"
    quality_gate:
      type: "tests_pass"
      on_failure: "escalation"
      
  - id: "05-reviewer"
    name: "Architecture Review"
    type: "review"
    config:
      template: "reviewer/architecture"
    quality_gate:
      type: "review_approved"
      on_failure: "escalation"
      
  - id: "06-e2e-test"
    name: "E2E Self-Test"
    type: "test"
    config:
      test_types: ["e2e"]
      description: "HELIX v4 führt ein Mini-Projekt mit sich selbst durch"
    quality_gate:
      type: "tests_pass"
      
  - id: "07-documentation"
    name: "Finale Dokumentation"
    type: "documentation"
    config:
      template: "documentation/technical"
      doc_types: ["architecture", "api", "user"]
    output:
      directory: "docs"
```

---

## Konsequenzen

### Positiv
- Maximale Flexibilität für verschiedene Projekt-Typen
- Consultant kann Workflow an Aufgabe anpassen
- Templates als Startpunkt, anpassbar
- Wiederverwendbare Phasen-Konfigurationen

### Negativ
- Komplexere Orchestrierung
- Mehr Validierung nötig
- Consultant muss gute phases.yaml generieren

---

## Referenzen

- ADR-000: Vision & Architecture
- ADR-005: Consultant Topologie

