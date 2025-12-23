# Aufgabe: ADR für Debug & Observability Engine

Du bist der HELIX Meta-Consultant.

## Hintergrund

HELIX führt Claude Code Instanzen aus, aber wir haben KEINE Live-Sichtbarkeit auf:
- Welche Tool Calls werden gemacht
- Was passiert gerade in der Phase  
- Kosten pro Phase/Projekt

## Entdeckung

Claude CLI hat eingebaute Observability:
```bash
claude -p --output-format stream-json --verbose --include-partial-messages
```

Das gibt strukturierte JSON Events:
- `type: system` mit `subtype: init` - Tools, Model, Session
- `type: assistant` mit `content[].type: tool_use` - Tool Calls
- `type: user` - Tool Results
- `type: result` - Duration, Cost, Turns

## Lösung

Ein Debug-System mit:
1. **StreamParser** - Parst Claude CLI stream-json Output
2. **ToolTracker** - Trackt Tool Usage Statistiken
3. **LiveDashboard** - Terminal-basierte Live-Ansicht
4. **helix-debug.sh** - CLI für Debugging

## Deine Aufgabe

Erstelle die Datei `output/ADR-debug-observability.md` mit folgendem Inhalt:

### YAML Header
```yaml
---
adr_id: "013"
title: "Debug & Observability Engine für HELIX Workflows"
status: Proposed
component_type: SERVICE
classification: NEW
change_scope: major
domain: helix
language: python
skills:
  - helix
  - observability
files:
  create:
    - src/helix/debug/__init__.py
    - src/helix/debug/stream_parser.py
    - src/helix/debug/tool_tracker.py
    - src/helix/debug/live_dashboard.py
    - tests/debug/test_stream_parser.py
    - control/helix-debug.sh
  modify:
    - control/claude-wrapper.sh
  docs:
    - docs/DEBUGGING.md
depends_on: ["003", "011"]
---
```

### Markdown Sections

1. **Kontext** - Das Problem mit fehlender Sichtbarkeit
2. **Entscheidung** - Die Lösung mit Architektur-Diagramm (ASCII)
3. **Implementation** - Code-Beispiel für StreamParser Klasse
4. **Dokumentation** - Welche Docs aktualisiert werden
5. **Akzeptanzkriterien** - Als Checkbox-Liste
6. **Konsequenzen** - Positiv, Negativ, Neutral

Schreibe jetzt die komplette Datei.
