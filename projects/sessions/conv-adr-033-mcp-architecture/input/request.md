# User Request

Ich brauche ein ADR für eine MCP Server Architektur.

Kontext:
- Wir haben bereits einen MCP Server für Hardware-Teststände (ADR-032) gebaut
- Der liegt aktuell in mcp-backup-adr032/ (temporär verschoben)
- Wir wollen einen "Raw Blueprint" MCP Server der Remote-fähig ist (HTTPS, OAuth)
- Dieser soll mit Claude Web und ChatGPT Web funktionieren
- Services sollen modular mountbar sein (Hardware, HELIX Orchestrator, Consultant/RAG, später PDM)
- Intern vs Extern sollte über Config steuerbar sein
- HELIX selbst soll als MCP Service nutzbar sein (Phase Status, Quality Gates, Escalation)
- Consultant/RAG Service für Semantic Search über Skills

Bitte analysiere das Problem und erstelle ein ADR. Lies die relevanten Skills und die existierenden ADRs (besonders 032) um den Kontext zu verstehen.
