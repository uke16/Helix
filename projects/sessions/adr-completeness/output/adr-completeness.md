# ADR Completeness Enforcement

> **Konzept für kontextabhängige Vollständigkeitsprüfung von ADRs**

---

## 1. Problem-Analyse

### Was ist passiert?

ADR-014 (Documentation Architecture) wurde erstellt mit:
- `change_scope: major`
- Komplexem 14-Tage Migrationsplan im Konzept

Das Problem: **Der Migrationsplan wurde im ADR vergessen.**

### Warum passiert das?

```
┌─────────────────────────────────────────────────────────────────────────┐
│  INFORMATION LOSS CHAIN                                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. KONZEPT erstellt (vollständig)                                      │
│     └── Enthält: Context, Entscheidung, Implementation, Migration, ...  │
│                                                                          │
│  2. ADR erstellt (Template-basiert)                                     │
│     └── Validator prüft: Sections vorhanden? ✓                          │
│     └── Validator prüft NICHT: Konzept-Inhalte übernommen?              │
│                                                                          │
│  3. VERLUST: Migrationsplan existiert nur im Konzept                    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Root Causes

| Root Cause | Beschreibung | Aktueller Zustand |
|------------|--------------|-------------------|
| **Statische Regeln** | Validator prüft nur Pflicht-Sections | Keine kontextabhängige Prüfung |
| **Keine Semantik** | Validator prüft Struktur, nicht Inhalt | Section kann leer sein |
| **Kein Konzept-Link** | Kein Abgleich zwischen Konzept und ADR | Inhalte gehen verloren |
| **Kein Scope-Awareness** | `change_scope: major` hat keine Konsequenzen | Gleiche Prüfung für alle |

---

## 2. Kontextabhängige Regeln

### 2.1 Rule Engine Schema

```yaml
# config/adr-completeness-rules.yaml

_meta:
  version: "1.0"
  description: "Kontextabhängige ADR-Validierungsregeln"

# Basis-Regeln (immer aktiv)
base_rules:
  required_sections:
    - Kontext
    - Entscheidung
    - Implementation
    - Dokumentation
    - Akzeptanzkriterien
    - Konsequenzen

  min_acceptance_criteria: 3
  min_section_length: 50  # Zeichen

# Kontextabhängige Regeln
contextual_rules:

  # Regel 1: Major Changes brauchen Migration
  - id: major-needs-migration
    name: "Major Changes erfordern Migrationsplan"
    when:
      change_scope: major
    require:
      sections:
        - name: "Migration"
          min_length: 100
          required_elements:
            - "Phase"     # Mindestens eine Phase erwähnt
            - "Schritt"   # Mindestens ein Schritt
      acceptance_criteria_keywords:
        - "migration"
        - "rollback"
    severity: error
    message: "change_scope=major erfordert einen Migrations-Plan"

  # Regel 2: Major Changes brauchen Rollback-Plan
  - id: major-needs-rollback
    name: "Major Changes erfordern Rollback-Plan"
    when:
      change_scope: major
    require:
      content_patterns:
        - pattern: "(rollback|zurückrollen|revert)"
          location: any
          min_matches: 1
    severity: warning
    message: "Major changes sollten einen Rollback-Plan dokumentieren"

  # Regel 3: Neue Features brauchen Beispiele
  - id: new-needs-examples
    name: "Neue Features brauchen Usage Examples"
    when:
      classification: NEW
      files_create_not_empty: true
    require:
      sections:
        - name: "Implementation"
          required_elements:
            - "```"    # Code-Block
            - "Beispiel|Example|Usage"
    severity: warning
    message: "Neue Features sollten Beispiele enthalten"

  # Regel 4: Breaking Changes brauchen Upgrade-Guide
  - id: breaking-needs-upgrade
    name: "Breaking Changes brauchen Upgrade-Guide"
    when:
      any:
        - content_contains: "breaking change"
        - content_contains: "nicht abwärtskompatibel"
        - content_contains: "inkompatibel"
    require:
      sections:
        - name: "Migration"
          min_length: 50
      content_patterns:
        - pattern: "(vorher|nachher|alt|neu)"
          min_matches: 2
    severity: error
    message: "Breaking Changes erfordern einen Upgrade-Guide"

  # Regel 5: Dependencies brauchen Integration-Section
  - id: deps-need-integration
    name: "Abhängigkeiten brauchen Integration-Beschreibung"
    when:
      depends_on_not_empty: true
    require:
      content_patterns:
        - pattern: "ADR-\\d{3}"
          location: content
          min_matches: 1  # Referenzierte ADRs müssen erwähnt werden
    severity: warning
    message: "Abhängige ADRs sollten im Content erwähnt werden"

  # Regel 6: Neue Tools brauchen CLI-Dokumentation
  - id: tools-need-cli
    name: "Neue Tools brauchen CLI-Dokumentation"
    when:
      component_type: TOOL
      classification: NEW
    require:
      content_patterns:
        - pattern: "python -m|CLI|--help|command"
          location: implementation
          min_matches: 1
    severity: warning
    message: "Tools sollten CLI-Verwendung dokumentieren"

  # Regel 7: Services brauchen API-Dokumentation
  - id: service-needs-api
    name: "Services brauchen API-Dokumentation"
    when:
      component_type: SERVICE
    require:
      content_patterns:
        - pattern: "(GET|POST|PUT|DELETE|endpoint|API)"
          min_matches: 1
    severity: warning
    message: "Services sollten API-Endpoints dokumentieren"

  # Regel 8: Config-Änderungen brauchen Schema
  - id: config-needs-schema
    name: "Config-Änderungen brauchen Schema"
    when:
      change_scope: config
    require:
      content_patterns:
        - pattern: "```ya?ml"
          min_matches: 1
    severity: warning
    message: "Config-Änderungen sollten YAML-Schema zeigen"
```

### 2.2 Condition Operators

```yaml
# Unterstützte Bedingungen
when:
  # Einfache Gleichheit
  field: value

  # Nicht-leer Check
  field_not_empty: true

  # Liste enthält Wert
  field_contains: value

  # Kombinationen
  any:
    - condition1
    - condition2
  all:
    - condition1
    - condition2

  # Content-basiert
  content_contains: "text"
  section_exists: "Sectionname"
```

### 2.3 Requirement Types

```yaml
require:
  # Section muss existieren mit Mindest-Inhalt
  sections:
    - name: "SectionName"
      min_length: 100
      required_elements:
        - "keyword1"
        - "keyword2"

  # Content-Patterns (Regex)
  content_patterns:
    - pattern: "regex"
      location: any|header|content|section_name
      min_matches: 1

  # Acceptance Criteria Keywords
  acceptance_criteria_keywords:
    - "keyword"
```

---

## 3. Validierungs-Strategien

### 3.1 Strategie-Vergleich

| Strategie | Vorteile | Nachteile | Empfehlung |
|-----------|----------|-----------|------------|
| **Mindest-Wortanzahl** | Einfach, deterministisch | Semantik wird ignoriert | Nur als Basis |
| **Keyword-Matching** | Prüft auf spezifische Inhalte | False Positives möglich | Für kritische Checks |
| **Regex-Patterns** | Flexibel, mächtig | Komplex zu warten | Für strukturelle Checks |
| **LLM-basiert** | Versteht Semantik | Nicht-deterministisch, langsam | Als Review-Layer |
| **Checklisten** | Transparent, auditierbar | Manueller Aufwand | Für kritische ADRs |
| **Hybrid** | Beste Abdeckung | Komplexität | **Empfohlen** |

### 3.2 Empfohlener Hybrid-Ansatz

```
┌─────────────────────────────────────────────────────────────────────────┐
│  HYBRID VALIDATION PIPELINE                                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  LAYER 1: Structural (Deterministisch, Schnell)                         │
│  ├── Sections vorhanden? (bestehendes adr_tool)                         │
│  ├── Min-Length pro Section? (erweitertes adr_tool)                     │
│  └── Acceptance Criteria Count? (bestehendes adr_tool)                  │
│                                                                          │
│  LAYER 2: Contextual Rules (Deterministisch, Mittel)                    │
│  ├── Lade Regeln aus config/adr-completeness-rules.yaml                 │
│  ├── Evaluiere `when`-Conditions gegen ADR-Metadata                     │
│  ├── Prüfe `require`-Requirements via Regex/Keyword                     │
│  └── Sammle Errors/Warnings                                             │
│                                                                          │
│  LAYER 3: Semantic (LLM, Optional)                                      │
│  ├── Aktiviert nur für major + status=Proposed                          │
│  ├── Prompt: "Ist dieser ADR vollständig für scope=major?"             │
│  └── Gibt Verbesserungsvorschläge                                       │
│                                                                          │
│  LAYER 4: Concept Diff (Falls Konzept verlinkt)                         │
│  ├── Parse verlinktes Konzept                                           │
│  ├── Extrahiere H2-Sections                                             │
│  └── Prüfe ob alle Sections im ADR übernommen                           │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Layer-Aktivierung

| Layer | Wann aktiv? | Blockiert? |
|-------|-------------|------------|
| Structural | Immer | Ja (bei Errors) |
| Contextual | Immer | Ja (bei Errors) |
| Semantic | `change_scope in [major]` AND `status=Proposed` | Nein (nur Warnings) |
| Concept Diff | Wenn Konzept-Link vorhanden | Nein (nur Warnings) |

---

## 4. Empfohlene Lösung

### 4.1 Architektur

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ADR COMPLETENESS VALIDATOR                                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  src/helix/adr/                                                          │
│  ├── validator.py          (bestehend - erweitern)                       │
│  ├── completeness.py       (NEU - Contextual Rules Engine)              │
│  └── concept_diff.py       (NEU - Konzept-zu-ADR Abgleich)              │
│                                                                          │
│  config/                                                                 │
│  └── adr-completeness-rules.yaml  (NEU - Regel-Definitionen)            │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Kern-Komponenten

```python
# src/helix/adr/completeness.py

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import re
import yaml

from .parser import ADRDocument
from .validator import ValidationIssue, IssueLevel, IssueCategory


@dataclass
class CompletenessRule:
    """Eine kontextabhängige Vollständigkeitsregel."""
    id: str
    name: str
    when: dict
    require: dict
    severity: str  # "error" | "warning"
    message: str


@dataclass
class CompletenessResult:
    """Ergebnis der Vollständigkeitsprüfung."""
    passed: bool
    issues: list[ValidationIssue]
    rules_checked: int
    rules_triggered: int
    rules_passed: int


class CompletenessValidator:
    """Prüft ADRs gegen kontextabhängige Regeln.

    Example:
        >>> validator = CompletenessValidator()
        >>> result = validator.check(adr_document)
        >>> if not result.passed:
        ...     for issue in result.issues:
        ...         print(issue)
    """

    def __init__(self, rules_path: Path = None):
        """Initialisiert mit Regel-Datei.

        Args:
            rules_path: Pfad zu YAML-Regeln. Default: config/adr-completeness-rules.yaml
        """
        self.rules_path = rules_path or Path("config/adr-completeness-rules.yaml")
        self.rules = self._load_rules()

    def _load_rules(self) -> list[CompletenessRule]:
        """Lädt Regeln aus YAML."""
        if not self.rules_path.exists():
            return []

        with open(self.rules_path) as f:
            config = yaml.safe_load(f)

        rules = []
        for rule_def in config.get("contextual_rules", []):
            rules.append(CompletenessRule(
                id=rule_def["id"],
                name=rule_def["name"],
                when=rule_def["when"],
                require=rule_def["require"],
                severity=rule_def.get("severity", "warning"),
                message=rule_def["message"],
            ))

        return rules

    def check(self, adr: ADRDocument) -> CompletenessResult:
        """Prüft ADR gegen alle anwendbaren Regeln.

        Args:
            adr: Das zu prüfende ADR-Dokument

        Returns:
            CompletenessResult mit allen gefundenen Issues
        """
        issues = []
        rules_triggered = 0
        rules_passed = 0

        for rule in self.rules:
            if self._matches_condition(rule.when, adr):
                rules_triggered += 1
                rule_issues = self._check_requirements(rule, adr)

                if not rule_issues:
                    rules_passed += 1
                else:
                    issues.extend(rule_issues)

        has_errors = any(i.level == IssueLevel.ERROR for i in issues)

        return CompletenessResult(
            passed=not has_errors,
            issues=issues,
            rules_checked=len(self.rules),
            rules_triggered=rules_triggered,
            rules_passed=rules_passed,
        )

    def _matches_condition(self, when: dict, adr: ADRDocument) -> bool:
        """Prüft ob eine Regel auf das ADR zutrifft."""
        metadata = adr.metadata

        for key, expected in when.items():
            # Handle special conditions
            if key == "any":
                if not any(self._matches_condition(cond, adr) for cond in expected):
                    return False
                continue

            if key == "all":
                if not all(self._matches_condition(cond, adr) for cond in expected):
                    return False
                continue

            if key == "content_contains":
                if expected.lower() not in adr.raw_content.lower():
                    return False
                continue

            if key.endswith("_not_empty"):
                field = key.replace("_not_empty", "")
                value = self._get_field(metadata, field)
                if not value:
                    return False
                continue

            # Simple field comparison
            actual = self._get_field(metadata, key)
            if actual != expected:
                return False

        return True

    def _get_field(self, metadata, field: str):
        """Holt Feld aus Metadata, unterstützt Dot-Notation."""
        if field == "files_create":
            return metadata.files.create
        if field == "depends_on":
            return metadata.depends_on
        return getattr(metadata, field, None)

    def _check_requirements(
        self,
        rule: CompletenessRule,
        adr: ADRDocument
    ) -> list[ValidationIssue]:
        """Prüft die Requirements einer Regel."""
        issues = []
        require = rule.require
        level = IssueLevel.ERROR if rule.severity == "error" else IssueLevel.WARNING

        # Check required sections
        if "sections" in require:
            for sec_req in require["sections"]:
                section_name = sec_req["name"]
                section = self._find_section(adr, section_name)

                if not section:
                    issues.append(ValidationIssue(
                        level=level,
                        category=IssueCategory.MISSING_SECTION,
                        message=f"{rule.message} - Section fehlt: {section_name}",
                        location=f"Rule: {rule.id}",
                    ))
                else:
                    # Check min_length
                    min_len = sec_req.get("min_length", 0)
                    if len(section.content) < min_len:
                        issues.append(ValidationIssue(
                            level=level,
                            category=IssueCategory.EMPTY_SECTION,
                            message=f"{rule.message} - Section zu kurz: {section_name}",
                            location=f"Rule: {rule.id}",
                        ))

                    # Check required elements
                    for element in sec_req.get("required_elements", []):
                        if not re.search(element, section.content, re.IGNORECASE):
                            issues.append(ValidationIssue(
                                level=level,
                                category=IssueCategory.MISSING_CRITERIA,
                                message=f"{rule.message} - Element fehlt: {element}",
                                location=f"Section: {section_name}",
                            ))

        # Check content patterns
        if "content_patterns" in require:
            for pattern_req in require["content_patterns"]:
                pattern = pattern_req["pattern"]
                min_matches = pattern_req.get("min_matches", 1)
                location = pattern_req.get("location", "any")

                search_text = self._get_search_text(adr, location)
                matches = len(re.findall(pattern, search_text, re.IGNORECASE))

                if matches < min_matches:
                    issues.append(ValidationIssue(
                        level=level,
                        category=IssueCategory.MISSING_CRITERIA,
                        message=f"{rule.message} - Pattern nicht gefunden: {pattern}",
                        location=f"Rule: {rule.id}",
                    ))

        return issues

    def _find_section(self, adr: ADRDocument, name: str):
        """Findet Section case-insensitive."""
        for sec_name, section in adr.sections.items():
            if sec_name.lower() == name.lower():
                return section
        return None

    def _get_search_text(self, adr: ADRDocument, location: str) -> str:
        """Holt den zu durchsuchenden Text basierend auf Location."""
        if location == "any":
            return adr.raw_content
        if location == "header":
            return str(adr.metadata)
        if location == "content":
            return adr.raw_content
        # Section-spezifisch
        section = self._find_section(adr, location)
        return section.content if section else ""
```

### 4.3 Konzept-zu-ADR Diff

```python
# src/helix/adr/concept_diff.py

from dataclasses import dataclass
from pathlib import Path
import re

from .parser import ADRDocument


@dataclass
class ConceptSection:
    """Eine Section aus einem Konzept-Dokument."""
    name: str
    level: int  # H2=2, H3=3, etc.
    content: str


@dataclass
class ConceptDiffResult:
    """Ergebnis des Konzept-ADR-Vergleichs."""
    concept_path: Path
    concept_sections: list[str]
    adr_sections: list[str]
    missing_in_adr: list[str]
    extra_in_adr: list[str]
    coverage_percent: float


class ConceptDiffer:
    """Vergleicht Konzept-Dokument mit generiertem ADR.

    Findet fehlende Sections die im Konzept waren aber im ADR fehlen.

    Example:
        >>> differ = ConceptDiffer()
        >>> result = differ.compare(
        ...     concept_path=Path("output/concept.md"),
        ...     adr=parsed_adr
        ... )
        >>> if result.missing_in_adr:
        ...     print(f"Fehlende Sections: {result.missing_in_adr}")
    """

    # Sections die im Konzept sein können aber nicht 1:1 im ADR
    IGNORED_SECTIONS = {
        "status", "zusammenfassung", "referenzen",
        "meta", "fragen", "open questions"
    }

    def compare(
        self,
        concept_path: Path,
        adr: ADRDocument
    ) -> ConceptDiffResult:
        """Vergleicht Konzept mit ADR.

        Args:
            concept_path: Pfad zum Konzept-Markdown
            adr: Das geparste ADR-Dokument

        Returns:
            ConceptDiffResult mit Abweichungen
        """
        if not concept_path.exists():
            return ConceptDiffResult(
                concept_path=concept_path,
                concept_sections=[],
                adr_sections=list(adr.sections.keys()),
                missing_in_adr=[],
                extra_in_adr=[],
                coverage_percent=100.0,
            )

        concept_content = concept_path.read_text(encoding="utf-8")
        concept_sections = self._extract_sections(concept_content)
        adr_sections = [name.lower() for name in adr.sections.keys()]

        # Filter ignored sections
        relevant_concept = [
            s for s in concept_sections
            if s.lower() not in self.IGNORED_SECTIONS
        ]

        # Find missing
        missing = [
            s for s in relevant_concept
            if s.lower() not in adr_sections
        ]

        # Find extra (informational only)
        extra = [
            s for s in adr_sections
            if s not in [c.lower() for c in relevant_concept]
        ]

        # Calculate coverage
        if relevant_concept:
            coverage = (len(relevant_concept) - len(missing)) / len(relevant_concept) * 100
        else:
            coverage = 100.0

        return ConceptDiffResult(
            concept_path=concept_path,
            concept_sections=concept_sections,
            adr_sections=list(adr.sections.keys()),
            missing_in_adr=missing,
            extra_in_adr=extra,
            coverage_percent=round(coverage, 1),
        )

    def _extract_sections(self, content: str) -> list[str]:
        """Extrahiert H2-Section-Namen aus Markdown."""
        sections = []
        for match in re.finditer(r"^##\s+(.+)$", content, re.MULTILINE):
            section_name = match.group(1).strip()
            # Remove markdown formatting
            section_name = re.sub(r"[*_`]", "", section_name)
            sections.append(section_name)
        return sections
```

---

## 5. Integration in adr_tool.py

### 5.1 Erweiterte validate_adr Funktion

```python
# src/helix/tools/adr_tool.py - Erweiterungen

from helix.adr.completeness import CompletenessValidator
from helix.adr.concept_diff import ConceptDiffer


def validate_adr(
    adr_path: str | Path,
    concept_path: str | Path = None,
    strict: bool = False,
) -> ADRToolResult:
    """Validate an ADR file against the template and completeness rules.

    Checks:
    - File exists and is readable
    - Valid YAML frontmatter
    - Required fields present (adr_id, title, status, files)
    - Required sections present (Kontext, Entscheidung, etc.)
    - Acceptance criteria defined
    - [NEU] Contextual completeness rules
    - [NEU] Concept-to-ADR diff (if concept_path provided)

    Args:
        adr_path: Path to the ADR file
        concept_path: Optional path to source concept document
        strict: If True, treat warnings as errors

    Returns:
        ADRToolResult with validation details
    """
    path = Path(adr_path)
    errors = []
    warnings = []

    # ... bestehende Validierung ...

    # NEU: Completeness Check
    try:
        completeness_validator = CompletenessValidator()
        completeness_result = completeness_validator.check(adr)

        for issue in completeness_result.issues:
            if issue.level == IssueLevel.ERROR:
                errors.append(issue.message)
            else:
                warnings.append(issue.message)

    except Exception as e:
        warnings.append(f"Completeness check failed: {e}")

    # NEU: Concept Diff (optional)
    if concept_path:
        try:
            differ = ConceptDiffer()
            diff_result = differ.compare(Path(concept_path), adr)

            if diff_result.missing_in_adr:
                for section in diff_result.missing_in_adr:
                    warnings.append(
                        f"Section aus Konzept fehlt im ADR: {section}"
                    )

        except Exception as e:
            warnings.append(f"Concept diff failed: {e}")

    # Strict mode: Warnings werden zu Errors
    if strict:
        errors.extend(warnings)
        warnings = []

    # ... Rest der Funktion ...
```

### 5.2 CLI-Erweiterungen

```bash
# Erweiterte CLI
python -m helix.tools.adr_tool validate path/to/ADR.md

# Mit Konzept-Abgleich
python -m helix.tools.adr_tool validate path/to/ADR.md --concept output/concept.md

# Strict Mode (Warnings = Errors)
python -m helix.tools.adr_tool validate path/to/ADR.md --strict

# Nur Completeness prüfen
python -m helix.tools.adr_tool check-completeness path/to/ADR.md

# Regeln anzeigen
python -m helix.tools.adr_tool list-rules

# Regeln testen (Dry-Run)
python -m helix.tools.adr_tool test-rules path/to/ADR.md
```

---

## 6. Integration in HELIX Workflow

### 6.1 Workflow-Integration

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ADR COMPLETENESS WORKFLOW                                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  CONSULTANT PHASE                                                        │
│  ├── Konzept erstellen (output/concept.md)                              │
│  ├── ADR generieren (output/ADR-xxx.md)                                 │
│  │                                                                       │
│  │   ┌──────────────────────────────────────────────────────────────┐   │
│  │   │  COMPLETENESS CHECK (automatisch vor Finalisierung)          │   │
│  │   ├──────────────────────────────────────────────────────────────┤   │
│  │   │  1. Structural Validation (adr_tool validate)                │   │
│  │   │  2. Contextual Rules (completeness.py)                       │   │
│  │   │  3. Concept Diff (concept_diff.py)                           │   │
│  │   │                                                               │   │
│  │   │  → Errors: Blockiert Finalisierung                           │   │
│  │   │  → Warnings: Zeigt Verbesserungsvorschläge                   │   │
│  │   └──────────────────────────────────────────────────────────────┘   │
│  │                                                                       │
│  └── ADR finalisieren (adr_tool finalize)                               │
│                                                                          │
│  QUALITY GATE                                                            │
│  └── type: adr_complete (NEU - ersetzt/erweitert adr_valid)             │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Neues Quality Gate: `adr_complete`

```yaml
# phases.yaml
phases:
  - id: consultant
    name: Consultant Meeting
    type: consultant
    quality_gate:
      type: adr_complete      # NEU: Erweiterte Prüfung
      file: output/ADR-*.md
      concept: output/concept.md  # Optional: Konzept-Abgleich
      strict: false           # Warnings als Errors behandeln
```

```python
# src/helix/quality_gates/adr_complete.py

class ADRCompleteGate:
    """Quality Gate für vollständige ADRs.

    Erweitert adr_valid um:
    - Kontextabhängige Regeln
    - Konzept-Diff
    - Strict Mode
    """

    def check(self, config: dict) -> GateResult:
        adr_file = self._find_adr_file(config["file"])
        concept_file = config.get("concept")
        strict = config.get("strict", False)

        result = validate_adr(
            adr_file,
            concept_path=concept_file,
            strict=strict,
        )

        return GateResult(
            passed=result.success,
            errors=result.errors,
            warnings=result.warnings,
        )
```

### 6.3 Consultant CLAUDE.md Update

```markdown
# In templates/consultant/CLAUDE.md ergänzen:

## ADR-Generierung

Wenn du ein ADR erstellst:

1. **Konzept zuerst**: Schreibe das vollständige Konzept in `output/concept.md`
2. **ADR generieren**: Erstelle `output/ADR-xxx.md` basierend auf dem Konzept
3. **Validieren**: Rufe `python -m helix.tools.adr_tool validate output/ADR-xxx.md --concept output/concept.md` auf
4. **Warnings beachten**: Prüfe ob alle Konzept-Sections übernommen wurden
5. **Finalisieren**: Erst wenn keine Errors, rufe `finalize` auf

### Kontextabhängige Sections

| Wenn... | Dann braucht das ADR... |
|---------|-------------------------|
| `change_scope: major` | Migration-Plan mit Phasen |
| `classification: NEW` | Usage-Beispiele |
| Breaking Changes | Upgrade-Guide |
| `depends_on` nicht leer | Referenzen auf abhängige ADRs |
```

---

## 7. Beispiel: Wie hätte ADR-014 geprüft werden sollen?

### 7.1 ADR-014 Metadata

```yaml
change_scope: major
classification: NEW
files:
  create:
    - docs/sources/quality-gates.yaml
    - src/helix/tools/docs_compiler.py
    - ...
```

### 7.2 Triggernde Regeln

```
┌─────────────────────────────────────────────────────────────────────────┐
│  REGELN DIE GETRIGGERT WERDEN                                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ✓ major-needs-migration                                                │
│    when: change_scope == major                                          │
│    require: Section "Migration" mit min_length=100                      │
│                                                                          │
│  ✓ major-needs-rollback                                                 │
│    when: change_scope == major                                          │
│    require: Pattern "(rollback|zurückrollen)" im Content                │
│                                                                          │
│  ✓ new-needs-examples                                                   │
│    when: classification == NEW AND files.create not empty              │
│    require: Code-Block in Implementation                                │
│                                                                          │
│  ✓ tools-need-cli                                                       │
│    when: component_type == TOOL (FALSCH - ist PROCESS)                  │
│    → Nicht getriggert                                                   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 7.3 Validierungs-Output (hypothetisch)

```bash
$ python -m helix.tools.adr_tool validate output/ADR-014.md --concept output/docs-architecture.md

✅ Structural Validation: PASSED
   - All required sections present
   - 20 acceptance criteria found
   - YAML header valid

❌ Contextual Completeness: FAILED

   ERROR [major-needs-migration]:
     change_scope=major erfordert einen Migrations-Plan
     - Section "Migration" fehlt oder zu kurz

   WARNING [major-needs-rollback]:
     Major changes sollten einen Rollback-Plan dokumentieren
     - Pattern "rollback" nicht gefunden

⚠️ Concept Diff: 1 MISSING SECTION

   Section aus Konzept fehlt im ADR:
   - "Migration Plan (14 Tage)"

   Coverage: 90% (9/10 Sections übernommen)

RESULT: VALIDATION FAILED
   2 errors, 1 warning

   To fix:
   1. Füge Section "## Migration" mit Migrations-Plan hinzu
   2. Dokumentiere Rollback-Strategie
```

### 7.4 Korrigiertes ADR-014

Nach dem Hinzufügen der Migration-Section:

```markdown
## Migration

### 14-Tage Implementationsplan

#### Phase 1: Foundation (Tag 1-3)
- [ ] YAML Sources erstellen
- [ ] Jinja2 Templates initial
...

### Rollback-Strategie

Falls die Migration fehlschlägt:
1. Git tag "pre-docs-architecture" wiederherstellen
2. Templates löschen
3. Manuelle Docs wiederherstellen
```

```bash
$ python -m helix.tools.adr_tool validate output/ADR-014.md --concept output/docs-architecture.md

✅ Structural Validation: PASSED
✅ Contextual Completeness: PASSED (3 rules triggered, 3 passed)
✅ Concept Diff: 100% coverage

RESULT: VALIDATION PASSED
```

---

## 8. Implementation Roadmap

### Phase 1: Basis-Infrastruktur

- [ ] `config/adr-completeness-rules.yaml` erstellen
- [ ] `src/helix/adr/completeness.py` implementieren
- [ ] Unit Tests für Rule Engine

### Phase 2: Integration

- [ ] `validate_adr()` erweitern
- [ ] CLI-Optionen hinzufügen
- [ ] `adr_complete` Quality Gate implementieren

### Phase 3: Concept Diff

- [ ] `src/helix/adr/concept_diff.py` implementieren
- [ ] Integration in validate_adr
- [ ] Consultant CLAUDE.md aktualisieren

### Phase 4: Dokumentation & Rollout

- [ ] ADR für dieses Feature erstellen
- [ ] Skills aktualisieren
- [ ] Bestehende ADRs migrieren/prüfen

---

## 9. Generische Anwendung

Dieses Konzept ist nicht auf ADRs beschränkt. Die Rule Engine kann für andere Dokument-Typen angepasst werden:

| Dokument-Typ | Regel-Datei | Beispiel-Regeln |
|--------------|-------------|-----------------|
| ADRs | `adr-completeness-rules.yaml` | major→Migration |
| Specs | `spec-completeness-rules.yaml` | type=feature→User Stories |
| PRs | `pr-completeness-rules.yaml` | breaking→Migration Notes |
| Code Docs | `docstring-rules.yaml` | public→Parameter-Docs |

Die Architektur unterstützt:
- Pluggable Rule Sources
- Custom Condition Operators
- Custom Requirement Checkers
- LLM-Integration für semantische Prüfung

---

*Konzept erstellt vom HELIX Meta-Consultant*
*Session: adr-completeness*
