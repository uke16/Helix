# Claude Code Project: MCP Server 032

## Mission

Implementiere ADR-032 via HELIX Evolution Workflow.

**KRITISCH:** Dokumentiere JEDEN manuellen Eingriff in `MANUAL_INTERVENTIONS.md`

---

## Workflow

Dieses Projekt wird via HELIX API orchestriert:

```bash
# Start:
curl -X POST http://localhost:8001/helix/execute \
  -d '{"project_path": "projects/evolution/mcp-server-032"}'

# Status:
curl http://localhost:8001/helix/jobs/{job_id}

# Nach Completion:
curl -X POST http://localhost:8001/helix/evolution/projects/mcp-server-032/deploy
curl -X POST http://localhost:8001/helix/evolution/projects/mcp-server-032/validate
curl -X POST http://localhost:8001/helix/evolution/projects/mcp-server-032/integrate
```

---

## Phasen

| Phase | Name | Output |
|-------|------|--------|
| 0 | Base Server | mcp/base/*.py |
| 1 | Hardware Server | mcp/hardware/*.py |
| 2 | Documentation | docs, skills |
| 3 | Integration Test | ITERATION_LOG |
| 4 | Deploy Test | - |
| 5 | Production | - |

---

## Bei manuellen Eingriffen

Schreibe in `MANUAL_INTERVENTIONS.md`:

```markdown
## Intervention {n} - Phase {x}

**Problem:** Was passiert?
**Lösung:** Was manuell gemacht?
**Kategorie:** [BUG|MISSING_FEATURE|UNCLEAR_ADR|EXTERNAL]
**Vorschlag:** Wie automatisieren?
```

---

## Source of Truth

Lies: `ADR-032.md`

---

## Nach Abschluss

Fülle `BUGS_AND_IMPROVEMENTS.md` aus → Input für Workflow-Verbesserungen.
