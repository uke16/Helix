# HELIX v4 Backlog

> Bugs, Technical Debt und offene Aufgaben
>
> Stand: 2025-12-23
> Letzte Session: ADR-014 + ADR-015 Implementation

---

## Kritische Bugs 🔴

### BUG-001: CompletenessValidator findet keine Checkboxen ✅ FIXED

**Datei:** `src/helix/adr/completeness.py`

**Ursprüngliche Diagnose:** Regex `- \[[ x]\]` funktioniert nicht
**Echtes Problem:** `_get_search_text()` gab nur Parent-Section content zurück (leer wenn Sub-Sections existieren)

**Root Cause:**
- Section "Akzeptanzkriterien" hat `content = None` (korrekt!)
- Checkboxen sind in Sub-Sections: "1. Funktionalität", "2. Qualität", etc.
- `_get_search_text()` musste Sub-Sections einschließen

**Fix:** `_get_search_text()` extrahiert jetzt den gesamten Section-Bereich aus raw_content,
inklusive aller Sub-Sections bis zur nächsten gleichwertigen Section.

**Reproduzieren:**
```bash
PYTHONPATH=src python3 -c "
from helix.adr import CompletenessValidator, ADRParser
parser = ADRParser()
adr = parser.parse_file('projects/external/test-e2e-flow/output/ADR-016-string-utils.md')
validator = CompletenessValidator()
result = validator.check(adr)
print([i for i in result.issues if 'acceptance' in str(i).lower()])
"
# Ergebnis: ERROR - Pattern nicht gefunden, obwohl Checkboxen vorhanden
```

**Fix:**
```python
# Korrigierter Regex:
pattern: "- \\[[ x]?\\]"  # Optional: Leerzeichen oder x
# Oder besser:
pattern: "- \\[([ xX])\\]"  # Explicit: Leerzeichen, x, oder X
```

**Priorität:** Hoch - blockiert adr_complete Gate
**Aufwand:** 15 min

---

### BUG-002: ADR Section-Content-Detection meldet 0 chars ✅ FIXED (via BUG-001)

**Datei:** `src/helix/tools/adr_tool.py`

**Problem:**
```
$ python -m helix.tools.adr_tool validate ADR-016.md
⚠️ Section has minimal content (0 chars): ## Kontext
⚠️ Section has minimal content (0 chars): ## Entscheidung
```

Die Sections haben aber 500+ Zeichen Inhalt!

**Ursache:** 
Der Parser extrahiert Section-Content falsch. Vermutlich:
- Nur erste Zeile nach Header wird gezählt
- Oder: Nested Headers (###) werden als Section-Ende interpretiert

**Reproduzieren:**
```bash
PYTHONPATH=src python3 -m helix.tools.adr_tool validate \
  projects/external/test-e2e-flow/output/ADR-016-string-utils.md
```

**Fix:**
Section-Extraktion in `_extract_sections()` debuggen und fixen.

**Priorität:** Hoch - False Positives verwirren
**Aufwand:** 1-2 Stunden

---

### BUG-003: ADR-Parser Classification Enum unvollständig

**Datei:** `src/helix/adr/parser.py`

**Problem:**
```python
class Classification(Enum):
    NEW = "NEW"
    UPDATE = "UPDATE"
    FIX = "FIX"
    REFACTOR = "REFACTOR"
    DEPRECATE = "DEPRECATE"
    # FEHLT: ENHANCEMENT
```

Test-ADRs mit `classification: ENHANCEMENT` schlagen fehl:
```
ValueError: 'ENHANCEMENT' is not a valid Classification
```

**Reproduzieren:**
```bash
PYTHONPATH=src python3 -m pytest tests/test_e2e_approval.py -v -k "minimal"
# Schlägt fehl wegen ENHANCEMENT
```

**Fix:**
```python
class Classification(Enum):
    NEW = "NEW"
    ENHANCEMENT = "ENHANCEMENT"  # Hinzufügen
    UPDATE = "UPDATE"
    FIX = "FIX"
    REFACTOR = "REFACTOR"
    DEPRECATE = "DEPRECATE"
```

**Priorität:** Mittel - Tests schlagen fehl
**Aufwand:** 5 min

---

## Mittlere Probleme 🟡

### DEBT-001: Sub-Agent Approval wird nie aufgerufen

**Dateien:**
- `src/helix/approval/runner.py` - Code existiert
- `src/helix/gates/adr_complete.py` - Ruft Approval auf
- `src/helix/gates/approval.py` - Generic Approval Gate

**Problem:**
Der ApprovalRunner und das Approval-System sind implementiert, aber:
1. Kein Orchestrator ruft `check_adr_complete()` mit `semantic=true` auf
2. Kein `type: approval` Phase-Type im Workflow
3. Manueller Review durch mich (Claude Opus) war nötig

**Was fehlt:**
```yaml
# In einem echten phases.yaml sollte stehen:
phases:
  - id: adr-review
    type: approval
    approval_type: adr
    input: [output/ADR-*.md]
```

Aber: Es gibt keinen Orchestrator der das interpretiert!

**Siehe:** FEATURE-001 (Phase Orchestrator)

**Priorität:** Hoch - Kernfeature nicht nutzbar
**Aufwand:** Teil von Phase Orchestrator

---

### DEBT-002: Integration nach Phasen nicht automatisiert

**Problem:**
Nach jeder Claude Code CLI Phase musste ich manuell:
```bash
cp -r projects/external/impl-*/output/* ziel/
git add -A && git commit
```

**Was existiert:**
- `scripts/migrate-docs.py` - Nur für Docs
- Kein generisches Integrations-Tool

**Was fehlt:**
```python
# src/helix/integration.py
class PhaseIntegrator:
    def integrate(self, phase_output: Path, target: Path):
        """Kopiert Phase-Output ins Hauptprojekt."""
        # 1. Validiere Output
        # 2. Erstelle Backup
        # 3. Kopiere Dateien
        # 4. Update imports
        # 5. Run tests
```

**Priorität:** Mittel
**Aufwand:** 1-2 Tage

---

### DEBT-003: Pre-Commit Hook regeneriert nicht automatisch

**Datei:** `scripts/pre-commit-docs`

**Problem:**
```bash
$ git commit -m "..."
[docs] Documentation validation failed!
Run: python3 -m helix.tools.docs_compiler validate
```

Der Hook blockiert, aber regeneriert nicht automatisch.
User muss manuell `docs_compiler compile` ausführen.

**Gewünschtes Verhalten:**
```bash
$ git commit -m "..."
[docs] Documentation sources changed
[docs] Regenerating CLAUDE.md, SKILL.md...
[docs] ✅ Documentation updated
[docs] Adding regenerated files to commit...
# Commit geht durch
```

**Fix:**
```bash
# In pre-commit-docs:
if ! validate_docs; then
    echo "Regenerating..."
    python3 -m helix.tools.docs_compiler compile
    git add CLAUDE.md skills/helix/SKILL.md
fi
```

**Priorität:** Niedrig - Workaround existiert
**Aufwand:** 30 min

---

### DEBT-004: Template erzeugt zu viele Leerzeilen

**Datei:** `docs/templates/CLAUDE.md.j2`

**Problem:**
Generierte CLAUDE.md hat 142 extra Leerzeilen wegen Jinja2 Whitespace.

**Ursache:**
```jinja2
{% for gate in quality_gates.gates %}

| `{{ gate.id }}` | {{ gate.description }} |

{% endfor %}
```

Jede Zeile hat Newlines vor und nach.

**Fix:**
```jinja2
{% for gate in quality_gates.gates -%}
| `{{ gate.id }}` | {{ gate.description }} |
{% endfor %}
```

Das `-` nach `%` entfernt Whitespace.

**Priorität:** Niedrig - Kosmetisch
**Aufwand:** 30 min

---

### DEBT-005: Sprach-Mix DE/EN in Templates

**Problem:**
- YAML Sources: Deutsch (`Prüft ob Dateien existieren`)
- Templates: Englisch (`Checks if files exist`)
- Generierte Docs: Gemischt

**Entscheidung nötig:**
- Option A: Alles Deutsch (Zielgruppe: FRABA intern)
- Option B: Alles Englisch (Open Source ready)
- Option C: Hybrid (DE für User-facing, EN für Code)

**Empfehlung:** Option C - Wie jetzt, aber konsistent

**Priorität:** Niedrig
**Aufwand:** 2-3 Stunden

---

## Fehlende Features 🟢

### FEATURE-001: Phase Orchestrator

**Status:** Nicht implementiert

**Was es tun soll:**
```python
# src/helix/orchestrator.py
class PhaseOrchestrator:
    async def run_project(self, project_dir: Path):
        """Führt komplettes Projekt autonom aus."""
        phases = self.load_phases(project_dir / "phases.yaml")
        
        for phase in phases:
            # 1. Spawne Claude Code CLI
            result = await self.run_phase(phase)
            
            # 2. Quality Gates prüfen
            gate_result = await self.check_gates(phase, result)
            
            # 3. Bei Failure: Retry oder Escalate
            if not gate_result.passed:
                action = await self.handle_rejection(phase, gate_result)
                if action == "retry":
                    continue
                elif action == "escalate":
                    await self.escalate(phase)
                    break
            
            # 4. Bei Success: Integrieren
            await self.integrate(phase)
        
        # 5. Finalisieren
        await self.finalize_project()
```

**Warum wichtig:**
Aktuell bin ICH (Claude Opus) der Orchestrator. Ich:
- Starte Claude Code CLI manuell
- Warte und polle
- Reviewe Output
- Kopiere Dateien
- Committe

Das sollte HELIX automatisch machen.

**Abhängigkeiten:**
- BUG-001, BUG-002, BUG-003 sollten zuerst gefixt werden
- DEBT-001 (Approval) wird Teil davon

**Aufwand:** 3-5 Tage

---

### FEATURE-002: HELIX CLI

**Status:** Nicht implementiert

**Gewünschte Commands:**
```bash
# Projekt erstellen
helix project create feature-x --template standard

# Projekt ausführen (alle Phasen)
helix project run feature-x

# Status prüfen
helix project status feature-x

# Einzelne Phase ausführen
helix phase run feature-x consultant

# Quality Gates manuell prüfen
helix gate check feature-x adr_complete

# Docs regenerieren
helix docs compile
helix docs validate
```

**Was existiert:**
- `python -m helix.tools.adr_tool` - ADR Tool
- `python -m helix.tools.docs_compiler` - Docs
- `python -m helix.quality_gates` - Gates (teilweise)

**Was fehlt:**
- Unified CLI (`helix` command)
- Project management commands
- Phase execution commands

**Aufwand:** 2-3 Tage

---

### FEATURE-003: Projekt-Templates

**Status:** Nicht implementiert

**Idee:**
```bash
helix project create my-feature --template adr-only
helix project create my-feature --template full-dev
helix project create my-feature --template docs-update
```

**Templates definieren:**
```yaml
# templates/adr-only.yaml
phases:
  - id: consultant
    type: consultant
    output: [output/ADR-*.md]
    
  - id: review
    type: approval
    approval_type: adr
```

```yaml
# templates/full-dev.yaml
phases:
  - id: consultant
    type: consultant
  - id: development
    type: development
  - id: testing
    type: testing
  - id: review
    type: approval
  - id: integration
    type: integration
```

**Aufwand:** 1 Tag

---

## Test-Schulden

### TEST-001: E2E Approval Tests mocken alles

**Datei:** `tests/test_e2e_approval.py`

**Problem:**
```python
# Alle Tests mocken den ApprovalRunner
@patch('helix.approval.runner.ApprovalRunner')
def test_approval_flow(mock_runner):
    mock_runner.return_value.run.return_value = ApprovalResult(...)
```

Es gibt keinen echten E2E Test der:
1. Echten Sub-Agent spawnt
2. Echte Claude Code CLI ausführt
3. Echtes Ergebnis prüft

**Grund:** Kosten und Zeit

**Lösung:**
- Separates `tests/integration/` Verzeichnis
- Marker: `@pytest.mark.integration`
- Nur in CI mit Flag: `pytest -m integration`

**Priorität:** Niedrig
**Aufwand:** 1 Tag

---

### TEST-002: CompletenessValidator Tests fehlen

**Datei:** `tests/test_completeness.py` - EXISTIERT NICHT

**Was getestet werden sollte:**
```python
def test_major_needs_migration_triggered():
    """major + keine Migration = ERROR"""

def test_major_needs_migration_not_triggered():
    """minor = Regel nicht aktiv"""

def test_regex_patterns():
    """Alle Regex-Patterns funktionieren"""

def test_yaml_loading():
    """Rules werden korrekt geladen"""
```

**Priorität:** Mittel
**Aufwand:** 2-3 Stunden

---

## Dokumentations-Schulden

### DOCS-001: SKILL.md zu lang

**Datei:** `skills/helix/SKILL.md`

**Problem:**
- Aktuell: 1080 Zeilen
- Budget: 600 Zeilen
- Wird immer in Context geladen → Token-Verschwendung

**Lösung:**
- Aufteilen in Sub-Skills
- `skills/helix/SKILL.md` → Übersicht (300 Zeilen)
- `skills/helix/adr/SKILL.md` → ADR Details
- `skills/helix/gates/SKILL.md` → Quality Gate Details
- `skills/helix/workflow/SKILL.md` → Workflow Details

**Priorität:** Mittel
**Aufwand:** 1 Tag

---

### DOCS-002: Architecture Decision Records Index

**Datei:** `adr/INDEX.md`

**Problem:**
ADR-Index ist manuell gepflegt und nicht aktuell.

**Lösung:**
```bash
# Automatisch generieren:
python -m helix.tools.adr_tool index > adr/INDEX.md
```

Oder: In docs_compiler integrieren.

**Priorität:** Niedrig
**Aufwand:** 1 Stunde

---

## Priorisierte Reihenfolge

### Sprint 1: Bug Fixes (1 Tag)

1. BUG-003: Classification Enum (5 min)
2. BUG-001: Checkbox Regex (15 min)
3. BUG-002: Section-Content-Detection (2 Stunden)
4. DEBT-004: Template Leerzeilen (30 min)

### Sprint 2: Core Features (1 Woche)

1. FEATURE-001: Phase Orchestrator (3-5 Tage)
2. DEBT-001: Approval Integration (Teil von Orchestrator)
3. DEBT-002: Auto-Integration (Teil von Orchestrator)

### Sprint 3: Polish (1 Woche)

1. FEATURE-002: HELIX CLI (2-3 Tage)
2. FEATURE-003: Projekt-Templates (1 Tag)
3. TEST-002: Completeness Tests (3 Stunden)
4. DOCS-001: SKILL.md aufteilen (1 Tag)

---

## Changelog

| Datum | Änderung |
|-------|----------|
| 2025-12-23 | Initial Backlog nach ADR-014/015 Session |

