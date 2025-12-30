# Antwort zu Projektstruktur-Fragen

Ich habe die bestehende Verzeichnisstruktur unter `/home/aiuser01/` analysiert und gebe dir meine Empfehlungen.

---

## Frage 1: Wo sollte der MCP Server fuer Hardware-Teststande liegen?

### Meine Empfehlung: `/home/aiuser01/docker/mcp-servers/hardware/`

**Begruendung:**

1. **Bestehende Struktur**: Es gibt bereits ein `/home/aiuser01/docker/mcp-servers/` Verzeichnis mit einer README.md, die eine geplante Struktur fuer MCP Server dokumentiert (siehe Zeile 63-83 der README).

2. **Konsistenz**: Die README zeigt die Konvention:
   ```
   docker/mcp-servers/
   ├── servers/
   │   ├── filesystem/
   │   ├── database/
   │   ├── web/
   │   └── code-exec/
   ```
   Dein `hardware/` Server passt perfekt in diese Struktur.

3. **Docker-Integration**: Der Ordner liegt unter `docker/`, was bedeutet:
   - Docker Compose Integration ist vorbereitet
   - Netzwerk-Konfiguration mit anderen Diensten (qdrant, neo4j, redis) ist einfacher
   - Port-Management ist zentralisiert

4. **Gegen die anderen Optionen**:
   - `/home/aiuser01/mcp-hardware/` - Wuerde die Struktur fragmentieren. Aktuell existiert dort nur `mcp-chrome-server/` als Einzelprojekt (Altlast aus Experimenten)
   - `/home/aiuser01/mcp/hardware/` - Das Verzeichnis `/home/aiuser01/mcp/` existiert nicht, waere eine neue Top-Level Struktur

### Empfohlene Struktur:

```
/home/aiuser01/docker/mcp-servers/
├── README.md                    # (existiert bereits)
├── docker-compose.yml           # (zu erstellen)
├── hardware/                    # <- DEIN NEUER SERVER
│   ├── Dockerfile
│   ├── server.py               # oder main.py
│   ├── requirements.txt
│   └── README.md               # J-Link API Referenz hier oder...
└── servers/                     # (geplante Struktur)
    ├── filesystem/
    └── ...
```

---

## Frage 2: Wo gehoert die J-Link REST API Dokumentation hin?

### Option A (Empfohlen fuer MCP-Server-spezifische Doku):

```
/home/aiuser01/docker/mcp-servers/hardware/docs/JLINK-API.md
```

Wenn die Doku primaer fuer die Entwicklung des MCP Servers relevant ist.

### Option B (Empfohlen fuer HELIX/Claude-weite Verfuegbarkeit):

Erstelle einen neuen HELIX Skill:

```
/home/aiuser01/helix-v4/skills/hardware/
├── SKILL.md           # Hauptdatei (wird von Claude gelesen)
├── jlink/
│   └── SKILL.md       # J-Link spezifische Details
└── fpga/
    └── SKILL.md       # FPGA-Board spezifische Details
```

**Vorteile von Option B:**
- Automatische Auffindbarkeit durch HELIX Consultants
- Strukturiert nach Domain (wie `pdm/`, `encoder/`, `infrastructure/`)
- Wiederverwendbar fuer weitere Hardware-Projekte
- Passt in das HELIX Skills-System (siehe `skills/helix/SKILL.md`)

### Skill Template fuer Hardware:

```markdown
# Hardware Domain Skill

## Overview
Hardware-Teststande und Embedded-Geraete fuer POSITAL.

## J-Link REST API
- Endpoint: http://<board-ip>:19080/
- Authentifizierung: ...
- Hauptoperationen:
  - GET /device - Geraeteinformationen
  - POST /flash - Firmware flashen
  - ...

## FPGA Boards
- Modell: ...
- Konfiguration: ...
```

---

## Klaerende Frage

Bevor ich eine finale Empfehlung geben kann:

**Wie wird der MCP Hardware Server primaer genutzt werden?**

1. **Nur von HELIX/Claude Code** - Dann ist der Skill-Ansatz (Option B) besser
2. **Auch von anderen Tools/Teams** - Dann Dokumentation im MCP Server selbst (Option A)
3. **Beides** - Dann kurze Referenz im Skill, Details im MCP Server

---

## Naechste Schritte

Wenn du mit meinen Empfehlungen einverstanden bist:

1. Erstelle `/home/aiuser01/docker/mcp-servers/hardware/`
2. Entscheide wo die J-Link Doku primaer leben soll
3. Optional: Soll ich einen ADR fuer die MCP Hardware Integration erstellen?

Lass mich wissen, wie du vorgehen moechtest!
