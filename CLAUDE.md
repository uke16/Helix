<!-- AUTO-GENERATED from docs/sources/*.yaml -->
<!-- Template: docs/templates/CLAUDE.md.j2 -->
<!-- Regenerate: python -m helix.tools.docs_compiler compile -->


# HELIX v4 - Instructions for Claude Code

> **Du arbeitest im HELIX v4 Projekt** - einem AI Development Orchestration System.
>
> Lies diese Datei um zu verstehen wie du hier arbeiten sollst.

---

## Projekt verstehen

HELIX orchestriert Claude Code Instanzen um Software zu entwickeln. Du bist möglicherweise:

1. **Consultant** - Führst ein Meeting mit dem User, generierst spec.yaml
2. **Developer** - Implementierst Code basierend auf Spezifikation
3. **Reviewer** - Überprüfst Code auf Qualität
4. **Dokumentation** - Schreibst technische Dokumentation

### Deine Rolle erkennen

Schau in deinem Arbeitsverzeichnis nach:
- `CLAUDE.md` - Enthält spezifische Anweisungen für deine Phase
- `input/` - Dateien die du als Input lesen sollst
- `output/` - Hier schreibst du deine Ergebnisse

---

## Wichtige Dateien zuerst lesen

### Immer lesen:
1. Diese Datei (CLAUDE.md im Root)
2. CLAUDE.md in deinem Phase-Verzeichnis
3. Relevante Skills in `skills/`

### Skills nach Bedarf:- `skills/helix/SKILL.md` - Orchestration & evolution- `skills/pdm/SKILL.md` - Product data management- `skills/encoder/SKILL.md` - Encoder products- `skills/infrastructure/SKILL.md` - System infrastructure- `skills/lsp/SKILL.md` - Dev tools (LSP, Debug)- `skills/api/SKILL.md` - API development
---

## Output-Regeln

### Dateien erstellen
- Schreibe Ergebnisse nach `output/` in deinem Phase-Verzeichnis
- Nutze sprechende Dateinamen: `schema-analysis.md`, `config_validator.py`
- Erstelle keine Dateien außerhalb deines Arbeitsverzeichnisses

### Formate
- `.yaml` für Konfiguration und Specs
- `.py` für Python Code
- `.md` für Dokumentation und Analysen

### Quality Gates
Dein Output wird automatisch validiert:
- Existieren alle erwarteten Dateien?
- Ist der Code syntaktisch korrekt?
- Laufen die Tests?

→ Schau in `phases.yaml` welche Output-Dateien erwartet werden.

---

## Quality Gates Reference

HELIX verwendet Quality Gates um die Qualität deiner Arbeit zu validieren.

### Verfügbare Gate-Typen

| Gate Type | Beschreibung | Verwendung |
|-----------|--------------|------------|| `files_exist` | Checks if output files exist | development, documentation || `syntax_check` | Validates code syntax | development || `tests_pass` | Runs tests and checks for success | testing || `review_approved` | LLM reviews output for quality | review || `adr_valid` | Validates ADR document structure | consultant, review |
### Gate: `adr_valid`

Validiert Architecture Decision Records gegen das ADR-086 Template:

```yaml
# phases.yaml
quality_gate:
  type: adr_valid
  file: output/feature-adr.md
```

**Was wird geprüft:**

1. **YAML Header** (Pflichtfelder)   - `adr_id` - Eindeutige ID   - `title` - Beschreibender Titel   - `status` - Proposed|Accepted|Implemented|Superseded|Rejected
2. **Markdown Sections** (alle müssen vorhanden sein)   - `## Kontext` - Warum diese Änderung?   - `## Entscheidung` - Was wird entschieden?   - `## Implementation` - Konkrete Umsetzung   - `## Dokumentation` - Zu aktualisierende Dokumente   - `## Akzeptanzkriterien` - Checkbox-Liste   - `## Konsequenzen` - Vorteile/Nachteile
3. **Akzeptanzkriterien**
   - Mindestens ein `- [ ]` oder `- [x]` Checkbox vorhanden

**Fehler vs. Warnungen:**

- **Fehler** (Gate schlägt fehl): Fehlende Pflichtfelder/Sections
- **Warnungen** (Gate besteht): Fehlende empfohlene Felder, wenige Kriterien

**Beispiel-Verwendung:**

```yaml
phases:
  - id: "3"
    name: ADR Review
    type: review
    quality_gate:
      type: adr_valid
      file: output/feature-adr.md
```

→ Siehe: [docs/ADR-TEMPLATE.md](docs/ADR-TEMPLATE.md) für das vollständige Template.
---

## Projekt-Struktur

```
helix-v4/
├── CLAUDE.md              ← Diese Datei
├── ONBOARDING.md          ← Konzept-Erklärung
│
├── src/helix/             # Python Orchestrator
├── config/                # Konfiguration
├── templates/             # CLAUDE.md Templates
├── skills/                # Domain-Wissen
│
├── projects/
│   ├── sessions/          # Consultant Sessions
│   │   └── {session-id}/
│   │       ├── CLAUDE.md
│   │       ├── input/
│   │       └── output/
│   │
│   └── external/          # Ausführbare Projekte
│       └── {projekt-name}/
│           ├── spec.yaml
│           ├── phases.yaml
│           └── phases/
│               ├── 01-analysis/
│               │   ├── CLAUDE.md
│               │   └── output/
│               ├── 02-implementation/
│               └── 03-testing/
```

---

## Consultant-Rolle

Wenn du als **Consultant** arbeitest:

### Deine Aufgabe1. Lies den User-Request in `input/request.md`2. Lies relevante Skills (`skills/pdm/`, etc.)3. Stelle klärende Fragen (Was? Warum? Constraints?)4. Generiere `output/spec.yaml` und `output/phases.yaml`
### Fragen-Schema
```markdown
## Klärende Fragen
### Was genau soll gebaut werden?
[Warte auf User-Antwort]
### Warum wird das benötigt?
[Warte auf User-Antwort]
### Welche Constraints gibt es?
[Warte auf User-Antwort]```

### Output generieren
Wenn du genug Informationen hast:

**spec.yaml:**
```yamlname: Feature Name
type: feature
description: Kurze Beschreibung
goals:
  - Ziel 1
  - Ziel 2
requirements:
  - Anforderung 1
constraints:
  - Constraint 1```

**phases.yaml:**
```yamlphases:
  - id: 01-analysis
    name: Analyse
    type: development
    # ...```

---

## Developer-Rolle

Wenn du als **Developer** arbeitest:

### Deine Aufgabe
1. Lies `spec.yaml` im Projekt-Root
2. Lies deine Phase-CLAUDE.md für spezifische Anweisungen
3. Lies Input-Dateien aus vorherigen Phasen
4. Implementiere und schreibe nach `output/`

### Code-Standards
- Python: PEP 8, Type Hints, Docstrings
- Dateien: UTF-8, Unix Line Endings
- Tests: pytest Format

---

## Wichtige Hinweise

### DO:
- ✅ Lies CLAUDE.md in deinem Verzeichnis
- ✅ Lies relevante Skills
- ✅ Schreibe nach output/
- ✅ Erstelle vollständige, lauffähige Dateien
- ✅ Dokumentiere was du getan hast

### DON'T:
- ❌ Ändere keine Dateien außerhalb deines Verzeichnisses
- ❌ Lösche keine existierenden Dateien
- ❌ Installiere keine System-Pakete
- ❌ Mache keine Netzwerk-Requests ohne Grund

---

## Hilfe

- **HELIX Konzept**: Lies [ONBOARDING.md](ONBOARDING.md)
- **Architektur**: Lies [docs/ARCHITECTURE-MODULES.md](docs/ARCHITECTURE-MODULES.md)
- **ADR Template**: Lies [docs/ADR-TEMPLATE.md](docs/ADR-TEMPLATE.md)
- **Skills**: Schau in `skills/` für Domain-Wissen

---

## Evolution Projects

HELIX supports self-evolution through isolated test system validation.

### Project Type: evolution

Evolution projects live in `projects/evolution/{name}/`:

```
projects/evolution/new-feature/
├── spec.yaml        # Project specification
├── phases.yaml      # Development phases
├── status.json      # Current status
├── new/             # New files to create
│   └── src/helix/...
└── modified/        # Modified files
    └── src/helix/...
```

### Status Flow

```PENDING → DEVELOPING → READY → DEPLOYED → VALIDATED → INTEGRATED
                              ↓           ↓
                           FAILED ← ← ← ROLLBACK```

### Evolution API

```bash# List projects
curl http://localhost:8001/helix/evolution/projects
# Deploy to test
curl -X POST http://localhost:8001/helix/evolution/projects/{name}/deploy
# Validate
curl -X POST http://localhost:8001/helix/evolution/projects/{name}/validate
# Integrate
curl -X POST http://localhost:8001/helix/evolution/projects/{name}/integrate
```

### Safety Guarantees1. Changes always deploy to test system first2. Full validation (syntax, unit, E2E) before integration3. Automatic rollback on failure4. Git tag backup before integration5. RAG database 1:1 copy for realistic testing
---

## Workflow System (ADR-023 bis ADR-026)

HELIX verwendet Workflows zur Projekt-Orchestrierung.

### Workflow-Typen

| Workflow | Projekt-Typ | Wann verwenden |
|----------|-------------|----------------|
| `intern-simple` | helix_internal | HELIX Feature, klar definiert |
| `intern-complex` | helix_internal | HELIX Feature, unklar/groß |
| `extern-simple` | external | Externes Tool, klar definiert |
| `extern-complex` | external | Externes Tool, groß/unklar |

### Sub-Agent Verifikation

Phasen mit `verify_agent: true` werden durch einen Sub-Agent (Haiku) geprüft:
- 3 Retries bei Fehlern
- Feedback via `feedback.md`
- Eskalation bei finalem Fail

### Dynamische Phasen

Complex Workflows nutzen einen PlanningAgent der 1-5 Phasen dynamisch generiert.

→ **Mehr Details:** [docs/WORKFLOW-SYSTEM.md](docs/WORKFLOW-SYSTEM.md)
→ **Skill:** [skills/helix/workflows.md](skills/helix/workflows.md)

---

## Self-Documentation Prinzip

> **Jede Änderung dokumentiert sich selbst.**

Wenn du ein neues Feature oder eine Änderung implementierst:

1. **CONCEPT.md** muss eine "Dokumentation" Section haben
2. **phases.yaml** braucht eine Documentation-Phase
3. **Alle 4 Ebenen** müssen aktualisiert werden:
   - Top-Level (README, ONBOARDING, CLAUDE.md)
   - Architecture Docs (docs/*.md)
   - Skills (skills/*/SKILL.md)
   - Docstrings (im Code)

→ **Lies:** [docs/SELF-DOCUMENTATION.md](docs/SELF-DOCUMENTATION.md)

### Warum?

Claude Code Instanzen lesen die Dokumentation um zu verstehen wie sie arbeiten sollen.
Features die nicht dokumentiert sind, werden von zukünftigen Instanzen ignoriert.

---

## Available Tools

HELIX provides tools that Claude Code instances can call during development.
### ADR Tool (`helix.tools.adr_tool`)

Validate and finalize Architecture Decision Records

```bash# Validate an ADR
python -m helix.tools.adr_tool validate path/to/ADR.md# Finalize (move to adr/ and update INDEX)
python -m helix.tools.adr_tool finalize path/to/ADR.md# Get next available ADR number
python -m helix.tools.adr_tool next-number```
**Python API:**
```python
from helix.tools import validate_adr, finalize_adr, get_next_adr_number
# Validate
result = validate_adr("ADR-feature.md")
if not result.success:
    print(result.errors)
# Finalize
result = finalize_adr("ADR-feature.md")
print(result.final_path)  # → adr/013-feature.md
# Next number
next_num = get_next_adr_number()  # → 13```
### Docs Compiler (`helix.tools.docs_compiler`)

Compile documentation from YAML sources and Jinja2 templates

```bash# Generate docs
python -m helix.tools.docs_compiler compile# Check without writing
python -m helix.tools.docs_compiler validate# List sources
python -m helix.tools.docs_compiler sources# Show changes
python -m helix.tools.docs_compiler diff```
**Python API:**
```python
from helix.tools.docs_compiler import DocsCompiler
# Compile
compiler = DocsCompiler()
result = compiler.compile()
print(f"Generated: {result.files}")
# Validate
compiler = DocsCompiler()
issues = compiler.validate()
if issues:
    print(issues)```
### Verify Phase Tool (`helix.tools.verify_phase`)

Verify phase outputs before completing a phase

```bash# Verify current phase outputs
python -m helix.tools.verify_phase```
### Debug & Observability Tools (`helix.debug`)

Live debugging and cost tracking for Claude CLI executions

```bash# Run Claude CLI with verbose debug output
./control/claude-wrapper.sh -v -- --print 'prompt'# Start debug session with terminal dashboard
./control/helix-debug.sh -d phases/01-analysis# Start debug session with web dashboard
./control/helix-debug.sh -w -p 8080 phases/01-analysis```
**Python API:**
```python
from helix.debug import StreamParser, ToolTracker, CostCalculator, LiveDashboard
# Parse Claude CLI stream
parser = StreamParser()
async for event in parser.parse_stream(process.stdout):
    print(f"{event.type}: {event.data}")
# Track tool calls
tracker = ToolTracker()
tracker.start_tool("123", "bash_tool", {"command": "ls"})
tracker.end_tool("123", output="file.txt", success=True)
print(tracker.get_stats())
# Calculate costs
calc = CostCalculator()
calc.add_usage(1000, 500, model="claude-sonnet")
print(f"Cost: ${calc.get_total_cost():.4f}")```
### Project Orchestrator CLI (`helix.cli.main`)

Autonomous project execution commands

```bash# Create new project with standard structure
helix new my-feature --type simple# Execute all phases autonomously
helix run projects/my-feature# Resume after failure
helix run projects/my-feature --resume# Show execution plan without running
helix run projects/my-feature --dry-run# Show current project status
helix status projects/my-feature# List all projects
helix list```
**Python API:**
```python
from helix.orchestrator import OrchestratorRunner, StatusTracker, PhaseExecutor
# Run project programmatically
runner = OrchestratorRunner(project_dir=Path("projects/my-feature"))
success = await runner.run()
if not success:
    print(f"Failed at: {runner.get_status().current_phase}")
# Check project status
tracker = StatusTracker(Path("projects/my-feature"))
tracker.load()
for phase_id, status in tracker.phases.items():
    print(f"{phase_id}: {status.state}")```
---