# Aufgabe: Dokumentations-Enforcement Konzept

Du bist der HELIX Meta-Consultant. Erweitere das Konzept in output/docs-architecture.md um Enforcement.

## Offene Fragen

Der User fragt:

1. **Wann wird dokumentiert?**
   - Im Development-Prozess direkt?
   - In einer separaten Documentation-Phase?
   - Beides?

2. **Wer dokumentiert was?**
   - Developer schreibt Docstrings im Code
   - Aber wer schreibt die YAML-Sources?
   - Wer pflegt die Templates?

3. **Wie enforced man Vollständigkeit?**
   - Woher weiß man dass ALLES dokumentiert ist?
   - Neue Funktion ohne Docstring → wie erkennen?
   - Neues Feature ohne YAML-Eintrag → wie erkennen?

4. **Wie verhindert man "Verschlampen"?**
   - Feature implementiert aber nicht dokumentiert
   - Feature entfernt aber Doku bleibt
   - Parameter geändert aber Beispiel veraltet

## Kontext aus bestehendem Konzept

Das bestehende Konzept hat:
- Primary Sources: Docstrings + YAML
- Kompilierung zu CLAUDE.md, Skills, docs/
- Quality Gate: `docs_compiled`

Aber es fehlt:
- Wann im Workflow wird dokumentiert?
- Wie erkennt man fehlende Dokumentation?
- Wie enforced man bei JEDER Code-Änderung?

## Deine Aufgabe

Entwickle ein Enforcement-Konzept das folgende Aspekte abdeckt:

### 1. Documentation-as-Code Workflow

Wann und wie wird dokumentiert?

```
Option A: Inline (im Development)
  → Docstrings + YAML im gleichen Commit wie Code
  → Quality Gate prüft sofort
  
Option B: Separate Phase
  → Code-Phase, dann Documentation-Phase
  → Spezialisierte Claude-Instanz für Doku
  
Option C: Hybrid
  → Docstrings inline (Pflicht)
  → YAML-Sources in Documentation-Phase (optional)
```

### 2. Vollständigkeits-Prüfung

Wie erkennt man dass ALLES dokumentiert ist?

```
Ideen:
- AST-Analyse: Jede public function hat docstring?
- Schema-Validierung: YAML gegen JSON-Schema?
- Coverage-Report: Wie viel % dokumentiert?
- Cross-Reference: Code-Exports ↔ YAML-Entries?
```

### 3. Lifecycle-Hooks

An welchen Stellen im Prozess wird geprüft?

```
1. Pre-Commit Hook
   → Lokale Prüfung vor Commit
   
2. Quality Gate in Phase
   → Phase schlägt fehl wenn Doku fehlt
   
3. CI/CD Pipeline
   → Merge blockiert wenn Doku fehlt
   
4. Periodic Audit
   → Regelmäßige Vollprüfung
```

### 4. Fehlende-Doku-Erkennung

Wie findet man "verschlampte" Dokumentation?

```
Tool: docs_coverage.py

Prüft:
- Jede public class/function hat docstring
- Jede exportierte Funktion ist in YAML
- Jedes YAML-Feature hat Code-Referenz
- Keine verwaisten Einträge
```

### 5. Integration mit HELIX Phasen

Wie passt das in den Evolution-Workflow?

```
Consultant-Phase:
  → ADR erstellt
  → ADR definiert welche Doku nötig ist

Development-Phase:
  → Code + Docstrings
  → Quality Gate: docstrings_complete

Documentation-Phase (optional):
  → YAML-Sources erweitern
  → Templates anpassen
  → Quality Gate: docs_compiled

Review-Phase:
  → Prüft Doku-Qualität
  → LLM-Review der Docstrings
```

## Output

Erweitere output/docs-architecture.md um einen neuen Abschnitt:

"## 10. Enforcement-Konzept"

Mit:
1. Workflow-Entscheidung (wann dokumentieren)
2. Vollständigkeits-Metriken
3. Lifecycle-Hooks
4. Tool: docs_coverage.py (Konzept)
5. Integration in HELIX Phasen
6. Beispiel: Neues Feature end-to-end

Sei konkret mit Code-Beispielen!
