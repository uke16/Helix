# Phase 13: Consultant Integration

## Ziel

Implementiere den **Consultant als Claude Code Instanz** für Multi-Turn Dialoge in Open WebUI.

## Kontext

- Phase 12 hat die API gebaut (läuft auf Port 8001)
- Open WebUI verbindet sich via /v1/chat/completions
- Aktuell: Statische Antworten
- Ziel: Echte Claude Code Instanz pro Session

## Session-Konzept

```
Open WebUI Chat
     │
     │ POST /v1/chat/completions
     │ Body: {"messages": [alle bisherigen messages]}
     ▼
HELIX API
     │
     │ 1. Parse messages → Extrahiere Session-State
     │ 2. Session existiert? → Lade context/
     │ 3. Session neu? → Erstelle projects/sessions/{id}/
     │ 4. Starte Claude Code mit aktuellem Kontext
     │ 5. Lese Output → Sende an Open WebUI
     ▼
Claude Code Instanz (Consultant)
     │
     │ - Liest CLAUDE.md, Skills
     │ - Analysiert Request + bisherige Antworten
     │ - Schreibt Fragen ODER spec.yaml
     ▼
Output in Session-Verzeichnis
```

## Zu erstellen

### 1. Session Manager
```
src/helix/api/session_manager.py
- create_session(session_id) → Session-Verzeichnis
- get_session(session_id) → Lade Status
- update_context(session_id, key, value) → Speichere Antwort
- get_state_from_messages(messages) → Parse Chat History
```

### 2. Consultant CLAUDE.md Template
```
templates/consultant/session.md.j2
- Anweisungen für Consultant Claude Code
- Welche Fragen stellen
- Wann spec.yaml generieren
```

### 3. API Route Update
```
src/helix/api/routes/openai.py
- Ersetze statische Antworten
- Integriere Session Manager
- Starte Claude Code pro Request
```

### 4. Session-Verzeichnis Struktur
```
projects/sessions/{session_id}/
├── CLAUDE.md           ← Generiert aus Template
├── status.json         ← {status, step, created_at}
├── input/
│   └── request.md      ← Ursprünglicher User Request
├── context/
│   ├── messages.json   ← Komplette Chat History
│   ├── what.md         ← Antwort auf "Was?"
│   ├── why.md          ← Antwort auf "Warum?"
│   └── constraints.md  ← Antwort auf "Constraints?"
└── output/
    ├── response.md     ← Aktuelle Antwort/Fragen
    ├── spec.yaml       ← Wenn fertig
    └── phases.yaml     ← Wenn fertig
```

## Session-State aus Messages

Open WebUI sendet ALLE Messages bei jedem Request:
```json
{
  "messages": [
    {"role": "user", "content": "Erstelle BOM Export"},
    {"role": "assistant", "content": "Was genau soll exportiert werden?"},
    {"role": "user", "content": "Stücklisten aus PDM"},
    {"role": "assistant", "content": "Warum wird das benötigt?"},
    {"role": "user", "content": "Für Excel Kalkulation"}
  ]
}
```

→ HELIX kann State rekonstruieren:
- Erster User Message = Original Request
- Assistant Messages = Bisherige Fragen
- User Messages = Bisherige Antworten

## Session-übergreifend

Da Open WebUI die History speichert und mitsendet:
- Chat kann jederzeit fortgesetzt werden
- Nach Browser-Neustart
- Nach Server-Neustart
- Session-ID = Hash aus erster User Message + Timestamp

## Quality Gate

- [ ] Session-Verzeichnis wird erstellt
- [ ] CLAUDE.md wird aus Template generiert
- [ ] Claude Code Instanz startet
- [ ] Antwort erscheint in Open WebUI
- [ ] Multi-Turn Dialog funktioniert
- [ ] spec.yaml wird bei genug Info generiert

## Output

```
src/helix/api/session_manager.py
templates/consultant/session.md.j2
src/helix/api/routes/openai.py (updated)
projects/sessions/ (directory)
```
