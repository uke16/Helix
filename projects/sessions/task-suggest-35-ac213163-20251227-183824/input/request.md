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
USER: Du hast den Evolution Workflow im letzten Chat gestartet wie ist der Status
ASSISTANT: [Starte Claude Code...]



---

Jetzt habe ich den vollständigen Überblick. Hier ist der **Status der Evolution Workflows**:

---

## Evolution Projekte - Status Übersicht

### 1. `adr-system` ✅ INTEGRATED
| Feld | Wert |
|------|------|
| Status | **integrated** (vollständig ins Hauptsystem integriert) |
| Alle Phasen | 1-5 abgeschlossen |
| Integriert am | 2024-12-22 |
| Neue Dateien | 33 |
| Modifizierte Dateien | 3 |

### 2. `adr-single-source` ✅ COMPLETED
| Feld | Wert |
|------|------|
| Status | **completed** |
| Alle Phasen | 1-5 abgeschlossen |
| Abgeschlossen am | 2025-12-22 19:54 |
| Notiz | Implementation wurde manuell durchgeführt (commits 705316b, 8d5b8c1, c8efa85) |

---

## Aktuell laufende Jobs

```
Keine aktiven Jobs - Queue ist leer []
```

---

## Zusammenfassung

Beide Evolution-Projekte sind **abgeschlossen**:
- `adr-system` wurde ins Hauptsystem integriert
- `adr-single-source` ist fertig (wurde parallel zum Workflow manuell implementiert)

Es läuft aktuell **kein aktiver Workflow**. 

Möchtest du:
1. Ein neues Projekt starten?
2. Details zu einem der abgeschlossenen Projekte sehen?
3. Den Output einer bestimmten Phase prüfen?
</chat_history>
