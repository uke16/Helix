# Sub-Phase 14.1: helix-control.sh

## Ziel

Erstelle ein Control Script für HELIX v4 basierend auf dem v3 Script.

## Referenz

Lies zuerst:
- `/home/aiuser01/helix-v3/control/helix-v3-control.sh` (das Original)
- `../../spec.yaml` (Spezifikation)

## Aufgabe

Erstelle `output/helix-control.sh` mit folgenden Befehlen:

```bash
./helix-control.sh status      # Status aller Komponenten anzeigen
./helix-control.sh start       # HELIX API starten
./helix-control.sh stop        # HELIX API stoppen
./helix-control.sh restart     # HELIX API neustarten
./helix-control.sh logs        # Logs anzeigen (tail -f)
./helix-control.sh docker-up   # Docker Container starten
./helix-control.sh docker-down # Docker Container stoppen
./helix-control.sh health      # Health Check
```

## Anpassungen für v4

- HELIX_ROOT = `/home/aiuser01/helix-v4`
- API Port = 8001
- Log File = `$HELIX_ROOT/logs/helix-v4.log`
- Python Module = `helix.api.main:app`
- NVM Path für Claude CLI berücksichtigen

## Output

Schreibe das Script nach: `output/helix-control.sh`

## Quality Gate

Das Script muss:
- Ausführbar sein (chmod +x)
- `status` Befehl muss funktionieren
- Farbige Ausgabe wie v3
