# HELIX v4 Phase 14 - Continuation Prompt

## Kontext

Wir implementieren das **HELIX v4 Self-Evolution System** (Phase 14).
Der vorherige Chat ist nach Sub-Phase 14.1 abgeschmiert.

## Aktueller Status

| Sub-Phase | Status | Beschreibung |
|-----------|--------|--------------|
| 14.1 | ✅ DONE | `control/helix-control.sh` (12KB, smart detection) |
| 14.2 | ❌ TODO | helix-v4-test Setup (Verzeichnis + Docker) |
| 14.3 | ❌ TODO | Evolution Project Manager |
| 14.4 | ❌ TODO | Deployer & Validator |
| 14.5 | ❌ TODO | Integrator & RAG Sync |
| 14.6 | ❌ TODO | API Endpoints & Consultant Update |

## Wichtige Dateien zum Lesen

**MUST READ vor Weiterarbeit:**
```
/home/aiuser01/helix-v4/docs/EVOLUTION-CONCEPT.md           # Das Konzept
/home/aiuser01/helix-v4/projects/internal/helix-v4-bootstrap/phases/14-self-evolution/CLAUDE.md    # Implementierungsplan
/home/aiuser01/helix-v4/projects/internal/helix-v4-bootstrap/phases/14-self-evolution/phases.yaml  # Sub-Phasen Definition
```

**Zusätzlicher Kontext:**
```
/home/aiuser01/helix-v4/ONBOARDING.md                      # HELIX Überblick
/home/aiuser01/helix-v4/docs/CONCEPT.md                    # Detailliertes Konzept
/home/aiuser01/helix-v4/control/helix-control.sh           # Bereits implementiert (14.1)
```

**Referenz von v3 (für docker-compose):**
```
/home/aiuser01/helix-v3/docker/                            # Production Docker Setup
```

## Was als nächstes zu tun ist

### Sub-Phase 14.2: helix-v4-test Setup

1. **Verzeichnis erstellen:**
   ```bash
   git clone /home/aiuser01/helix-v4 /home/aiuser01/helix-v4-test
   ```

2. **docker/test/ erstellen in helix-v4:**
   - `docker/test/docker-compose.yaml` (Test-Ports: 9001, 5433, 7475, etc.)
   - `docker/test/.env.test`

3. **Test-System starten und Health Check**

### Dann weiter mit 14.3, 14.4, 14.5, 14.6

Siehe `/home/aiuser01/helix-v4/projects/internal/helix-v4-bootstrap/phases/14-self-evolution/CLAUDE.md` für Details.

## Architektur-Überblick

```
helix-v4/ (Production, Port 8001)
├── control/helix-control.sh     ✅ DONE
├── src/helix/evolution/         ❌ TODO (14.3-14.5)
├── docker/test/                 ❌ TODO (14.2)
└── projects/evolution/          # Für Self-Evolution Projekte

helix-v4-test/ (Test, Port 9001)  ❌ TODO (14.2)
└── (Clone von helix-v4 mit Test-Ports)
```

## Kernprinzip (WICHTIG!)

**Zettel statt Telefon:** Claude Code Instanzen sind kurzlebig.
Keine Echtzeit-Kommunikation zwischen Instanzen.
Kommunikation über Dateien (spec.yaml, status.json, etc.)

## Aufgabe

Bitte führe die Implementierung von Phase 14 fort, beginnend mit **Sub-Phase 14.2**.
Lies zuerst die MUST READ Dateien, dann implementiere systematisch.

Nach jeder Sub-Phase: Git commit und push zu GitLab.
