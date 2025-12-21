# User Request

### Task:
Generate a concise, 3-5 word title with an emoji summarizing the chat history.
### Guidelines:
- The title should clearly represent the main theme or subject of the conversation.
- Use emojis that enhance understanding of the topic, but avoid quotation marks or special formatting.
- Write the title in the chat's primary language; default to English if multilingual.
- Prioritize accuracy over excessive creativity; keep it clear and simple.
- Your entire response must consist solely of the JSON object, without any introductory or concluding text.
- The output must be a single, raw JSON object, without any markdown code fences or other encapsulating text.
- Ensure no conversational text, affirmations, or explanations precede or follow the raw JSON output, as this will cause direct parsing failure.
### Output:
JSON format: { "title": "your concise title here" }
### Examples:
- { "title": "📉 Stock Market Trends" },
- { "title": "🍪 Perfect Chocolate Chip Recipe" },
- { "title": "Evolution of Music Streaming" },
- { "title": "Remote Work Productivity Tips" },
- { "title": "Artificial Intelligence in Healthcare" },
- { "title": "🎮 Video Game Development Insights" }
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
