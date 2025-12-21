# HELIX v4 Konzept

> Dieses Dokument erklärt die Kernideen hinter HELIX v4.

---

## Das Problem

Große Software-Projekte sind zu komplex für eine einzelne AI-Session:
- Context Window wird voll
- Keine Spezialisierung möglich
- Fehler propagieren durch das ganze Projekt
- Kein Review-Mechanismus

## Die Lösung: Phasen-Orchestrierung

HELIX teilt Arbeit in **isolierte Phasen** auf:

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│  Phase 01          Phase 02          Phase 03                  │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐              │
│  │ Claude   │      │ Claude   │      │ Claude   │              │
│  │ Code #1  │─────▶│ Code #2  │─────▶│ Code #3  │              │
│  └──────────┘      └──────────┘      └──────────┘              │
│       │                 │                 │                    │
│       ▼                 ▼                 ▼                    │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐              │
│  │ Quality  │      │ Quality  │      │ Quality  │              │
│  │   Gate   │      │   Gate   │      │   Gate   │              │
│  └──────────┘      └──────────┘      └──────────┘              │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### Vorteile

| Aspekt | Single Session | HELIX Phasen |
|--------|---------------|--------------|
| Context | Wird voll | Frisch pro Phase |
| Spezialisierung | Generalist | Analyst, Developer, Reviewer |
| Fehler | Propagieren | Gate stoppt Fehler |
| Review | Keins | Automatisch nach jeder Phase |

---

## Kernkomponenten

### 1. Python Orchestrator

Der Orchestrator ist das "Gehirn":
- Lädt `phases.yaml`
- Startet Claude Code Instanzen
- Prüft Quality Gates
- Koordiniert Übergaben zwischen Phasen

```python
# Vereinfacht
for phase in phases:
    result = await claude_runner.run_phase(phase.directory)
    if not quality_gate.check(result):
        escalate()
```

### 2. Claude Code CLI

Claude Code ist das "Werkzeug":
- Führt die eigentliche Arbeit aus
- Liest CLAUDE.md für Anweisungen
- Hat Zugriff auf Dateisystem
- Kann Code schreiben, ausführen, testen

```bash
claude --print --dangerously-skip-permissions \
       --output-format stream-json \
       --prompt "$(cat CLAUDE.md)"
```

### 3. Skills (Domain-Wissen)

Skills sind strukturiertes Wissen:
- Werden von Claude Code Instanzen gelesen
- Enthalten Domain-spezifische Information
- Ermöglichen Spezialisierung

```
skills/
├── pdm/
│   ├── SKILL.md          # Übersicht
│   └── bom-structure.md  # Stücklisten-Details
├── encoder/
│   └── SKILL.md          # Encoder-Produkte
└── helix/
    └── SKILL.md          # HELIX selbst
```

### 4. Quality Gates

Gates validieren Output:
- `files_exist` - Dateien vorhanden?
- `syntax_check` - Code korrekt?
- `tests_pass` - Tests grün?
- `review_approved` - LLM sagt OK?

---

## Der Consultant-Flow

Bevor Code geschrieben wird, muss verstanden werden WAS gebaut werden soll:

```
┌─────────────────────────────────────────────────────────────────┐
│                     CONSULTANT FLOW                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  User: "Ich brauche einen BOM Export"                            │
│                                                                  │
│  Consultant (Claude Code #0):                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 1. Liest skills/pdm/SKILL.md                               │  │
│  │ 2. Versteht was "BOM" im Kontext bedeutet                  │  │
│  │ 3. Fragt: "Welches Format? Excel? CSV? JSON?"              │  │
│  │ 4. Fragt: "Multi-Level oder Single-Level BOM?"             │  │
│  │ 5. Fragt: "Welche Felder sollen exportiert werden?"        │  │
│  │ 6. Generiert spec.yaml mit allen Requirements              │  │
│  │ 7. Generiert phases.yaml mit Umsetzungs-Plan               │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Output:                                                         │
│  - spec.yaml    (Was soll gebaut werden)                         │
│  - phases.yaml  (Wie wird es gebaut)                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Session-Management

Jede Consultant-Diskussion ist eine **Session**:

```
projects/sessions/
└── bom-export-20241221-143022/
    ├── CLAUDE.md              # Consultant-Anweisungen
    ├── status.json            # discussing/ready/executed
    ├── input/
    │   └── request.md         # User-Anfrage
    ├── context/
    │   ├── what.md            # Antwort: Was?
    │   ├── why.md             # Antwort: Warum?
    │   └── constraints.md     # Antwort: Constraints?
    └── output/
        ├── spec.yaml          # Generierte Spec
        ├── phases.yaml        # Generierter Plan
        └── summary.md         # Meeting-Zusammenfassung
```

### Session-Lifecycle

1. **Created** - User startet Chat
2. **Discussing** - Consultant fragt, User antwortet
3. **Ready** - spec.yaml generiert, bereit zur Ausführung
4. **Executed** - Projekt läuft/fertig

---

## API-Integration

HELIX bietet eine REST API (OpenAI-kompatibel):

```
┌─────────────────────────────────────────────────────────────────┐
│  Open WebUI (Browser)                                            │
│  https://helix2.duckdns.org:8443                                 │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               │ POST /v1/chat/completions
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  HELIX API (FastAPI)                                             │
│  http://localhost:8001                                           │
│                                                                  │
│  Endpoints:                                                      │
│  - POST /v1/chat/completions  ← OpenAI-kompatibel                │
│  - POST /helix/execute        ← Projekt starten                  │
│  - GET  /helix/stream/{id}    ← SSE Live Updates                 │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  Claude Code Instanzen                                           │
│  - Consultant (Session)                                          │
│  - Developer (Phase 01, 02, ...)                                 │
│  - Reviewer, Documentation                                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Escalation

Wenn etwas schief geht:

### Stufe 1: Autonomous Recovery
- Anderes LLM Model probieren
- Hints hinzufügen
- Phase wiederholen

### Stufe 2: Human in the Loop
- User wird benachrichtigt
- User kann eingreifen
- User kann überspringen

---

## Zusammenfassung

HELIX v4 = **Claude Code** + **Phasen** + **Quality Gates** + **Skills**

1. **Consultant** klärt Anforderungen
2. **Orchestrator** koordiniert Phasen
3. **Claude Code** führt Arbeit aus
4. **Quality Gates** validieren Output
5. **Skills** liefern Domain-Wissen

Das Ergebnis: Zuverlässige, qualitätsgesicherte Software-Entwicklung mit AI.
