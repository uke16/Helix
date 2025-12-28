# Projekt gestartet: ADR-029 Session Persistence

## Bestätigung

Das Evolution-Projekt für **ADR-029: Open WebUI Session Persistence** wurde mit dem vollständigen **intern-simple** Workflow erstellt.

## Session-ID für Tracking

```
Projekt-Pfad: projects/internal/adr-029-session-persistence/
Session-ID:   problem-consultant-chat-2d6ce79a-20251228-002659
ADR:          ADR-029
```

## Workflow-Phasen (7 Phasen)

Das Projekt verwendet den `intern-simple` Workflow mit vollständigem Deploy-Zyklus:

| # | Phase | Typ | Beschreibung |
|---|-------|-----|--------------|
| 1 | **Planning & ADR** | consultant | ADR bereits erstellt (ADR-029) |
| 2 | **Development** | development | Implementierung des SessionManager mit X-Conversation-ID Support |
| 3 | **Verification** | test | Unit Tests für SessionManager |
| 4 | **Documentation** | documentation | Update ARCHITECTURE-MODULES.md |
| 5 | **Deploy to Test** | deploy | Deploy zum Test-System |
| 6 | **E2E Tests** | test | End-to-End Tests auf Test-System |
| 7 | **Deploy to Production** | deploy | Integration ins Produktiv-System + API Restart |

## Was du erwarten kannst

1. **Phasen-Ausführung**: Jede Phase wird von einer Claude Code Instanz bearbeitet
2. **Sub-Agent Verifikation**: Nach jeder Phase (außer Docs) prüft ein Sub-Agent den Output
3. **Automatischer Retry**: Bei Problemen bis zu 3 Retries mit Feedback
4. **Deploy-Zyklus**: Test-Deploy → Validierung → Production-Deploy

## Nächster Schritt

Starte den Workflow via API:

```bash
curl -X POST http://localhost:8001/helix/execute \
  -H "Content-Type: application/json" \
  -d '{"project_path": "projects/internal/adr-029-session-persistence/"}'
```

Oder überspringe die Planning-Phase (ADR existiert bereits):

```bash
curl -X POST http://localhost:8001/helix/execute \
  -H "Content-Type: application/json" \
  -d '{"project_path": "projects/internal/adr-029-session-persistence/", "phase_filter": "development"}'
```

## Projekt-Struktur

```
projects/internal/adr-029-session-persistence/
├── ADR-029.md          # Single Source of Truth (Link zu adr/)
├── phases.yaml         # intern-simple Workflow (7 Phasen)
├── status.json         # Aktueller Status
└── phases/
    ├── 1/ (planning)
    ├── 2/ (development)
    ├── 3/ (verify)
    ├── 4/ (documentation)
    ├── 5/ (deploy-test)
    ├── 6/ (e2e)
    └── 7/ (deploy-prod)
```

---

**Status**: PENDING - Bereit für Ausführung
