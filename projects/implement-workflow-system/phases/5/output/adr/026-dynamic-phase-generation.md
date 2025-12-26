---
adr_id: "026"
title: Dynamische Phasen-Generierung für komplexe Projekte
status: Proposed

project_type: helix_internal
component_type: AGENT
classification: NEW
change_scope: major

files:
  create:
    - src/helix/planning/__init__.py
    - src/helix/planning/agent.py
    - src/helix/planning/phase_generator.py
    - tests/test_planning_agent.py
  docs:
    - docs/WORKFLOW-SYSTEM.md

depends_on:
  - ADR-023  # Workflow-Definitionen
  - ADR-025  # Sub-Agent Verifikation
---

# ADR-026: Dynamische Phasen-Generierung für komplexe Projekte

## Status

📋 Proposed

---

## Kontext

### Was ist das Problem?

Komplexe Projekte (ADR-023: `intern-complex`, `extern-complex`) können nicht mit einer festen Anzahl von Phasen abgebildet werden. Der Scope ist oft unklar und muss erst analysiert werden.

Die Workflow-Templates definieren `generates_phases: true` für den Planning-Agent, aber es gibt keine Implementation die:
1. Den Projekt-Scope analysiert
2. Dynamisch 1-5 Phasen generiert
3. Bei Bedarf eine Feasibility-Phase einfügt

### Warum muss es gelöst werden?

- Komplexe Projekte brauchen flexible Phasen-Anzahl
- Ein Planning-Agent kann besser einschätzen was nötig ist
- Feste Templates sind zu rigide für unklare Scopes

### Was passiert wenn wir nichts tun?

- Komplexe Projekte werden mit unpassenden festen Phasen gestartet
- Entweder zu viele oder zu wenige Phasen
- Manuelle Anpassung der phases.yaml nötig

---

## Entscheidung

### Wir entscheiden uns für:

Einen PlanningAgent der den Projekt-Scope analysiert und dynamisch 1-5 Phasen generiert, inklusive optionaler Feasibility-Phase.

### Diese Entscheidung beinhaltet:

1. `PlanningAgent`: Analysiert Scope, generiert Plan
2. `PhaseGenerator`: Erstellt phases.yaml und CLAUDE.md pro Phase
3. Konfigurierbare Obergrenze (default: 5 Phasen)
4. Optional: Feasibility-Phase bei unklarem Scope

### Warum diese Lösung?

- Agent kann Komplexität einschätzen
- 5 Phasen-Limit verhindert Over-Engineering
- Feasibility-Option für Risiko-Minimierung
- Generierte CLAUDE.md pro Phase gibt klare Anweisungen

---

## Implementation

### 1. Package-Struktur

```
src/helix/planning/
├── __init__.py
├── agent.py           # PlanningAgent
└── phase_generator.py # PhaseGenerator
```

### 2. Datenmodelle

```python
# src/helix/planning/agent.py

@dataclass
class PlannedPhase:
    """A planned phase from the Planning Agent."""
    id: str                    # e.g., "dev-1", "dev-2"
    name: str                  # Human-readable name
    type: str                  # development, documentation, test, research
    description: str           # What this phase accomplishes
    estimated_sessions: int    # Estimated Claude sessions (1-2)
    dependencies: list[str]    # IDs of phases this depends on

@dataclass
class ProjectPlan:
    """Complete plan from the Planning Agent."""
    phases: list[PlannedPhase]
    feasibility_needed: bool
    total_estimated_sessions: int
    reasoning: str             # Why this plan was chosen
```

### 3. PlanningAgent

```python
class PlanningAgent:
    """Generates dynamic phases for complex projects.

    The agent analyzes the project scope and generates
    an appropriate number of phases (1-5).
    """

    PLANNING_PROMPT = '''
You are a Planning Agent for HELIX projects.

## Project Description
{description}

## ADR Content (if available)
{adr_content}

## Your Task

Analyze this project and create a plan with 1-{max_phases} phases.

### Rules
- Maximum {max_phases} phases
- Each phase should be completable in 1-2 Claude Code sessions
- If scope is unclear: recommend feasibility study first
- Order phases by dependencies

### Output Format (YAML)

```yaml
feasibility_needed: true/false
reasoning: "Why this plan was chosen"
phases:
  - id: dev-1
    name: "Phase Name"
    type: development
    description: "What this phase accomplishes"
    estimated_sessions: 1
    dependencies: []
  - id: dev-2
    name: "Next Phase"
    type: development
    description: "What this phase accomplishes"
    estimated_sessions: 2
    dependencies: [dev-1]
```
'''

    def __init__(self, max_phases: int = 5):
        self.max_phases = max_phases
        self.runner = ClaudeRunner()

    async def analyze_and_plan(
        self,
        project_description: str,
        adr_content: str | None = None,
    ) -> ProjectPlan:
        """Analyze project and generate phases."""
        prompt = self.PLANNING_PROMPT.format(
            description=project_description,
            adr_content=adr_content or "No ADR provided",
            max_phases=self.max_phases,
        )

        result = await self.runner.run_phase(
            phase_dir=Path.cwd(),
            prompt=prompt,
            timeout=180,  # 3 minutes
            env_overrides={"CLAUDE_MODEL": "claude-sonnet-4-20250514"},
        )

        return self._parse_plan(result)
```

### 4. PhaseGenerator

```python
class PhaseGenerator:
    """Generates phase files from a ProjectPlan."""

    CLAUDE_MD_TEMPLATE = '''# Phase: {name}

> {description}

---

## Dependencies

{dependencies}

## Tasks

1. Read the project ADR for context
2. Implement the functionality described above
3. Write tests for your implementation
4. Update documentation as needed

## Output

Write all output to `output/` in this phase directory.

## Quality Gate

Your output will be verified by a sub-agent.
Ensure all expected files exist and have valid syntax.
'''

    def generate_phases_yaml(
        self,
        plan: ProjectPlan,
        project_dir: Path,
    ) -> Path:
        """Generate phases.yaml from plan."""
        phases_data = {"phases": []}

        # Feasibility first if needed
        if plan.feasibility_needed:
            phases_data["phases"].append({
                "id": "feasibility",
                "name": "Feasibility Study",
                "type": "research",
                "description": "Analyze scope and risks",
                "verify_agent": True,
                "optional": True,
            })

        # Add planned phases
        for phase in plan.phases:
            phases_data["phases"].append({
                "id": phase.id,
                "name": phase.name,
                "type": phase.type,
                "description": phase.description,
                "estimated_sessions": phase.estimated_sessions,
                "depends_on": phase.dependencies,
                "verify_agent": True,
            })

        # Add standard closing phases
        phases_data["phases"].extend([
            {"id": "verify", "name": "Verification", "type": "test"},
            {"id": "documentation", "name": "Documentation", "type": "documentation"},
        ])

        output = project_dir / "phases.yaml"
        output.write_text(yaml.dump(phases_data, default_flow_style=False))
        return output

    def generate_phase_claudes(
        self,
        plan: ProjectPlan,
        project_dir: Path,
    ) -> list[Path]:
        """Generate CLAUDE.md for each dynamic phase."""
        created = []
        phase_num = 1

        # Feasibility if needed
        if plan.feasibility_needed:
            phase_dir = project_dir / "phases" / str(phase_num)
            phase_dir.mkdir(parents=True, exist_ok=True)
            (phase_dir / "output").mkdir(exist_ok=True)
            self._write_claude_md(
                phase_dir,
                "Feasibility Study",
                "Analyze scope, identify risks, validate approach",
                [],
            )
            phase_num += 1

        # Dynamic phases
        for phase in plan.phases:
            phase_dir = project_dir / "phases" / str(phase_num)
            phase_dir.mkdir(parents=True, exist_ok=True)
            (phase_dir / "output").mkdir(exist_ok=True)
            created.append(
                self._write_claude_md(
                    phase_dir,
                    phase.name,
                    phase.description,
                    phase.dependencies,
                )
            )
            phase_num += 1

        return created
```

---

## Dokumentation

### Zu aktualisierende Dokumente

| Dokument | Änderung |
|----------|----------|
| `docs/WORKFLOW-SYSTEM.md` | Planning Agent und dynamische Phasen |
| `templates/consultant/workflow-guide.md` | Wie complex Workflows funktionieren |

---

## Akzeptanzkriterien

### 1. PlanningAgent

- [x] Kann Projekt-Scope analysieren
- [x] Generiert 1-5 Phasen dynamisch
- [x] max_phases ist konfigurierbar
- [x] Kann Feasibility-Bedarf erkennen

### 2. PhaseGenerator

- [x] Erstellt phases.yaml aus ProjectPlan
- [x] Generiert CLAUDE.md pro Phase
- [x] Fügt Standard-Schlussphasen hinzu (Verify, Docs)

### 3. Integration

- [x] Verwendet Sonnet für Planning (braucht Reasoning)
- [x] Output ist valides YAML
- [x] Phasen haben korrekte Abhängigkeiten

---

## Konsequenzen

### Vorteile

- Flexible Phasen-Anzahl je nach Projekt-Komplexität
- Agent-basierte Scope-Analyse
- Konsistente Phase-Struktur durch Generator
- Feasibility-Option reduziert Risiko

### Nachteile / Risiken

- Zusätzlicher LLM-Call für Planning
- Agent könnte falsch einschätzen
- Generierte Phasen könnten zu grob sein

### Mitigation

- Sonnet Model für gutes Reasoning
- max_phases Limit verhindert Übertreibung
- Sub-Agent Verifikation (ADR-025) fängt Fehler ab
- Feasibility-Phase bei unklarem Scope

---

## Referenzen

- ADR-023: Workflow-Definitionen (complex Templates)
- ADR-025: Sub-Agent Verifikation
- `docs/ARCHITECTURE-ORCHESTRATOR.md`: Complex Projekt-Typ
- `templates/workflows/intern-complex.yaml`: Base Template
