# ADR-038: Deterministic LLM Response Enforcement

## Zusammenfassung

Das ADR wurde erstellt und finalisiert. Es adressiert:

### 1. Response Enforcement (Hauptfeature)

- **ResponseEnforcer**: Wrapper um ClaudeRunner mit max 2 Retries
- **Validators**:
  - `StepMarkerValidator` - Prüft STEP-Marker am Ende jeder Antwort
  - `ADRStructureValidator` - Prüft ADR-Pflicht-Sections und YAML-Header
  - `FileExistenceValidator` - Prüft ob files.modify nur existierende Dateien referenziert
- **Retry mit --continue**: Nutzt Claude's Session-Continuation für schnelles Retry
- **Fallback-Heuristiken**: Wenn max_retries erreicht, wird z.B. Step-Marker automatisch ergänzt
- **Open WebUI Integration**: Fehler werden als spezielle Events gestreamt

### 2. Code Cleanup

- **Toter Code entfernen**: `_generate_session_id_stable()`, `generate_session_id()`, `_find_or_create_session_id()`
- **Hardcoded Paths**: 30+ Stellen von `/home/aiuser01/...` → `HELIX_ROOT` Variable
- **.bak Dateien löschen**: 2 Backup-Dateien in api/

### 3. Bug-006 Status Update

Bug-006 (Chat-History wird nicht übergeben) wurde bereits in Commit `c93c1ad` gefixt. Status in `bugs/INDEX.md` wurde auf DONE gesetzt.

---

## Dateien

| Aktion | Datei |
|--------|-------|
| ✅ Erstellt | `adr/038-deterministic-llm-response-enforcement.md` |
| ✅ Aktualisiert | `adr/INDEX.md` (ADR-035 und ADR-038 hinzugefügt) |
| ✅ Aktualisiert | `bugs/INDEX.md` (Bug-006 → DONE) |

---

## Nächste Schritte

1. **ADR reviewen** - Prüfe ob die Akzeptanzkriterien vollständig sind
2. **Implementation starten** - Kann als Evolution-Projekt ausgeführt werden
3. **Cleanup zuerst** - Toter Code und Hardcoded Paths sind schnelle Wins

---

## Architektur-Diagramm

```
┌─────────────────────────────────────────────────────────────────┐
│                    LLM Response Flow                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ClaudeRunner                                                   │
│       │                                                          │
│       ▼                                                          │
│   ┌───────────────────┐                                          │
│   │ ResponseEnforcer  │◄─── Wrapper um ClaudeRunner              │
│   │                   │                                          │
│   │ • max_retries: 2  │                                          │
│   │ • validators: []  │                                          │
│   └─────────┬─────────┘                                          │
│             │                                                    │
│             ▼                                                    │
│   ┌───────────────────┐                                          │
│   │  Validators       │                                          │
│   │  ─────────────    │                                          │
│   │  • StepMarker     │                                          │
│   │  • ADRStructure   │                                          │
│   │  • FileExistence  │                                          │
│   └─────────┬─────────┘                                          │
│             │                                                    │
│     ┌───────┴───────┐                                            │
│     │               │                                            │
│     ▼               ▼                                            │
│  VALID           INVALID                                         │
│     │               │                                            │
│     ▼               ▼                                            │
│  Return         Retry mit Feedback                               │
│                     │                                            │
│              ┌──────┴──────┐                                     │
│              │             │                                     │
│              ▼             ▼                                     │
│         Success      Max Retries → Fallback oder Stream Error    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

*ADR-038 Proposed | Nächste freie ADR-Nummer: 039*
