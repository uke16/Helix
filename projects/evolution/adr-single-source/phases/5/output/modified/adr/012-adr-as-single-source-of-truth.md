---
adr_id: "012"
title: "ADR als Single Source of Truth für Evolution Workflows"
status: Implemented

component_type: PROCESS
classification: NEW
change_scope: major

files:
  create:
    - adr/001-adr-as-single-source-of-truth.md
  modify:
    - docs/ARCHITECTURE-EVOLUTION.md
    - docs/EVOLUTION-WORKFLOW.md
    - CLAUDE.md
  docs:
    - docs/ARCHITECTURE-EVOLUTION.md
    - skills/helix/evolution/SKILL.md

depends_on: []
---

# ADR-001: ADR als Single Source of Truth für Evolution Workflows

## Status
✅ Implemented

---

## Kontext

### Aktuelles Problem

Der Evolution-Workflow verwendet aktuell mehrere redundante Dateien:

```
Phase 0 (Consultant) Output:
├── spec.yaml      ← Projektbeschreibung
├── phases.yaml    ← Phasen-Definition
└── (kein ADR)
```

**Probleme:**

1. **Redundanz**: spec.yaml enthält Informationen die auch in einem ADR stehen würden:
   - `name` = ADR `title`
   - `description` = ADR `Kontext` + `Entscheidung`
   - `output` = ADR `files.create` + `files.modify`
   - `reference` = ADR `depends_on`

2. **Fehlende Struktur**: spec.yaml hat keine standardisierte Struktur:
   - Keine Akzeptanzkriterien
   - Keine Dokumentations-Anforderungen
   - Keine Status-Verwaltung
   - Keine Klassifikation (component_type, change_scope)

3. **Keine Verification**: Ohne ADR kann das ADR-System nicht verifizieren ob:
   - Alle erwarteten Files erstellt wurden
   - Akzeptanzkriterien erfüllt sind
   - Dokumentation aktualisiert wurde

4. **Inkonsistenz zwischen Phasen**: 
   - phases.yaml definiert `output:` Pfade
   - Templates sagen `output/` Verzeichnis
   - Claude schreibt mal hierhin, mal dorthin

### ADR-086 Template aus HELIX v3

Das bewährte ADR-086 Template definiert bereits alles was wir brauchen:

```yaml
# YAML Header
adr_id: "XXX"
title: "Feature Name"
status: Implemented|Accepted|Implemented
component_type: TOOL|NODE|AGENT|SERVICE|...
classification: NEW|UPDATE|FIX|REFACTOR
change_scope: major|minor|config|docs|hotfix

files:
  create: [...]      # Neue Dateien
  modify: [...]      # Zu ändernde Dateien
  docs: [...]        # Dokumentation

depends_on: [...]    # Abhängigkeiten
```

```markdown
# Markdown Sections
## Kontext           # Warum?
## Entscheidung      # Was?
## Implementation    # Wie? (Code-Beispiele, API-Design)
## Dokumentation     # Welche Docs updaten?
## Akzeptanzkriterien  # Wann ist es fertig?
## Konsequenzen      # Was sind die Auswirkungen?
```

---

## Entscheidung

**ADR wird zur Single Source of Truth für Evolution-Projekte.**

### Neuer Workflow

```
Phase 0 (Consultant):
  Output:
    - ADR-XXX.md      ← SINGLE SOURCE OF TRUTH
    - phases.yaml     ← Generiert/abgeleitet aus ADR
  
  Quality Gate: ADR-System
    → ADR valide?
    → files.create/modify vorhanden?
    → Akzeptanzkriterien definiert?

Phase 1 (Concept):
  Input: ADR
  Output: CONCEPT.md
  
  Quality Gate: File exists

Phase 2-N (Development):
  Input: CONCEPT.md + ADR
  Output: Code gemäß ADR.files
  
  Quality Gate: 
    → Alle Files aus ADR.files.create existieren?
    → Syntax-Check bestanden?
    → Tests bestanden?

Final (Integration):
  Quality Gate:
    → Full test suite
    → ADR.files.docs aktualisiert?
    → Akzeptanzkriterien (alle checked)?
```

### spec.yaml wird abgeschafft

| Vorher (spec.yaml) | Nachher (ADR) |
|-------------------|---------------|
| `name:` | `title:` im YAML Header |
| `description:` | `## Kontext` + `## Entscheidung` |
| `output:` | `files.create:` + `files.modify:` |
| `reference:` | `depends_on:` |
| `components:` | `## Implementation` Section |
| (fehlt) | `## Akzeptanzkriterien` |
| (fehlt) | `files.docs:` |
| (fehlt) | `status:`, `component_type:`, etc. |

### phases.yaml bleibt

phases.yaml definiert die Ausführungsreihenfolge und wird vom Consultant erstellt,
aber die **erwarteten Outputs** kommen aus dem ADR:

```yaml
# phases.yaml
phases:
  - id: "1"
    name: "Concept"
    type: development
    # output: wird aus ADR.files abgeleitet für Quality Gate
    quality_gate:
      type: adr_files_exist
      phase: 1
```

---

## Implementation

### 1. Consultant-Änderung

Der Consultant erstellt künftig:

```
projects/evolution/{name}/
├── ADR-{name}.md     # Single Source of Truth
├── phases.yaml       # Phasen-Definition
└── phases/
    └── ...
```

### 2. ADR-basierte Quality Gates

```python
# src/helix/evolution/verification.py

from helix.adr import ADRParser
from pathlib import Path

class ADRBasedVerification:
    """Verify phase outputs against ADR expectations."""
    
    def __init__(self, adr_path: Path):
        parser = ADRParser()
        self.adr = parser.parse_file(adr_path)
    
    def verify_phase_outputs(self, phase_dir: Path) -> VerificationResult:
        """Check if expected files from ADR exist."""
        missing = []
        
        for file_path in self.adr.metadata.files.create:
            # Check in output/ and direct path
            candidates = [
                phase_dir / "output" / file_path,
                phase_dir / file_path,
            ]
            if not any(p.exists() for p in candidates):
                missing.append(file_path)
        
        return VerificationResult(
            success=len(missing) == 0,
            missing_files=missing,
            expected_files=self.adr.metadata.files.create,
        )
    
    def get_acceptance_status(self) -> dict:
        """Get acceptance criteria completion status."""
        total = len(self.adr.acceptance_criteria)
        checked = sum(1 for c in self.adr.acceptance_criteria if c.checked)
        return {
            "total": total,
            "checked": checked,
            "complete": total == checked,
            "criteria": self.adr.acceptance_criteria,
        }
```

### 3. Template-Anpassung

Templates erhalten ADR-Informationen:

```jinja2
{# templates/developer/_base.md #}

## Expected Output Files

Create these files (from ADR):
{% for file in adr_files_create %}
- `{{ file }}`
{% endfor %}

{% if adr_files_modify %}
Modify these existing files:
{% for file in adr_files_modify %}
- `{{ file }}`
{% endfor %}
{% endif %}
```

---

## Dokumentation

### Zu aktualisierende Dokumente

1. **docs/ARCHITECTURE-EVOLUTION.md**
   - ADR als Single Source of Truth dokumentieren
   - Workflow-Diagramm aktualisieren

2. **docs/EVOLUTION-WORKFLOW.md** (neu)
   - Schritt-für-Schritt Anleitung
   - Quality Gate Beschreibung

3. **CLAUDE.md**
   - Evolution-Section aktualisieren
   - ADR-Erstellung dokumentieren

4. **skills/helix/evolution/SKILL.md** (neu)
   - Best Practices für Evolution-Projekte
   - ADR-Schreiben Anleitung

---

## Akzeptanzkriterien

- [x] Consultant erstellt ADR statt spec.yaml
- [x] ADR-System validiert Consultant-Output
- [x] phases.yaml referenziert ADR für expected files
- [x] Post-Phase Verification nutzt ADR.files
- [x] Templates zeigen erwartete Files aus ADR
- [x] Finale Integration prüft Akzeptanzkriterien
- [x] Dokumentation aktualisiert

---

## Konsequenzen

### Positiv

1. **Single Source of Truth**: Keine Redundanz mehr zwischen spec.yaml und anderen Dateien
2. **Automatische Verification**: ADR-System prüft Vollständigkeit
3. **Akzeptanzkriterien**: Klare Definition wann ein Feature "fertig" ist
4. **Bessere Traceability**: Von Idee → ADR → Code → Docs alles nachvollziehbar
5. **Self-Documentation**: ADR dokumentiert seine eigenen Docs-Anforderungen

### Negativ

1. **Mehr Aufwand für Consultant**: ADR-Format ist strenger als spec.yaml
2. **Migration**: Bestehende Evolution-Projekte müssen angepasst werden

### Neutral

1. phases.yaml bleibt als Ausführungs-Definition
2. CONCEPT.md bleibt als Phase-1 Output

---

## Referenzen

- [ADR-086 Template v2](/home/aiuser01/helix-v3/adr/086-adr-template-v2.md)
- [HELIX v4 ADR-System](src/helix/adr/)
