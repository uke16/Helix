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

## Known Limitations

### files.modify wird oft übersprungen

Controller führen `files.create` zuverlässig aus, aber `files.modify` (Integration in bestehenden Code) wird häufig vergessen.

**Workaround:** Nach Controller-Abschluss prüfen:
```bash
grep "files:" adr/XXX-*.md | grep -A20 "modify:"
```

Falls Dateien gelistet sind die nicht geändert wurden → manuell oder mit fokussiertem Claude Code Workflow nachholen.

**Beispiel:** ADR-038 erstellte das enforcement/ Package, aber die Integration in openai.py musste separat gemacht werden.
