# Orchestrator Architecture

> Design-Dokument für den HELIX Phase Orchestrator
>
> Stand: 2025-12-23

---

## Kern-Insight: Consultant bestimmt Projekt-Typ

Der Consultant ist nicht nur ADR-Schreiber, sondern **Projekt-Architekt**:

```
User: "Ich brauche Feature X"
                │
                ▼
┌─────────────────────────────────────────────────────────────┐
│                      CONSULTANT                             │
│                                                             │
│  Analysiert und entscheidet:                                │
│                                                             │
│  A) "Schema F" - Kalkulierbar                               │
│     → Standard-Workflow: ADR → Dev → Review → Done          │
│     → Feste phases.yaml                                     │
│                                                             │
│  B) "Komplex" - Unklar                                      │
│     → Schreibt High-Level Requirements + Uwes Decisions     │
│     → Empfiehlt: Feasibility zuerst                         │
│     → Danach: Planning für nächste Schritte                 │
│                                                             │
│  Output:                                                    │
│  ├── ADR-xxx.md (immer)                                     │
│  ├── spec.yaml (immer)                                      │
│  └── project-type: simple | complex | exploratory           │
└─────────────────────────────────────────────────────────────┘
```

---

## Projekt-Typen und ihre Workflows

### Typ A: Simple (Schema F)

```yaml
# Vom Consultant generiert oder fix vordefiniert
project:
  type: simple
  
phases:
  - id: consultant
    type: consultant
    output: [ADR, spec.yaml]
    gate: adr_valid
    
  - id: development
    type: development
    input_from: consultant
    output: [src/, tests/]
    gate: [syntax_check, tests_pass]
    
  - id: review
    type: review
    input_from: development
    gate: review_approved
    
  - id: integration
    type: integration
    input_from: [development, review]
```

**Keine Planung nötig** - Workflow ist fix.

### Typ B: Complex

```yaml
project:
  type: complex
  
phases:
  - id: consultant
    type: consultant
    output: [ADR, spec.yaml, requirements.md]
    gate: adr_valid
    # Consultant sagt: "Braucht Feasibility"
    next_recommendation: feasibility
    
  - id: feasibility
    type: feasibility
    input_from: consultant
    output: [poc/, findings.yaml]
    gate: poc_working
    
  - id: planning
    type: planning
    input_from: feasibility
    decompose: true  # Kann 1-4 neue Phasen erzeugen
    max_phases: 4
    output: [plan.yaml]  # Neue Phasen
    
  # ... dynamisch hinzugefügte Phasen ...
```

### Typ C: Exploratory (sehr unklar)

```yaml
project:
  type: exploratory
  
phases:
  - id: consultant
    type: consultant
    output: [questions.md, assumptions.md]
    # Kein ADR - zu früh!
    
  - id: research
    type: research
    input_from: consultant
    output: [findings.md]
    
  - id: decision
    type: consultant  # Nochmal Consultant
    input_from: research
    output: [ADR, recommendation.yaml]
    # Jetzt entscheiden: simple oder complex?
```

---

## Decompose: 1-4 Phasen Regel

### Warum 1-4?

```
Zu wenig (1):    Kein echter Decompose nötig
Optimal (2-4):   Überschaubar, parallelisierbar, reviewbar
Zu viel (5+):    Context Loss, schwer zu tracken
```

### Planning Output Format

```yaml
# output/plan.yaml - vom Planning-Agent generiert

decomposed_phases:
  - id: dev-data-layer
    type: development
    description: "Datenbank-Schema und Repository"
    estimated_sessions: 1  # 1 Claude Code CLI Session
    input: [spec.yaml, schema-design.md]
    output: [src/data/, tests/test_data/]
    gate: tests_pass
    
  - id: dev-api-layer
    type: development
    description: "REST API Endpoints"
    estimated_sessions: 2
    depends_on: [dev-data-layer]
    input: [src/data/, api-spec.yaml]
    output: [src/api/, tests/test_api/]
    gate: [syntax_check, tests_pass]
    
  - id: dev-integration
    type: development
    description: "Integration und E2E Tests"
    estimated_sessions: 1
    depends_on: [dev-api-layer]
    output: [tests/e2e/]
    gate: e2e_pass

# Meta-Info für Orchestrator
meta:
  total_phases: 3
  estimated_total_sessions: 4
  can_parallelize: [dev-data-layer]  # Erste Phase hat keine Deps
  critical_path: [dev-data-layer, dev-api-layer, dev-integration]
```

---

## Datenfluss zwischen Phasen

### Strukturierter Output (YAML/JSON)

```
Phase A                          Phase B
───────                          ───────
output/                          input/
├── result.yaml      ──COPY──►   ├── result.yaml
├── findings.yaml    ──COPY──►   ├── findings.yaml
└── src/             ──COPY──►   └── src/
```

### Orchestrator kopiert automatisch

```python
class PhaseRunner:
    async def prepare_phase(self, phase: Phase, previous: PhaseResult):
        """Kopiert relevante Outputs als Inputs."""
        
        # Was kopiert wird, steht in phases.yaml
        for source in phase.input_from:
            src_path = previous.output_dir / source
            dst_path = phase.input_dir / source
            
            if src_path.is_file():
                shutil.copy(src_path, dst_path)
            elif src_path.is_dir():
                shutil.copytree(src_path, dst_path)
```

### Strukturierte Outputs für Todos

```yaml
# output/todos.yaml - von jeder Phase
todos:
  - id: todo-1
    description: "API Rate Limiting implementieren"
    priority: high
    phase: dev-api-layer
    
  - id: todo-2
    description: "Caching für häufige Queries"
    priority: medium
    phase: dev-data-layer

# Orchestrator kann diese sammeln und an Planning weitergeben
```

---

## Quality Gates: Fix vs. Dynamisch

### Option A: Feste Gates pro Phase-Type (empfohlen für Start)

```yaml
# config/phase-types.yaml
phase_types:
  consultant:
    default_gates: [adr_valid]
    
  development:
    default_gates: [files_exist, syntax_check, tests_pass]
    
  review:
    default_gates: [review_approved]
    
  feasibility:
    default_gates: [poc_working]
    
  integration:
    default_gates: [all_tests_pass, docs_current]
```

**Vorteil:** Einfach, vorhersagbar
**Nachteil:** Weniger flexibel

### Option B: Gates in phases.yaml überschreibbar

```yaml
phases:
  - id: development
    type: development
    # Überschreibt default_gates
    gates:
      - syntax_check
      - tests_pass
      - coverage_min: 80  # Custom Parameter
```

### Option C: Planning-Agent kann Gates vorschlagen (später)

```yaml
# In plan.yaml vom Planning-Agent
decomposed_phases:
  - id: dev-critical-component
    type: development
    gates:
      - tests_pass
      - review_approved  # Weil kritisch!
      - security_scan    # Weil externe API
    
  - id: dev-utility
    type: development
    gates:
      - tests_pass  # Reicht für Utility
```

**Empfehlung:** Start mit A, dann B, später C.

---

## Orchestrator-Implementierung

### Minimal Viable Orchestrator

```python
# src/helix/orchestrator/runner.py

class Orchestrator:
    """Führt Projekte aus."""
    
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.phases = self.load_phases()
        self.status = ProjectStatus(project_dir / "status.yaml")
    
    async def run(self):
        """Hauptschleife."""
        
        phase_queue = deque(self.phases)
        
        while phase_queue:
            phase = phase_queue.popleft()
            
            # Skip wenn schon erledigt
            if self.status.is_complete(phase.id):
                continue
            
            # Inputs vorbereiten
            await self.prepare_inputs(phase)
            
            # Phase ausführen (Claude Code CLI)
            result = await self.run_phase(phase)
            
            # Gates prüfen
            gate_result = await self.check_gates(phase, result)
            
            if gate_result.passed:
                self.status.mark_complete(phase.id)
                
                # Decompose?
                if phase.decompose and result.has_plan():
                    new_phases = self.parse_plan(result)
                    phase_queue.extendleft(reversed(new_phases))
            else:
                # Retry oder Abbruch
                action = self.handle_failure(phase, gate_result)
                if action == "retry":
                    phase_queue.appendleft(phase)
                elif action == "abort":
                    break
        
        await self.finalize()
    
    async def run_phase(self, phase: Phase) -> PhaseResult:
        """Spawnt Claude Code CLI für eine Phase."""
        
        phase_dir = self.project_dir / "phases" / phase.id
        
        # Claude Code CLI starten
        process = await asyncio.create_subprocess_exec(
            "claude",
            "-p",  # Print mode
            "--dangerously-skip-permissions",
            f"Du bist in Phase '{phase.id}'. Lies CLAUDE.md und führe die Aufgabe aus.",
            cwd=phase_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        stdout, stderr = await process.communicate()
        
        return PhaseResult(
            phase_id=phase.id,
            success=process.returncode == 0,
            output_dir=phase_dir / "output",
        )
```

### Status-Tracking

```yaml
# status.yaml - vom Orchestrator gepflegt
project: my-feature
started_at: 2025-12-23T10:00:00
status: in_progress

phases:
  consultant:
    status: complete
    completed_at: 2025-12-23T10:05:00
    retries: 0
    
  development:
    status: in_progress
    started_at: 2025-12-23T10:06:00
    retries: 1
    last_error: "tests_pass failed"
    
  review:
    status: pending
```

---

## CLI Integration

### Existierende API nutzen

```python
# src/helix/cli/project.py

@click.group()
def project():
    """Projekt-Management."""
    pass

@project.command()
@click.argument("name")
@click.option("--type", default="simple", type=click.Choice(["simple", "complex"]))
def create(name: str, type: str):
    """Neues Projekt erstellen."""
    ProjectCreator(name, type).create()

@project.command()
@click.argument("name")
def run(name: str):
    """Projekt ausführen."""
    orchestrator = Orchestrator(Path(f"projects/{name}"))
    asyncio.run(orchestrator.run())

@project.command()
@click.argument("name")
def status(name: str):
    """Projekt-Status anzeigen."""
    status = ProjectStatus.load(Path(f"projects/{name}/status.yaml"))
    status.print_summary()
```

### API Endpoint

```python
# src/helix/api/routes/project.py

@router.post("/project/{name}/run")
async def run_project(name: str, background_tasks: BackgroundTasks):
    """Startet Projekt-Ausführung im Hintergrund."""
    background_tasks.add_task(run_orchestrator, name)
    return {"status": "started", "project": name}

@router.get("/project/{name}/status")
async def get_status(name: str):
    """Gibt Projekt-Status zurück."""
    status = ProjectStatus.load(...)
    return status.to_dict()
```

---

## Beispiel: ADR-Implementation Workflow

So würde der heutige Workflow aussehen:

```yaml
# projects/implement-adr-014/phases.yaml
project:
  name: implement-adr-014
  type: simple  # Consultant hat entschieden: Schema F
  
phases:
  - id: phase-1-2
    type: development
    description: "Core Implementation (completeness, concept_diff, approval)"
    input:
      - ../../adr/014-documentation-architecture.md
      - ../../adr/015-approval-validation-system.md
    output:
      - src/helix/adr/completeness.py
      - src/helix/adr/concept_diff.py
      - src/helix/approval/
    gate: [syntax_check, tests_pass]
    
  - id: phase-3
    type: development
    description: "Quality Gate Integration"
    depends_on: [phase-1-2]
    input_from: phase-1-2
    output:
      - src/helix/gates/
    gate: [syntax_check, tests_pass]
    
  - id: phase-4
    type: development
    description: "Templates & Sources"
    depends_on: [phase-1-2]  # Kann parallel zu phase-3!
    output:
      - docs/sources/*.yaml
      - docs/templates/*.j2
    gate: files_exist
    
  - id: phase-5
    type: integration
    description: "Migration & E2E Tests"
    depends_on: [phase-3, phase-4]
    output:
      - scripts/
      - tests/
    gate: [tests_pass, docs_compiled]
    
  - id: review
    type: review
    depends_on: [phase-5]
    gate: review_approved
```

### Was der Orchestrator gemacht hätte

```
1. Lädt phases.yaml
2. phase-1-2: Spawnt Claude Code CLI, wartet, prüft gates ✓
3. phase-3 + phase-4: Parallel möglich (keine gegenseitige Dep)
4. phase-5: Wartet auf 3+4, dann spawnt
5. review: Spawnt Approval Sub-Agent
6. Kopiert alle outputs nach Hauptprojekt
7. Schreibt status.yaml: complete
```

**Statt dass ICH das manuell gemacht habe.**

---

## Zusammenfassung der Entscheidungen

| Frage | Entscheidung |
|-------|--------------|
| Orchestrator wo? | CLI + API (beides) |
| Decompose Granularität | 1-4 Phasen |
| Quality Gates | Fix pro Phase-Type, überschreibbar |
| Datenfluss | Orchestrator kopiert input_from |
| Hardware-Tools | Bash zuerst |
| Projekt-Typen | simple, complex, exploratory |

## Nächste Schritte

1. **ADR-017: Phase Orchestrator** - Formal dokumentieren
2. **MVP implementieren** - Minimal Orchestrator ohne Decompose
3. **Test mit echtem Projekt** - z.B. "Bug Fixes aus BACKLOG"
4. **Decompose hinzufügen** - Planning-Phase die plan.yaml generiert

