---
adr_id: "015"
title: "Approval & Validation System - Hybrid Pre-Checks + Sub-Agent"
status: Proposed

component_type: PROCESS
classification: NEW
change_scope: major

domain: helix
language: python
skills:
  - helix

files:
  create:
    - approvals/README.md
    - approvals/adr/CLAUDE.md
    - approvals/adr/checks/completeness.md
    - approvals/adr/checks/migration.md
    - approvals/adr/checks/acceptance.md
    - approvals/adr/checks/conflicts.md
    - approvals/code/CLAUDE.md
    - approvals/code/checks/security.md
    - approvals/code/checks/tests.md
    - config/adr-completeness-rules.yaml
    - config/approvals.yaml
    - src/helix/adr/completeness.py
    - src/helix/adr/concept_diff.py
    - src/helix/adr/semantic.py
    - src/helix/approval/__init__.py
    - src/helix/approval/runner.py
    - src/helix/approval/result.py
    - src/helix/approval/config.py
  modify:
    - src/helix/adr/validator.py
    - src/helix/adr/gate.py
    - src/helix/quality_gates/__init__.py
    - src/helix/tools/adr_tool.py

depends_on: ["002", "003", "012"]
related_to: ["014"]
---

# ADR-015: Approval & Validation System - Hybrid Pre-Checks + Sub-Agent

## Kontext

### Das Problem: Selbstprüfung = Bestätigungsbias

Wenn eine Claude Code Instanz ein Artefakt erstellt (z.B. ein ADR, Code, Dokumentation), ist die **gleiche Instanz kontaminiert durch den Erstellungsprozess**:

```
Consultant erstellt ADR
    ↓
Consultant prüft eigenes ADR  ← PROBLEMATISCH!
    ↓
"Ja, sieht gut aus"           ← Bestätigungsbias
```

Die erstellende Instanz kennt:
- Die Intention hinter Formulierungen
- Implizite Annahmen die nicht dokumentiert wurden
- Was sie "eigentlich meinte" aber nicht schrieb

### Das Problem: Vergessene Sections

Bei ADR-014 (Documentation Architecture) wurde ein kritisches Problem entdeckt:

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

- ADR-014 hatte `change_scope: major`
- Das Konzept enthielt einen 14-Tage Migrationsplan
- Der Migrationsplan wurde im finalen ADR vergessen
- Bestehende Validierung erkannte das Problem nicht

### Root Causes

| Root Cause | Beschreibung | Aktueller Zustand |
|------------|--------------|-------------------|
| **Statische Regeln** | Validator prüft nur Pflicht-Sections | Keine kontextabhängige Prüfung |
| **Keine Semantik** | Validator prüft Struktur, nicht Inhalt | Section kann leer sein |
| **Kein Konzept-Link** | Kein Abgleich zwischen Konzept und ADR | Inhalte gehen verloren |
| **Kein Scope-Awareness** | `change_scope: major` hat keine Konsequenzen | Gleiche Prüfung für alle |
| **Selbstprüfung** | Ersteller prüft eigenes Artefakt | Bestätigungsbias |

### Warum nicht nur API-Call?

API-Calls an ein LLM für Validierung haben Limitierungen:

| Aspekt | Direkter API-Call | Sub-Agent |
|--------|-------------------|-----------|
| **Context** | Kein HELIX-Context | Voller HELIX-Context via CLAUDE.md |
| **Tools** | Keine | Alle Claude Code Tools |
| **Skills** | Nicht ladbar | Kann beliebige Skills laden |
| **Flexibilität** | Statische Regeln | Dynamisch, LLM-gesteuert |
| **Unabhängigkeit** | Teilt Erstellungskontext | Vollständig frischer Context |
| **Tiefe** | Nur explizite Checks | Kann explorativ prüfen |
| **Codebase-Zugriff** | Keiner | Voller Zugriff |

### Die Lösung: Hybrid-Ansatz

Ein **Hybrid-System** kombiniert das Beste beider Welten:

1. **Phase 1: Pre-Checks** (deterministisch, kostenlos, schnell)
   - Strukturelle Validierung
   - Kontextabhängige Regeln
   - Konzept-Diff

2. **Phase 2: Sub-Agent Approval** (LLM, ~$0.02-0.20, tiefgehend)
   - Semantische Prüfung
   - Frischer Context (kein Ersteller-Bias)
   - Voller Codebase-Zugriff

---

## Entscheidung

### Wir entscheiden uns für einen Hybrid-Ansatz

```
┌─────────────────────────────────────────────────────────────────────────┐
│  HYBRID VALIDATION PIPELINE                                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  PHASE 1: PRE-CHECKS (deterministisch, kostenlos)                       │
│                                                                          │
│  ├── Layer 1: Structural Validation                                      │
│  │   ├── Sections vorhanden?                                             │
│  │   ├── YAML Header gültig?                                             │
│  │   └── Min-Length pro Section?                                         │
│  │                                                                       │
│  ├── Layer 2: Contextual Rules                                           │
│  │   ├── change_scope: major → Migration-Plan erforderlich              │
│  │   ├── classification: NEW → Beispiele erforderlich                   │
│  │   └── Breaking Changes → Upgrade-Guide erforderlich                  │
│  │                                                                       │
│  └── Layer 3: Concept Diff (falls Konzept vorhanden)                    │
│      └── Alle Konzept-Sections im ADR übernommen?                       │
│                                                                          │
│  → Wenn FAILED: Sofort abbrechen (keine Kosten)                         │
│  → Wenn PASSED: Weiter zu Phase 2                                       │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  PHASE 2: SUB-AGENT APPROVAL (LLM, ~$0.02-0.20)                         │
│                                                                          │
│  └── Layer 4: Semantic + Tiefenprüfung                                  │
│      ├── Frischer Context (kein Ersteller-Bias)                         │
│      ├── Kann Codebase lesen (referenzierte Dateien existieren?)       │
│      ├── Kann Skills laden (Domain-Wissen)                              │
│      └── Semantische Vollständigkeit prüfen                              │
│                                                                          │
│  → APPROVED: Weiter zur Implementation                                   │
│  → REJECTED: Feedback an Ersteller                                       │
│  → NEEDS_REVISION: Spezifische Verbesserungsvorschläge                   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Diese Entscheidung beinhaltet:

1. **Deterministischer Pre-Check Layer** (`src/helix/adr/completeness.py`)
   - YAML-basierte Regeln in `config/adr-completeness-rules.yaml`
   - Kontextabhängige Validierung (change_scope, classification, etc.)
   - Konzept-zu-ADR Diff

2. **Sub-Agent als neue Claude CLI Instanz** (`src/helix/approval/runner.py`)
   - Neuer Prozess via `subprocess` mit `claude --print`
   - Läuft in dediziertem `approvals/` Verzeichnis
   - Hat eigene CLAUDE.md mit Prüfanweisungen

3. **Approval-Verzeichnis-Pattern** (`approvals/`)
   - Zentrale Verwaltung aller Approval-Typen
   - Eigene CLAUDE.md pro Approval-Typ (adr, code, docs)
   - Check-Definitionen in `checks/*.md`

4. **Quality Gate Integration**
   - Neuer Gate-Type `approval` im QualityGateRunner
   - Neuer Gate-Type `adr_complete` für erweiterte ADR-Prüfung
   - Konfigurierbar in `phases.yaml`

### Warum diese Lösung?

| Kriterium | API-Call Only | Sub-Agent Only | Hybrid (gewählt) |
|-----------|---------------|----------------|------------------|
| **Latenz** | ~100ms | ~30-60s | ~5-30s |
| **Kosten** | ~$0.01 | ~$0.10-0.50 | ~$0.02-0.20 |
| **Tiefe** | Oberflächlich | Tiefgehend | Tiefgehend (wenn nötig) |
| **Context** | Kontaminiert | Frisch | Frisch |
| **Early-Exit** | Nein | Nein | Ja (bei Pre-Check Failure) |
| **Tools** | Keine | Alle | Alle (in Phase 2) |

---

## Implementation

### 1. Verzeichnis-Struktur

```
helix-v4/
├── approvals/                          # NEU: Approval-Definitionen
│   ├── README.md                       # Übersicht aller Approval-Typen
│   │
│   ├── adr/                            # ADR-Prüfung
│   │   ├── CLAUDE.md                   # Instruktionen für Sub-Agent
│   │   ├── checks/                     # Prüfungsanweisungen
│   │   │   ├── completeness.md         # Vollständigkeitsprüfung
│   │   │   ├── migration.md            # Migrationspläne vorhanden?
│   │   │   ├── acceptance.md           # Akzeptanzkriterien checkbar?
│   │   │   └── conflicts.md            # Konflikte mit anderen ADRs?
│   │   ├── skills/                     # Symlinks zu relevanten Skills
│   │   │   └── adr -> ../../../skills/helix/adr
│   │   ├── input/                      # Runtime: Zu prüfende Dateien (Symlinks)
│   │   └── output/                     # Runtime: Prüfergebnisse
│   │
│   ├── code/                           # Code-Review
│   │   ├── CLAUDE.md
│   │   └── checks/
│   │       ├── security.md             # OWASP Top 10
│   │       ├── tests.md                # Test-Coverage & Quality
│   │       └── patterns.md             # Design Pattern Compliance
│   │
│   └── docs/                           # Dokumentations-Review (Phase 2)
│       ├── CLAUDE.md
│       └── checks/
│           ├── completeness.md
│           └── consistency.md
│
├── config/
│   ├── adr-completeness-rules.yaml     # NEU: Kontextabhängige Regeln
│   └── approvals.yaml                  # NEU: Approval-Konfiguration
│
└── src/helix/
    ├── adr/
    │   ├── validator.py                # ERWEITERT
    │   ├── completeness.py             # NEU: Layer 2 Rules Engine
    │   ├── concept_diff.py             # NEU: Layer 3 Konzept-Diff
    │   ├── semantic.py                 # NEU: Layer 4 LLM-Prüfung
    │   └── gate.py                     # ERWEITERT: adr_complete Gate
    │
    ├── approval/                       # NEU: Approval-System
    │   ├── __init__.py
    │   ├── runner.py                   # ApprovalRunner
    │   ├── result.py                   # ApprovalResult, Finding
    │   └── config.py                   # ApprovalConfig
    │
    └── quality_gates/
        └── __init__.py                 # ERWEITERT: check_approval()
```

### 2. Kontextabhängige Regeln (Layer 2)

**`config/adr-completeness-rules.yaml`:**

```yaml
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
            - "Phase"
            - "Schritt"
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
            - "```"
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

  # Regel 5: Dependencies brauchen Referenzen
  - id: deps-need-references
    name: "Abhängigkeiten brauchen Referenzen"
    when:
      depends_on_not_empty: true
    require:
      content_patterns:
        - pattern: "ADR-\\d{3}"
          location: content
          min_matches: 1
    severity: warning
    message: "Abhängige ADRs sollten im Content erwähnt werden"

  # Regel 6: Tools brauchen CLI-Dokumentation
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
```

### 3. CompletenessValidator (Layer 2)

```python
# src/helix/adr/completeness.py

"""Contextual completeness validation for ADRs.

Layer 2 of the ADR validation system. Applies context-dependent
rules based on ADR metadata (change_scope, classification, etc.).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import re
import yaml

from .parser import ADRDocument
from .validator import ValidationIssue, IssueLevel, IssueCategory


@dataclass
class CompletenessRule:
    """A contextual completeness rule."""
    id: str
    name: str
    when: dict
    require: dict
    severity: str  # "error" | "warning"
    message: str


@dataclass
class CompletenessResult:
    """Result of completeness validation."""
    passed: bool
    issues: list[ValidationIssue]
    rules_checked: int
    rules_triggered: int
    rules_passed: int


class CompletenessValidator:
    """Validates ADRs against contextual rules.

    Example:
        >>> validator = CompletenessValidator()
        >>> result = validator.check(adr_document)
        >>> if not result.passed:
        ...     for issue in result.issues:
        ...         print(issue)
    """

    def __init__(self, rules_path: Path = None):
        """Initialize with rule file.

        Args:
            rules_path: Path to YAML rules. Default: config/adr-completeness-rules.yaml
        """
        self.rules_path = rules_path or Path("config/adr-completeness-rules.yaml")
        self.rules = self._load_rules()

    def _load_rules(self) -> list[CompletenessRule]:
        """Load rules from YAML."""
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
        """Check ADR against all applicable rules.

        Args:
            adr: The ADR document to check

        Returns:
            CompletenessResult with found issues
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
        """Check if a rule applies to the ADR."""
        metadata = adr.metadata

        for key, expected in when.items():
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

            actual = self._get_field(metadata, key)
            if actual != expected:
                return False

        return True

    def _get_field(self, metadata, field: str):
        """Get field from metadata, supports nested access."""
        if field == "files_create":
            return metadata.files.create if metadata.files else None
        if field == "depends_on":
            return metadata.depends_on
        return getattr(metadata, field, None)

    def _check_requirements(
        self,
        rule: CompletenessRule,
        adr: ADRDocument
    ) -> list[ValidationIssue]:
        """Check the requirements of a rule."""
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
                    min_len = sec_req.get("min_length", 0)
                    if len(section.content) < min_len:
                        issues.append(ValidationIssue(
                            level=level,
                            category=IssueCategory.EMPTY_SECTION,
                            message=f"{rule.message} - Section zu kurz: {section_name}",
                            location=f"Rule: {rule.id}",
                        ))

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
        """Find section case-insensitive."""
        for sec_name, section in adr.sections.items():
            if sec_name.lower() == name.lower():
                return section
        return None

    def _get_search_text(self, adr: ADRDocument, location: str) -> str:
        """Get text to search based on location."""
        if location == "any":
            return adr.raw_content
        if location == "header":
            return str(adr.metadata)
        if location == "content":
            return adr.raw_content
        section = self._find_section(adr, location)
        return section.content if section else ""
```

### 4. ConceptDiffer (Layer 3)

```python
# src/helix/adr/concept_diff.py

"""Concept-to-ADR diff for validating completeness.

Layer 3 of the ADR validation system. Compares a source concept
document with the generated ADR to find missing sections.
"""

from dataclasses import dataclass
from pathlib import Path
import re

from .parser import ADRDocument


@dataclass
class ConceptDiffResult:
    """Result of concept-ADR comparison."""
    concept_path: Path
    concept_sections: list[str]
    adr_sections: list[str]
    missing_in_adr: list[str]
    extra_in_adr: list[str]
    coverage_percent: float


class ConceptDiffer:
    """Compares concept document with generated ADR.

    Finds missing sections that were in the concept but not in the ADR.

    Example:
        >>> differ = ConceptDiffer()
        >>> result = differ.compare(
        ...     concept_path=Path("output/concept.md"),
        ...     adr=parsed_adr
        ... )
        >>> if result.missing_in_adr:
        ...     print(f"Missing: {result.missing_in_adr}")
    """

    IGNORED_SECTIONS = {
        "status", "zusammenfassung", "referenzen",
        "meta", "fragen", "open questions"
    }

    def compare(
        self,
        concept_path: Path,
        adr: ADRDocument
    ) -> ConceptDiffResult:
        """Compare concept with ADR.

        Args:
            concept_path: Path to concept markdown
            adr: Parsed ADR document

        Returns:
            ConceptDiffResult with deviations
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

        relevant_concept = [
            s for s in concept_sections
            if s.lower() not in self.IGNORED_SECTIONS
        ]

        missing = [
            s for s in relevant_concept
            if s.lower() not in adr_sections
        ]

        extra = [
            s for s in adr_sections
            if s not in [c.lower() for c in relevant_concept]
        ]

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
        """Extract H2 section names from markdown."""
        sections = []
        for match in re.finditer(r"^##\s+(.+)$", content, re.MULTILINE):
            section_name = match.group(1).strip()
            section_name = re.sub(r"[*_`]", "", section_name)
            sections.append(section_name)
        return sections
```

### 5. ApprovalRunner (Layer 4 - Sub-Agent)

```python
# src/helix/approval/runner.py

"""Sub-Agent Approval Runner for HELIX v4.

Spawns independent Claude Code instances for approval checks.
This is Layer 4 of the validation system - semantic deep checks.
"""

import asyncio
import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .result import ApprovalResult, Finding, Severity


@dataclass
class ApprovalConfig:
    """Configuration for an approval run."""
    approval_type: str
    model: str = "claude-sonnet-4-20250514"
    timeout: int = 300
    retry_on_failure: bool = True
    required_confidence: float = 0.8


class ApprovalRunner:
    """Runs approval checks using sub-agents.

    The ApprovalRunner spawns a new Claude Code CLI instance
    with a fresh context to perform independent validation.

    Example:
        runner = ApprovalRunner()
        result = await runner.run_approval(
            approval_type="adr",
            input_files=[Path("output/ADR-feature.md")],
        )

        if result.approved:
            print("ADR approved!")
        else:
            for finding in result.errors:
                print(f"Error: {finding.message}")
    """

    APPROVALS_DIR = Path("approvals")
    CLAUDE_CMD = "claude"

    def __init__(
        self,
        approvals_base: Path | None = None,
        claude_cmd: str | None = None,
    ) -> None:
        """Initialize the ApprovalRunner.

        Args:
            approvals_base: Base directory for approval definitions.
            claude_cmd: Path to Claude CLI executable.
        """
        self.approvals_base = approvals_base or self.APPROVALS_DIR
        self.claude_cmd = claude_cmd or self.CLAUDE_CMD

    async def run_approval(
        self,
        approval_type: str,
        input_files: list[Path],
        config: ApprovalConfig | None = None,
    ) -> ApprovalResult:
        """Run an approval check using a sub-agent.

        Args:
            approval_type: Type of approval (e.g., "adr", "code").
            input_files: Files to check.
            config: Optional configuration.

        Returns:
            ApprovalResult with findings and decision.
        """
        config = config or ApprovalConfig(approval_type=approval_type)
        approval_id = str(uuid.uuid4())[:8]
        start_time = datetime.now()

        approval_dir = self.approvals_base / approval_type
        if not approval_dir.exists():
            return ApprovalResult(
                approval_id=approval_id,
                approval_type=approval_type,
                result="rejected",
                confidence=0.0,
                findings=[Finding(
                    severity=Severity.ERROR,
                    check="setup",
                    message=f"Approval type not found: {approval_type}",
                )],
            )

        # Prepare input directory
        input_dir = approval_dir / "input"
        input_dir.mkdir(exist_ok=True)

        # Clean previous inputs
        for old_file in input_dir.iterdir():
            old_file.unlink()

        # Symlink input files (not copy!)
        for input_file in input_files:
            if input_file.exists():
                abs_path = input_file.absolute()
                link_path = input_dir / input_file.name
                os.symlink(abs_path, link_path)

        # Build prompt
        prompt = self._build_prompt(approval_type, input_files)

        # Spawn sub-agent
        try:
            await self._spawn_agent(
                approval_dir=approval_dir,
                prompt=prompt,
                timeout=config.timeout,
            )
        except asyncio.TimeoutError:
            return ApprovalResult(
                approval_id=approval_id,
                approval_type=approval_type,
                result="rejected",
                confidence=0.0,
                findings=[Finding(
                    severity=Severity.ERROR,
                    check="timeout",
                    message=f"Approval timed out after {config.timeout}s",
                )],
            )

        # Parse result
        output_file = approval_dir / "output" / "approval-result.json"
        duration = (datetime.now() - start_time).total_seconds()

        if output_file.exists():
            try:
                with open(output_file) as f:
                    result_data = json.load(f)
                result = ApprovalResult.from_dict(
                    approval_id=approval_id,
                    approval_type=approval_type,
                    data=result_data,
                )
                result.duration_seconds = duration
                return result
            except (json.JSONDecodeError, KeyError) as e:
                return ApprovalResult(
                    approval_id=approval_id,
                    approval_type=approval_type,
                    result="rejected",
                    confidence=0.0,
                    findings=[Finding(
                        severity=Severity.ERROR,
                        check="parse",
                        message=f"Failed to parse result: {e}",
                    )],
                    duration_seconds=duration,
                )

        return ApprovalResult(
            approval_id=approval_id,
            approval_type=approval_type,
            result="rejected",
            confidence=0.0,
            findings=[Finding(
                severity=Severity.ERROR,
                check="output",
                message="No approval result file generated",
            )],
            duration_seconds=duration,
        )

    async def _spawn_agent(
        self,
        approval_dir: Path,
        prompt: str,
        timeout: int,
    ) -> None:
        """Spawn a sub-agent process.

        Args:
            approval_dir: Working directory for the agent.
            prompt: Prompt to send to the agent.
            timeout: Timeout in seconds.
        """
        cmd = [
            self.claude_cmd,
            "--print",
            "--dangerously-skip-permissions",
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=approval_dir,
        )

        await asyncio.wait_for(
            process.communicate(input=prompt.encode()),
            timeout=timeout,
        )

    def _build_prompt(
        self,
        approval_type: str,
        input_files: list[Path],
    ) -> str:
        """Build the prompt for the sub-agent.

        Args:
            approval_type: Type of approval.
            input_files: Files being checked.

        Returns:
            Prompt string.
        """
        file_list = ", ".join(f.name for f in input_files)

        return f"""Lies CLAUDE.md und führe eine {approval_type.upper()}-Freigabeprüfung durch.

Zu prüfende Dateien (in input/):
{file_list}

Führe ALLE Checks in checks/ aus und schreibe das Ergebnis nach:
output/approval-result.json

Halte dich strikt an das Output-Format aus CLAUDE.md."""
```

### 6. ApprovalResult Dataclass

```python
# src/helix/approval/result.py

"""Result classes for approval checks."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class Severity(Enum):
    """Severity levels for findings."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ApprovalDecision(Enum):
    """Possible approval decisions."""
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


@dataclass
class Finding:
    """A single finding from an approval check."""
    severity: Severity
    check: str
    message: str
    location: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity.value,
            "check": self.check,
            "message": self.message,
            "location": self.location,
        }


@dataclass
class ApprovalResult:
    """Result of an approval check."""
    approval_id: str
    approval_type: str
    result: str  # "approved", "rejected", "needs_revision"
    confidence: float
    findings: list[Finding] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    duration_seconds: float = 0.0
    tokens_used: int = 0

    @property
    def approved(self) -> bool:
        """Check if the result is approved."""
        return self.result == "approved"

    @property
    def errors(self) -> list[Finding]:
        """Get all error-level findings."""
        return [f for f in self.findings if f.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[Finding]:
        """Get all warning-level findings."""
        return [f for f in self.findings if f.severity == Severity.WARNING]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "approval_id": self.approval_id,
            "approval_type": self.approval_type,
            "result": self.result,
            "confidence": self.confidence,
            "findings": [f.to_dict() for f in self.findings],
            "recommendations": self.recommendations,
            "timestamp": self.timestamp.isoformat(),
            "agent_context": {
                "duration_seconds": self.duration_seconds,
                "tokens_used": self.tokens_used,
            },
        }

    @classmethod
    def from_dict(
        cls,
        approval_id: str,
        approval_type: str,
        data: dict[str, Any],
    ) -> "ApprovalResult":
        """Create from dictionary (parsed from agent output)."""
        findings = [
            Finding(
                severity=Severity(f["severity"]),
                check=f["check"],
                message=f["message"],
                location=f.get("location"),
            )
            for f in data.get("findings", [])
        ]

        return cls(
            approval_id=approval_id,
            approval_type=approval_type,
            result=data.get("result", "rejected"),
            confidence=data.get("confidence", 0.0),
            findings=findings,
            recommendations=data.get("recommendations", []),
        )
```

### 7. Approval CLAUDE.md Template

**`approvals/adr/CLAUDE.md`:**

```markdown
# Approval: ADR-Prüfung

Du bist ein unabhängiger Prüfer für Architecture Decision Records.

## Deine Aufgabe

1. Lies die zu prüfenden ADRs in `input/`
2. Führe alle Checks in `checks/` durch
3. Schreibe das Ergebnis nach `output/approval-result.json`

## Prüfungen

Für jeden Check in `checks/`:
1. Lies die Check-Beschreibung
2. Prüfe das ADR gegen diese Kriterien
3. Notiere Findings (errors, warnings, infos)

## Output-Format

```json
{
  "result": "approved" | "rejected" | "needs_revision",
  "confidence": 0.0-1.0,
  "findings": [
    {
      "severity": "error" | "warning" | "info",
      "check": "check_name",
      "message": "Beschreibung des Problems",
      "location": "Section/Zeile (optional)"
    }
  ],
  "recommendations": [
    "Verbesserungsvorschlag 1",
    "Verbesserungsvorschlag 2"
  ]
}
```

## Wichtig

- Du hast KEINEN Zugriff auf den Erstellungsprozess
- Prüfe objektiv und unvoreingenommen
- Sei konstruktiv in deinen Empfehlungen
- Lies die Skills in `skills/` für Domain-Wissen
- Du kannst die Codebase lesen um zu prüfen ob referenzierte Dateien existieren

## Entscheidungskriterien

- `approved`: Alle Pflicht-Checks bestanden, keine kritischen Issues
- `needs_revision`: Minor Issues die behoben werden sollten
- `rejected`: Kritische Issues die das ADR ungültig machen
```

### 8. Check-Datei Beispiel

**`approvals/adr/checks/completeness.md`:**

```markdown
# Check: ADR Vollständigkeit

## Zu prüfende Kriterien

### 1. YAML Header (Pflichtfelder)
- [ ] `adr_id` vorhanden
- [ ] `title` vorhanden
- [ ] `status` vorhanden und gültig (Proposed|Accepted|Implemented|Superseded|Rejected)

### 2. Sections (alle müssen vorhanden sein)
- [ ] `## Kontext` - Warum diese Änderung?
- [ ] `## Entscheidung` - Was wird entschieden?
- [ ] `## Implementation` - Konkrete Umsetzung
- [ ] `## Dokumentation` - Zu aktualisierende Docs
- [ ] `## Akzeptanzkriterien` - Checkboxen
- [ ] `## Konsequenzen` - Trade-offs

### 3. Inhaltliche Qualität
- [ ] Kontext erklärt das "Warum" (nicht nur das "Was")
- [ ] Entscheidung ist klar und eindeutig formuliert
- [ ] Implementation enthält konkrete Schritte/Code
- [ ] Mindestens 3 Akzeptanzkriterien definiert
- [ ] Konsequenzen listen Vor- UND Nachteile

### 4. Zusätzliche Prüfungen (bei change_scope: major)
- [ ] Migration-Section vorhanden
- [ ] Migrations-Schritte/Phasen definiert
- [ ] Rollback-Strategie dokumentiert

## Severity-Mapping

| Kriterium | Bei Fehlen |
|-----------|------------|
| YAML Pflichtfelder | ERROR |
| Pflicht-Sections | ERROR |
| Inhaltliche Qualität | WARNING |
| Migration (wenn major) | ERROR |
```

### 9. Quality Gate Integration

```yaml
# phases.yaml - Approval als Quality Gate

phases:
  - id: consultant
    type: consultant
    output:
      - output/ADR-feature.md
    quality_gate:
      type: adr_complete          # Erweiterte ADR-Prüfung
      file: output/ADR-*.md
      concept: output/concept.md  # Optional: Konzept-Abgleich
      semantic: auto              # auto | true | false

  # ODER: Approval als eigene Phase
  - id: approval
    type: approval
    approval_type: adr
    input:
      - output/ADR-feature.md
    output:
      - approvals/adr/output/approval-result.json
    on_rejection:
      action: retry_phase
      target_phase: consultant
      max_retries: 2
```

### 10. Approval-Konfiguration

**`config/approvals.yaml`:**

```yaml
# Globale Approval-Konfiguration

approvals:
  adr:
    enabled: true
    model: claude-sonnet-4-20250514
    timeout: 300              # 5 Minuten max
    retry_on_failure: true
    required_confidence: 0.8  # Min. Confidence für Auto-Approve

  code:
    enabled: true
    model: claude-sonnet-4-20250514
    timeout: 600              # 10 Minuten für größere Reviews
    checks:
      - security
      - tests
      # performance und patterns optional

  docs:
    enabled: false            # Noch nicht implementiert

defaults:
  model: claude-sonnet-4-20250514
  timeout: 300
  retry_on_failure: true
```

---

## Approval-Typen

### Übersicht

| Approval-Typ | Use Case | Priorität | Phase |
|--------------|----------|-----------|-------|
| **adr** | ADR-Freigabe vor Implementation | HOCH | MVP |
| **code** | Code-Review nach Implementation | HOCH | MVP |
| **docs** | Dokumentations-Review | MITTEL | Phase 2 |
| **security** | Dedizierter Security-Audit | HOCH | Phase 2 |
| **architecture** | Architektur-Review bei großen Änderungen | MITTEL | Phase 3 |

### ADR-Approval (MVP)

**Checks:**
- Vollständigkeit (Sections, Header)
- Kontextabhängige Regeln (Migration bei major)
- Konzept-Diff (falls Konzept vorhanden)
- Semantische Prüfung

### Code-Approval (MVP)

**Checks:**
- Security (OWASP Top 10)
- Test-Coverage
- Code-Patterns
- Type Hints & Docstrings

### Docs-Approval (Phase 2)

**Checks:**
- Konsistenz mit Code
- Beispiele funktional
- Links gültig

---

## Workflow-Integration

### on_rejection Handler

Bei Ablehnung eines Approvals kann konfiguriert werden was passiert:

```yaml
on_rejection:
  action: retry_phase           # Wiederholt vorherige Phase
  target_phase: consultant      # Mit Feedback an Consultant
  max_retries: 2                # Max. 2 Überarbeitungen
  feedback_template: |
    ## Freigabe nicht erteilt

    ### Blocking Issues:
    {{blocking_issues}}

    ### Bitte überarbeiten:
    {{suggestions}}
```

**Verfügbare Actions:**
- `retry_phase` - Wiederholt target_phase mit Feedback
- `escalate` - Eskaliert an menschlichen Reviewer
- `fail` - Bricht Workflow ab (Default)

### Approval-Kaskaden

Für kritische Änderungen können mehrere Approvals verkettet werden:

```yaml
phases:
  - id: adr-creation
    type: consultant
    output: [output/ADR-critical.md]

  - id: adr-approval
    type: approval
    approval_type: adr
    input: [output/ADR-critical.md]

  - id: implementation
    type: development
    depends_on: adr-approval
    output: [new/src/critical/*.py]

  - id: code-approval
    type: approval
    approval_type: code
    input: [new/src/critical/*.py]

  - id: security-approval
    type: approval
    approval_type: security
    input: [new/src/critical/*.py]
```

---

## Implementierungsreihenfolge

### Abhängigkeiten zwischen ADR-014 und ADR-015

```
ADR-014 (Docs Architecture)        ADR-015 (Approval System)
         │                                    │
         │                                    │
         ▼                                    ▼
┌─────────────────┐               ┌─────────────────────┐
│ UNABHÄNGIG VON  │               │  UNABHÄNGIG VON     │
│ ADR-015:        │               │  ADR-014:           │
│                 │               │                     │
│ - docs/sources/ │               │ - approvals/        │
│ - templates/    │               │ - completeness.py   │
│ - docs_compiler │               │ - concept_diff.py   │
│                 │               │ - ApprovalRunner    │
└─────────────────┘               └─────────────────────┘
         │                                    │
         └────────────┬───────────────────────┘
                      │
                      ▼
           ┌─────────────────────┐
           │  KANN KOMBINIERT    │
           │  WERDEN:            │
           │                     │
           │  - docs_compiled    │
           │    als Quality Gate │
           │  - docstrings_      │
           │    complete als     │
           │    Approval-Check   │
           └─────────────────────┘
```

### Empfohlene Reihenfolge

**Phase 1: ADR-015 Fundament (Tage 1-3)**
- [ ] `approvals/` Verzeichnisstruktur erstellen
- [ ] `config/adr-completeness-rules.yaml` erstellen
- [ ] `src/helix/adr/completeness.py` implementieren
- [ ] `src/helix/adr/concept_diff.py` implementieren
- [ ] Unit Tests für Layer 2-3

**Phase 2: ADR-015 Sub-Agent (Tage 4-6)**
- [ ] `src/helix/approval/result.py` implementieren
- [ ] `src/helix/approval/runner.py` implementieren
- [ ] `approvals/adr/CLAUDE.md` erstellen
- [ ] `approvals/adr/checks/*.md` erstellen
- [ ] E2E-Test: ADR erstellen → Approval

**Phase 3: Quality Gate Integration (Tage 7-8)**
- [ ] `adr_complete` Gate implementieren
- [ ] `approval` Gate-Type im QualityGateRunner
- [ ] `phases.yaml` Schema erweitern
- [ ] `on_rejection` Handler implementieren

**Phase 4: ADR-014 parallel (Tage 5-10)**
- [ ] `docs/sources/*.yaml` erstellen
- [ ] `docs_compiler.py` implementieren
- [ ] Templates erstellen

**Phase 5: Integration & Test (Tage 9-12)**
- [ ] Alle Quality Gates testen
- [ ] Approval-Workflow durchspielen
- [ ] Dokumentation aktualisieren

---

## Dokumentation

Diese Änderung erfordert neue und aktualisierte Dokumentation:

| Dokument | Aktion | Beschreibung |
|----------|--------|--------------|
| `approvals/README.md` | Erstellen | Übersicht Approval-System |
| `CLAUDE.md` | Aktualisieren | Approval-Workflow beschreiben |
| `skills/helix/SKILL.md` | Aktualisieren | Approval-Tools dokumentieren |
| `docs/ARCHITECTURE-MODULES.md` | Aktualisieren | Approval-Modul dokumentieren |

---

## Akzeptanzkriterien

### 1. Pre-Check Layer (Layer 1-3)

- [ ] `config/adr-completeness-rules.yaml` existiert mit mindestens 5 Regeln
- [ ] `CompletenessValidator` lädt Regeln und prüft ADRs korrekt
- [ ] Regel `major-needs-migration` blockiert ADRs ohne Migration-Section
- [ ] `ConceptDiffer` findet fehlende Sections aus Konzept
- [ ] Unit Tests für alle Validatoren grün

### 2. Sub-Agent Layer (Layer 4)

- [ ] `approvals/adr/` Verzeichnis existiert mit CLAUDE.md und checks/
- [ ] `ApprovalRunner` spawnt Sub-Agent und parst Ergebnis
- [ ] Sub-Agent schreibt valides `approval-result.json`
- [ ] Timeout wird korrekt behandelt
- [ ] E2E-Test: ADR → Approval → Result funktioniert

### 3. Quality Gate Integration

- [ ] `adr_complete` Gate-Type implementiert
- [ ] `approval` Gate-Type implementiert
- [ ] Gates können in `phases.yaml` konfiguriert werden
- [ ] `on_rejection` Handler funktioniert

### 4. Dokumentation

- [ ] `approvals/README.md` dokumentiert alle Approval-Typen
- [ ] CLAUDE.md aktualisiert mit Approval-Workflow
- [ ] Check-Dateien beschreiben alle Prüfkriterien

### 5. Integration

- [ ] ADR-014-Fall würde jetzt erkannt: major ohne Migration → ERROR
- [ ] Kosten pro Approval < $0.30
- [ ] Latenz: Pre-Checks < 1s, Sub-Agent < 60s

---

## Konsequenzen

### Vorteile

1. **Unvoreingenommene Prüfung** - Sub-Agent hat frischen Context
2. **Kontextabhängige Validierung** - major → Migration erforderlich
3. **Konzept-Tracking** - Keine Section geht mehr verloren
4. **Kosteneffizienz** - Early-Exit bei Pre-Check Failure
5. **Tiefgehende Prüfung** - Sub-Agent kann Codebase lesen
6. **Generisches Pattern** - Nicht nur ADRs, auch Code, Docs, Security

### Nachteile / Risiken

1. **Komplexität** - Neues Sub-System mit eigenem Verzeichnis
2. **Kosten** - ~$0.02-0.20 pro Sub-Agent Approval
3. **Latenz** - Sub-Agent braucht 30-60 Sekunden
4. **Maintenance** - Check-Dateien müssen gepflegt werden

### Mitigation

| Risiko | Mitigation |
|--------|------------|
| Kosten | Hybrid-Ansatz: Pre-Checks zuerst, Sub-Agent nur wenn nötig |
| Latenz | Parallele Approvals möglich |
| Komplexität | Klare Verzeichnisstruktur, gute Dokumentation |
| Maintenance | Regeln in YAML, einfach anzupassen |

### Metriken nach Implementation

| Metrik | Ziel | Messung |
|--------|------|---------|
| Approval-Latenz | < 60s | Timer im Runner |
| Approval-Kosten | < $0.30 | Token-Tracking |
| False-Positive-Rate | < 5% | Manuelle Review |
| False-Negative-Rate | < 1% | Post-Deployment Issues |
| ADR-014-Case | 100% erkannt | Regression-Test |

---

## Referenzen

- ADR-002: Phase-Konzept
- ADR-003: Quality Gates
- ADR-012: Claude Runner
- ADR-014: Documentation Architecture (related)
- [Konzept: Sub-Agent Approval](../projects/sessions/subagent-approval/output/subagent-approval.md)
- [Konzept: ADR Completeness](../projects/sessions/adr-completeness/output/adr-completeness.md)
- [Design: Semantic Validation](../projects/sessions/adr-completeness/output/semantic-validation-design.md)

---

*ADR erstellt vom HELIX Meta-Consultant*
*Session: subagent-approval*
