# Consultant Meeting Notes - ADR-020

## Skills gelesen

1. ✅ skills/helix/SKILL.md - Core Orchestration, Quality Gates
2. ✅ skills/helix/adr/SKILL.md - ADR Format und Validierung  
3. ✅ docs/sources/documentation-system.yaml - Bestehendes Docs-System

## Klärende Fragen

### 1. Scope für Skill Index

**Frage:** Soll der Skill Index nur SKILL.md Dateien erfassen oder auch andere Docs?

**Antwort:** Nur SKILL.md Dateien in skills/. Das sind die primären Wissensquellen für Agents.

### 2. Keyword-Extraktion

**Frage:** Welche Elemente aus SKILL.md sollen als Keywords extrahiert werden?

**Antwort (aus Elaboration):**
- Headers (## Something)
- Code-Begriffe (`backticks`)
- Fettgedruckte Begriffe (**bold**)
- Plus: manuelle aliases für Synonyme

### 3. Reverse Index Persistenz

**Frage:** Soll der Reverse Index als Datei gespeichert werden oder on-demand generiert?

**Antwort:** On-demand (empfohlen aus Elaboration). Gründe:
- Immer aktuell
- Kein Sync-Problem
- ~20 ADRs parsen dauert <1 Sekunde

### 4. Integration mit Consultant Phase

**Frage:** Wie soll Smart Selection in den Consultant Workflow integriert werden?

**Antwort:** 
- Phase Orchestrator ruft skill_selector vor Consultant Phase auf
- Ergebnis wird in CLAUDE.md für Consultant eingebettet
- Consultant sieht: "Empfohlene Skills: X, Y (matched: keyword1, keyword2)"

### 5. ADR Status Validation

**Frage:** Was passiert wenn ADR sagt "Implemented" aber Dateien fehlen?

**Antwort:**
- Quality Gate `adr_files_exist` prüft das
- Warning in INDEX.md: "⚠️ ADR-009: 2 files missing"
- Kann auch als blocking gate konfiguriert werden

## Entscheidungen

1. **skills/INDEX.yaml** als Single Source für Skill-Metadaten
   - auto_keywords: automatisch extrahiert
   - aliases: manuell für Synonyme
   - triggers: optionale Phrasen-Matcher

2. **On-Demand Reverse Index** statt persistierter Datei
   - CLI: `python -m helix.tools.adr_tool code-to-adr [file]`
   - Auch als Quality Gate verfügbar

3. **Transparente Skill Selection**
   - Consultant sieht Score und matched Keywords
   - Kann immer alle Skills laden (Override)

4. **Neues Quality Gate: adr_files_exist**
   - Prüft files.create gegen Filesystem
   - Warning bei fehlenden Dateien
