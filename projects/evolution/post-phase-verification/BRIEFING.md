# Consultant Briefing: Post-Phase Verification System

## Das Problem

Im Evolution Workflow fehlt eine kritische Komponente: **Nach jeder Claude Code Phase wird nicht geprüft ob die erwarteten Dateien tatsächlich erstellt wurden.**

### Aktueller Zustand

```
Phase X läuft (Claude Code)
    ↓
Exit Code = 0?
    ↓
✅ Phase als "completed" markiert
    ↓
Weiter zu Phase X+1
```

**Was fehlt:** Niemand prüft ob Claude die Dateien wirklich erstellt hat die in `phases.yaml` unter `output:` definiert sind.

### Konkretes Beispiel aus dem ADR-System Projekt

```yaml
# phases.yaml
- id: "2"
  name: "ADR Parser"
  output:
    - new/src/helix/adr/parser.py
    - new/tests/adr/test_parser.py
```

Claude Code beendete mit Exit 0, aber:
- Manchmal schrieb Claude nach `output/` statt `new/`
- Manchmal fehlten Tests komplett
- Manchmal hatte der Code Syntax-Fehler

Wir haben das nur durch manuelles Prüfen bemerkt.

## Der Kontext

### ADR als Single Source of Truth (ADR-001)

Wir haben gerade beschlossen dass **ADRs die Single Source of Truth** für Evolution-Projekte sind. Ein ADR enthält:

```yaml
files:
  create:
    - src/helix/module.py
    - tests/test_module.py
  modify:
    - src/helix/__init__.py
  docs:
    - docs/ARCHITECTURE.md
```

Diese Information existiert also bereits - sie wird nur nicht genutzt!

### Das ADR-System

Wir haben ein funktionierendes ADR-System:

```python
from helix.adr import ADRParser

parser = ADRParser()
adr = parser.parse_file(Path("ADR-feature.md"))

# Zugriff auf erwartete Files
adr.metadata.files.create   # ["src/module.py", ...]
adr.metadata.files.modify   # ["src/__init__.py", ...]
```

## Die Idee

Es gibt zwei Ansätze die sich ergänzen könnten:

### 1. Claude ruft selbst ein Verification-Tool auf

Claude Code könnte vor dem Beenden ein Tool aufrufen das prüft ob alles da ist. Wenn nicht, kann Claude selbst korrigieren.

**Vorteil:** Schnell, günstig, Claude hat den Kontext noch
**Frage:** Wie stellen wir sicher dass Claude das Tool auch wirklich aufruft?

### 2. Externes Safety Net nach der Phase

Nach dem Claude Code Run prüft das System extern ob alles stimmt. Falls nicht, wird Claude nochmal gestartet mit den Fehlermeldungen.

**Vorteil:** Funktioniert auch wenn Claude vergisst zu verifizieren
**Frage:** Wie viele Retries? Wie übergeben wir den Fehler-Kontext?

### Hybrid?

Vielleicht eine Kombination? Claude versucht selbst zu verifizieren, und das externe System ist das Safety Net mit max 2 Retries?

## Deine Aufgabe

Entwirf eine Lösung für dieses Problem. Erstelle ein ADR das:

1. Das Problem und den Kontext dokumentiert
2. Die Entscheidung und den Lösungsansatz beschreibt
3. Konkrete Implementation vorschlägt (welche Files, welche Komponenten)
4. Quality Gates / Akzeptanzkriterien definiert

### Zu berücksichtigen

- Das ADR-System (`helix.adr`) existiert bereits und kann Files parsen
- `phases.yaml` hat bereits `output:` Listen pro Phase
- Templates könnten Instruktionen für Claude enthalten
- `streaming.py` führt die Phasen aus und könnte erweitert werden
- Wir wollen keine Endlos-Loops (max 2 Retries)

### Referenzen

- `adr/001-adr-as-single-source-of-truth.md` - ADR Architektur
- `docs/ARCHITECTURE-EVOLUTION.md` - Evolution System
- `src/helix/adr/` - ADR Parser/Validator
- `src/helix/api/streaming.py` - Phase Execution
- `templates/developer/_base.md` - Claude Template
