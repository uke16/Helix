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
USER: Das ist Nachricht 1. ist ein Claude Code aktiv? Falls ja, wie viel und für was
ASSISTANT: [Starte Claude Code...]



---

# HELIX Status Report

Ja, Claude Code ist aktiv! Hier der aktuelle Status:

## Aktive Instanzen

| Typ | Anzahl | Zweck |
|-----|--------|-------|
| **HELIX API (Production)** | 1 | Port 8001 - Haupt-Orchestrator |
| **HELIX API (Test)** | 1 | Port 9001 - Test-System |
| **Claude Code Prozesse** | 2 | Aktive AI-Instanzen |

## Laufende Jobs

Es gibt **1 aktiven Job**:
- **Job ID**: `3b68386a`
- **Status**: `running`
- **Gestartet**: 2025-12-28 17:41:41

Dieser Job ist die aktuelle Consultant-Session (diese Konversation mit dir).

## Prozess-Details

```
Claude CLI Prozesse:
- claude (PID 1245085) - Hauptinstanz
- claude (PID 1245300) - Zusätzliche Instanz (wahrscheinlich für Suche/Analyse)
```

---

## Wie kann ich dir helfen?

Du bist jetzt in einer **HELIX Consultant Session**. Ich bin hier um:

1. **Anforderungen zu verstehen** - Was möchtest du bauen/ändern?
2. **Fragen zu klären** - Welche Details brauchen wir?
3. **Einen Plan zu erstellen** - Wie setzen wir es um?

**Was möchtest du heute erreichen?**

- Ein neues Feature für HELIX?
- Eine Erweiterung für PDM/Encoder?
- Etwas anderes?
</chat_history>
