


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

### Skills nach Bedarf:


- `skills/helix/SKILL.md` - Orchestration & evolution

- `skills/pdm/SKILL.md` - Product data management

- `skills/encoder/SKILL.md` - Encoder products

- `skills/infrastructure/SKILL.md` - System infrastructure

- `skills/api/SKILL.md` - API development



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

-> Schau in `phases.yaml` welche Output-Dateien erwartet werden.

---

## Quality Gates Reference

HELIX verwendet Quality Gates um die Qualität deiner Arbeit zu validieren.

### Verfügbare Gate-Typen

| Gate Type | Beschreibung | Verwendung |
|-----------|--------------|------------|


| `files_exist` | Checks if output files exist | development, documentation |

| `syntax_check` | Validates code syntax | development |

| `tests_pass` | Runs tests and checks for success | testing |

| `review_approved` | LLM reviews output for quality | review |

| `adr_valid` | Validates ADR document structure | consultant, review |














### Gate: `adr_valid`

Validiert Architecture Decision Records gegen das ADR-086 Template:

```yaml
# phases.yaml
quality_gate:
  type: adr_valid
  file: output/feature-adr.md
```

**Was wird geprüft:**

1. **YAML Header** (Pflichtfelder)

   - `adr_id`

   - `title`

   - `status`


2. **Markdown Sections** (alle müssen vorhanden sein)

   - `## Kontext`

   - `## Entscheidung`

   - `## Implementation`

   - `## Dokumentation`

   - `## Akzeptanzkriterien`

   - `## Konsequenzen`


3. **Akzeptanzkriterien**
   - Mindestens ein `- [ ]` oder `- [x]` Checkbox vorhanden

-> Siehe: [docs/ADR-TEMPLATE.md](docs/ADR-TEMPLATE.md) für das vollständige Template.




---

## Phase Types

HELIX unterstützt verschiedene Phase-Typen:

| Type | Rolle | Outputs |
|------|-------|---------|


| `consultant` | Consultant | adr, spec, phases |

| `development` | Developer | code, tests |

| `testing` | Developer | test_results, coverage |

| `review` | Reviewer | review_report, approval |

| `documentation` | Documentation | docs, diagrams |

| `integration` | Developer | merged_code, backup |



-> Details: [skills/helix/SKILL.md](skills/helix/SKILL.md)

---

## Projekt-Struktur

```
helix-v4/
├── CLAUDE.md              <- Diese Datei
├── ONBOARDING.md          <- Konzept-Erklärung
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
```

---

## Consultant-Rolle

Wenn du als **Consultant** arbeitest:

### Deine Aufgabe
1. Lies den User-Request in `input/request.md`
2. Lies relevante Skills (`skills/pdm/`, etc.)
3. Stelle klärende Fragen (Was? Warum? Constraints?)
4. Generiere `output/spec.yaml` und `output/phases.yaml`

-> Details: [skills/helix/SKILL.md](skills/helix/SKILL.md)

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
- Lies CLAUDE.md in deinem Verzeichnis
- Lies relevante Skills
- Schreibe nach output/
- Erstelle vollständige, lauffähige Dateien
- Dokumentiere was du getan hast

### DON'T:
- Ändere keine Dateien außerhalb deines Verzeichnisses
- Lösche keine existierenden Dateien
- Installiere keine System-Pakete
- Mache keine Netzwerk-Requests ohne Grund

---

## Escalation


Bei Fehlern eskaliert HELIX automatisch:

| Level | Name | Aktion |
|-------|------|--------|

| 1 | Phase Retry | retry_phase |

| 2 | Domain Expert | escalate_to_domain |

| 3 | Architecture Review | architecture_review |

| 4 | Human Intervention | pause_for_human |



-> Details: [skills/helix/SKILL.md](skills/helix/SKILL.md)

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
└── modified/        # Modified files
```

### Status Flow

```
PENDING -> DEVELOPING -> READY -> DEPLOYED -> VALIDATED -> INTEGRATED
                               |           |
                            FAILED <- <- ROLLBACK
```

---

## Self-Documentation Prinzip

> **Jede Änderung dokumentiert sich selbst.**

Wenn du ein neues Feature implementierst, müssen aktualisiert werden:
- Top-Level (README, ONBOARDING, CLAUDE.md)
- Architecture Docs (docs/*.md)
- Skills (skills/*/SKILL.md)
- Docstrings (im Code)

-> Lies: [docs/SELF-DOCUMENTATION.md](docs/SELF-DOCUMENTATION.md)

---

## Available Tools

### ADR Tool (`helix.tools.adr_tool`)

```bash
python -m helix.tools.adr_tool validate path/to/ADR.md
python -m helix.tools.adr_tool finalize path/to/ADR.md
python -m helix.tools.adr_tool next-number
```

### Docs Compiler (`helix.tools.docs_compiler`)

```bash
python -m helix.tools.docs_compiler compile    # Generate docs
python -m helix.tools.docs_compiler validate   # Check without writing
python -m helix.tools.docs_compiler sources    # List sources
python -m helix.tools.docs_compiler diff       # Show changes
```

### Verify Phase Tool

```bash
python -m helix.tools.verify_phase
```

---

## Hilfe

- **HELIX Konzept**: [ONBOARDING.md](ONBOARDING.md)
- **Architektur**: [docs/ARCHITECTURE-MODULES.md](docs/ARCHITECTURE-MODULES.md)
- **ADR Template**: [docs/ADR-TEMPLATE.md](docs/ADR-TEMPLATE.md)
- **Skills**: `skills/` für Domain-Wissen

---