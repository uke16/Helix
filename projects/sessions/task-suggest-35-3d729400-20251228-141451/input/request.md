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

Das andere Problem was wir angehen können ist ein Claude code launcher. Es dauert immer super lang Claude Code zu launchen. Vielleicht ramdrive oder eine Instanz mehr ist immer schon am laufen haben und Verzeichnis wechseln und Session neustarten ? Erstelle ein ausgearbeitetes AdR und speichere es
ASSISTANT: [Starte Claude Code...]



---

# ADR-028 erstellt: Claude Code Launcher Performance

Ich habe deine Anfrage analysiert und ein ausgearbeitetes ADR für das **Claude Code Launcher Performance** Problem erstellt.

## Das Problem

Claude Code Start dauert **10-20 Sekunden**:
- Node.js Bootstrap: 2-3s
- CLI Initialization: 2-3s
- API Connection: 1-2s
- Context Loading: 1-2s
- MCP Servers: 2-3s
- First Token: 3-5s

**70% ist Startup-Overhead**, nur 30% ist echte LLM-Arbeit.

## Die Lösung: Pre-warmed Instance Pool

```
┌──────────────────────────────────────────────────┐
│            PoolManager (Daemon)                   │
│  • Hält 2 warme Instanzen bereit                 │
│  • Ersetzt genutzte Instanzen sofort             │
│  • Health-Checks alle 30s                        │
└──────────────────────────────────────────────────┘
                      │
    ┌─────────────────┼─────────────────┐
    ▼                 ▼                 ▼
[Instance #1]   [Instance #2]   [Instance #3]
  WARM            WARM           Starting...
```

**Effekt:** Startup von 10-20s auf **<1 Sekunde**

## ADR gespeichert

Das ADR wurde finalisiert und liegt jetzt in:
```
adr/028-claude-code-launcher-performance---pre-warmed-inst.md
```

## Zweites Problem: Session History

Zum **Open WebUI Session Problem** - jeder Chat ist eine neue Session:

Das liegt daran, dass der `SessionManager` die Session-ID aus:
1. Hash der ersten Nachricht
2. **Timestamp** (!)

generiert. Der Timestamp ändert sich bei jedem Request.

**Fix-Vorschlag für das nächste ADR:**

Open WebUI sendet einen `X-Conversation-ID` Header. Dieser sollte für die Session-Zuordnung verwendet werden statt des Timestamps.

Soll ich dafür auch ein ADR erstellen?
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
</chat_history>
