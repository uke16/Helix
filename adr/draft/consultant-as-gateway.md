# Draft: Consultant als einziger Gateway

**Status:** Draft / Architecture Vision
**Erstellt:** 2024-12-24

---

## Vision: Eine Interaktion für alles

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER INTERAKTION                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  User: "Welche ADRs haben wir?"                                         │
│  Consultant: [ruft list_adrs() auf] → "Wir haben 22 ADRs..."            │
│                                                                         │
│  User: "Lass uns ADR-022 implementieren"                                │
│  Consultant: [ruft implement_adr("022") auf] → "Starte Implementation"  │
│                                                                         │
│  User: "Lass uns ein neues ADR für X diskutieren"                       │
│  Consultant: [diskutiert] → [ruft create_adr() auf]                     │
│                                                                         │
│  User: "Lass uns ein externes Python Tool bauen"                        │
│  Consultant: [diskutiert] → [ruft create_external_project() auf]        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Architektur

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│                    ┌───────────────────┐                                │
│                    │   Open WebUI      │                                │
│                    │   Claude.ai       │                                │
│                    │   CLI             │                                │
│                    └─────────┬─────────┘                                │
│                              │                                          │
│                              ▼                                          │
│                    ┌───────────────────┐                                │
│                    │   HELIX API       │                                │
│                    │   /v1/chat/...    │                                │
│                    └─────────┬─────────┘                                │
│                              │                                          │
│                              ▼                                          │
│              ┌───────────────────────────────┐                          │
│              │        CONSULTANT             │                          │
│              │   (LLM mit Function Calling)  │                          │
│              └───────────────┬───────────────┘                          │
│                              │                                          │
│         ┌────────────────────┼────────────────────┐                     │
│         │                    │                    │                     │
│         ▼                    ▼                    ▼                     │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐              │
│  │ list_adrs() │      │implement_   │      │create_      │              │
│  │             │      │adr()        │      │project()    │              │
│  └─────────────┘      └──────┬──────┘      └─────────────┘              │
│                              │                                          │
│                              ▼                                          │
│                    ┌───────────────────┐                                │
│                    │  UnifiedOrchest.  │                                │
│                    │  (ADR-022)        │                                │
│                    └─────────┬─────────┘                                │
│                              │                                          │
│                              ▼                                          │
│                    ┌───────────────────┐                                │
│                    │   Claude Code     │                                │
│                    │   (Sub-Agent)     │                                │
│                    └───────────────────┘                                │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Consultant Tools

```python
# Tools die der Consultant aufrufen kann

@tool
def list_adrs() -> list[ADRSummary]:
    """Liste alle ADRs mit Status."""
    pass

@tool
def show_adr(adr_id: str) -> str:
    """Zeige ADR Details."""
    pass

@tool  
def create_adr(
    title: str,
    description: str,
    project_type: Literal["helix_internal", "helix_external"]
) -> str:
    """Erstelle neues ADR nach Diskussion."""
    pass

@tool
def implement_adr(adr_id: str) -> str:
    """Starte Implementation eines ADR."""
    # Ruft UnifiedOrchestrator auf
    pass

@tool
def list_projects() -> list[ProjectSummary]:
    """Liste alle Projekte."""
    pass

@tool
def resume_project(project_id: str) -> str:
    """Setze Projekt fort."""
    pass

@tool
def create_external_project(
    name: str,
    description: str,
) -> str:
    """Erstelle externes (nicht-HELIX) Projekt."""
    pass
```

## Beispiel-Interaktionen

### 1. ADR Liste abfragen

```
User: Welche ADRs haben wir?

Consultant: [list_adrs()]

Consultant: Wir haben 22 ADRs:
- ADR-001 bis ADR-015: Implemented
- ADR-017: Superseded (by 022)
- ADR-018-021: Proposed
- ADR-022: Proposed (Unified API)

Welches interessiert dich?
```

### 2. ADR implementieren

```
User: Lass uns ADR-022 implementieren

Consultant: ADR-022 "Unified API Architecture" hat 5 Phasen:
1. UnifiedOrchestrator erstellen
2. API Endpoints aktualisieren
3. CLI als API Client
4. Aufräumen (Code löschen)
5. Integration Test

Soll ich den Implementierungszyklus starten?

User: Ja

Consultant: [implement_adr("022")]

Consultant: ✅ Implementation gestartet (Job: job-abc123)
Phase 1 läuft... Du kannst mit `helix logs job-abc123` den Status sehen.
```

### 3. Neues ADR diskutieren

```
User: Ich möchte ein Tool bauen das PDFs analysiert

Consultant: Interessant! Lass mich verstehen:
- Soll das Tool in HELIX integriert werden oder standalone?
- Welche Art von Analyse? Text-Extraktion, Zusammenfassung?
- Gibt es bestehende Tools die du erweitern willst?

User: Standalone, für meine Arbeit. Text-Extraktion und Zusammenfassung.

Consultant: OK, das wäre ein externes Projekt (nicht HELIX-intern).
Ich würde vorschlagen:
- Python CLI Tool
- PyMuPDF für Extraktion
- Claude API für Zusammenfassung

Soll ich ein ADR dafür erstellen?

User: Ja

Consultant: [create_adr(
    title="PDF Analysis Tool",
    description="CLI tool für PDF Text-Extraktion und AI-Zusammenfassung",
    project_type="helix_external"
)]

Consultant: ✅ ADR-023 erstellt: "PDF Analysis Tool"
Soll ich das Projekt aufsetzen?
```

## Vorteile

1. **Ein Einstiegspunkt**: Egal ob CLI, WebUI, API - alles geht durch Consultant
2. **Natürliche Sprache**: User muss keine Commands kennen
3. **Kontext-Erhaltung**: Consultant erinnert sich an Diskussion
4. **Delegation**: Consultant delegiert komplexe Aufgaben an Sub-Agents
5. **Open WebUI kompatibel**: /v1/chat/completions → Consultant

## Nächste Schritte

- [ ] Consultant Tools definieren (ADR-023?)
- [ ] Tool-Implementierung in API
- [ ] Open WebUI Integration testen
- [ ] Beispiel-Sessions dokumentieren
