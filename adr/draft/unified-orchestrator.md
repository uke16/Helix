# Draft: Unified Orchestrator - Eine Implementierung für alle Entry Points

**Status:** Draft / Critical Architecture Issue
**Erstellt:** 2024-12-24

---

## Kontext: Das Chaos

### Aktuelle Situation

Es gibt **DREI** verschiedene Orchestrator-Implementierungen:

| Datei | Genutzt von | Zeilen | Features |
|-------|-------------|--------|----------|
| `orchestrator_legacy.py` | CLI (`helix run`) | 417 | Quality Gates, Escalation |
| `streaming.py` | API (`/helix/execute`) | 400+ | Verification, SSE Events |
| `orchestrator/` package | **NIEMAND** | ~2000 | ADR-017, OrchestratorRunner |

### Warum ist das passiert?

1. **Ursprünglich:** `orchestrator.py` für CLI
2. **Dann:** API brauchte Streaming → `streaming.py` mit eigener Logik
3. **Dann:** ADR-017 definiert neuen Orchestrator → `orchestrator/` package
4. **Dann:** Package shadowed Module → Renamed zu `orchestrator_legacy.py`
5. **Resultat:** 3 Implementierungen, keine einheitliche Nutzung

### Konkrete Probleme

```
CLI (helix run):
├── Nutzt orchestrator_legacy.py
├── ❌ Keine Verification (ADR-011 nicht integriert)
├── ✅ Quality Gates funktionieren
└── ❌ Kein Streaming Output

API (/helix/execute):
├── Nutzt streaming.py
├── ✅ Verification integriert
├── ⚠️ Eigene Quality Gate Logik
└── ✅ SSE Streaming

orchestrator/ package:
├── Nutzt NIEMAND
├── ✅ Sauber designed (ADR-017)
├── ✅ DataFlowManager, PhaseExecutor, StatusTracker
└── ❌ Nicht integriert
```

---

## Entscheidungsbedarf

### Option A: orchestrator_legacy.py als Standard

```
CLI ──────────────┐
                  ▼
API ────────► orchestrator_legacy.py ───► ClaudeRunner
                  ▲
Open WebUI ───────┘
```

**Pro:**
- Funktioniert bereits
- Weniger Refactoring

**Contra:**
- "Legacy" im Namen
- Verification muss nachgerüstet werden
- Kein Streaming eingebaut

### Option B: orchestrator/ package als Standard

```
CLI ──────────────┐
                  ▼
API ────────► orchestrator/runner.py ───► ClaudeRunner
                  ▲
Open WebUI ───────┘
```

**Pro:**
- Sauber designed (ADR-017)
- Zukunftssicher
- Alle Features eingebaut

**Contra:**
- Noch nicht integriert
- Mehr Refactoring nötig

### Option C: API ruft CLI auf

```
CLI ◄───────────────────────────────┐
  │                                 │
  ▼                                 │
orchestrator_legacy.py         API (Proxy)
  │                                 ▲
  ▼                                 │
ClaudeRunner                  Open WebUI
```

**Pro:**
- Eine Implementierung
- CLI ist "Single Source of Truth"

**Contra:**
- Keine echten SSE Events
- Umständlich

### Option D: Thin API Layer über orchestrator/

```
                    ┌─────────────────┐
                    │ orchestrator/   │
                    │ runner.py       │
                    │ (Core Logic)    │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ CLI Adapter   │    │ API Adapter   │    │ WebUI Adapter │
│ (helix run)   │    │ (FastAPI)     │    │ (OpenAI)      │
└───────────────┘    └───────────────┘    └───────────────┘
```

**Pro:**
- Saubere Trennung
- Ein Core, mehrere Adapter
- Einfach zu testen

**Contra:**
- Mehr Aufwand initial

---

## Empfehlung: Option D

### Warum?

1. **orchestrator/ package existiert bereits** (ADR-017)
2. **Adapter Pattern** ist Standard für Multi-Interface Apps
3. **Verification, Quality Gates, Escalation** einmal implementieren
4. **Streaming** kann im API Adapter hinzugefügt werden

### Migration

```
Phase 1: orchestrator/ package finalisieren
├── OrchestratorRunner als Haupt-Entry
├── Verification integrieren (ADR-011)
├── Quality Gates vereinheitlichen
└── Escalation aus orchestrator_legacy übernehmen

Phase 2: CLI Adapter
├── helix run nutzt OrchestratorRunner
├── orchestrator_legacy.py deprecated
└── Progress Output (nicht SSE, aber informativ)

Phase 3: API Adapter
├── streaming.py wird thin wrapper
├── SSE Events vom OrchestratorRunner
└── OpenAI-kompatibel für Open WebUI

Phase 4: Cleanup
├── orchestrator_legacy.py löschen
├── Duplikate in streaming.py entfernen
└── Tests konsolidieren
```

---

## Offene Fragen

1. **Wie viel von orchestrator_legacy.py ist noch relevant?**
   - Escalation Logic?
   - Quality Gate Runner?

2. **Was fehlt in orchestrator/ package?**
   - Verification Integration
   - SSE Event Emission

3. **Open WebUI: Was genau brauchen wir?**
   - Nur /v1/chat/completions?
   - Oder auch /v1/completions?
   - Model Switching?

---

## Nächste Schritte

- [ ] Audit: Was kann orchestrator/ was orchestrator_legacy nicht kann?
- [ ] Audit: Was kann orchestrator_legacy was orchestrator/ nicht kann?
- [ ] Entscheidung: Welche Option?
- [ ] ADR schreiben: Unified Orchestrator Architecture
- [ ] Implementation

---

## Verwandte ADRs

- ADR-017: Phase Orchestrator (definiert orchestrator/ package)
- ADR-011: Post-Phase Verification
- ADR-004: Escalation System
