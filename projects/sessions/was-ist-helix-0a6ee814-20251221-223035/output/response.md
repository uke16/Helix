# Was ist HELIX und wie funktioniert es?

## Kurz gesagt

**HELIX v4** ist ein **AI Development Orchestration System** - ein System, das mehrere Claude Code Instanzen koordiniert, um Software zu entwickeln.

Statt einer einzelnen AI-Session teilt HELIX komplexe Aufgaben in **isolierte Phasen** auf, die von separaten Claude Code Instanzen bearbeitet werden.

---

## Das Problem, das HELIX löst

Große Software-Projekte sind zu komplex für eine einzelne AI-Session:

| Problem | HELIX Lösung |
|---------|--------------|
| Context Window wird voll | Jede Phase startet mit frischem Context |
| Keine Spezialisierung | Analyst, Developer, Reviewer als spezialisierte Rollen |
| Fehler propagieren | Quality Gates stoppen Fehler zwischen Phasen |
| Kein Review-Mechanismus | Automatisches Review nach jeder Phase |

---

## Wie funktioniert HELIX?

```
┌──────────────────────────────────────────────────────────────────┐
│                         HELIX v4                                 │
│                                                                  │
│   User: "Erstelle einen BOM Export"                              │
│                    │                                             │
│                    ▼                                             │
│   ┌─────────────────────────────────┐                            │
│   │  Claude Code #0 (Consultant)    │  ← Das bin ich jetzt!      │
│   │  - Liest Skills (PDM, etc.)     │                            │
│   │  - Stellt klärende Fragen       │                            │
│   │  - Generiert spec.yaml          │                            │
│   └─────────────────────────────────┘                            │
│                    │                                             │
│                    ▼                                             │
│   ┌─────────────────────────────────┐                            │
│   │  Claude Code #1 (Analyse)       │  ← Analysiert das Problem  │
│   └─────────────────────────────────┘                            │
│                    │                                             │
│                    ▼                                             │
│   ┌─────────────────────────────────┐                            │
│   │  Claude Code #2 (Implementation)│  ← Schreibt den Code       │
│   └─────────────────────────────────┘                            │
│                    │                                             │
│                    ▼                                             │
│   ┌─────────────────────────────────┐                            │
│   │  Claude Code #3 (Testing)       │  ← Testet und validiert    │
│   └─────────────────────────────────┘                            │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Die 5 Kernkomponenten

### 1. Consultant (Phase 0 - das bin ich)
Bevor Code geschrieben wird, führe ich ein "Meeting" mit dir:
- **Was** soll gebaut werden?
- **Warum** wird es benötigt?
- **Welche Constraints** gibt es?

Am Ende generiere ich:
- `spec.yaml` - Die Anforderungsspezifikation
- `phases.yaml` - Der Umsetzungs-Plan

### 2. Python Orchestrator
Das "Gehirn" von HELIX:
- Lädt die Phasen-Definition
- Startet Claude Code Instanzen nacheinander
- Prüft Quality Gates nach jeder Phase
- Koordiniert die Übergaben

### 3. Claude Code CLI
Das "Werkzeug":
- Führt die eigentliche Arbeit aus
- Liest CLAUDE.md für Anweisungen
- Hat Zugriff auf das Dateisystem
- Kann Code schreiben, ausführen, testen

### 4. Quality Gates
Validierung nach jeder Phase:
- `files_exist` - Wurden die erwarteten Dateien erstellt?
- `syntax_check` - Ist der Code syntaktisch korrekt?
- `tests_pass` - Laufen die Tests?
- `review_approved` - Hat das LLM-Review bestanden?

### 5. Skills (Domain-Wissen)
Strukturiertes Wissen, das ich lesen kann:
- **PDM** - Product Data Management, Stücklisten
- **Encoder** - POSITAL Encoder Produkte
- **Infrastructure** - Docker, PostgreSQL, etc.
- **HELIX** - Das System selbst

---

## Wie kann man HELIX bedienen?

### Option 1: Browser (Open WebUI)
- Öffne: https://helix2.duckdns.org:8443
- Wähle Model: `helix-consultant`
- Beschreibe was du bauen möchtest

### Option 2: REST API
```bash
# Projekt ausführen
curl -X POST http://localhost:8001/helix/execute \
  -H "Content-Type: application/json" \
  -d '{"project_path": "/path/to/project"}'
```

### Option 3: CLI
```bash
python -m helix.cli.main discuss ./projects/external/mein-projekt
```

---

## Zusammenfassung

**HELIX v4 = Claude Code + Phasen + Quality Gates + Skills**

Das Ergebnis: Zuverlässige, qualitätsgesicherte Software-Entwicklung mit AI.

---

## Nächster Schritt

Da du jetzt verstehst was HELIX ist: **Hast du ein konkretes Projekt, das du mit HELIX umsetzen möchtest?**

Ich kann dir helfen:
- Ein neues Feature zu planen
- Einen Bug zu analysieren
- Code zu refactoren
- Eine Integration zu bauen

Was möchtest du entwickeln?
