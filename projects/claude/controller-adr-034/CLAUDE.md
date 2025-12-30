# Controller: ADR-034 (Consultant Flow Refactoring - LLM-Native)

Du supervisest den Evolution Workflow für ADR-034.

## Kontext

ADR-034 wurde vom Audit-Orchestrator erstellt. Es refactored die kaputte State-Machine im Consultant zu einem LLM-nativen Flow.

**ADR**: `/home/aiuser01/helix-v4/adr/034-consultant-flow-refactoring-llm-native.md`
**Audit Findings**: `/home/aiuser01/claude-memory/audit-orchestrator/phase-1-result.md`

## Aufgaben

1. **Skills lesen** - Verstehe HELIX Evolution Workflow
2. **Projekt erstellen** - Evolution-Projekt für ADR-034
3. **Phasen ausführen** - /helix/execute für jede Phase
4. **Überwachen** - Job-Status tracken bis COMPLETED/FAILED
5. **Eingreifen** - Bei Problemen dokumentieren + fixen
6. **Deployen** - deploy → validate → integrate
7. **Dokumentieren** - MANUAL_INTERVENTIONS.md + BUGS.md

## Skills zuerst lesen

```bash
cat /home/aiuser01/helix-v4/skills/helix/SKILL.md
cat /home/aiuser01/helix-v4/skills/helix/evolution/SKILL.md
cat /home/aiuser01/helix-v4/skills/helix/adr/SKILL.md
```

## Projekt erstellen

```bash
# Projekt-Verzeichnis
mkdir -p /home/aiuser01/helix-v4/projects/evolution/consultant-refactor-034

# ADR kopieren
cp /home/aiuser01/helix-v4/adr/034-consultant-flow-refactoring-llm-native.md \
   /home/aiuser01/helix-v4/projects/evolution/consultant-refactor-034/ADR-034.md

# phases.yaml erstellen (oder via Consultant)
```

## Erwartete Phasen

Basierend auf ADR-034:

1. **01-analysis** - Verstehe extract_state_from_messages() komplett
2. **02-simplify-state** - Entferne Index-Logik, behalte nur notwendiges
3. **03-template-refactor** - Ein Template ohne step-Branches
4. **04-llm-output-step** - LLM setzt Step-Marker, Python extrahiert
5. **05-testing** - Alle Szenarien testen (one-shot, iterativ, etc.)
6. **06-documentation** - Docs aktualisieren

## API Commands

```bash
# Start
curl -X POST http://localhost:8001/helix/execute \
  -H "Content-Type: application/json" \
  -d '{"project_path": "projects/evolution/consultant-refactor-034"}'

# Status
curl http://localhost:8001/helix/jobs/{job_id}

# Deploy Pipeline
curl -X POST http://localhost:8001/helix/evolution/projects/consultant-refactor-034/deploy
curl -X POST http://localhost:8001/helix/evolution/projects/consultant-refactor-034/validate  
curl -X POST http://localhost:8001/helix/evolution/projects/consultant-refactor-034/integrate
```

## Bei Problemen dokumentieren

→ `projects/evolution/consultant-refactor-034/MANUAL_INTERVENTIONS.md`

```markdown
## Intervention 1: [Datum]
**Phase**: [welche Phase]
**Problem**: [was ging schief]
**Lösung**: [was du gemacht hast]
**Vorschlag**: [wie HELIX das selbst machen könnte]
```

## Nach Abschluss

→ `projects/evolution/consultant-refactor-034/BUGS_AND_IMPROVEMENTS.md`

```markdown
## Bugs
- [ ] Bug 1: ...

## Improvements
- [ ] Improvement 1: ...
```

## Akzeptanzkriterien aus ADR-034

- [ ] Kein `step` Variable mehr in SessionState (oder nur für Logging)
- [ ] Kein `extract_state_from_messages` mit Index-Logik mehr
- [ ] Template hat keine `{% if step == "..." %}` Branches
- [ ] Consultant funktioniert mit beliebiger Message-Anzahl
- [ ] User kann in 1 Message alles spezifizieren
- [ ] User kann in 10 Messages iterieren
- [ ] ADR-Erstellung funktioniert ohne Magic Trigger Words

## Feature Flag

ADR-034 empfiehlt ein Feature-Flag für Migration:
```
HELIX_USE_LLM_FLOW=true
```

Das ermöglicht Parallel-Betrieb mit Fallback.
