# Controller: ADR-038

Du supervisest den Evolution Workflow für Deterministic LLM Response Enforcement.

## Aufgaben

1. **Skills lesen** - Verstehe das System
2. **Consultant nutzen** - Projekt erstellen lassen (oder manuell)
3. **Überwachen** - Job-Status tracken
4. **Eingreifen** - Bei Problemen dokumentieren + fixen
5. **Deployen** - deploy → validate → integrate
6. **Dokumentieren** - MANUAL_INTERVENTIONS.md + BUGS.md

## Skills zuerst

```bash
cat skills/helix/SKILL.md
cat skills/helix/evolution/SKILL.md
cat skills/helix/adr/SKILL.md
```

## ADR

`adr/038-deterministic-llm-response-enforcement.md`

## Workflow starten

```bash
# Via Consultant (wenn verfügbar)
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"helix-consultant","messages":[{"role":"user","content":"Erstelle Evolution-Projekt für ADR-038"}]}'

# Oder manuell
curl -X POST http://localhost:8001/helix/execute \
  -d '{"project_path": "projects/evolution/response-enforcement-038"}'
```

## Überwachen

```bash
curl http://localhost:8001/helix/jobs/{job_id}
```

## Deploy Pipeline

```bash
curl -X POST http://localhost:8001/helix/evolution/projects/response-enforcement-038/deploy
curl -X POST http://localhost:8001/helix/evolution/projects/response-enforcement-038/validate
curl -X POST http://localhost:8001/helix/evolution/projects/response-enforcement-038/integrate
```

## Dokumentation

Bei JEDEM manuellen Eingriff → `MANUAL_INTERVENTIONS.md`
Nach Abschluss → `BUGS_AND_IMPROVEMENTS.md`
