# ADR-033: MCP Blueprint Server - FINALISIERT

Das ADR wurde erfolgreich erstellt, validiert und finalisiert.

---

## Status

| Schritt | Status |
|---------|--------|
| ADR erstellt | **ERLEDIGT** |
| ADR validiert | **ERLEDIGT** (valid mit 6 Warnungen*) |
| ADR finalisiert | **ERLEDIGT** |

*Die Warnungen sind nur Formathinweise (Subsection-Headers), nicht inhaltliche Fehler.

---

## Finale Datei

```
/home/aiuser01/helix-v4/adr/033-mcp-blueprint-server---modulare-remote-fähige-arch.md
```

---

## Architektur-Zusammenfassung

### Drei-Schichten-Modell

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Layer 3: Composed Servers                            │
│  ┌──────────────────────┐  ┌──────────────────────┐                     │
│  │  fraba-internal      │  │  fraba-external      │                     │
│  │  - Hardware ✓        │  │  - HELIX ✓           │                     │
│  │  - HELIX ✓           │  │  - Consultant ✓      │                     │
│  │  - Consultant ✓      │  │  (NO Hardware!)      │                     │
│  │  No Auth             │  │  OAuth 2.1           │                     │
│  └──────────────────────┘  └──────────────────────┘                     │
└──────────────────────────────────────────────────────────────────────────┘
                              │ mount()
┌─────────────────────────────────────────────────────────────────────────┐
│                     Layer 2: Services                                    │
│  HardwareService  │  HELIXService  │  ConsultantService  │  PDMService  │
│  (ADR-032)        │  (NEU)         │  (NEU)              │  (später)    │
└──────────────────────────────────────────────────────────────────────────┘
                              │ extends
┌─────────────────────────────────────────────────────────────────────────┐
│                     Layer 1: Blueprint Base                              │
│  BlueprintMCP(FastMCP) + OAuth Middleware + Config                      │
└──────────────────────────────────────────────────────────────────────────┘
```

### Tools pro Service

| Service | Tools |
|---------|-------|
| **Hardware** (ADR-032) | station_acquire, station_release, station_connect, station_registers, station_flash, etc. |
| **HELIX** (NEU) | phase_status, list_jobs, run_quality_gate, escalate_to_consultant |
| **Consultant** (NEU) | skill_search, adr_search, list_skills, read_skill |
| **PDM** (später) | TBD |

### Auth-Matrix

| Server | Netzwerk | Auth | Exposed Services |
|--------|----------|------|------------------|
| fraba-internal | LAN/VPN | None | Hardware, HELIX, Consultant |
| fraba-external | Internet | OAuth 2.1 | HELIX, Consultant (NO Hardware!) |

---

## Akzeptanzkriterien (5 Phasen)

1. **Phase 0: Blueprint Base** - BlueprintMCP, OAuth middleware, Config
2. **Phase 1: Hardware Refactor** - ADR-032 als mountbares Modul
3. **Phase 2: HELIX Service** - Orchestrator-Integration
4. **Phase 3: Consultant Service** - RAG/Semantic Search
5. **Phase 4: Composed Servers** - fraba-internal + fraba-external

---

## Nächste Schritte

Das ADR ist jetzt in `adr/` und kann implementiert werden.

Optionen:
1. **Evolution Projekt erstellen** - phases.yaml für die 5 Phasen
2. **Direkt implementieren** - Manuell mit dem Code anfangen
3. **Review anfordern** - Jemanden das ADR reviewen lassen

**Was möchtest du als nächstes tun?**
