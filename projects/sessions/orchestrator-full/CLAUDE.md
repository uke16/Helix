# Consultant Session: ARCHITECTURE-ORCHESTRATOR-FULL.md

Du bist der HELIX Consultant. Erstelle das vollständige Orchestrator-Architektur-Dokument.

## Kontext

Lies diese Dateien:

1. `input/ARCHITECTURE-ORCHESTRATOR.md` - Aktuelles MVP Design
2. `input/VISION.md` - Langfristige Vision
3. `input/ADR-017.md` - Phase Orchestrator ADR
4. `input/ADR-005.md` - Consultant Topology (Sub-Agenten!)

## Wichtige Klarstellungen von Uwe

### Domain Consultants = Sub-Agenten
- Domain Consultants sind Sub-Agenten vom Haupt-Consultant
- Das Konzept existiert schon in ADR-005!
- Noch nicht umgesetzt, aber das Pattern ist klar
- Dokumentiere wie der Haupt-Consultant Domain-Experten einbindet

### Hardware-Tools = Generisch
- Pattern: VPN → SSH → Python → Library
- Jedes Tool ist einfach eine Python-Library/Funktion
- Muss nur dokumentiert sein (wie ein Skill)
- Claude Code CLI nutzt es dann über SSH/Bash

Beispiel:
```
skills/tools/jtag/
├── SKILL.md          # Dokumentation für Claude
├── examples/         # Code-Beispiele
└── requirements.txt  # pyocd, etc.
```

Claude Code CLI connected via SSH kann dann:
```python
from pyocd.core.helpers import ConnectHelper
session = ConnectHelper.session_with_chosen_probe()
```

## Deine Aufgabe

Erstelle `output/ARCHITECTURE-ORCHESTRATOR-FULL.md` mit klarer Trennung:

### Teil 1: MVP (2 Wochen)
- Was in ADR-017 steht
- Basis-Orchestrator
- Einfacher Datenfluss
- Feste Quality Gates

### Teil 2: MaxVP - Domain Consultants
- Haupt-Consultant ruft Domain-Experten
- Routing basierend auf Projekt-Typ/Domain
- Skills-basierte Expertise

### Teil 3: MaxVP - Hardware-Tool Integration
- Generic Pattern: SSH + Python + Dokumentation
- Skill-Format für Tools
- Beispiel: JTAG, Oscilloscope

### Teil 4: MaxVP - Projekt-Hierarchie
- Sub-Projekte
- Status-Tracking über Hierarchien
- Shared Context

### Teil 5: MaxVP - Parallele Ausführung
- DAG-basierte Dependencies
- Parallel wo möglich
- Critical Path Berechnung

### Teil 6: Roadmap
- Was wann implementieren
- Dependencies zwischen Features

## Qualitätskriterien

- Klare MVP vs MaxVP Trennung
- Konkrete Code-Beispiele
- Realistische Aufwandsschätzungen
- Baut auf existierenden ADRs auf

## Output

Schreibe nach `output/ARCHITECTURE-ORCHESTRATOR-FULL.md`
