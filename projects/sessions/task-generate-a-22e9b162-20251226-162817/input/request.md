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
USER: hi wer bist du? kanns tdu mir den inhalt des home verzeichnisses parsen= ls -la in home?
ASSISTANT: Hier ist der Inhalt des Home-Verzeichnisses `/home/aiuser01`. Du siehst:

**Projekte:**
- `helix-v4/` - Das aktuelle HELIX Projekt (wo wir uns befinden)
- `helix-v3/`, `helix-v2/`, `helix/` - Ältere Versionen
- `PDM_RECONSTRUCTION_PROJECT/` - PDM Feature Rekonstruktion
- `RAG_Chat_UI_Project/` - RAG Chat UI

**Dokumentation:**
- Viele `.md` Dateien (README, PHASES, PROGRESS, etc.)
- API_ENDPOINTS_REFERENCE.md, FEATURE_*.md

**Infrastruktur:**
- `docker/` - Docker Konfiguration
- `caddy` - Reverse Proxy Binary
- Diverse Shell-Scripts

---

**Kann ich dir bei etwas Konkretem helfen?** Zum Beispiel:
- Ein Feature für HELIX planen?
- Code in einem der Projekte analysieren?
- Eine technische Frage beantworten?
</chat_history>
