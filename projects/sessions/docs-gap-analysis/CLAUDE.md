# Consultant Session: Documentation Gap Analysis

Du analysierst warum die Dokumentation für ADR-013 und ADR-017 nicht automatisch aktualisiert wurde.

## Kontext

Lies diese Dateien:
1. `input/ADR-014.md` - Documentation Architecture (Single Source of Truth)
2. `input/ARCHITECTURE-MODULES.md` - Module-Dokumentation
3. `input/docs-sources/` - Aktuelle YAML Sources

## Das Problem

Nach der Implementation von ADR-013 (Debug) und ADR-017 (Orchestrator):
- Code wurde erstellt: src/helix/debug/, src/helix/orchestrator/
- Docs wurden erstellt: docs/DEBUGGING.md, docs/ORCHESTRATOR-GUIDE.md
- ABER: skills/helix/SKILL.md wurde NICHT aktualisiert
- ABER: docs/sources/*.yaml wurde NICHT erweitert

Die neuen Features sind nicht im "Single Source of Truth" System!

## Fragen zu beantworten

### 1. Root Cause Analyse

Warum ist das passiert?
- Liegt es am Dokumentations-Konzept (ADR-014)?
- Liegt es daran, dass wir Claude Code CLI statt den Consultant-Prozess genutzt haben?
- Fehlt ein automatischer Schritt?

### 2. Prozess-Lücke

Wo genau ist die Lücke?
```
ADR schreiben → Implementation → ??? → SKILL.md aktualisiert
```

Was sollte bei "???" passieren?

### 3. Lösungsoptionen

Analysiere mindestens 3 Optionen:

A) **Post-Implementation Hook**
   - Nach jeder Implementation: docs/sources/*.yaml aktualisieren
   - Wie erzwingen?

B) **ADR-Template erweitern**
   - ADR muss docs/sources/*.yaml Änderungen enthalten
   - Validator prüft das

C) **Automatische Extraktion**
   - Tool das aus Code + Docstrings die YAML Sources generiert
   - Wie realistisch?

D) **Andere Ideen?**

### 4. Empfehlung

Was ist die pragmatischste Lösung für HELIX v4?

## Output

Schreibe nach `output/DOCS-GAP-ANALYSIS.md`:
- Root Cause
- Prozess-Lücke visualisiert
- Optionen mit Pro/Contra
- Konkrete Empfehlung
- Vorgeschlagene Änderungen an ADR-014 oder Templates
