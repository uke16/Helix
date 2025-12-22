# ADR-008: Implementation Spec Schema

**Status:** Superseded by ADR-012  
**Datum:** 2025-12-21  
**Bezug:** ADR-000, ADR-005, ADR-006

---

> **⚠️ SUPERSEDED:** This ADR is superseded by [ADR-012: ADR as Single Source of Truth](012-adr-as-single-source-of-truth.md).  
> spec.yaml is now deprecated. Use ADR with YAML header instead.

## Kontext

Die Implementation Spec ist das zentrale Dokument das vom Consultant erstellt 
wird und alle nachfolgenden Phasen steuert. Das Schema muss klar und validierbar sein.

---

## Entscheidung

### Minimales Spec Schema

```yaml
# spec.yaml - Vollständiges Schema mit Annotationen

# ═══════════════════════════════════════════════════════════════
# META - Projekt-Identifikation
# ═══════════════════════════════════════════════════════════════
meta:
  id: string                    # REQUIRED - Eindeutige ID (kebab-case)
                                # Beispiel: "bom-export-csv-001"
                                
  domain: string                # REQUIRED - Haupt-Domain
                                # Werte: pdm | erp | infrastructure | frontend | backend | helix
                                
  language: string              # OPTIONAL - Haupt-Programmiersprache (auto-detect falls leer)
                                # Werte: python | cpp | go | typescript | rust | markdown
                                
  type: string                  # OPTIONAL - Projekt-Typ (default: feature)
                                # Werte: feature | bugfix | documentation | research | migration
                                
  priority: string              # OPTIONAL - Priorität
                                # Werte: p0 | p1 | p2 | p3
                                
  tags: [string]                # OPTIONAL - Tags für Kategorisierung
                                # Beispiel: ["export", "csv", "legacy-compat"]

# ═══════════════════════════════════════════════════════════════
# IMPLEMENTATION - Was gebaut werden soll
# ═══════════════════════════════════════════════════════════════
implementation:
  summary: string               # REQUIRED - Kurzbeschreibung (1-3 Sätze)
                                # Beispiel: "CSV-Export für BOMs mit Revision-History"
  
  description: string           # OPTIONAL - Ausführliche Beschreibung
                                # Markdown erlaubt
  
  # Zu erstellende Dateien
  files_to_create:              # REQUIRED - Mindestens eine Datei
    - path: string              # REQUIRED - Relativer Pfad
      description: string       # REQUIRED - Was diese Datei macht
      template: string          # OPTIONAL - Template-Referenz
      
  # Zu modifizierende Dateien  
  files_to_modify:              # OPTIONAL
    - path: string              # REQUIRED - Pfad zur bestehenden Datei
      change: string            # REQUIRED - Was geändert werden soll
      
  # Akzeptanzkriterien
  acceptance_criteria:          # REQUIRED - Mindestens ein Kriterium
    - string                    # Präzise, testbare Aussage
                                # Beispiel: "CSV enthält Spalten: ID, Name, Revision"
                                
  # Technische Constraints
  constraints:                  # OPTIONAL
    - string                    # Beispiel: "Muss mit Python 3.10+ laufen"

# ═══════════════════════════════════════════════════════════════
# CONTEXT - Relevante Informationen
# ═══════════════════════════════════════════════════════════════
context:
  relevant_docs:                # OPTIONAL - Referenzierte Dokumentation
    - path: string              # Pfad zu Dok
      relevance: string         # Warum relevant
      
  code_references:              # OPTIONAL - Bestehender Code als Referenz
    - path: string
      relevance: string
      
  dependencies:                 # OPTIONAL - Abhängigkeiten
    - name: string              # Package-Name
      version: string           # Version-Constraint
      reason: string            # Warum gebraucht
      
  external_apis:                # OPTIONAL - Externe APIs
    - name: string
      endpoint: string
      auth_type: string

# ═══════════════════════════════════════════════════════════════
# TESTING - Test-Anforderungen
# ═══════════════════════════════════════════════════════════════
testing:
  unit_tests:                   # OPTIONAL
    required: boolean           # Default: true
    coverage_target: number     # Ziel-Coverage in %
    
  integration_tests:            # OPTIONAL
    required: boolean
    scenarios: [string]         # Test-Szenarien
    
  e2e_tests:                    # OPTIONAL
    required: boolean
    scenarios: [string]

# ═══════════════════════════════════════════════════════════════
# DOCUMENTATION - Doku-Anforderungen
# ═══════════════════════════════════════════════════════════════
documentation:
  required_docs:                # OPTIONAL
    - type: string              # api | user | architecture | readme
      path: string              # Ziel-Pfad
      
  inline_docs:                  # OPTIONAL
    docstrings: boolean         # Default: true
    comments: string            # minimal | standard | verbose
```

### Minimal-Beispiel

```yaml
# Minimale gültige Spec

meta:
  id: "hello-world-001"
  domain: "backend"

implementation:
  summary: "Hello World Endpoint"
  files_to_create:
    - path: "src/hello.py"
      description: "Hello World HTTP Endpoint"
  acceptance_criteria:
    - "GET /hello gibt 'Hello World' zurück"
```

### Vollständiges Beispiel

```yaml
# spec.yaml - BOM Export Feature

meta:
  id: "bom-export-csv-001"
  domain: "pdm"
  language: "python"
  type: "feature"
  priority: "p1"
  tags: ["export", "csv", "bom", "legacy-compat"]

implementation:
  summary: "CSV-Export für BOMs mit Revision-History und SAP-Mapping"
  
  description: |
    Exportiert Stücklisten (BOMs) aus dem PDM-System in CSV-Format.
    Unterstützt:
    - Aktuelle Revision und History
    - SAP-Materialnummern Mapping
    - Konfigurierbare Delimiter (für deutsche Excel-Versionen)
  
  files_to_create:
    - path: "src/exporters/bom_csv.py"
      description: "Hauptmodul mit BOMExporter-Klasse"
    - path: "src/exporters/formatters.py"
      description: "CSV-Formatierung und Encoding"
    - path: "tests/test_bom_csv.py"
      description: "Unit Tests für BOMExporter"
    - path: "tests/fixtures/sample_bom.json"
      description: "Test-Fixture mit Beispiel-BOM"
      
  files_to_modify:
    - path: "src/exporters/__init__.py"
      change: "BOMExporter importieren und exportieren"
      
  acceptance_criteria:
    - "CSV enthält Spalten: ID, Name, Revision, SAP-Nr, Menge, Einheit"
    - "Revision-History ist optional aktivierbar"
    - "Delimiter ist konfigurierbar (default: Semikolon)"
    - "Encoding ist UTF-8 mit BOM für Excel-Kompatibilität"
    - "Unit Tests haben >80% Coverage"
    - "Export von 1000 Positionen < 5 Sekunden"
    
  constraints:
    - "Python 3.10+"
    - "Keine externen Dependencies außer stdlib"
    - "Muss mit bestehendem PDM-Client kompatibel sein"

context:
  relevant_docs:
    - path: "skills/domains/pdm/bom.md"
      relevance: "BOM-Datenstruktur"
    - path: "skills/domains/pdm/revisions.md"
      relevance: "Revisions-System"
      
  code_references:
    - path: "src/pdm/client.py"
      relevance: "PDM API Client"
    - path: "src/exporters/article_csv.py"
      relevance: "Ähnlicher Exporter als Vorlage"
      
  dependencies:
    - name: "typing_extensions"
      version: ">=4.0"
      reason: "Für TypedDict"

testing:
  unit_tests:
    required: true
    coverage_target: 80
  integration_tests:
    required: true
    scenarios:
      - "Export kleine BOM (10 Positionen)"
      - "Export große BOM (1000+ Positionen)"
      - "Export mit Revision-History"

documentation:
  required_docs:
    - type: "api"
      path: "docs/api/bom-exporter.md"
    - type: "user"
      path: "docs/guides/export-bom.md"
  inline_docs:
    docstrings: true
    comments: "standard"
```

### Spec Validator

```python
# spec_validator.py

from dataclasses import dataclass
from pathlib import Path
import yaml
from typing import Optional

@dataclass
class ValidationError:
    field: str
    message: str
    severity: str  # error | warning

@dataclass
class ValidationResult:
    valid: bool
    errors: list[ValidationError]
    warnings: list[ValidationError]

class SpecValidator:
    """Validiert Implementation Specs."""
    
    REQUIRED_FIELDS = {
        "meta.id": str,
        "meta.domain": str,
        "implementation.summary": str,
        "implementation.files_to_create": list,
        "implementation.acceptance_criteria": list,
    }
    
    VALID_DOMAINS = ["pdm", "erp", "infrastructure", "frontend", "backend", "helix"]
    VALID_LANGUAGES = ["python", "cpp", "go", "typescript", "rust", "markdown"]
    VALID_TYPES = ["feature", "bugfix", "documentation", "research", "migration"]
    
    def validate(self, spec_path: Path) -> ValidationResult:
        """Validiert eine Spec-Datei."""
        
        errors = []
        warnings = []
        
        try:
            spec = yaml.safe_load(spec_path.read_text())
        except yaml.YAMLError as e:
            return ValidationResult(
                valid=False,
                errors=[ValidationError("yaml", f"Invalid YAML: {e}", "error")],
                warnings=[]
            )
        
        # Required Fields
        for field, expected_type in self.REQUIRED_FIELDS.items():
            value = self._get_nested(spec, field)
            if value is None:
                errors.append(ValidationError(field, f"Required field missing", "error"))
            elif not isinstance(value, expected_type):
                errors.append(ValidationError(field, f"Expected {expected_type.__name__}", "error"))
        
        # Domain Validation
        domain = self._get_nested(spec, "meta.domain")
        if domain and domain not in self.VALID_DOMAINS:
            warnings.append(ValidationError(
                "meta.domain",
                f"Unknown domain '{domain}'. Valid: {self.VALID_DOMAINS}",
                "warning"
            ))
        
        # Language Validation
        language = self._get_nested(spec, "meta.language")
        if language and language not in self.VALID_LANGUAGES:
            warnings.append(ValidationError(
                "meta.language",
                f"Unknown language '{language}'. Valid: {self.VALID_LANGUAGES}",
                "warning"
            ))
        
        # Files to Create Validation
        files = self._get_nested(spec, "implementation.files_to_create") or []
        for i, file in enumerate(files):
            if not isinstance(file, dict):
                errors.append(ValidationError(
                    f"implementation.files_to_create[{i}]",
                    "Must be object with 'path' and 'description'",
                    "error"
                ))
            elif "path" not in file:
                errors.append(ValidationError(
                    f"implementation.files_to_create[{i}].path",
                    "Required field missing",
                    "error"
                ))
        
        # Acceptance Criteria Validation
        criteria = self._get_nested(spec, "implementation.acceptance_criteria") or []
        if len(criteria) == 0:
            errors.append(ValidationError(
                "implementation.acceptance_criteria",
                "At least one criterion required",
                "error"
            ))
        for i, criterion in enumerate(criteria):
            if not isinstance(criterion, str) or len(criterion) < 10:
                warnings.append(ValidationError(
                    f"implementation.acceptance_criteria[{i}]",
                    "Criterion should be descriptive (>10 chars)",
                    "warning"
                ))
        
        # ID Format
        spec_id = self._get_nested(spec, "meta.id")
        if spec_id and not self._is_valid_id(spec_id):
            errors.append(ValidationError(
                "meta.id",
                "ID must be kebab-case (lowercase, hyphens only)",
                "error"
            ))
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _get_nested(self, d: dict, path: str):
        """Holt verschachtelten Wert."""
        keys = path.split(".")
        for key in keys:
            if isinstance(d, dict) and key in d:
                d = d[key]
            else:
                return None
        return d
    
    def _is_valid_id(self, id_str: str) -> bool:
        """Prüft ob ID gültiges Format hat."""
        import re
        return bool(re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', id_str))


# CLI Usage
def validate_spec(spec_path: str):
    """CLI: Validiert eine Spec."""
    
    validator = SpecValidator()
    result = validator.validate(Path(spec_path))
    
    if result.errors:
        print("❌ ERRORS:")
        for e in result.errors:
            print(f"  • {e.field}: {e.message}")
    
    if result.warnings:
        print("⚠️  WARNINGS:")
        for w in result.warnings:
            print(f"  • {w.field}: {w.message}")
    
    if result.valid:
        print("✅ Spec is valid")
    else:
        print("❌ Spec has errors")
        exit(1)
```

---

## Konsequenzen

### Positiv
- Klares, validiertes Schema
- Flexibel aber strukturiert
- Automatische Sprach-Erkennung möglich
- Maschinenlesbar für Orchestrator

### Negativ
- Consultant muss Schema kennen
- Schema-Evolution muss verwaltet werden

---

## Referenzen

- ADR-000: Vision & Architecture
- ADR-005: Consultant Topologie
- ADR-006: Dynamische Phasen

