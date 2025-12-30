# Controller-Projekte

## Was

Ein Controller ist eine Claude Code Instanz die den Evolution Workflow **superviset** statt darin zu arbeiten.

## Warum

Der Evolution Workflow (ADR → Phasen → Deploy → Integrate) läuft noch nicht autonom. Der Controller:
- Dokumentiert wo es hakt
- Greift bei Problemen ein
- Sammelt Bugs/Improvements für zukünftige Autonomie

## Struktur

```
helix-v4/projects/claude/controller-adr-XXX/
├── CLAUDE.md       # Supervisor-Instruktionen
├── status.md       # Tracking
└── commands.sh     # API Helper
```

## Workflow

```
Controller startet
    ↓
Consultant anrufen (oder manuell Projekt erstellen)
    ↓
/helix/execute aufrufen
    ↓
Job überwachen bis COMPLETED/FAILED
    ↓
Bei Problemen: dokumentieren + fixen
    ↓
/deploy → /validate → /integrate
    ↓
MANUAL_INTERVENTIONS.md + BUGS_AND_IMPROVEMENTS.md ausfüllen
```

## Trigger

"Erstelle Controller für ADR-XX"

## Template

`templates/controller/CLAUDE.md.j2`

## Ziel

Jede dokumentierte Intervention = Input für Workflow-Verbesserung → Richtung Autonomie.
