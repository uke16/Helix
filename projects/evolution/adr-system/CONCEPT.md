# ADR-System Konzept für HELIX v4

## Motivation

### Warum braucht HELIX v4 ein ADR-System?

HELIX v4 orchestriert Claude Code Instanzen für strukturierte Softwareentwicklung. Die Qualität der Ergebnisse hängt direkt davon ab, wie gut die Architektur-Entscheidungen dokumentiert und validiert werden können.

**Aktuelle Situation ohne ADR-System:**

1. **Fehlende Traceability** - Architektur-Entscheidungen sind nur in Prosa dokumentiert
2. **Keine automatische Validierung** - Entwickler-Outputs werden nicht gegen ADR-Standards geprüft
3. **Wissenstransfer-Verlust** - Consultant-Wissen geht zwischen Phasen verloren

**HELIX v3 Referenz:**

Das bewährte ADR-086 Template aus HELIX v3 definiert:
- Strukturierten YAML-Header mit Metadaten
- Pflicht-Sections: Kontext, Entscheidung, Implementation, Dokumentation, Akzeptanzkriterien
- Klare Klassifikation (component_type, classification, change_scope)

**Ziele für v4:**

1. **Automatische ADR-Validierung** - Quality Gate prüft ADR-Konformität
2. **Metadata-Extraktion** - Parser extrahiert strukturierte Informationen für Orchestrierung
3. **Integration mit Evolution-System** - ADRs dokumentieren Self-Evolution Changes

---

## Komponenten

Das ADR-System besteht aus drei Hauptkomponenten:

```
┌─────────────────────────────────────────────────────────────────┐
│                      ADR System                                  │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   ADR Parser    │  ADR Validator  │  Quality Gate Integration   │
│                 │                 │                             │
│ • YAML Header   │ • Required      │ • Phase Validation          │
│ • Markdown Body │   Sections      │ • Evolution Checks          │
│ • Metadata      │ • Header Fields │ • Acceptance Criteria       │
└─────────────────┴─────────────────┴─────────────────────────────┘
```

### 1. ADR Parser (`src/helix/adr/parser.py`)

**Verantwortung:** Parse ADR-Dateien und extrahiere strukturierte Metadaten.

**Funktionalität:**
- YAML Frontmatter parsen (zwischen `---` Markern)
- Markdown-Sections extrahieren (## Überschriften)
- Akzeptanzkriterien-Checkboxen parsen (`- [ ]` und `- [x]`)
- File-Listen aus Header auslesen

**Datenstruktur:**

```python
# src/helix/adr/parser.py

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import yaml
import re


@dataclass
class ADRSection:
    """Eine Markdown-Section innerhalb eines ADR."""
    name: str           # z.B. "Kontext", "Entscheidung"
    content: str        # Markdown-Inhalt
    level: int = 2      # Überschriften-Level (## = 2)


@dataclass
class AcceptanceCriterion:
    """Ein einzelnes Akzeptanzkriterium."""
    text: str           # Kriterium-Text
    checked: bool       # [ ] = False, [x] = True


@dataclass
class ADRFiles:
    """Dateilisten aus dem YAML-Header."""
    create: list[str] = field(default_factory=list)
    modify: list[str] = field(default_factory=list)
    docs: list[str] = field(default_factory=list)


@dataclass
class ADRMetadata:
    """Extrahierte ADR-Metadaten."""
    adr_id: str
    title: str
    status: str

    # Klassifikation (optional, aber empfohlen)
    project_type: Optional[str] = None
    component_type: Optional[str] = None
    classification: Optional[str] = None
    change_scope: Optional[str] = None

    # Abhängigkeiten
    depends_on: list[str] = field(default_factory=list)
    files: ADRFiles = field(default_factory=ADRFiles)

    # Raw YAML für zusätzliche Felder
    raw_header: dict = field(default_factory=dict)


@dataclass
class ParsedADR:
    """Vollständig geparstes ADR-Dokument."""
    path: Path
    metadata: ADRMetadata
    sections: list[ADRSection]
    acceptance_criteria: list[AcceptanceCriterion]

    def get_section(self, name: str) -> Optional[ADRSection]:
        """Hole Section nach Name (case-insensitive)."""
        name_lower = name.lower()
        for section in self.sections:
            if section.name.lower() == name_lower:
                return section
        return None

    @property
    def has_required_sections(self) -> bool:
        """Prüfe ob alle Pflicht-Sections vorhanden sind."""
        required = ["kontext", "entscheidung", "implementation",
                    "dokumentation", "akzeptanzkriterien", "konsequenzen"]
        section_names = {s.name.lower() for s in self.sections}
        return all(r in section_names for r in required)


class ADRParser:
    """Parser für ADR-Dokumente im v2 Format."""

    YAML_PATTERN = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)
    SECTION_PATTERN = re.compile(r'^(#{2,6})\s+(.+)$', re.MULTILINE)
    CHECKBOX_PATTERN = re.compile(r'^-\s*\[([ xX])\]\s*(.+)$', re.MULTILINE)

    def parse_file(self, path: Path) -> ParsedADR:
        """Parse eine ADR-Datei.

        Args:
            path: Pfad zur ADR-Datei

        Returns:
            ParsedADR mit Metadaten und Sections

        Raises:
            ADRParseError: Bei Parse-Fehlern
        """
        content = path.read_text(encoding="utf-8")
        return self.parse_content(content, path)

    def parse_content(self, content: str, path: Path = None) -> ParsedADR:
        """Parse ADR-Content direkt.

        Args:
            content: ADR-Markdown-Inhalt
            path: Optionaler Pfad für Fehlermeldungen

        Returns:
            ParsedADR mit Metadaten und Sections
        """
        # 1. YAML Header extrahieren
        yaml_match = self.YAML_PATTERN.match(content)
        if not yaml_match:
            raise ADRParseError("No YAML frontmatter found", path)

        yaml_content = yaml_match.group(1)
        body = content[yaml_match.end():]

        try:
            header = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise ADRParseError(f"Invalid YAML: {e}", path)

        # 2. Metadaten extrahieren
        metadata = self._extract_metadata(header, path)

        # 3. Sections parsen
        sections = self._parse_sections(body)

        # 4. Akzeptanzkriterien extrahieren
        acceptance_criteria = self._parse_acceptance_criteria(body)

        return ParsedADR(
            path=path or Path("unknown"),
            metadata=metadata,
            sections=sections,
            acceptance_criteria=acceptance_criteria,
        )

    def _extract_metadata(self, header: dict, path: Path = None) -> ADRMetadata:
        """Extrahiere Metadaten aus YAML-Header."""
        # Pflichtfelder
        adr_id = str(header.get("adr_id", header.get("adr_number", "")))
        title = header.get("title", "")
        status = header.get("status", "Unknown")

        if not adr_id:
            raise ADRParseError("Missing adr_id in YAML header", path)

        # Optionale Klassifikation
        project_type = header.get("project_type")
        component_type = header.get("component_type")
        classification = header.get("classification")
        change_scope = header.get("change_scope")

        # Abhängigkeiten
        depends_on = header.get("depends_on", [])
        if isinstance(depends_on, str):
            depends_on = [depends_on]

        # Dateilisten
        files_data = header.get("files", {})
        files = ADRFiles(
            create=files_data.get("create", []) or [],
            modify=files_data.get("modify", []) or [],
            docs=files_data.get("docs", []) or [],
        )

        return ADRMetadata(
            adr_id=adr_id,
            title=title,
            status=status,
            project_type=project_type,
            component_type=component_type,
            classification=classification,
            change_scope=change_scope,
            depends_on=depends_on,
            files=files,
            raw_header=header,
        )

    def _parse_sections(self, body: str) -> list[ADRSection]:
        """Parse Markdown-Sections aus Body."""
        sections = []
        matches = list(self.SECTION_PATTERN.finditer(body))

        for i, match in enumerate(matches):
            level = len(match.group(1))
            name = match.group(2).strip()

            # Content bis zur nächsten Section
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
            content = body[start:end].strip()

            sections.append(ADRSection(
                name=name,
                content=content,
                level=level,
            ))

        return sections

    def _parse_acceptance_criteria(self, body: str) -> list[AcceptanceCriterion]:
        """Parse Akzeptanzkriterien-Checkboxen."""
        criteria = []

        for match in self.CHECKBOX_PATTERN.finditer(body):
            checked = match.group(1).lower() == "x"
            text = match.group(2).strip()
            criteria.append(AcceptanceCriterion(text=text, checked=checked))

        return criteria


class ADRParseError(Exception):
    """Fehler beim Parsen eines ADR."""

    def __init__(self, message: str, path: Path = None):
        self.path = path
        super().__init__(f"{path}: {message}" if path else message)
```

### 2. ADR Validator (`src/helix/adr/validator.py`)

**Verantwortung:** Validiere ADRs gegen Template-Anforderungen.

**Validierungs-Regeln:**
- Alle Pflicht-Sections vorhanden
- YAML-Header enthält Pflichtfelder
- Akzeptanzkriterien sind definiert
- Dateireferenzen sind konsistent

```python
# src/helix/adr/validator.py

from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

from .parser import ParsedADR, ADRParser, ADRParseError


@dataclass
class ValidationIssue:
    """Ein Validierungs-Problem."""
    level: str          # "error" | "warning"
    category: str       # z.B. "missing_section", "missing_field"
    message: str
    location: Optional[str] = None  # z.B. Section-Name


@dataclass
class ValidationResult:
    """Ergebnis der ADR-Validierung."""
    valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    adr: Optional[ParsedADR] = None

    @property
    def errors(self) -> list[ValidationIssue]:
        """Nur Fehler zurückgeben."""
        return [i for i in self.issues if i.level == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        """Nur Warnungen zurückgeben."""
        return [i for i in self.issues if i.level == "warning"]


class ADRValidator:
    """Validator für ADR-Dokumente nach v2 Template."""

    REQUIRED_SECTIONS = [
        "Kontext",
        "Entscheidung",
        "Implementation",
        "Dokumentation",
        "Akzeptanzkriterien",
        "Konsequenzen",
    ]

    OPTIONAL_SECTIONS = [
        "Status",
        "Referenzen",
    ]

    REQUIRED_HEADER_FIELDS = [
        "adr_id",
        "title",
        "status",
    ]

    RECOMMENDED_HEADER_FIELDS = [
        "component_type",
        "classification",
        "change_scope",
    ]

    def __init__(self, parser: ADRParser = None):
        self.parser = parser or ADRParser()

    def validate_file(self, path: Path) -> ValidationResult:
        """Validiere ADR-Datei.

        Args:
            path: Pfad zur ADR-Datei

        Returns:
            ValidationResult mit allen Issues
        """
        issues = []

        # 1. Parsing versuchen
        try:
            adr = self.parser.parse_file(path)
        except ADRParseError as e:
            return ValidationResult(
                valid=False,
                issues=[ValidationIssue(
                    level="error",
                    category="parse_error",
                    message=str(e),
                )],
            )

        # 2. Header validieren
        issues.extend(self._validate_header(adr))

        # 3. Sections validieren
        issues.extend(self._validate_sections(adr))

        # 4. Akzeptanzkriterien validieren
        issues.extend(self._validate_acceptance_criteria(adr))

        # 5. Konsistenz-Checks
        issues.extend(self._validate_consistency(adr))

        has_errors = any(i.level == "error" for i in issues)

        return ValidationResult(
            valid=not has_errors,
            issues=issues,
            adr=adr,
        )

    def validate_content(self, content: str) -> ValidationResult:
        """Validiere ADR-Content direkt."""
        issues = []

        try:
            adr = self.parser.parse_content(content)
        except ADRParseError as e:
            return ValidationResult(
                valid=False,
                issues=[ValidationIssue(
                    level="error",
                    category="parse_error",
                    message=str(e),
                )],
            )

        issues.extend(self._validate_header(adr))
        issues.extend(self._validate_sections(adr))
        issues.extend(self._validate_acceptance_criteria(adr))
        issues.extend(self._validate_consistency(adr))

        has_errors = any(i.level == "error" for i in issues)

        return ValidationResult(
            valid=not has_errors,
            issues=issues,
            adr=adr,
        )

    def _validate_header(self, adr: ParsedADR) -> list[ValidationIssue]:
        """Validiere YAML-Header."""
        issues = []

        # Pflichtfelder prüfen
        for field_name in self.REQUIRED_HEADER_FIELDS:
            if field_name not in adr.metadata.raw_header:
                issues.append(ValidationIssue(
                    level="error",
                    category="missing_field",
                    message=f"Required header field missing: {field_name}",
                    location="YAML header",
                ))

        # Empfohlene Felder prüfen
        for field_name in self.RECOMMENDED_HEADER_FIELDS:
            if field_name not in adr.metadata.raw_header:
                issues.append(ValidationIssue(
                    level="warning",
                    category="missing_recommended_field",
                    message=f"Recommended header field missing: {field_name}",
                    location="YAML header",
                ))

        # Status-Wert validieren
        valid_statuses = ["Proposed", "Accepted", "Implemented",
                         "Superseded", "Rejected", "Deprecated"]
        if adr.metadata.status not in valid_statuses:
            issues.append(ValidationIssue(
                level="warning",
                category="invalid_status",
                message=f"Non-standard status: {adr.metadata.status}",
                location="YAML header",
            ))

        return issues

    def _validate_sections(self, adr: ParsedADR) -> list[ValidationIssue]:
        """Validiere Pflicht-Sections."""
        issues = []
        section_names = {s.name for s in adr.sections}

        for required in self.REQUIRED_SECTIONS:
            # Case-insensitive match
            found = any(
                s.lower() == required.lower()
                for s in section_names
            )
            if not found:
                issues.append(ValidationIssue(
                    level="error",
                    category="missing_section",
                    message=f"Required section missing: ## {required}",
                ))

        # Prüfe ob Sections Inhalt haben
        for section in adr.sections:
            if section.name in self.REQUIRED_SECTIONS:
                if len(section.content.strip()) < 10:
                    issues.append(ValidationIssue(
                        level="warning",
                        category="empty_section",
                        message=f"Section has minimal content: ## {section.name}",
                        location=section.name,
                    ))

        return issues

    def _validate_acceptance_criteria(
        self, adr: ParsedADR
    ) -> list[ValidationIssue]:
        """Validiere Akzeptanzkriterien."""
        issues = []

        if not adr.acceptance_criteria:
            issues.append(ValidationIssue(
                level="error",
                category="missing_criteria",
                message="No acceptance criteria defined (no checkboxes found)",
                location="Akzeptanzkriterien",
            ))
        elif len(adr.acceptance_criteria) < 3:
            issues.append(ValidationIssue(
                level="warning",
                category="few_criteria",
                message=f"Only {len(adr.acceptance_criteria)} acceptance criteria (recommend at least 3)",
                location="Akzeptanzkriterien",
            ))

        return issues

    def _validate_consistency(self, adr: ParsedADR) -> list[ValidationIssue]:
        """Konsistenz-Checks zwischen Header und Body."""
        issues = []

        # Check: files.docs sollte mit Dokumentation-Section übereinstimmen
        docs_section = adr.get_section("Dokumentation")
        if docs_section and adr.metadata.files.docs:
            for doc_file in adr.metadata.files.docs:
                if doc_file not in docs_section.content:
                    issues.append(ValidationIssue(
                        level="warning",
                        category="inconsistent_docs",
                        message=f"File in header but not in Dokumentation section: {doc_file}",
                        location="Dokumentation",
                    ))

        return issues
```

### 3. Quality Gate Integration (`src/helix/quality_gates/adr_gate.py`)

**Verantwortung:** Integration mit dem bestehenden QualityGateRunner.

```python
# src/helix/quality_gates/adr_gate.py

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from helix.quality_gates import GateResult, QualityGateRunner
from helix.adr.parser import ADRParser
from helix.adr.validator import ADRValidator, ValidationResult


@dataclass
class ADRGateConfig:
    """Konfiguration für ADR Quality Gate."""
    pattern: str = "*.md"           # Glob-Pattern für ADR-Dateien
    require_all_criteria: bool = False  # Alle Akzeptanzkriterien müssen erfüllt sein
    strict: bool = False            # Warnungen als Fehler behandeln


class ADRQualityGate:
    """Quality Gate für ADR-Validierung.

    Integriert sich mit dem bestehenden QualityGateRunner.

    Example:
        runner = QualityGateRunner()
        adr_gate = ADRQualityGate()

        result = adr_gate.check_adr_valid(
            Path("/project/adr/001-feature.md")
        )

        # Oder über run_gate:
        result = await runner.run_gate(
            phase_dir,
            {
                "type": "adr_valid",
                "file": "output/feature-adr.md",
                "strict": True,
            }
        )
    """

    def __init__(self):
        self.parser = ADRParser()
        self.validator = ADRValidator(self.parser)

    def check_adr_valid(
        self,
        adr_path: Path,
        config: ADRGateConfig = None
    ) -> GateResult:
        """Prüfe ob ein ADR valide ist.

        Args:
            adr_path: Pfad zur ADR-Datei
            config: Optionale Konfiguration

        Returns:
            GateResult mit Validierungs-Details
        """
        config = config or ADRGateConfig()

        if not adr_path.exists():
            return GateResult(
                passed=False,
                gate_type="adr_valid",
                message=f"ADR file not found: {adr_path}",
                details={"path": str(adr_path)},
            )

        result = self.validator.validate_file(adr_path)

        # Bei strict-Modus sind Warnungen auch Fehler
        has_issues = len(result.errors) > 0
        if config.strict:
            has_issues = has_issues or len(result.warnings) > 0

        if has_issues:
            return GateResult(
                passed=False,
                gate_type="adr_valid",
                message=f"ADR validation failed: {len(result.errors)} error(s), {len(result.warnings)} warning(s)",
                details={
                    "errors": [
                        {"category": i.category, "message": i.message, "location": i.location}
                        for i in result.errors
                    ],
                    "warnings": [
                        {"category": i.category, "message": i.message, "location": i.location}
                        for i in result.warnings
                    ],
                    "adr_id": result.adr.metadata.adr_id if result.adr else None,
                },
            )

        # Akzeptanzkriterien prüfen (optional)
        if config.require_all_criteria and result.adr:
            unchecked = [c for c in result.adr.acceptance_criteria if not c.checked]
            if unchecked:
                return GateResult(
                    passed=False,
                    gate_type="adr_valid",
                    message=f"ADR has {len(unchecked)} unchecked acceptance criteria",
                    details={
                        "unchecked_criteria": [c.text for c in unchecked],
                        "total_criteria": len(result.adr.acceptance_criteria),
                    },
                )

        return GateResult(
            passed=True,
            gate_type="adr_valid",
            message=f"ADR '{result.adr.metadata.adr_id}' is valid",
            details={
                "adr_id": result.adr.metadata.adr_id,
                "title": result.adr.metadata.title,
                "status": result.adr.metadata.status,
                "sections_found": len(result.adr.sections),
                "acceptance_criteria": len(result.adr.acceptance_criteria),
                "warnings": len(result.warnings),
            },
        )

    def check_adrs_in_directory(
        self,
        directory: Path,
        pattern: str = "*.md",
    ) -> GateResult:
        """Prüfe alle ADRs in einem Verzeichnis.

        Args:
            directory: Verzeichnis mit ADR-Dateien
            pattern: Glob-Pattern für ADR-Dateien

        Returns:
            GateResult mit Gesamt-Ergebnis
        """
        adr_files = list(directory.glob(pattern))

        if not adr_files:
            return GateResult(
                passed=True,
                gate_type="adr_valid",
                message=f"No ADR files found matching {pattern}",
                details={"directory": str(directory), "pattern": pattern},
            )

        results = {}
        all_valid = True
        total_errors = 0
        total_warnings = 0

        for adr_file in adr_files:
            result = self.validator.validate_file(adr_file)
            results[str(adr_file.name)] = {
                "valid": result.valid,
                "errors": len(result.errors),
                "warnings": len(result.warnings),
            }
            if not result.valid:
                all_valid = False
            total_errors += len(result.errors)
            total_warnings += len(result.warnings)

        return GateResult(
            passed=all_valid,
            gate_type="adr_valid",
            message=f"Validated {len(adr_files)} ADR(s): {total_errors} error(s), {total_warnings} warning(s)",
            details={
                "files_checked": len(adr_files),
                "results": results,
                "total_errors": total_errors,
                "total_warnings": total_warnings,
            },
        )


# Integration mit QualityGateRunner
def register_adr_gate(runner: QualityGateRunner) -> None:
    """Registriere ADR Gate beim QualityGateRunner.

    Erweitert run_gate() um den Type "adr_valid".

    Example:
        runner = QualityGateRunner()
        register_adr_gate(runner)

        result = await runner.run_gate(
            phase_dir,
            {"type": "adr_valid", "file": "output/adr.md"}
        )
    """
    adr_gate = ADRQualityGate()
    original_run_gate = runner.run_gate

    async def extended_run_gate(
        phase_dir: Path,
        gate_config: dict[str, Any]
    ) -> GateResult:
        gate_type = gate_config.get("type")

        if gate_type == "adr_valid":
            file_path = gate_config.get("file")
            if file_path:
                adr_path = phase_dir / file_path
            else:
                # Alle ADRs im Verzeichnis prüfen
                pattern = gate_config.get("pattern", "*.md")
                return adr_gate.check_adrs_in_directory(phase_dir, pattern)

            config = ADRGateConfig(
                require_all_criteria=gate_config.get("require_all_criteria", False),
                strict=gate_config.get("strict", False),
            )
            return adr_gate.check_adr_valid(adr_path, config)

        return await original_run_gate(phase_dir, gate_config)

    runner.run_gate = extended_run_gate
```

---

## API Design

### Einfache Verwendung

```python
from helix.adr import ADRParser, ADRValidator
from pathlib import Path

# Parser verwenden
parser = ADRParser()
adr = parser.parse_file(Path("adr/086-template.md"))

print(f"ADR-{adr.metadata.adr_id}: {adr.metadata.title}")
print(f"Status: {adr.metadata.status}")
print(f"Component: {adr.metadata.component_type}")
print(f"Sections: {[s.name for s in adr.sections]}")

# Validator verwenden
validator = ADRValidator()
result = validator.validate_file(Path("adr/086-template.md"))

if not result.valid:
    for error in result.errors:
        print(f"ERROR: {error.message}")
    for warning in result.warnings:
        print(f"WARNING: {warning.message}")
```

### Quality Gate in Phases

```yaml
# phases.yaml
phases:
  - id: "3"
    name: ADR Review
    type: review

    quality_gate:
      type: adr_valid
      file: output/feature-adr.md
      strict: true
      require_all_criteria: false
```

### Programmatische Quality Gate Verwendung

```python
from helix.quality_gates import QualityGateRunner
from helix.quality_gates.adr_gate import register_adr_gate

runner = QualityGateRunner()
register_adr_gate(runner)

result = await runner.run_gate(
    phase_dir=Path("/project/phases/01"),
    gate_config={
        "type": "adr_valid",
        "file": "output/my-adr.md",
        "strict": True,
    }
)

if not result.passed:
    print(f"Gate failed: {result.message}")
    for error in result.details.get("errors", []):
        print(f"  - {error['message']}")
```

---

## Integration mit bestehendem System

### 1. Quality Gates Erweiterung

Das ADR-System erweitert den bestehenden `QualityGateRunner` in `src/helix/quality_gates.py`:

```
┌───────────────────────────────────────────────────────────────┐
│                    QualityGateRunner                          │
├───────────────────────────────────────────────────────────────┤
│ Existing Gates:                                               │
│ • files_exist    - Dateien existieren                        │
│ • syntax_check   - Python/TS/Go Syntax                       │
│ • tests_pass     - Tests laufen                              │
│ • review_approved - Review vorhanden                         │
├───────────────────────────────────────────────────────────────┤
│ NEW: ADR Gate (via register_adr_gate)                        │
│ • adr_valid      - ADR Template-Konformität                  │
└───────────────────────────────────────────────────────────────┘
```

### 2. Evolution System Integration

ADRs können Evolution-Projekte dokumentieren:

```yaml
# projects/evolution/new-feature/adr.md
---
adr_id: "EVO-001"
title: New Feature for Self-Evolution
status: Proposed
component_type: SERVICE
classification: NEW

files:
  create:
    - src/helix/new_feature.py
  modify:
    - src/helix/__init__.py
---

## Kontext
...
```

### 3. Verzeichnisstruktur

```
src/helix/
├── adr/
│   ├── __init__.py        # Export: ADRParser, ADRValidator, ParsedADR
│   ├── parser.py          # ADR Parser Implementation
│   └── validator.py       # ADR Validator Implementation
│
├── quality_gates.py       # Bestehend - unverändert
└── quality_gates/
    └── adr_gate.py        # ADR Gate Plugin

tests/
├── adr/
│   ├── test_parser.py
│   └── test_validator.py
└── quality_gates/
    └── test_adr_gate.py
```

---

## Nächste Schritte

Die Implementation erfolgt in den folgenden Phasen:

1. **Phase 2: ADR Parser** - Implementiere `parser.py` mit Tests
2. **Phase 3: ADR Validator** - Implementiere `validator.py` mit Tests
3. **Phase 4: Quality Gate** - Implementiere `adr_gate.py` und Integration

Jede Phase hat eigene Quality Gates zur Validierung.

---

## Dokumentation (Self-Documentation)

> **Prinzip:** Jede Änderung dokumentiert sich selbst. 
> Keine Änderung ist fertig bis die Dokumentation aktualisiert ist.

### HELIX Dokumentations-Ebenen

HELIX hat 4 Dokumentations-Ebenen:

| Ebene | Zielgruppe | Dateien | Zweck |
|-------|------------|---------|-------|
| **1. Top-Level** | Mensch & Claude | `README.md`, `ONBOARDING.md`, `CLAUDE.md` | Einstieg, Konzept, Arbeitsanweisungen |
| **2. Architecture** | Entwickler | `docs/*.md` | Technische Entscheidungen, Module, Konzepte |
| **3. Skills** | Claude Code | `skills/*/SKILL.md` | Domain-Wissen für AI-Instanzen |
| **4. Docstrings** | Code-Leser | Im Code | API-Dokumentation |

### Zu aktualisierende Dateien für ADR-System

#### Ebene 1: Top-Level

| Datei | Änderung |
|-------|----------|
| `CLAUDE.md` | Quality Gate `adr_valid` dokumentieren |
| `ONBOARDING.md` | Section "ADR-System" hinzufügen |

#### Ebene 2: Architecture Docs

| Datei | Änderung |
|-------|----------|
| `docs/ARCHITECTURE-MODULES.md` | `src/helix/adr/` Package beschreiben |
| `docs/ADR-TEMPLATE.md` | **NEU** - Template für neue ADRs |
| `docs/QUALITY-GATES.md` | `adr_valid` Gate dokumentieren (falls existiert) |

#### Ebene 3: Skills

| Datei | Änderung |
|-------|----------|
| `skills/helix/adr/SKILL.md` | **NEU** - Wie schreibt man ADRs für HELIX |

Skill-Inhalt sollte enthalten:
- Warum ADRs wichtig sind
- Das Template (basierend auf ADR-086)
- Beispiele für gute/schlechte ADRs
- Quality Gate Anforderungen

#### Ebene 4: Docstrings

Automatisch durch Implementation:
- `ADRParser` - Docstrings für alle public methods
- `ADRValidator` - Docstrings mit Beispielen
- `ADRQualityGate` - Docstrings mit Usage-Beispielen

### Self-Documentation Checkliste

Bevor das ADR-System als "fertig" gilt:

- [ ] `docs/ARCHITECTURE-MODULES.md` enthält `helix.adr` Package
- [ ] `CLAUDE.md` erklärt `adr_valid` Quality Gate
- [ ] `ONBOARDING.md` hat ADR-Workflow Section
- [ ] `skills/helix/adr/SKILL.md` existiert und ist vollständig
- [ ] Alle Public Classes/Functions haben Docstrings
- [ ] `docs/ADR-TEMPLATE.md` enthält das v4 Template

### Warum Self-Documentation wichtig ist

1. **Claude Code Instanzen** lesen die Dokumentation um zu verstehen wie sie arbeiten sollen
2. **Neue Features** die nicht dokumentiert sind, werden von zukünftigen Instanzen ignoriert
3. **Quality Gates** können prüfen ob Dokumentation vorhanden ist
4. **Konsistenz** - alle Features folgen dem gleichen Dokumentations-Pattern
