# ADR-000: HELIX v4 Vision & Architektur

**Status:** Akzeptiert  
**Datum:** 2025-12-21  
**Autor:** Uwe + Claude  
**Vorgänger:** HELIX v3

---

## Kontext & Problem

HELIX v3 hat gezeigt, dass Multi-Agent-Systeme funktionieren, aber wir haben 
zu viel Aufwand in eigene Agent-Implementierung gesteckt.

### Erkenntnis

> "Claude Code ist bereits das perfekte Agent-Harness.
>  Wir müssen es nur richtig orchestrieren."

---

## Entscheidung

### HELIX v4 = Claude Code CLI + Datei-basierte Orchestrierung

**Kein SDK nötig!** Claude Code liest automatisch `CLAUDE.md` als Context.

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│   CLAUDE CODE MACHT              WIR MACHEN                     │
│   ──────────────────             ──────────                     │
│   • Agent Loop                   • Verzeichnisse vorbereiten    │
│   • Tool Calling                 • CLAUDE.md aus Templates      │
│   • Error Handling               • Skills verlinken             │
│   • ReAct/CoT                    • Quality Gates (Python)       │
│   • File Operations              • Orchestrierung (Python)      │
│   • Context aus CLAUDE.md        • Observability & Logs         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Kernarchitektur

### 1. Projekt-Struktur

```
helix-v4/
├── templates/                      # Prompt-Templates
│   ├── consultant/
│   │   ├── pdm.md                 # PDM Domain
│   │   ├── erp.md                 # ERP Domain
│   │   └── generic.md
│   ├── developer/
│   │   ├── python.md              # Python Developer
│   │   ├── cpp.md                 # C++ Developer
│   │   ├── go.md                  # Go Developer
│   │   ├── typescript.md          # TypeScript Developer
│   │   └── deploy.md              # DevOps/Deploy
│   ├── reviewer/
│   │   ├── code.md                # Code Review
│   │   ├── security.md            # Security Review
│   │   └── architecture.md        # Architecture Review
│   └── documentation/
│       ├── api.md                 # API Docs
│       ├── user.md                # User Docs
│       └── technical.md           # Technical Docs
│
├── skills/                         # Wiederverwendbare Skills
│   ├── languages/
│   │   ├── python-patterns.md
│   │   ├── python-testing.md
│   │   ├── cpp-modern.md
│   │   └── go-idioms.md
│   ├── tools/
│   │   ├── docker.md
│   │   ├── kubernetes.md
│   │   └── git.md
│   └── domains/
│       ├── pdm-structure.md
│       ├── erp-integration.md
│       └── legacy-patterns.md
│
├── projects/
│   ├── internal/                   # HELIX Selbst-Entwicklung
│   │   └── {feature-name}/
│   └── external/                   # Externe Projekte
│       └── {project-name}/
│
├── logs/                           # Zentrale Logs
│   └── {date}/
│       └── {project-id}/
│
└── src/                            # Python Orchestrator
    └── helix/
        ├── orchestrator.py
        ├── quality_gates.py
        ├── template_engine.py
        └── observability.py
```

### 2. Projekt-Verzeichnis (pro Feature/Task)

```
projects/external/bom-export-csv/
│
├── state.json                      # Workflow-State
├── spec.yaml                       # Implementation Spec (von Consultant)
│
├── phases/
│   ├── 01-consultant/
│   │   ├── CLAUDE.md              # Generiert aus template + context
│   │   ├── context/               # Domain-Wissen (symlinks)
│   │   │   ├── pdm-structure.md → /helix-v4/skills/domains/pdm-structure.md
│   │   │   └── bom-format.md    → /helix-v4/skills/domains/bom-format.md
│   │   ├── input/                 # User Request
│   │   │   └── request.md
│   │   ├── output/                # Consultant Output
│   │   │   └── spec.yaml         # → wird nach ../spec.yaml kopiert
│   │   └── logs/
│   │       ├── claude.log         # Claude Code Output
│   │       ├── claude.json        # Strukturierter Output (--output-format json)
│   │       └── session.md         # Conversation Transcript
│   │
│   ├── 02-developer/
│   │   ├── CLAUDE.md              # Generiert basierend auf spec.yaml
│   │   ├── skills/                # Relevante Skills (symlinks)
│   │   │   ├── python-patterns.md
│   │   │   └── python-testing.md
│   │   ├── src/                   # Hier schreibt Developer Code
│   │   └── logs/
│   │       ├── claude.log
│   │       ├── claude.json
│   │       └── files-created.json # Tracking was erstellt wurde
│   │
│   ├── 03-reviewer/
│   │   ├── CLAUDE.md
│   │   ├── input/                 # Was reviewed wird
│   │   │   └── files-to-review.json
│   │   ├── output/
│   │   │   └── review.json        # Strukturiertes Review-Ergebnis
│   │   └── logs/
│   │
│   └── 04-documentation/
│       ├── CLAUDE.md
│       ├── output/
│       │   └── docs/
│       └── logs/
│
└── final/
    ├── summary.json               # Projekt-Zusammenfassung
    ├── lessons-learned.md         # Final Consultant Review
    └── metrics.json               # Performance-Metriken
```

---

## Workflow im Detail

### Phase 0: Projekt-Setup (Python Orchestrator)

```python
def setup_project(project_name: str, domain: str, request: str) -> Path:
    """Erstellt Projekt-Verzeichnis mit allen Phasen."""
    
    project_dir = PROJECTS_DIR / "external" / project_name
    project_dir.mkdir(parents=True)
    
    # State initialisieren
    state = {
        "project_id": project_name,
        "created": datetime.now().isoformat(),
        "domain": domain,
        "phase": "consultant",
        "quality_gates": {}
    }
    (project_dir / "state.json").write_text(json.dumps(state, indent=2))
    
    # Consultant-Phase vorbereiten
    setup_consultant_phase(project_dir, domain, request)
    
    return project_dir
```

### Phase 1: Consultant Meeting

```python
def setup_consultant_phase(project_dir: Path, domain: str, request: str):
    """Bereitet Consultant-Phase vor."""
    
    phase_dir = project_dir / "phases" / "01-consultant"
    phase_dir.mkdir(parents=True)
    
    # Template laden und füllen
    template = load_template(f"consultant/{domain}.md")
    claude_md = template.render(
        domain=domain,
        request=request,
        output_format="spec.yaml"
    )
    (phase_dir / "CLAUDE.md").write_text(claude_md)
    
    # Context verlinken
    context_dir = phase_dir / "context"
    context_dir.mkdir()
    for skill in get_domain_skills(domain):
        (context_dir / skill.name).symlink_to(skill.path)
    
    # Request speichern
    (phase_dir / "input").mkdir()
    (phase_dir / "input" / "request.md").write_text(request)
    
    # Logs vorbereiten
    (phase_dir / "logs").mkdir()
    (phase_dir / "output").mkdir()
```

### Claude Code starten (mit Logging)

```python
def run_claude_phase(phase_dir: Path) -> dict:
    """Startet Claude Code in einer Phase mit vollem Logging."""
    
    logs_dir = phase_dir / "logs"
    
    # Claude Code mit JSON Output starten
    result = subprocess.run(
        [
            "claude",
            "--print",                    # Non-interactive
            "--output-format", "json",    # Strukturierter Output
            "--verbose"                   # Mehr Details
        ],
        cwd=phase_dir,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "ANTHROPIC_BASE_URL": "https://openrouter.ai/api/v1",
            "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY"),
        }
    )
    
    # Logs speichern
    (logs_dir / "claude.log").write_text(result.stdout + "\n" + result.stderr)
    
    # JSON Output parsen und speichern
    try:
        output = json.loads(result.stdout)
        (logs_dir / "claude.json").write_text(json.dumps(output, indent=2))
    except json.JSONDecodeError:
        output = {"raw": result.stdout}
    
    # Metriken extrahieren
    metrics = extract_metrics(output)
    (logs_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))
    
    return {
        "success": result.returncode == 0,
        "output": output,
        "metrics": metrics
    }
```

### Phase 2: Developer (Context aus Spec)

```python
def setup_developer_phase(project_dir: Path):
    """Bereitet Developer-Phase basierend auf Spec vor."""
    
    spec = yaml.safe_load((project_dir / "spec.yaml").read_text())
    phase_dir = project_dir / "phases" / "02-developer"
    phase_dir.mkdir(parents=True)
    
    # Sprache aus Spec ermitteln
    language = detect_language(spec)  # python, cpp, go, etc.
    
    # Template für diese Sprache laden
    template = load_template(f"developer/{language}.md")
    
    claude_md = template.render(
        summary=spec["implementation"]["summary"],
        files_to_create=spec["implementation"]["files_to_create"],
        files_to_modify=spec["implementation"].get("files_to_modify", []),
        acceptance_criteria=spec["implementation"]["acceptance_criteria"],
        context_docs=spec.get("context", {}).get("relevant_docs", [])
    )
    (phase_dir / "CLAUDE.md").write_text(claude_md)
    
    # Sprach-spezifische Skills verlinken
    skills_dir = phase_dir / "skills"
    skills_dir.mkdir()
    for skill in get_language_skills(language):
        (skills_dir / skill.name).symlink_to(skill.path)
    
    # Arbeitsverzeichnis
    (phase_dir / "src").mkdir()
    (phase_dir / "logs").mkdir()
```

---

## Kommunikation zwischen Phasen

**Alles über Dateien - kein SDK, kein EventBus!**

```
┌─────────────┐                      ┌─────────────┐
│  Consultant │                      │  Developer  │
│   (claude)  │                      │   (claude)  │
└──────┬──────┘                      └──────┬──────┘
       │                                    │
       │  spec.yaml                         │  src/*.py
       │  (strukturiert)                    │  files-created.json
       ▼                                    ▼
┌─────────────────────────────────────────────────────┐
│                  Dateisystem                         │
│                                                      │
│  spec.yaml ──────────────────▶ CLAUDE.md (Developer) │
│  src/*.py ───────────────────▶ CLAUDE.md (Reviewer)  │
│  review.json ────────────────▶ CLAUDE.md (Docs)      │
└─────────────────────────────────────────────────────┘
```

### Strukturierte Outputs

```yaml
# spec.yaml (Consultant → Developer)
meta:
  id: "spec-2025-12-21-001"
  domain: "pdm"
  language: "python"

implementation:
  summary: "BOM-to-CSV Exporter"
  files_to_create:
    - path: "src/exporters/bom_csv.py"
      description: "Hauptmodul"
    - path: "tests/test_bom_csv.py"
      description: "Unit Tests"
  acceptance_criteria:
    - "Export generiert valides CSV"
    - "Tests sind grün"
```

```json
// review.json (Reviewer → Developer/Docs)
{
  "status": "changes_requested",
  "summary": "Gute Struktur, aber fehlende Error-Handling",
  "issues": [
    {
      "file": "src/exporters/bom_csv.py",
      "line": 45,
      "severity": "high",
      "message": "FileNotFoundError nicht abgefangen",
      "suggestion": "try/except Block hinzufügen"
    }
  ],
  "approved_files": ["tests/test_bom_csv.py"],
  "requires_changes": ["src/exporters/bom_csv.py"]
}
```

---

## Observability & Debugging

### 3-Ebenen Logging

```
┌─────────────────────────────────────────────────────────────────┐
│  EBENE 1: Claude Code Logs (pro Phase)                          │
│  ─────────────────────────────────────                          │
│  phases/02-developer/logs/                                      │
│  ├── claude.log        # Vollständiger stdout/stderr            │
│  ├── claude.json       # Strukturierter Output (--output-format)│
│  ├── session.md        # Conversation Transcript                │
│  └── metrics.json      # Tokens, Duration, Tool Calls           │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  EBENE 2: Orchestrator Logs (pro Projekt)                       │
│  ────────────────────────────────────────                       │
│  logs/2025-12-21/bom-export-csv/                                │
│  ├── orchestrator.log  # Python Orchestrator Actions            │
│  ├── quality-gates.log # Gate Results                           │
│  ├── state-history.jsonl # State Changes over Time              │
│  └── errors.log        # Errors & Exceptions                    │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  EBENE 3: System Logs (global)                                  │
│  ─────────────────────────────                                  │
│  logs/system/                                                   │
│  ├── helix.log         # Alle Projekte, alle Phasen             │
│  ├── metrics.jsonl     # Aggregierte Metriken                   │
│  └── audit.log         # Wer hat was wann gestartet             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Metriken pro Phase

```python
# observability.py

@dataclass
class PhaseMetrics:
    phase: str
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    
    # Claude Code Metriken
    tokens_input: int
    tokens_output: int
    tokens_total: int
    cost_usd: float
    
    # Tool Usage
    tool_calls: int
    tools_used: dict[str, int]  # {"Read": 5, "Write": 3, ...}
    
    # Ergebnis
    files_created: list[str]
    files_modified: list[str]
    errors: list[str]
    
    # Quality Gate
    gate_passed: bool
    gate_details: dict


def extract_metrics(claude_output: dict) -> PhaseMetrics:
    """Extrahiert Metriken aus Claude Code JSON Output."""
    
    usage = claude_output.get("usage", {})
    
    return PhaseMetrics(
        tokens_input=usage.get("input_tokens", 0),
        tokens_output=usage.get("output_tokens", 0),
        tokens_total=usage.get("total_tokens", 0),
        cost_usd=calculate_cost(usage),
        tool_calls=len(claude_output.get("tool_uses", [])),
        tools_used=count_tools(claude_output.get("tool_uses", [])),
        # ... etc
    )
```

### Debug Dashboard (CLI)

```python
# debug_dashboard.py

def show_project_status(project_id: str):
    """Zeigt aktuellen Projekt-Status."""
    
    project_dir = PROJECTS_DIR / "external" / project_id
    state = json.loads((project_dir / "state.json").read_text())
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║  HELIX v4 - Project: {project_id:<40} ║
╠══════════════════════════════════════════════════════════════╣
║  Phase:    {state['phase']:<50} ║
║  Created:  {state['created']:<50} ║
╠══════════════════════════════════════════════════════════════╣
║  Quality Gates:                                              ║
""")
    
    for gate, result in state.get("quality_gates", {}).items():
        status = "✅ PASS" if result.get("passed") else "❌ FAIL"
        print(f"║    {gate}: {status:<48} ║")
    
    print("╚══════════════════════════════════════════════════════════════╝")


def tail_phase_logs(project_id: str, phase: str):
    """Live-Tail der Phase-Logs."""
    
    log_file = PROJECTS_DIR / "external" / project_id / "phases" / phase / "logs" / "claude.log"
    
    subprocess.run(["tail", "-f", str(log_file)])


def show_cost_summary(project_id: str):
    """Zeigt Kosten-Übersicht."""
    
    project_dir = PROJECTS_DIR / "external" / project_id
    total_cost = 0.0
    
    for phase_dir in (project_dir / "phases").iterdir():
        metrics_file = phase_dir / "logs" / "metrics.json"
        if metrics_file.exists():
            metrics = json.loads(metrics_file.read_text())
            phase_cost = metrics.get("cost_usd", 0)
            total_cost += phase_cost
            print(f"  {phase_dir.name}: ${phase_cost:.4f}")
    
    print(f"\n  TOTAL: ${total_cost:.4f}")
```

### Error Tracking

```python
# Bei Fehlern in einer Phase
def handle_phase_error(project_dir: Path, phase: str, error: Exception):
    """Dokumentiert Fehler für Debugging."""
    
    error_record = {
        "timestamp": datetime.now().isoformat(),
        "phase": phase,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "traceback": traceback.format_exc(),
        "state_snapshot": json.loads((project_dir / "state.json").read_text())
    }
    
    # In Phase-Logs
    phase_errors = project_dir / "phases" / phase / "logs" / "errors.json"
    errors = json.loads(phase_errors.read_text()) if phase_errors.exists() else []
    errors.append(error_record)
    phase_errors.write_text(json.dumps(errors, indent=2))
    
    # In globale Error-Logs
    global_errors = LOGS_DIR / "errors.jsonl"
    with open(global_errors, "a") as f:
        f.write(json.dumps(error_record) + "\n")
```

---

## Template-System

### CLAUDE.md Template (Developer Python)

```markdown
# Developer - Python

Du bist ein erfahrener Python Developer für das HELIX Projekt.

## Deine Aufgabe

Implementiere folgendes Feature:

**{{summary}}**

## Zu erstellende Dateien

{{#each files_to_create}}
### `{{path}}`
{{description}}

{{/each}}

## Akzeptanzkriterien

{{#each acceptance_criteria}}
- [ ] {{this}}
{{/each}}

## Wichtige Regeln

1. Erstelle ALLE oben genannten Dateien
2. Schreibe sauberen, typisierten Python Code (typing hints!)
3. Jede Funktion braucht einen Docstring
4. Tests müssen mit pytest laufen
5. Halte dich an PEP 8

## Verfügbare Skills

Lies die Dateien in `skills/` für Best Practices:
{{#each skills}}
- `skills/{{this}}`
{{/each}}

## Output

Wenn du fertig bist, erstelle eine Datei `logs/files-created.json`:

```json
{
  "files_created": ["path/to/file1.py", "path/to/file2.py"],
  "files_modified": [],
  "tests_passed": true,
  "notes": "Optional: Besondere Hinweise"
}
```
```

### Template Engine

```python
# template_engine.py

from jinja2 import Environment, FileSystemLoader

class TemplateEngine:
    def __init__(self, templates_dir: Path):
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            trim_blocks=True,
            lstrip_blocks=True
        )
    
    def render(self, template_name: str, **context) -> str:
        template = self.env.get_template(f"{template_name}.md")
        return template.render(**context)
    
    def render_developer(self, spec: dict, language: str) -> str:
        return self.render(
            f"developer/{language}",
            summary=spec["implementation"]["summary"],
            files_to_create=spec["implementation"]["files_to_create"],
            acceptance_criteria=spec["implementation"]["acceptance_criteria"],
            skills=self.get_language_skills(language)
        )
```

---

## Quality Gates (unverändert von ADR-002)

```
Phase 1 ──▶ QG1 (Spec complete?) ──▶ Phase 2
Phase 2 ──▶ QG2 (Files created? Syntax OK?) ──▶ Phase 3
Phase 3 ──▶ QG3 (Review approved?) ──▶ Phase 4
Phase 4 ──▶ QG4 (Docs written?) ──▶ Final Review
```

---

## Vorteile dieses Ansatzes

| Aspekt | Warum besser |
|--------|--------------|
| **Kein SDK** | Weniger Abhängigkeiten, einfacher |
| **CLAUDE.md** | Native Claude Code Feature |
| **Datei-basiert** | Debuggbar, versionierbar, nachvollziehbar |
| **Templates** | Wiederverwendbar, anpassbar |
| **Logging** | 3-Ebenen für volle Transparenz |
| **Skills** | Symlinks = keine Duplikation |

---

## Nächste Schritte

1. **Template-Sammlung** erstellen (Consultant, Developer, Reviewer, Docs)
2. **Orchestrator** implementieren (Python)
3. **Quality Gates** implementieren (Python)
4. **POC** mit einem echten Projekt testen
5. **Open WebUI** Integration

---

## Referenzen

- [Claude Code CLAUDE.md](https://docs.claude.ai/claude-code/project-files)
- HELIX v3 ADRs: 043, 047, 067, 071, 084, 094, 095

