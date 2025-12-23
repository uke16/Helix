# HELIX Dokumentations-Strategie

> **Meta-Consultant Analyse und Empfehlungen**
>
> Erstellt: 2025-12-23

---

## 1. Analyse des Status Quo

### 1.1 Aktuelle Dokumentations-Landschaft

| Kategorie | Anzahl | Zeilen | Probleme |
|-----------|--------|--------|----------|
| **docs/*.md** | 18 | ~3000 | Überlappungen, keine klare Hierarchie |
| **adr/*.md** | 15 | ~2000 | Gut strukturiert, aber wachsend |
| **skills/**/SKILL.md** | 9 | ~1500 | Inkonsistente Tiefe |
| **CLAUDE.md (Root)** | 1 | 377 | Zu lang für "immer geladen" |
| **templates/*.md** | ~10 | ~500 | OK, spezifisch |
| **Sonstige** | ~100+ | ~25000 | Sessions, Projekte (ephemer) |
| **GESAMT** | ~150 | ~32000 | **~80.000 Tokens potentiell** |

### 1.2 Identifizierte Probleme

#### Problem 1: Context Window Überlastung

```
AKTUELL:
┌─────────────────────────────────────────────────────┐
│  Claude Code lädt:                                   │
│  - Root CLAUDE.md (~377 Zeilen = ~2000 Tokens)      │
│  - Kein Lazy Loading definiert                       │
│  - Skills werden "nach Bedarf" geladen (unklar wie) │
└─────────────────────────────────────────────────────┘

RISIKO:
- Bei komplexen Tasks: 5+ Skills × ~400 Zeilen = 8000+ Tokens nur für Context
- + ADRs für Architektur-Verständnis = 2000+ Tokens
- + Projekt-spezifische Docs = unbegrenzt
→ Context Window wird schnell knapp
```

#### Problem 2: Redundanz und Inkonsistenz

```
BEISPIEL: ADR-Validierung ist dokumentiert in:

1. CLAUDE.md (Root)
   → Section "Quality Gates Reference" (Zeile 65-125)

2. docs/ADR-TEMPLATE.md
   → Template Details

3. skills/helix/adr/SKILL.md
   → Vollständige Anleitung (~400 Zeilen)

4. adr/INDEX.md
   → Nochmal Template-Beispiel

PROBLEM:
- 4 Stellen, die synchron gehalten werden müssen
- Widersprüche entstehen bei Updates
- Claude Code liest möglicherweise veraltete Version
```

#### Problem 3: Kein Lifecycle Management

```
SZENARIO: Feature X wird entfernt

AKTUELL:
1. Code wird gelöscht ✓
2. Doku in docs/*.md wird vielleicht aktualisiert ?
3. Skills vergessen ✗
4. CLAUDE.md Referenzen bleiben ✗
5. ADRs als "Superseded" markieren vergessen ✗

→ "Zombie-Dokumentation" entsteht
```

#### Problem 4: Fehlende Ownership

```
FRAGEN ohne Antwort:
- Wer ist verantwortlich für docs/QUICKSTART.md?
- Welches Feature "besitzt" welche Doku-Stellen?
- Wie findet man alle Stellen die zu Feature X gehören?
```

---

## 2. Vorgeschlagene Dokumentations-Hierarchie

### 2.1 Drei-Schichten-Modell

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1: KERN (immer geladen)                                  │
│  Token-Budget: ~1500 Tokens (= ~300 Zeilen)                     │
├─────────────────────────────────────────────────────────────────┤
│  • CLAUDE.md (Kurzversion)                                      │
│    - Rollen-Erkennung (5 Zeilen)                                │
│    - Wichtigste DO/DON'T (10 Zeilen)                            │
│    - Pointer zu Layer 2 ("Lies X wenn du Y tust")               │
│    - Projekt-Struktur (10 Zeilen)                               │
│                                                                  │
│  MAXIMAL 300 Zeilen, keine Code-Beispiele, keine Details!       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 2: DOMAIN (lazy loaded, bei Bedarf)                      │
│  Token-Budget: ~3000 Tokens pro Skill (= ~600 Zeilen)           │
├─────────────────────────────────────────────────────────────────┤
│  skills/helix/SKILL.md      ← Wenn HELIX-Arbeit                 │
│  skills/helix/adr/SKILL.md  ← Wenn ADR-Erstellung               │
│  skills/pdm/SKILL.md        ← Wenn PDM-Arbeit                   │
│  skills/encoder/SKILL.md    ← Wenn Encoder-Arbeit               │
│                                                                  │
│  REGEL: Max 2-3 Skills pro Phase laden!                         │
│  JEDER Skill hat max 600 Zeilen.                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 3: REFERENZ (nur explizit angefordert)                   │
│  Token-Budget: Unbegrenzt, aber selten geladen                  │
├─────────────────────────────────────────────────────────────────┤
│  docs/ARCHITECTURE-MODULES.md  ← Bei tiefer Code-Arbeit         │
│  docs/ADR-TEMPLATE.md          ← Nur bei ADR-Erstellung         │
│  adr/XXX-*.md                  ← Nur bei spezifischer Frage     │
│  docs/USER-GUIDE.md            ← Für End-User, nicht Claude     │
│                                                                  │
│  NICHT von CLAUDE.md referenziert!                              │
│  Skills referenzieren diese Dateien.                            │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Token-Budget-Übersicht

| Layer | Max pro Datei | Typische Nutzung | Token-Budget |
|-------|---------------|------------------|--------------|
| **1: Kern** | 300 Zeilen | Immer | ~1500 Tokens |
| **2: Domain** | 600 Zeilen | 2-3 Skills/Phase | ~6000 Tokens |
| **3: Referenz** | Unbegrenzt | 0-1/Phase | ~2000 Tokens |
| **GESAMT** | - | Pro Phase | **~10.000 Tokens** |

### 2.3 Konkrete Struktur

```
helix-v4/
├── CLAUDE.md                     # Layer 1: Kurzversion (~300 Zeilen)
│
├── skills/                       # Layer 2: Domain-Wissen
│   ├── helix/
│   │   ├── SKILL.md             # HELIX Grundlagen (~400 Zeilen)
│   │   └── adr/
│   │       └── SKILL.md         # ADR-Erstellung (~400 Zeilen)
│   ├── pdm/
│   │   └── SKILL.md             # PDM Wissen (~600 Zeilen)
│   ├── encoder/
│   │   └── SKILL.md             # Encoder Produkte (~600 Zeilen)
│   └── infrastructure/
│       └── SKILL.md             # Docker, DB (~600 Zeilen)
│
├── docs/                         # Layer 3: Referenz
│   ├── ARCHITECTURE-MODULES.md  # Modul-Details (unbegrenzt)
│   ├── ADR-TEMPLATE.md          # Template (unbegrenzt)
│   ├── USER-GUIDE.md            # Für Menschen
│   └── ...
│
└── adr/                          # Layer 3: Architektur-Historie
    ├── INDEX.md                 # Übersicht
    └── XXX-*.md                 # Einzelne Entscheidungen
```

---

## 3. Single Source of Truth

### 3.1 Das Ownership-Modell

```
┌────────────────────────────────────────────────────────────────┐
│  JEDES Feature hat EINEN Ownership-Punkt                       │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Architektur-Entscheidungen → ADR (im adr/ Ordner)             │
│  Domain-Wissen             → Skill (im skills/ Ordner)         │
│  API-Referenz              → Docstrings (im Code)              │
│  User-Dokumentation        → docs/ (für Menschen)              │
│  Claude-Anweisungen        → CLAUDE.md (nur Pointer!)          │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

### 3.2 Referenzierungs-Regeln

```yaml
# ERLAUBT: Pointer von oben nach unten

CLAUDE.md:
  - "Für ADRs lies: skills/helix/adr/SKILL.md"
  - "Für PDM lies: skills/pdm/SKILL.md"

Skills:
  - "Details siehe: docs/ARCHITECTURE-MODULES.md"
  - "Template: docs/ADR-TEMPLATE.md"

# VERBOTEN: Inhalt duplizieren

CLAUDE.md:
  ✗ Kopiert ADR-Template Details
  ✗ Erklärt Quality Gates ausführlich
  ✗ Enthält Code-Beispiele die auch in Skills sind
```

### 3.3 Master-Index

Neues File: `docs/DOC-INDEX.md`

```markdown
# HELIX Dokumentations-Index

## Wo finde ich was?

| Thema | Source of Truth | Pointer in |
|-------|-----------------|------------|
| ADR-Erstellung | skills/helix/adr/SKILL.md | CLAUDE.md |
| Quality Gates | src/helix/quality_gates.py (Docstrings) | CLAUDE.md |
| Projekt-Struktur | CLAUDE.md | - |
| Evolution System | adr/012-*.md | skills/helix/SKILL.md |
| PDM Domain | skills/pdm/SKILL.md | CLAUDE.md |

## Feature → Doku Mapping

| Feature | ADR | Skill | Docs | Code |
|---------|-----|-------|------|------|
| ADR System | 012 | helix/adr | ADR-TEMPLATE.md | src/helix/adr/ |
| Evolution | - | helix | EVOLUTION-CONCEPT.md | src/helix/evolution/ |
| Quality Gates | 002 | helix | CLAUDE.md | src/helix/quality_gates.py |
```

---

## 4. Konsistenz-Regeln

### 4.1 Die "Änderung dokumentiert sich selbst" Regel

```
BEI JEDER CODE-ÄNDERUNG:

1. Ist dies eine Architektur-Entscheidung? → ADR erstellen/updaten
2. Ändert sich Domain-Wissen? → Skill updaten
3. Ändert sich das öffentliche API? → Docstrings updaten
4. Ändert sich der Workflow? → CLAUDE.md Pointer prüfen
```

### 4.2 Invalidierungs-Kette

Wenn ein Feature entfernt wird:

```
1. Code löschen
   │
   ├─→ 2. ADR auf "Superseded" setzen
   │      └─→ Neues ADR mit "supersedes: XXX"
   │
   ├─→ 3. Skill-Section entfernen
   │      └─→ Suche: grep -r "feature_name" skills/
   │
   ├─→ 4. CLAUDE.md Pointer prüfen
   │      └─→ Pointer entfernen wenn Skill weg
   │
   └─→ 5. docs/*.md prüfen
          └─→ Verwaiste Referenzen finden
```

### 4.3 Cross-Reference Format

Um Referenzen automatisch prüfbar zu machen:

```markdown
# In CLAUDE.md
→ **Lies:** [skills/helix/adr/SKILL.md](skills/helix/adr/SKILL.md)

# In Skills
→ **Details:** [docs/ARCHITECTURE-MODULES.md](../../../docs/ARCHITECTURE-MODULES.md)

# Format
[display_text](relative_path) ← IMMER relativer Pfad!
```

---

## 5. Lifecycle-Prozesse

### 5.1 Feature hinzufügen

```
┌─────────────────────────────────────────────────────────────┐
│  1. CONCEPT.md erstellen mit Dokumentations-Section         │
│     → Listet alle zu erstellenden Doku-Stellen              │
│                                                              │
│  2. phases.yaml mit Documentation-Phase                     │
│     → Quality Gate prüft Existenz aller Doku-Dateien        │
│                                                              │
│  3. Implementation                                           │
│     → Docstrings im Code                                    │
│     → ADR wenn Architektur-Entscheidung                     │
│                                                              │
│  4. Documentation-Phase                                      │
│     → Skill erstellen/erweitern                             │
│     → docs/*.md wenn nötig                                  │
│     → DOC-INDEX.md aktualisieren                            │
│                                                              │
│  5. Quality Gate: docs_valid                                 │
│     → Prüft alle referenzierten Dateien existieren          │
│     → Prüft Token-Budget eingehalten                        │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Feature entfernen

```
┌─────────────────────────────────────────────────────────────┐
│  1. docs/DOC-INDEX.md konsultieren                          │
│     → Alle zugehörigen Doku-Stellen identifizieren          │
│                                                              │
│  2. ADR als "Superseded" markieren                          │
│     → Neues ADR: "Removes Feature X"                        │
│                                                              │
│  3. Skill-Sections entfernen                                │
│     → grep -r "feature_name" skills/                        │
│                                                              │
│  4. CLAUDE.md Pointer entfernen                             │
│     → Wenn Skill-Section weg, Pointer weg                   │
│                                                              │
│  5. docs/*.md aufräumen                                     │
│     → Referenzen zu Feature entfernen                       │
│                                                              │
│  6. DOC-INDEX.md aktualisieren                              │
│     → Feature-Zeile entfernen                               │
│                                                              │
│  7. docs_audit.py ausführen                                 │
│     → Verwaiste Referenzen finden                           │
└─────────────────────────────────────────────────────────────┘
```

### 5.3 Feature ändern

```
┌─────────────────────────────────────────────────────────────┐
│  1. Ist es eine Breaking Change?                            │
│     JA  → Neues ADR erstellen                               │
│     NEIN → Bestehendes ADR/Skill updaten                    │
│                                                              │
│  2. DOC-INDEX.md konsultieren                               │
│     → Alle betroffenen Stellen identifizieren               │
│                                                              │
│  3. Änderungen durchführen (atomisch!)                      │
│     → Code + Doku in einem Commit                           │
│                                                              │
│  4. docs_validate.py ausführen                              │
│     → Konsistenz prüfen                                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Tooling-Vorschläge

### 6.1 docs_validate.py

**Zweck:** Prüft Dokumentations-Konsistenz

```python
"""
helix/tools/docs_validate.py

Usage:
    python -m helix.tools.docs_validate

Checks:
1. Alle Markdown-Links zeigen auf existierende Dateien
2. Token-Budgets werden eingehalten (Layer 1: 300, Layer 2: 600)
3. Keine Duplikate in verschiedenen Dateien
4. Jedes Feature im DOC-INDEX.md hat alle Spalten gefüllt
"""

from pathlib import Path
import re

def validate_links(md_file: Path) -> list[str]:
    """Prüft alle [text](link) auf Existenz."""
    errors = []
    content = md_file.read_text()
    links = re.findall(r'\[.*?\]\((.*?)\)', content)
    for link in links:
        if link.startswith('http'):
            continue  # Externe Links ignorieren
        target = md_file.parent / link
        if not target.exists():
            errors.append(f"{md_file}: Broken link → {link}")
    return errors

def check_token_budget(md_file: Path, max_lines: int) -> str | None:
    """Prüft ob Datei Token-Budget einhält."""
    lines = len(md_file.read_text().splitlines())
    if lines > max_lines:
        return f"{md_file}: {lines} lines > {max_lines} budget"
    return None

def main():
    root = Path(".")

    # Layer 1 Budget
    claude_md = root / "CLAUDE.md"
    if claude_md.exists():
        result = check_token_budget(claude_md, 300)
        if result:
            print(f"WARNING: {result}")

    # Layer 2 Budget
    for skill in root.glob("skills/**/SKILL.md"):
        result = check_token_budget(skill, 600)
        if result:
            print(f"WARNING: {result}")

    # Link Validation
    for md_file in root.glob("**/*.md"):
        for error in validate_links(md_file):
            print(f"ERROR: {error}")
```

### 6.2 docs_audit.py

**Zweck:** Findet verwaiste Referenzen und Inkonsistenzen

```python
"""
helix/tools/docs_audit.py

Usage:
    python -m helix.tools.docs_audit

Checks:
1. Dateien die in DOC-INDEX.md aber nicht auf Disk existieren
2. Skills die kein Feature mehr referenziert
3. ADRs die auf "Accepted" aber Feature existiert nicht mehr
4. Code-Dateien ohne Docstrings
"""

from pathlib import Path
import ast

def find_orphaned_skills(doc_index: Path, skills_dir: Path) -> list[str]:
    """Findet Skills die nicht im Index referenziert werden."""
    # Implementation...
    pass

def find_missing_docstrings(src_dir: Path) -> list[str]:
    """Findet Python-Dateien ohne Modul-Docstring."""
    issues = []
    for py_file in src_dir.glob("**/*.py"):
        if py_file.name.startswith("_"):
            continue
        try:
            tree = ast.parse(py_file.read_text())
            if not ast.get_docstring(tree):
                issues.append(f"{py_file}: Missing module docstring")
        except SyntaxError:
            pass
    return issues
```

### 6.3 docs_index.py

**Zweck:** Generiert/aktualisiert den Master-Index

```python
"""
helix/tools/docs_index.py

Usage:
    python -m helix.tools.docs_index rebuild

Generates:
- docs/DOC-INDEX.md from:
  - Existing ADRs
  - Existing Skills
  - src/helix/ module structure
"""

from pathlib import Path
from helix.adr import ADRParser

def rebuild_index():
    """Baut DOC-INDEX.md neu auf."""
    root = Path(".")

    # Sammle alle ADRs
    adrs = []
    for adr_file in (root / "adr").glob("*.md"):
        if adr_file.name == "INDEX.md":
            continue
        parser = ADRParser()
        adr = parser.parse_file(adr_file)
        adrs.append({
            "id": adr.metadata.adr_id,
            "title": adr.metadata.title,
            "status": adr.metadata.status,
            "files": adr.metadata.files,
        })

    # Sammle alle Skills
    skills = list(root.glob("skills/**/SKILL.md"))

    # Generiere Markdown
    # ...
```

### 6.4 Quality Gate: docs_valid

```yaml
# Neuer Quality Gate Typ für phases.yaml

quality_gate:
  type: docs_valid
  checks:
    - links_valid: true        # Alle Links prüfen
    - budget_respected: true   # Token-Budgets
    - index_updated: true      # DOC-INDEX.md aktuell
```

---

## 7. Empfohlene nächste Schritte

### Sofort umsetzbar (1-2 Tage)

| Nr | Aktion | Aufwand | Impact |
|----|--------|---------|--------|
| 1 | **CLAUDE.md kürzen** auf 300 Zeilen | 2h | Hoch |
| 2 | **docs/DOC-INDEX.md erstellen** | 1h | Hoch |
| 3 | **docs_validate.py implementieren** | 3h | Mittel |

### Kurzfristig (1 Woche)

| Nr | Aktion | Aufwand | Impact |
|----|--------|---------|--------|
| 4 | Skills auf 600 Zeilen Limit kürzen | 4h | Mittel |
| 5 | Duplikate zwischen CLAUDE.md und Skills entfernen | 2h | Hoch |
| 6 | Cross-Reference Format einführen | 2h | Mittel |

### Mittelfristig (2-4 Wochen)

| Nr | Aktion | Aufwand | Impact |
|----|--------|---------|--------|
| 7 | docs_audit.py implementieren | 4h | Mittel |
| 8 | docs_index.py implementieren | 4h | Mittel |
| 9 | Quality Gate `docs_valid` implementieren | 3h | Hoch |
| 10 | Alle phases.yaml mit Documentation-Phase versehen | 2h | Hoch |

### Langfristig (Continuous)

- **Doku-Audit** als regelmäßiges Projekt (monatlich)
- **Token-Budget Monitoring** in Observability integrieren
- **Automatische Invalidierung** bei Feature-Removal

---

## 8. CLAUDE.md Kurzversion (Vorschlag)

Hier ein konkreter Vorschlag für die gekürzte CLAUDE.md:

```markdown
# HELIX v4 - Claude Code Instruktionen

> Du arbeitest im HELIX v4 Projekt - einem AI Development Orchestration System.

## Deine Rolle

1. **Consultant** - Meeting mit User → spec.yaml, phases.yaml
2. **Developer** - Implementierung nach Spezifikation
3. **Reviewer** - Code-Review
4. **Documentation** - Technische Dokumentation

### Rolle erkennen

Schau in deinem Arbeitsverzeichnis:
- `CLAUDE.md` - Spezifische Anweisungen
- `input/` - Input-Dateien
- `output/` - Hier schreibst du

## Domain-Wissen laden

| Wenn du... | Lies: |
|------------|-------|
| HELIX verstehen willst | skills/helix/SKILL.md |
| ADRs erstellen musst | skills/helix/adr/SKILL.md |
| Mit PDM arbeitest | skills/pdm/SKILL.md |
| Encoder-Produkte brauchst | skills/encoder/SKILL.md |

## Wichtigste Regeln

### DO:
- Lies relevante Skills vor der Arbeit
- Schreibe nach output/
- Dokumentiere was du getan hast

### DON'T:
- Ändere keine Dateien außerhalb deines Verzeichnisses
- Lösche keine existierenden Dateien
- Mache keine Netzwerk-Requests ohne Grund

## Projekt-Struktur

```
helix-v4/
├── src/helix/        # Python Orchestrator
├── skills/           # Domain-Wissen
├── adr/              # Architektur-Entscheidungen
├── projects/
│   ├── sessions/     # Consultant Sessions
│   └── external/     # Ausführbare Projekte
└── docs/             # Referenz-Dokumentation
```

## Quality Gates

Dein Output wird validiert:
- `files_exist` - Dateien vorhanden?
- `syntax_check` - Code syntaktisch korrekt?
- `adr_valid` - ADR-Format korrekt?

→ Details: skills/helix/SKILL.md

## Hilfe

- HELIX Konzept: ONBOARDING.md
- Architektur: docs/ARCHITECTURE-MODULES.md
- ADR Template: docs/ADR-TEMPLATE.md
```

**Zeilenzahl: ~80 Zeilen** (statt 377)

---

## 9. Zusammenfassung

### Das Problem

- 150+ Markdown-Dateien mit 32.000 Zeilen
- Keine klare Hierarchie für Context Loading
- Redundanzen führen zu Inkonsistenzen
- Kein Lifecycle Management für Dokumentation

### Die Lösung

1. **Drei-Schichten-Modell** mit Token-Budgets
2. **Single Source of Truth** pro Feature-Typ
3. **DOC-INDEX.md** als Master-Referenz
4. **Tooling** für Validierung und Audit
5. **Lifecycle-Prozesse** für Add/Remove/Change

### Der Gewinn

- Claude Code lädt nur ~10.000 Tokens Context statt potentiell 80.000
- Konsistenz durch Single Source of Truth
- Automatische Validierung durch Tools
- Klare Ownership durch DOC-INDEX.md

---

*Erstellt vom Meta-Consultant, 2025-12-23*
