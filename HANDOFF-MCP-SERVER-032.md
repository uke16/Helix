# Handoff: MCP Server ADR-032

**Datum:** 2025-12-30

## Start Controller

```bash
cd /home/aiuser01/helix-v4/projects/claude/controller-adr-032
claude
```

## Struktur

```
helix-v4/projects/claude/controller-adr-032/   ← Controller (START)
    │
    ▼ überwacht
helix-v4-test/projects/evolution/mcp-server-032/   ← Projekt-Daten
    │
    ▼ orchestriert
helix-v4-test/mcp/base/, mcp/hardware/             ← Output
```

## Artefakte

| Was | Pfad |
|-----|------|
| Controller | `helix-v4/projects/claude/controller-adr-032/` |
| Projekt | `helix-v4-test/projects/evolution/mcp-server-032/` |
| ADR | `helix-v4-test/adr/032-mcp-server-hardware-teststand.md` |

## Session Updates

- `helix-v4/ONBOARDING.md` - Section 8 (Controller) hinzugefügt
- `helix-v4/CLAUDE_CONTROLLER.md` - NEU erstellt
- `helix-v4-test/skills/helix/evolution/SKILL.md` - Orchestration ergänzt
- `helix-v4/templates/controller/CLAUDE.md.j2` - Template erstellt

## Bekannte Lücke

`POST /helix/evolution/projects` fehlt → Projekt manuell erstellt
