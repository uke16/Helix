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
