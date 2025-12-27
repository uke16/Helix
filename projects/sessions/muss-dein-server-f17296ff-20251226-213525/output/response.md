# Analyse: Server-Reload, ADR-013 Status & Empfehlung

## 1. Server-Neustart Frage

**Der HELIX Server läuft aktuell:**
```
aiuser01 3924085  python3 -m uvicorn helix.api.main:app --port 8001
```

**Antwort:** Ja, der Server muss neugestartet werden um Code-Änderungen zu laden.

Uvicorn läuft OHNE `--reload` Flag, daher kein Auto-Reload. Um den 600s Timeout und andere Änderungen zu aktivieren:

```bash
# Server neustarten
pkill -f "uvicorn helix.api.main:app"
cd /home/aiuser01/helix-v4 && \
  source config/env.sh && \
  PYTHONPATH=src python3 -m uvicorn helix.api.main:app --host 0.0.0.0 --port 8001 &
```

---

## 2. ADR-013 Status-Analyse

### Was existiert (aus letzter Session korrekt):

| Modul | Pfad | Status |
|-------|------|--------|
| StreamParser | `src/helix/debug/stream_parser.py` | **Existiert** |
| ToolTracker | `src/helix/debug/tool_tracker.py` | **Existiert** |
| CostCalculator | `src/helix/debug/cost_calculator.py` | **Existiert** |
| Events | `src/helix/debug/events.py` | **Existiert** |
| LiveDashboard | `src/helix/debug/live_dashboard.py` | **Existiert** |

### Was fehlt (OpenAI Route Integration):

Die **kritische letzte Meile** - die Integration in die OpenAI Route:
- `src/helix/api/routes/openai.py` nutzt die Debug-Module NICHT
- Claude wird aufgerufen, aber ohne `--output-format stream-json`
- Kein Live-Streaming von Tool Calls/Status an Open WebUI

---

## 3. Empfehlung: Wie weitermachen?

### Kein neues ADR nötig!

ADR-013 ist **vollständig spezifiziert** und hat Status `Implemented` im YAML Header (obwohl die Integration fehlt). Die Module existieren - nur die letzte Integration fehlt.

**Was fehlt laut Akzeptanzkriterien:**
- `[ ] ClaudeRunner.run_phase_debug() funktioniert`
- `[ ] SSE Events werden an Dashboard gestreamt`

### Nächsten Chat starten mit:

```
Fertigstelle die ADR-013 Integration in die OpenAI Route.

Status:
- Debug-Module existieren in src/helix/debug/
- Was fehlt: Integration in src/helix/api/routes/openai.py

Aufgabe:
1. ClaudeRunner um run_phase_debug() erweitern
   - Mit --output-format stream-json aufrufen
   - StreamParser nutzen um Events zu parsen

2. OpenAI Route auf echtes Streaming umstellen
   - Statt "warten bis fertig + wort-für-wort streamen"
   - Live Events streamen während Claude arbeitet

3. Tool Calls als Status an Open WebUI senden
   - Format: "Thinking..." / "Reading file X..." etc.

Die Debug-Module und ADR-013 haben alle Details.
Workflow: intern-simple (2-3 Dateien, klar definiert)
```

### Workflow-Auswahl: `intern-simple`

- **Scope**: 2-3 Dateien (claude_runner.py, openai.py, evtl. models.py)
- **Module existieren**: Nur Wiring/Integration
- **ADR hat Details**: Implementation bereits dokumentiert

---

## 4. Zusammenfassung

| Frage | Antwort |
|-------|---------|
| Server neustarten? | **Ja** - kein Auto-Reload aktiv |
| ADR-013 Status? | **Teils implementiert** - Module da, Integration fehlt |
| Neues ADR (13b)? | **Nein** - ADR-013 reicht |
| Wie starten? | Mit obigem Prompt, Workflow `intern-simple` |

---

*Session: muss-dein-server-f17296ff-20251226-213525*
*Analysiert: 2025-12-26*
