# Sub-Phase 14.2: helix-v4-test Setup

## Ziel

Erstelle das Test-System als separates Verzeichnis mit Docker-Konfiguration.

## Referenz

- `/home/aiuser01/helix-v3-test/docker/testsystem/docker-compose.yaml` (Beispiel von v3)
- `../../docs/EVOLUTION-CONCEPT.md`

## Aufgabe

1. Erstelle `output/docker-compose.test.yaml` mit Test-Ports:
   - HELIX API: 9001
   - PostgreSQL: 5433
   - Neo4j HTTP: 7475, Bolt: 7688
   - Qdrant: 6335, 6336
   - Redis: 6380

2. Erstelle `output/.env.test` mit Test-Credentials

3. Erstelle `output/setup-test-system.sh`:
   - Clone helix-v4 nach helix-v4-test
   - Kopiere Docker-Konfiguration
   - Starte Container

## Output

- `output/docker-compose.test.yaml`
- `output/.env.test`
- `output/setup-test-system.sh`
