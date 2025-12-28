# User Request

### Task:
Suggest 3-5 relevant follow-up questions or prompts that the user might naturally ask next in this conversation as a **user**, based on the chat history, to help continue or deepen the discussion.
### Guidelines:
- Write all follow-up questions from the user’s point of view, directed to the assistant.
- Make questions concise, clear, and directly related to the discussed topic(s).
- Only suggest follow-ups that make sense given the chat content and do not repeat what was already covered.
- If the conversation is very short or not specific, suggest more general (but relevant) follow-ups the user might ask.
- Use the conversation's primary language; default to English if multilingual.
- Response must be a JSON array of strings, no extra text or formatting.
### Output:
JSON format: { "follow_ups": ["Question 1?", "Question 2?", "Question 3?"] }
### Chat History:
<chat_history>
USER: Problem: consultant chat session via open webui hat keine history. Jeder chat ist neue Session. Das soll nicht so sein.
  
## **Session History**
Zum **Open WebUI Session Problem** - jeder Chat ist eine neue Session:
Das liegt daran, dass der `SessionManager` die Session-ID aus:
1.  Hash der ersten Nachricht
    
2.  **Timestamp** (!)
    
generiert. Der Timestamp ändert sich bei jedem Request.
**Fix-Vorschlag für das nächste ADR:**
Open WebUI sendet einen `X-Conversation-ID` Header. Dieser sollte für die Session-Zuordnung verwendet werden statt des Timestamps.
kannst du dafür auch ein ADR erstellen und speichern?
ASSISTANT: [Starte Claude Code...]



---

Alle Aufgaben erledigt. Hier die Zusammenfassung:

---

## ✅ ADR-029 erstellt und finalisiert!

**Pfad:** `adr/029-open-webui-session-persistence---x-conversation-id.md`  
**Status:** 📋 Proposed

### Das Problem

Der SessionManager generierte Session-IDs mit Timestamp:
```python
hash_input = f"{first_message}:{timestamp}"  # Timestamp ändert sich!
```
→ Jeder Request = neue Session, keine History.

### Die Lösung

Open WebUI sendet `X-Conversation-ID` Header. Diesen als primäre Session-ID verwenden:

1. **Header First**: `X-Conversation-ID` → `conv-{id}` Session
2. **Fallback**: Ohne Header → Hash ohne Timestamp
3. **Messages persistieren**: In `context/messages.json` speichern

### Zu ändernde Dateien

| Datei | Änderung |
|-------|----------|
| `src/helix/session/manager.py` | `conversation_id` Parameter, ohne Timestamp |
| `src/helix/api/routes/openai.py` | `X-Conversation-ID` Header extrahieren |

---

### Zusammenfassung beider ADRs

| ADR | Titel | Status |
|-----|-------|--------|
| **028** | Claude Code Launcher Performance | 📋 Proposed |
| **029** | Open WebUI Session Persistence | 📋 Proposed |

Beide ADRs sind jetzt im `adr/` Verzeichnis und im INDEX.md registriert.
USER: kannst du den evolution workflow mit adr 029 starten bitte?
ASSISTANT: [Starte Claude Code...]



---

Der Evolution Workflow für ADR-029 läuft jetzt!

**Status:**
- **Job ID**: `8988415d`
- **Status**: `running`
- **Aktuelle Phase**: `development` (Implementierung)

**Projekt erstellt unter:**
```
projects/internal/adr-029-session-persistence/
├── ADR-029.md           # Die Spezifikation
├── phases.yaml          # Workflow-Definition (3 Phasen)
└── phases/              # Phase-Verzeichnisse werden erstellt
```

**Workflow-Phasen:**
1. **Development** (läuft) - Implementiert `SessionManager` und API-Route
2. **Verify** - Unit Tests für die Änderungen
3. **Documentation** - Aktualisiert `ARCHITECTURE-MODULES.md`

Du kannst den Fortschritt überwachen mit:
```bash
# Status abfragen
curl http://localhost:8001/helix/jobs/8988415d

# Live-Stream (SSE)
curl http://localhost:8001/helix/stream/8988415d
```

Soll ich den Workflow weiter überwachen und dir Updates geben?
USER: das hier habe ich geschrieben:
kannst du den evolution workflow mit adr 029 starten bitte?
du hast das projekt angelegt. aber nur mit 3 phasen. evolution workflow heisst doch dass es auf das testsystem iplementiert wird und dann auf das productoin system und dann restart von der api gemacht wird oder? ist es möglich das projekt noch zu erweitern? mit den nötigen phasen? falls das möglich ist bitte mach das
ASSISTANT: [Starte Claude Code...]



---

# Projekt ADR-029 Session Persistence - Vollständiger Evolution Workflow

## Bestätigung

Das Evolution-Projekt für **ADR-029: Open WebUI Session Persistence** wurde mit dem vollständigen Workflow erweitert.

## Session-ID für Tracking

```
Project: adr-029-session-persistence
Location: projects/internal/adr-029-session-persistence/
Status: PENDING (bereit zum Start)
```

## Workflow-Phasen (8 Phasen)

Das Projekt durchläuft jetzt den vollständigen Evolution-Zyklus:

| # | Phase | Typ | Beschreibung |
|---|-------|-----|--------------|
| 1 | **Implementation** | development | Code-Änderungen gemäß ADR-029 |
| 2 | **Unit Tests** | test | Tests für SessionManager |
| 3 | **Integration Tests** | test | API Integration Tests |
| 4 | **Deploy to Test** | deploy | Deploy zum Test-System |
| 5 | **E2E Tests** | test | End-to-End auf Test-System |
| 6 | **Deploy to Production** | deploy | Integration ins Prod-System |
| 7 | **Post-Verification** | verification | Production Health Check |
| 8 | **Documentation** | docs | ARCHITECTURE-MODULES.md Update |

## Status-Flow

```
Development → Test → Deploy-Test → E2E → Deploy-Prod → Restart → Verify → Docs
    [1]      [2,3]      [4]        [5]      [6]         [7]       [7]     [8]
```

## Was passiert als nächstes

Um den Workflow zu starten:

```bash
# Via API
curl -X POST http://localhost:8001/helix/execute \
  -H "Content-Type: application/json" \
  -d '{"project_path": "projects/internal/adr-029-session-persistence/"}'

# Oder via CLI
helix run projects/internal/adr-029-session-persistence/
```

## Wichtige Hinweise

1. **Phase 6 erfordert Approval**: Deploy to Production wartet auf manuelle Freigabe
2. **Sub-Agent Verifikation**: Die meisten Phasen werden durch Haiku-Agent verifiziert
3. **Max 3 Retries**: Bei Fehlern wird automatisch bis zu 3x wiederholt

## Projekt-Struktur

```
projects/internal/adr-029-session-persistence/
├── ADR-029.md           # ADR (Single Source of Truth)
├── phases.yaml          # 8 Phasen mit vollem Workflow
├── status.json          # Aktueller Status
└── phases/
    ├── 1/output/        # Implementation
    ├── 2/output/        # Unit Tests
    ├── 3/output/        # Integration Tests
    ├── 4/output/        # Deploy to Test
    ├── 5/output/        # E2E Tests
    ├── 6/output/        # Deploy to Prod
    ├── 7/output/        # Verification
    └── 8/output/        # Documentation
```

---

*Projekt erweitert am 2025-12-28 durch Meta-Consultant*
</chat_history>
