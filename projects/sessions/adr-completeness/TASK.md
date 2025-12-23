# Aufgabe: ADR-Vollständigkeits-Enforcement

Du bist der HELIX Meta-Consultant. Entwickle eine Strategie um sicherzustellen dass ADRs vollständig sind.

## Das Problem

Gerade passiert:
- ADR-014 wurde erstellt
- Das zugrundeliegende Konzept hatte einen detaillierten 14-Tage Migrations-Plan
- Der Migrations-Plan wurde im ADR VERGESSEN
- Erst durch manuelles Nachfragen wurde er hinzugefügt

Das ist ein generisches Problem:
- ADRs haben Pflicht-Sections (Kontext, Entscheidung, etc.)
- Manche Sections sind KONTEXTABHÄNGIG:
  - `change_scope: major` → Migration-Plan erforderlich?
  - `classification: NEW` → Mehr Details nötig als bei `FIX`?
  - Files werden erstellt → Dokumentation wie sie zu nutzen sind?

## Aktuelle Validierung

Das ADR-Tool prüft aktuell:
```python
# Pflicht-Sections existieren
REQUIRED_SECTIONS = ["Kontext", "Entscheidung", "Implementation", "Akzeptanzkriterien", "Konsequenzen"]
```

Aber es prüft NICHT:
- Ob die Section inhaltlich vollständig ist
- Ob kontextabhängige Sections vorhanden sind
- Ob referenzierte Konzepte übernommen wurden

## Deine Aufgabe

Entwickle ein generisches Konzept für "ADR Completeness Enforcement":

### 1. Kontextabhängige Pflicht-Sections

Welche Sections sind wann Pflicht?

```yaml
# Beispiel-Idee
rules:
  - when: change_scope == "major"
    require: ["Migration-Plan", "Rollback-Plan"]
    
  - when: classification == "NEW" AND files.create is not empty
    require: ["Usage Examples"]
    
  - when: depends_on is not empty
    require: ["Integration mit abhängigen ADRs"]
```

### 2. Inhalts-Validierung

Wie prüft man ob eine Section "vollständig" ist?

Ideen:
- Mindest-Wortanzahl?
- Bestimmte Schlüsselwörter müssen vorkommen?
- LLM-basierte Prüfung?
- Checkliste die abgehakt werden muss?

### 3. Konzept-zu-ADR Mapping

Wenn ein ADR auf einem Konzept basiert:
- Wie stellt man sicher dass alle Sections übernommen werden?
- Automatischer Abgleich?
- Manuelle Checkliste?

### 4. Integration in Workflow

Wo wird geprüft?
- Bei ADR-Erstellung (Consultant warnt)?
- Bei ADR-Validierung (Tool blockiert)?
- Bei ADR-Finalisierung (Gate)?
- Im Review (LLM prüft)?

### 5. Generische Lösung

Das Konzept soll nicht nur für ADRs funktionieren sondern auch für:
- Andere Dokument-Typen
- Code-Dokumentation
- Projekt-Spezifikationen

## Output

Schreibe in output/adr-completeness.md:

1. Problem-Analyse (warum passiert das?)
2. Kontextabhängige Regeln (YAML-Format)
3. Validierungs-Strategien (mit Vor/Nachteilen)
4. Empfohlene Lösung
5. Implementation (Erweiterung adr_tool.py)
6. Integration in HELIX Workflow
7. Beispiel: Wie hätte ADR-014 geprüft werden sollen?

---

# Folge-Aufgabe: Layer 4 Semantic Validation - Wie implementieren?

## Die Frage

Layer 4 (Semantic/LLM) ist definiert als:
- Aktiviert nur für major + status=Proposed
- Prüft semantische Vollständigkeit
- Gibt Verbesserungsvorschläge

Aber WIE wird das technisch umgesetzt?

## Optionen

### Option A: Separate Claude Code CLI Instanz

```bash
# Im adr_tool.py
subprocess.run([
    "claude", "-p", 
    f"Prüfe dieses ADR auf Vollständigkeit: {adr_content}",
    "--output-format", "json"
])
```

Pro:
- Nutzt bestehende Infrastruktur
- Volle Claude-Fähigkeiten
- Kann Skills laden

Contra:
- Langsam (~10-30 Sekunden)
- Teuer (API-Kosten)
- Komplexität (subprocess handling)

### Option B: Direkter API-Call

```python
# Im adr_tool.py
import anthropic

client = anthropic.Client()
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    messages=[{"role": "user", "content": prompt}]
)
```

Pro:
- Schneller
- Mehr Kontrolle
- Einfacher zu integrieren

Contra:
- API-Key Management
- Keine Tool-Nutzung
- Zusätzliche Dependency

### Option C: Als Quality Gate (Review-Phase)

```yaml
# phases.yaml
phases:
  - id: consultant
    quality_gate:
      type: adr_complete
      semantic_review: true  # Aktiviert LLM-Review
```

Der Quality Gate Runner startet eine Claude-Instanz für Review.

Pro:
- Passt in HELIX-Architektur
- Trennung von Concerns
- Wiederverwendbar

Contra:
- Nur in HELIX-Kontext
- Nicht standalone nutzbar

### Option D: Hybrid - Tool + Optional LLM

```python
def validate_adr(path, semantic=False):
    # Layer 1-3: Deterministisch
    result = structural_check(path)
    result += contextual_check(path)
    result += concept_diff(path)
    
    # Layer 4: Optional, nur wenn --semantic Flag
    if semantic:
        result += semantic_check_via_cli(path)
    
    return result
```

```bash
# Schnell (ohne LLM)
python -m helix.tools.adr_tool validate ADR-014.md

# Gründlich (mit LLM)
python -m helix.tools.adr_tool validate ADR-014.md --semantic
```

## Deine Aufgabe

Analysiere die Optionen und empfehle die beste Lösung.

Kriterien:
1. Passt in HELIX-Architektur
2. Standalone nutzbar (ohne HELIX-Kontext)
3. Performance akzeptabel
4. Kosten-bewusst (LLM nur wenn nötig)
5. Einfach zu implementieren

Schreibe die Empfehlung in output/semantic-validation-design.md
