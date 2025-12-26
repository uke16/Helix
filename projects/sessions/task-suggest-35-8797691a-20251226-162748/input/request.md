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
