# Draft: Sub-Agent Enhancement mit Context-Aware Capabilities

**Status:** Draft / Research
**Erstellt:** 2024-12-24

---

## Kontext

Der Sub-Agent (Claude CLI) hat strukturelle Vorteile gegenüber einem durchgehenden Chat:

### Aktuelle Vorteile

1. **Frischer Context**
   - Keine Vorurteile aus vorherigen Gesprächen
   - Keine "Drift" durch lange Konversationen
   - Jede Phase startet neutral

2. **Fokus**
   - Nur die aktuelle Aufgabe im Context
   - Kein Ballast von unrelated Diskussionen
   - Klare Input/Output Grenzen

3. **Self-Validation** (via ADR-011)
   - Agent kann `verify_phase_output()` aufrufen
   - Sofortiges Feedback während Ausführung
   - Korrektur VOR Beendigung möglich

---

## Erweiterungsmöglichkeiten

### 1. Code-Beispiele aus Context extrahieren und enforced

**Idee:** 
Der Agent analysiert den bestehenden Codebase und extrahiert Patterns die er dann anwendet.

```
Phase startet
    ↓
Agent liest relevante src/ Dateien
    ↓
Extrahiert: "Alle Klassen haben __init__ mit Type Hints"
    ↓
Wendet Pattern auf neuen Code an
    ↓
Validiert: "Hat neue Klasse auch Type Hints?"
```

**Mögliche Implementation:**
- Pre-Phase: Pattern-Extraktor läuft über relevante Dateien
- Pattern-Prompt wird in CLAUDE.md injiziert
- Post-Phase: Gate prüft ob Patterns eingehalten wurden

### 2. Doku-Patterns ableiten

**Idee:**
Aus bestehender Dokumentation werden Standards abgeleitet.

```python
# Beispiel: Docstring-Analyse
existing_docstrings = analyze_project_docstrings()
# → "Google-Style Docstrings"
# → "Args/Returns/Raises Sections"
# → "Examples in allen public methods"

# Prompt-Injection:
"""
Doku-Standards in diesem Projekt:
- Google-Style Docstrings
- Args/Returns/Raises für jede public Method
- Mindestens ein Example pro Klasse
"""
```

### 3. Automatisch ähnliche ADRs als Referenz laden

**Idee:**
Bevor der Agent ein neues ADR schreibt, werden ähnliche ADRs geladen.

```
Request: "Neues Tool für XYZ"
    ↓
Semantic Search über bestehende ADRs
    ↓
Findet: ADR-013 (Tool), ADR-018 (Tool), ADR-003 (Tool)
    ↓
Lädt diese als Context
    ↓
Agent sieht: "So wurden ähnliche ADRs geschrieben"
```

**Bezug zu ADR-020:**
- Skill Index mit Keywords existiert bereits als Konzept
- Könnte auf ADRs erweitert werden
- Hybrid: Keyword + Semantic Search

### 4. Iterative Selbst-Verbesserung

**Idee:**
Agent überprüft seinen Output selbst und verbessert iterativ.

```
Agent erstellt Draft
    ↓
Agent ruft "review_my_output" Tool auf
    ↓
Tool gibt strukturiertes Feedback:
  - "Section X ist zu kurz"
  - "Missing: Fehlerbehandlung"
  - "Code-Beispiel fehlt"
    ↓
Agent verbessert
    ↓
Wiederholen bis "gut genug" oder max iterations
```

---

## Offene Fragen

1. **Wie viel Context ist zu viel?**
   - Pattern-Extraktion kann 1000+ Zeilen generieren
   - Semantic Search kann irrelevante ADRs laden
   - Balance: Fokus vs. Vollständigkeit

2. **Wer entscheidet was relevant ist?**
   - Meta-Consultant (ADR-005)?
   - Keyword-Matching (einfach)?
   - Embedding-basierte Suche (komplex)?

3. **Kosten-Nutzen?**
   - Mehr Context = mehr Tokens = mehr Kosten
   - Aber: Bessere Qualität = weniger Retries?

---

## Nächste Schritte

- [ ] POC: Pattern-Extraktor für Python Code
- [ ] POC: ADR Semantic Search
- [ ] Messen: Qualitätsverbesserung vs. Kosten
- [ ] Entscheiden: In welcher Phase am wertvollsten?

---

## Verwandte ADRs

- ADR-005: Consultant Topology (Meta-Consultant)
- ADR-011: Post-Phase Verification
- ADR-020: Intelligent Documentation Discovery
