# Phase 5: Dynamische Phasen-Generierung (ADR-026)

Du bist ein Claude Code Entwickler der dynamische Phasen für komplexe Projekte implementiert.

---

## 🎯 Ziel

Implementiere einen Planning-Agent der für komplexe Projekte:
1. Den Scope analysiert
2. 1-5 Phasen dynamisch generiert
3. Optional eine Feasibility-Phase einfügt

---

## 📚 Zuerst lesen

1. `docs/ARCHITECTURE-ORCHESTRATOR.md` - Complex Projekt-Typ
2. `templates/workflows/intern-complex.yaml` (aus Phase 2)
3. `src/helix/api/orchestrator.py` - Orchestrator
4. `docs/ROADMAP-CONSULTANT-WORKFLOWS.md` - Entscheidungen Q9-Q10

---

## 📋 Aufgaben

### 1. ADR-026 erstellen

```yaml
---
adr_id: "026"
title: "Dynamische Phasen-Generierung für komplexe Projekte"
status: Proposed
project_type: helix_internal
component_type: AGENT
classification: NEW

files:
  create:
    - src/helix/planning/__init__.py
    - src/helix/planning/agent.py
    - src/helix/planning/phase_generator.py
  modify:
    - src/helix/api/orchestrator.py
---
```

### 2. Planning Agent implementieren

`src/helix/planning/agent.py`:

```python
"""Planning Agent for complex projects."""

from dataclasses import dataclass
from typing import Optional
from helix.claude_runner import ClaudeRunner

@dataclass
class PlannedPhase:
    id: str
    name: str
    type: str  # development, documentation, test, etc.
    description: str
    estimated_sessions: int
    dependencies: list[str]

@dataclass  
class ProjectPlan:
    phases: list[PlannedPhase]
    feasibility_needed: bool
    total_estimated_sessions: int

class PlanningAgent:
    """Generates dynamic phases for complex projects."""
    
    MAX_PHASES = 5  # Konfigurierbar
    
    def __init__(self, max_phases: int = 5):
        self.max_phases = max_phases
        self.runner = ClaudeRunner()
    
    async def analyze_and_plan(
        self,
        project_description: str,
        adr_content: Optional[str] = None
    ) -> ProjectPlan:
        """
        Analyze project scope and generate phases.
        
        Steps:
        1. Analyze complexity
        2. Determine if feasibility needed
        3. Generate 1-5 phases
        4. Estimate sessions per phase
        """
        prompt = self._build_planning_prompt(
            project_description, 
            adr_content
        )
        
        result = await self.runner.run_prompt(
            prompt,
            model="sonnet"  # Braucht Reasoning
        )
        
        return self._parse_plan(result)
    
    def _build_planning_prompt(self, desc: str, adr: str) -> str:
        return f"""
Du bist ein Planning-Agent für HELIX Projekte.

## Projekt-Beschreibung
{desc}

## ADR (falls vorhanden)
{adr or "Kein ADR vorhanden"}

## Deine Aufgabe

Analysiere das Projekt und erstelle einen Plan mit 1-{self.max_phases} Phasen.

### Regeln
- Max {self.max_phases} Phasen
- Jede Phase sollte in 1-2 Claude Code Sessions machbar sein
- Bei Unklarheit: Feasibility-Phase zuerst

### Output Format (YAML)

```yaml
feasibility_needed: true/false
phases:
  - id: phase-1
    name: "Phase Name"
    type: development|documentation|test|research
    description: "Was wird gemacht"
    estimated_sessions: 1
    dependencies: []
```
"""
```

### 3. Phase Generator

`src/helix/planning/phase_generator.py`:

```python
"""Generates phases.yaml from ProjectPlan."""

from pathlib import Path
import yaml

class PhaseGenerator:
    """Generates phase files from a plan."""
    
    def generate_phases_yaml(
        self,
        plan: ProjectPlan,
        project_dir: Path,
        base_workflow: str = "intern-complex"
    ) -> Path:
        """
        Generate phases.yaml from plan.
        
        1. Load base workflow template
        2. Replace dynamic phases
        3. Write to project
        """
        phases_data = {
            "project": {
                "name": project_dir.name,
                "type": "complex",
                "generated": True
            },
            "phases": []
        }
        
        # Optional: Feasibility first
        if plan.feasibility_needed:
            phases_data["phases"].append({
                "id": "feasibility",
                "name": "Feasibility Study",
                "type": "research",
                "template": "developer/research.md"
            })
        
        # Add planned phases
        for phase in plan.phases:
            phases_data["phases"].append({
                "id": phase.id,
                "name": phase.name,
                "type": phase.type,
                "description": phase.description,
                "depends_on": phase.dependencies
            })
        
        # Write
        output = project_dir / "phases.yaml"
        output.write_text(yaml.dump(phases_data))
        return output
    
    def generate_phase_claudes(
        self,
        plan: ProjectPlan,
        project_dir: Path
    ) -> list[Path]:
        """Generate CLAUDE.md for each phase."""
        created = []
        
        for i, phase in enumerate(plan.phases, 1):
            phase_dir = project_dir / "phases" / str(i)
            phase_dir.mkdir(parents=True, exist_ok=True)
            
            claude_md = phase_dir / "CLAUDE.md"
            claude_md.write_text(self._generate_claude_md(phase))
            created.append(claude_md)
        
        return created
```

### 4. Orchestrator Integration

In `src/helix/api/orchestrator.py`:

```python
async def start_complex_project(
    self,
    project_path: Path,
    description: str
) -> Job:
    """Start a complex project with dynamic planning."""
    
    # Planning Agent erstellt Phasen
    planner = PlanningAgent(max_phases=5)
    plan = await planner.analyze_and_plan(description)
    
    # Phasen generieren
    generator = PhaseGenerator()
    generator.generate_phases_yaml(plan, project_path)
    generator.generate_phase_claudes(plan, project_path)
    
    # Normaler Workflow starten
    return await self.start_project(project_path)
```

---

## 📁 Output

| Datei | Beschreibung |
|-------|--------------|
| `output/adr/026-dynamic-phase-generation.md` | ADR |
| `output/src/helix/planning/__init__.py` | Package |
| `output/src/helix/planning/agent.py` | Planning Agent |
| `output/src/helix/planning/phase_generator.py` | Phase Generator |
| `output/tests/test_planning_agent.py` | Tests |

---

## ✅ Quality Gate

- [ ] ADR-026 valide
- [ ] PlanningAgent kann 1-5 Phasen generieren
- [ ] max_phases ist konfigurierbar
- [ ] Feasibility wird bei Bedarf eingefügt
- [ ] phases.yaml wird korrekt generiert
- [ ] CLAUDE.md pro Phase wird erstellt

---

## 🔗 Entscheidungen

| Q | Antwort |
|---|---------|
| Q9 | Komplexe Projekte starten mit Planning-Agent |
| Q10 | Max 5 Phasen (konfigurierbar) |
