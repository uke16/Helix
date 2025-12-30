# Controller: ADR-032 (MCP Server Hardware Teststand)

Du supervisest den Evolution Workflow für ADR-032.

## Aufgaben

1. **Skills lesen** - Verstehe das System
2. **Consultant nutzen** - Projekt erstellen (oder manuell)
3. **Überwachen** - Job-Status tracken
4. **Eingreifen** - Bei Problemen dokumentieren + fixen
5. **Deployen** - deploy → validate → integrate
6. **Dokumentieren** - MANUAL_INTERVENTIONS.md + BUGS.md

## Skills zuerst

```bash
cat /home/aiuser01/helix-v4/skills/helix/SKILL.md
cat /home/aiuser01/helix-v4/skills/helix/evolution/SKILL.md
cat /home/aiuser01/helix-v4/skills/helix/adr/SKILL.md
```

## ADR

`/home/aiuser01/helix-v4/adr/032-mcp-server-hardware-teststand.md`

## Workflow

```bash
# 1. Start
curl -X POST http://localhost:8001/helix/execute \
  -H "Content-Type: application/json" \
  -d '{"project_path": "projects/evolution/mcp-server-032"}'

# 2. Überwachen
curl http://localhost:8001/helix/jobs/{job_id}

# 3. Deploy Pipeline
curl -X POST http://localhost:8001/helix/evolution/projects/mcp-server-032/deploy
curl -X POST http://localhost:8001/helix/evolution/projects/mcp-server-032/validate
curl -X POST http://localhost:8001/helix/evolution/projects/mcp-server-032/integrate
```

## Bei Problemen

→ `projects/evolution/mcp-server-032/MANUAL_INTERVENTIONS.md`

## Nach Abschluss

→ `projects/evolution/mcp-server-032/BUGS_AND_IMPROVEMENTS.md`

## Bekannte Lücke

POST /helix/evolution/projects fehlt → Projekt manuell erstellen
