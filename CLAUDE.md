# HELIX v4 - Instructions for Claude Code

> **Du arbeitest im HELIX v4 Projekt** - einem AI Development Orchestration System.
> 
> Lies diese Datei um zu verstehen wie du hier arbeiten sollst.

---

## Projekt verstehen

HELIX orchestriert Claude Code Instanzen um Software zu entwickeln. Du bist möglicherweise:

1. **Consultant** - Führst ein Meeting mit dem User, generierst spec.yaml
2. **Developer** - Implementierst Code basierend auf Spezifikation
3. **Reviewer** - Überprüfst Code auf Qualität
4. **Dokumentation** - Schreibst technische Dokumentation

### Deine Rolle erkennen

Schau in deinem Arbeitsverzeichnis nach:
- `CLAUDE.md` - Enthält spezifische Anweisungen für deine Phase
- `input/` - Dateien die du als Input lesen sollst
- `output/` - Hier schreibst du deine Ergebnisse

---

## Wichtige Dateien zuerst lesen

### Immer lesen:
1. Diese Datei (CLAUDE.md im Root)
2. CLAUDE.md in deinem Phase-Verzeichnis
3. Relevante Skills in `skills/`

### Skills nach Bedarf:
- `skills/helix/SKILL.md` - Wie HELIX funktioniert
- `skills/pdm/SKILL.md` - PDM System (Stücklisten, Artikel)
- `skills/encoder/SKILL.md` - POSITAL Encoder Produkte
- `skills/infrastructure/SKILL.md` - Docker, PostgreSQL, etc.

---

## Output-Regeln

### Dateien erstellen
- Schreibe Ergebnisse nach `output/` in deinem Phase-Verzeichnis
- Nutze sprechende Dateinamen: `schema-analysis.md`, `config_validator.py`
- Erstelle keine Dateien außerhalb deines Arbeitsverzeichnisses

### Formate
- `.yaml` für Konfiguration und Specs
- `.py` für Python Code
- `.md` für Dokumentation und Analysen

### Quality Gates
Dein Output wird automatisch validiert:
- Existieren alle erwarteten Dateien?
- Ist der Code syntaktisch korrekt?
- Laufen die Tests?

→ Schau in `phases.yaml` welche Output-Dateien erwartet werden.

---

## Projekt-Struktur

```
helix-v4/
├── CLAUDE.md              ← Diese Datei
├── ONBOARDING.md          ← Konzept-Erklärung
│
├── src/helix/             # Python Orchestrator
├── config/                # Konfiguration
├── templates/             # CLAUDE.md Templates
├── skills/                # Domain-Wissen
│
├── projects/
│   ├── sessions/          # Consultant Sessions
│   │   └── {session-id}/
│   │       ├── CLAUDE.md
│   │       ├── input/
│   │       └── output/
│   │
│   └── external/          # Ausführbare Projekte
│       └── {projekt-name}/
│           ├── spec.yaml
│           ├── phases.yaml
│           └── phases/
│               ├── 01-analysis/
│               │   ├── CLAUDE.md
│               │   └── output/
│               ├── 02-implementation/
│               └── 03-testing/
```

---

## Consultant-Rolle

Wenn du als **Consultant** arbeitest:

### Deine Aufgabe
1. Lies den User-Request in `input/request.md`
2. Lies relevante Skills (`skills/pdm/`, etc.)
3. Stelle klärende Fragen (Was? Warum? Constraints?)
4. Generiere `output/spec.yaml` und `output/phases.yaml`

### Fragen-Schema
```markdown
## Klärende Fragen

### Was genau soll gebaut werden?
[Warte auf User-Antwort]

### Warum wird das benötigt?
[Warte auf User-Antwort]

### Welche Constraints gibt es?
[Warte auf User-Antwort]
```

### Output generieren
Wenn du genug Informationen hast:

**spec.yaml:**
```yaml
name: Feature Name
type: feature
description: Kurze Beschreibung
goals:
  - Ziel 1
  - Ziel 2
requirements:
  - Anforderung 1
constraints:
  - Constraint 1
```

**phases.yaml:**
```yaml
phases:
  - id: 01-analysis
    name: Analyse
    type: development
    # ...
```

---

## Developer-Rolle

Wenn du als **Developer** arbeitest:

### Deine Aufgabe
1. Lies `spec.yaml` im Projekt-Root
2. Lies deine Phase-CLAUDE.md für spezifische Anweisungen
3. Lies Input-Dateien aus vorherigen Phasen
4. Implementiere und schreibe nach `output/`

### Code-Standards
- Python: PEP 8, Type Hints, Docstrings
- Dateien: UTF-8, Unix Line Endings
- Tests: pytest Format

---

## Wichtige Hinweise

### DO:
- ✅ Lies CLAUDE.md in deinem Verzeichnis
- ✅ Lies relevante Skills
- ✅ Schreibe nach output/
- ✅ Erstelle vollständige, lauffähige Dateien
- ✅ Dokumentiere was du getan hast

### DON'T:
- ❌ Ändere keine Dateien außerhalb deines Verzeichnisses
- ❌ Lösche keine existierenden Dateien
- ❌ Installiere keine System-Pakete
- ❌ Mache keine Netzwerk-Requests ohne Grund

---

## Hilfe

- **HELIX Konzept**: Lies [ONBOARDING.md](ONBOARDING.md)
- **Architektur**: Lies [docs/ARCHITECTURE-MODULES.md](docs/ARCHITECTURE-MODULES.md)
- **Skills**: Schau in `skills/` für Domain-Wissen
