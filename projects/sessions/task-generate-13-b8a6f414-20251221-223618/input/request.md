# User Request

### Task:
Generate 1-3 broad tags categorizing the main themes of the chat history, along with 1-3 more specific subtopic tags.

### Guidelines:
- Start with high-level domains (e.g. Science, Technology, Philosophy, Arts, Politics, Business, Health, Sports, Entertainment, Education)
- Consider including relevant subfields/subdomains if they are strongly represented throughout the conversation
- If content is too short (less than 3 messages) or too diverse, use only ["General"]
- Use the chat's primary language; default to English if multilingual
- Prioritize accuracy over specificity

### Output:
JSON format: { "tags": ["tag1", "tag2", "tag3"] }

### Chat History:
<chat_history>
USER: hi! wer bist du
ASSISTANT: # Hallo!

Ich bin der **HELIX Meta-Consultant** - die zentrale Intelligenz des HELIX v4 Systems.

## Was ich bin

HELIX v4 ist ein **AI Development Orchestration System**. Das bedeutet:

- Ich orchestriere **mehrere Claude Code Instanzen** um Software zu entwickeln
- Ich bin die "Phase 0" - der Consultant der mit dir spricht bevor Code geschrieben wird
- Meine Aufgabe ist es zu verstehen **was** du bauen willst und **wie** wir es umsetzen

## Was ich kann

```
┌─────────────────────────────────────────────┐
│  DU sprichst mit mir (Consultant)           │
│  ↓                                          │
│  Ich verstehe dein Problem                  │
│  ↓                                          │
│  Ich erstelle einen Plan (spec.yaml)        │
│  ↓                                          │
│  Andere Claude Instanzen setzen um:         │
│  • Phase 01: Analyse                        │
│  • Phase 02: Implementation                 │
│  • Phase 03: Testing                        │
│  • Phase 04: Dokumentation                  │
└─────────────────────────────────────────────┘
```

Ich habe Zugriff auf **Domain-Wissen** (Skills) zu:
- PDM/Stücklisten-Systeme
- POSITAL Encoder Produkte
- Infrastruktur (Docker, PostgreSQL, etc.)
- Und mehr...

---

## Wie kann ich dir helfen?

Erzähl mir was du bauen oder umsetzen möchtest. Ich stelle dir dann gezielte Fragen um die Anforderungen zu verstehen, und erstelle einen professionellen Umsetzungsplan.

**Was hast du vor?**
</chat_history>
