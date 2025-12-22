# ADR-System für HELIX v4 - Concept

> **Phase 1: Concept Development**
>
> Basierend auf ADR-086 (ADR-Template v2) aus HELIX v3.

---

## Übersicht

Das ADR-System ermöglicht HELIX v4:

1. **ADR-Dateien zu parsen** - YAML-Header und Markdown-Sections extrahieren
2. **ADRs zu validieren** - Struktur, Pflichtfelder, Acceptance Criteria prüfen
3. **Quality Gates zu integrieren** - Automatische Validierung in Workflows

```
┌─────────────────────────────────────────────────────────────────┐
│                      ADR-System Architektur                     │
│                                                                  │
│   ADR File (.md)                                                │
│        │                                                         │
│        ▼                                                         │
│   ┌─────────────┐                                               │
│   │  ADRParser  │──────► ADRDocument                            │
│   └─────────────┘           │                                    │
│                             ▼                                    │
│                    ┌───────────────┐                            │
│                    │ ADRValidator  │──────► ValidationResult    │
│                    └───────────────┘           │                 │
│                                                ▼                 │
│                                       ┌─────────────────┐       │
│                                       │ QualityGate     │       │
│                                       │ (adr_valid)     │       │
│                                       └─────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Referenz: ADR-086 Template v2

Das ADR-System basiert auf dem bewährten ADR-Template v2 aus HELIX v3:

### YAML-Header Struktur

```yaml
---
adr_id: "086"
title: ADR Title
status: Proposed  # Proposed | Accepted | Implemented | Superseded | Rejected

project_type: helix_internal  # helix_internal | external
component_type: TOOL          # TOOL | NODE | AGENT | PROCESS | SERVICE | SKILL | PROMPT | CONFIG | DOCS | MISC
classification: NEW           # NEW | UPDATE | FIX | REFACTOR | DEPRECATE
change_scope: major           # major | minor | config | docs | hotfix

files:
  create:
    - path/to/new/file.py
  modify:
    - path/to/existing/file.py
  docs:
    - docs/architecture/feature-x.md

depends_on:
  - ADR-0YY
  - ADR-0ZZ
---
```

### Pflicht-Sections (Markdown Body)

1. `## Status` - Aktueller Status mit Emoji
2. `## Kontext` - Warum diese Änderung?
3. `## Entscheidung` - Was wird entschieden?
4. `## Implementation` - Konkrete Umsetzungsschritte
5. `## Dokumentation` - Welche Doku muss aktualisiert werden?
6. `## Akzeptanzkriterien` - Checkbox-Liste für Definition of Done
7. `## Konsequenzen` - Tradeoffs, Risiken
8. `## Referenzen` - Links zu anderen ADRs, Dateien

---

## API Design

### 1. ADR Parser (`src/helix/adr/parser.py`)

#### Datenmodelle

```python
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

class ADRStatus(Enum):
    """Valid ADR status values."""
    PROPOSED = "Proposed"
    ACCEPTED = "Accepted"
    IMPLEMENTED = "Implemented"
    SUPERSEDED = "Superseded"
    REJECTED = "Rejected"

class ComponentType(Enum):
    """Valid component types per ADR-069."""
    TOOL = "TOOL"
    NODE = "NODE"
    AGENT = "AGENT"
    PROCESS = "PROCESS"
    SERVICE = "SERVICE"
    SKILL = "SKILL"
    PROMPT = "PROMPT"
    CONFIG = "CONFIG"
    DOCS = "DOCS"
    MISC = "MISC"

class Classification(Enum):
    """Change classification types."""
    NEW = "NEW"
    UPDATE = "UPDATE"
    FIX = "FIX"
    REFACTOR = "REFACTOR"
    DEPRECATE = "DEPRECATE"

class ChangeScope(Enum):
    """Change scope levels."""
    MAJOR = "major"
    MINOR = "minor"
    CONFIG = "config"
    DOCS = "docs"
    HOTFIX = "hotfix"

@dataclass
class ADRFiles:
    """Files affected by an ADR."""
    create: list[str] = field(default_factory=list)
    modify: list[str] = field(default_factory=list)
    docs: list[str] = field(default_factory=list)

@dataclass
class ADRMetadata:
    """YAML header metadata from ADR."""
    adr_id: str
    title: str
    status: ADRStatus
    project_type: str = "helix_internal"
    component_type: Optional[ComponentType] = None
    classification: Optional[Classification] = None
    change_scope: Optional[ChangeScope] = None
    files: ADRFiles = field(default_factory=ADRFiles)
    depends_on: list[str] = field(default_factory=list)

@dataclass
class AcceptanceCriterion:
    """Single acceptance criterion with checkbox state."""
    text: str
    checked: bool = False
    line_number: int = 0

@dataclass
class ADRSection:
    """A parsed markdown section."""
    name: str           # e.g., "Kontext", "Implementation"
    content: str        # Raw markdown content
    level: int = 2      # Heading level (##)
    line_start: int = 0 # Starting line number

@dataclass
class ADRDocument:
    """Complete parsed ADR document."""
    file_path: Path
    metadata: ADRMetadata
    sections: dict[str, ADRSection]  # section_name -> ADRSection
    acceptance_criteria: list[AcceptanceCriterion]
    raw_content: str
```

#### ADRParser Klasse

```python
class ADRParser:
    """Parse ADR documents in v2 format.

    Extracts YAML frontmatter and markdown sections from ADR files.
    Supports the ADR-086 template format from HELIX v3.

    Example:
        parser = ADRParser()
        adr = parser.parse_file(Path("adr/001-feature.md"))
        print(adr.metadata.title)
        print(adr.sections["Kontext"].content)
    """

    def parse_file(self, file_path: Path) -> ADRDocument:
        """Parse an ADR file from disk.

        Args:
            file_path: Path to the ADR markdown file.

        Returns:
            Parsed ADRDocument with metadata and sections.

        Raises:
            ADRParseError: If the file cannot be parsed.
            FileNotFoundError: If the file doesn't exist.
        """
        ...

    def parse_string(self, content: str, file_path: Path | None = None) -> ADRDocument:
        """Parse ADR content from a string.

        Args:
            content: Raw ADR content (YAML header + Markdown body).
            file_path: Optional path for error messages.

        Returns:
            Parsed ADRDocument.
        """
        ...

    def _extract_yaml_header(self, content: str) -> tuple[dict, str]:
        """Extract YAML frontmatter from content.

        Returns:
            Tuple of (yaml_dict, remaining_markdown)
        """
        ...

    def _parse_metadata(self, yaml_data: dict) -> ADRMetadata:
        """Convert YAML dict to ADRMetadata dataclass."""
        ...

    def _parse_sections(self, markdown: str) -> dict[str, ADRSection]:
        """Parse markdown into sections by heading."""
        ...

    def _extract_acceptance_criteria(
        self, section_content: str, line_offset: int
    ) -> list[AcceptanceCriterion]:
        """Extract acceptance criteria checkboxes from section."""
        ...


class ADRParseError(Exception):
    """Raised when ADR parsing fails."""

    def __init__(self, message: str, file_path: Path | None = None, line: int = 0):
        self.file_path = file_path
        self.line = line
        super().__init__(message)
```

---

### 2. ADR Validator (`src/helix/adr/validator.py`)

#### Datenmodelle

```python
from dataclasses import dataclass, field
from enum import Enum

class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    ERROR = "error"      # Must fix, blocks acceptance
    WARNING = "warning"  # Should fix, but not blocking
    INFO = "info"        # Suggestion

@dataclass
class ValidationIssue:
    """Single validation issue."""
    severity: ValidationSeverity
    code: str           # e.g., "missing_section", "invalid_status"
    message: str        # Human-readable message
    line: int = 0       # Line number if applicable
    section: str = ""   # Section name if applicable

@dataclass
class ValidationResult:
    """Result of ADR validation."""
    valid: bool                          # True if no errors
    issues: list[ValidationIssue] = field(default_factory=list)
    warnings_count: int = 0
    errors_count: int = 0

    def add_issue(self, issue: ValidationIssue) -> None:
        """Add an issue and update counts."""
        ...

    def has_errors(self) -> bool:
        """Check if there are any error-level issues."""
        return self.errors_count > 0
```

#### ADRValidator Klasse

```python
class ADRValidator:
    """Validate ADR documents against template requirements.

    Validates:
    - Required YAML header fields
    - Required markdown sections
    - Section order
    - Acceptance criteria format
    - Files list consistency

    Example:
        validator = ADRValidator()
        result = validator.validate(adr_document)
        if not result.valid:
            for issue in result.issues:
                print(f"{issue.severity}: {issue.message}")
    """

    # Required sections in order
    REQUIRED_SECTIONS = [
        "Status",
        "Kontext",
        "Entscheidung",
        "Implementation",
        "Dokumentation",
        "Akzeptanzkriterien",
        "Konsequenzen",
        "Referenzen",
    ]

    # Required YAML header fields
    REQUIRED_HEADER_FIELDS = [
        "adr_id",
        "title",
        "status",
    ]

    def validate(self, adr: ADRDocument) -> ValidationResult:
        """Run all validation checks on an ADR document.

        Args:
            adr: Parsed ADRDocument to validate.

        Returns:
            ValidationResult with all issues found.
        """
        ...

    def validate_header(self, metadata: ADRMetadata) -> list[ValidationIssue]:
        """Validate YAML header metadata."""
        ...

    def validate_sections(self, sections: dict[str, ADRSection]) -> list[ValidationIssue]:
        """Validate presence and order of required sections."""
        ...

    def validate_acceptance_criteria(
        self, criteria: list[AcceptanceCriterion]
    ) -> list[ValidationIssue]:
        """Validate acceptance criteria format."""
        ...

    def validate_files_consistency(
        self, metadata: ADRMetadata, sections: dict[str, ADRSection]
    ) -> list[ValidationIssue]:
        """Check if files.docs matches Dokumentation section."""
        ...

    def validate_section_content(
        self, section: ADRSection, section_name: str
    ) -> list[ValidationIssue]:
        """Validate content of specific sections (not empty, etc.)."""
        ...
```

---

### 3. Quality Gate Integration (`src/helix/quality_gates/adr_gate.py`)

```python
from pathlib import Path
from helix.quality_gates import GateResult
from helix.adr import ADRParser, ADRValidator

class ADRQualityGate:
    """Quality gate for ADR validation.

    Integrates ADR validation with the HELIX quality gate system.
    Can be used as a gate type in phases.yaml.

    Example phases.yaml:
        quality_gate:
          type: adr_valid
          file: adr/086-new-feature.md

    Example:
        gate = ADRQualityGate()
        result = gate.check(
            phase_dir=Path("/project/phases/01"),
            adr_file="adr/086-feature.md"
        )
    """

    def __init__(self, parser: ADRParser = None, validator: ADRValidator = None):
        self.parser = parser or ADRParser()
        self.validator = validator or ADRValidator()

    def check(self, phase_dir: Path, adr_file: str) -> GateResult:
        """Check if an ADR file is valid.

        Args:
            phase_dir: Base directory for resolving relative paths.
            adr_file: Path to ADR file (relative to phase_dir or absolute).

        Returns:
            GateResult with pass/fail status and validation details.
        """
        ...

    def check_multiple(self, phase_dir: Path, adr_files: list[str]) -> GateResult:
        """Validate multiple ADR files.

        Args:
            phase_dir: Base directory.
            adr_files: List of ADR file paths.

        Returns:
            GateResult that passes only if ALL ADRs are valid.
        """
        ...
```

#### Integration mit QualityGateRunner

In `quality_gates.py` muss der neue Gate-Typ registriert werden:

```python
# In QualityGateRunner.run_gate()
async def run_gate(self, phase_dir: Path, gate_config: dict) -> GateResult:
    gate_type = gate_config.get("type")

    # ... existing gates ...

    elif gate_type == "adr_valid":
        from helix.quality_gates.adr_gate import ADRQualityGate
        adr_gate = ADRQualityGate()
        adr_file = gate_config.get("file")
        if adr_file:
            return adr_gate.check(phase_dir, adr_file)
        else:
            adr_files = gate_config.get("files", [])
            return adr_gate.check_multiple(phase_dir, adr_files)
```

---

## Implementierungsplan

### Phase 2: ADR Parser

**Dateien:**
- `new/src/helix/adr/__init__.py` - Package exports
- `new/src/helix/adr/parser.py` - ADRParser implementation
- `new/tests/adr/test_parser.py` - Unit tests

**Testziele:**
- Parse valid ADR file
- Parse ADR without optional fields
- Error handling for malformed YAML
- Error handling for missing frontmatter
- Extract all sections correctly
- Extract acceptance criteria checkboxes

### Phase 3: ADR Validator

**Dateien:**
- `new/src/helix/adr/validator.py` - ADRValidator implementation
- `new/tests/adr/test_validator.py` - Unit tests

**Testziele:**
- Validate missing required sections
- Validate section order
- Validate missing header fields
- Validate acceptance criteria format
- Validate files.docs consistency

### Phase 4: Quality Gate Integration

**Dateien:**
- `new/src/helix/quality_gates/adr_gate.py` - ADRQualityGate
- `new/tests/quality_gates/test_adr_gate.py` - Unit tests
- `modified/src/helix/quality_gates.py` - Register new gate type

**Testziele:**
- Gate returns passed for valid ADR
- Gate returns failed with details for invalid ADR
- Gate handles missing file gracefully
- Integration with QualityGateRunner

---

## Dokumentation

Per Self-Documentation Prinzip müssen folgende Dokumentationen aktualisiert werden:

### Zu aktualisierende Dateien

| Ebene | Datei | Änderung |
|-------|-------|----------|
| **Top-Level** | `CLAUDE.md` | Neue Regel: `adr_valid` Quality Gate dokumentieren |
| **Top-Level** | `ONBOARDING.md` | ADR-Workflow Section hinzufügen |
| **Architecture** | `docs/ARCHITECTURE-MODULES.md` | `helix.adr` Package beschreiben |
| **Architecture** | `docs/ADR-TEMPLATE.md` | NEU: ADR Template für HELIX v4 |
| **Skills** | `skills/helix/adr/SKILL.md` | NEU: Wie schreibt man ADRs in HELIX |
| **Docstrings** | Im Code | Alle public Classes und Functions |

### Details pro Datei

#### CLAUDE.md

Neuen Abschnitt zu Quality Gates:

```markdown
## Quality Gates

### adr_valid Gate

Prüft ob ADR-Dateien dem Template v2 Format entsprechen.

```yaml
quality_gate:
  type: adr_valid
  file: adr/001-feature.md
```
```

#### ONBOARDING.md

Neuen Abschnitt zum ADR Workflow:

```markdown
## ADR Workflow

1. ADR erstellen mit Template aus `docs/ADR-TEMPLATE.md`
2. ADR validieren mit `adr_valid` Quality Gate
3. ADR implementieren in Phasen
```

#### docs/ARCHITECTURE-MODULES.md

```markdown
## src/helix/adr/ - ADR System

**Purpose:** Parse and validate Architecture Decision Records.

### Modules

| Module | Description |
|--------|-------------|
| `parser.py` | ADRParser - Parse ADR YAML header and markdown sections |
| `validator.py` | ADRValidator - Validate ADRs against template requirements |

### Key Classes

```python
from helix.adr import (
    ADRParser,
    ADRValidator,
    ADRDocument,
    ADRMetadata,
    ValidationResult,
)
```
```

#### docs/ADR-TEMPLATE.md (NEU)

Vollständiges ADR Template basierend auf ADR-086.

#### skills/helix/adr/SKILL.md (NEU)

```markdown
# ADR Skill

## Kontext
Dieses Skill erklärt wie ADRs in HELIX v4 geschrieben werden.

## Template
Nutze das Template aus `docs/ADR-TEMPLATE.md`.

## Pflicht-Sections
- Kontext, Entscheidung, Implementation
- Dokumentation, Akzeptanzkriterien
- Konsequenzen, Referenzen

## Validierung
ADRs werden automatisch validiert durch das `adr_valid` Quality Gate.
```

---

## Akzeptanzkriterien

### Parser (Phase 2)

- [ ] ADRParser kann YAML-Header extrahieren
- [ ] ADRParser kann alle Markdown-Sections parsen
- [ ] ADRParser extrahiert Acceptance Criteria Checkboxes
- [ ] Fehlerbehandlung für ungültige Dateien
- [ ] Unit Tests erreichen >90% Coverage

### Validator (Phase 3)

- [ ] Validator prüft alle Pflicht-Sections
- [ ] Validator prüft Section-Reihenfolge
- [ ] Validator prüft YAML-Header Pflichtfelder
- [ ] Validator gibt klare Fehlermeldungen
- [ ] Unit Tests für alle Validierungsregeln

### Quality Gate (Phase 4)

- [ ] `adr_valid` Gate ist in QualityGateRunner registriert
- [ ] Gate gibt GateResult mit Details zurück
- [ ] Gate kann einzelne und mehrere ADRs prüfen
- [ ] Integration mit phases.yaml funktioniert

### Dokumentation (Phase 5)

- [ ] `docs/ARCHITECTURE-MODULES.md` beschreibt helix.adr
- [ ] `docs/ADR-TEMPLATE.md` existiert
- [ ] `skills/helix/adr/SKILL.md` existiert
- [ ] `CLAUDE.md` dokumentiert adr_valid Gate
- [ ] `ONBOARDING.md` hat ADR-Workflow Section

---

## Konsequenzen

**Vorteile:**

- **Automatische Validierung**: ADRs können automatisch auf Vollständigkeit geprüft werden
- **Konsistenz**: Alle ADRs folgen dem gleichen Format
- **Quality Gates**: ADR-Validierung kann in Workflows integriert werden
- **Structured Data**: Parser liefert strukturierte Daten für weitere Verarbeitung

**Nachteile:**

- **Zusätzliche Abhängigkeit**: Neues Package in helix
- **Migration**: Bestehende ADRs müssen ggf. angepasst werden

**Risiken:**

- **Zu strenge Validierung** könnte Autoren frustrieren → Lösung: Warnings statt Errors für optionale Felder

---

## Referenzen

- ADR-086: ADR-Template v2 (HELIX v3) - `/home/aiuser01/helix-v3/adr/086-adr-template-v2.md`
- ADR-069: Structured Change Classification (HELIX v3)
- docs/SELF-DOCUMENTATION.md - Self-Documentation Prinzip
- src/helix/quality_gates.py - Existing Quality Gate System
