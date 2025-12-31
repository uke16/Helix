# Sub-Agent Pattern in HELIX

## Übersicht

Ein Sub-Agent ist ein Claude, der von einem anderen Claude (dem "Parent") gestartet wird.

```
┌─────────────────────────────────────────────────┐
│           PARENT AGENT (z.B. Developer)         │
│                                                  │
│  Implementiert Code...                          │
│       ↓                                          │
│  "Ich brauche ein Code Review"                  │
│       ↓                                          │
│  spawn-consultant.sh review src/foo.py          │
│       ↓                                          │
│  ┌─────────────────────────────────────────┐    │
│  │     SUB-AGENT (Consultant)              │    │
│  │                                          │    │
│  │  Analysiert Code...                     │    │
│  │  Gibt Feedback...                       │    │
│  │  Beendet sich                           │    │
│  └─────────────────────────────────────────┘    │
│       ↓                                          │
│  Parent erhält Review                           │
│  Arbeitet weiter...                             │
│                                                  │
└─────────────────────────────────────────────────┘
```

## Methoden

### 1. spawn-consultant.sh (Empfohlen)

```bash
# Einfache Frage
./control/spawn-consultant.sh "Was ist der beste Ansatz für X?"

# Code Review
./control/spawn-consultant.sh review src/helix/foo.py

# Analyse
./control/spawn-consultant.sh analyze "Performance-Optimierung für RAG"

# ADR Draft
./control/spawn-consultant.sh adr "Caching Layer für LLM Responses"
```

### 2. HTTP Call (API)

```bash
curl -s -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "helix-consultant",
    "messages": [{"role": "user", "content": "Review: ..."}],
    "stream": false
  }'
```

### 3. Direkter Claude Spawn

```bash
claude --print \
  --dangerously-skip-permissions \
  --system-prompt "Du bist ein Code Reviewer..." \
  "Review diesen Code: $(cat src/foo.py)"
```

## Use Cases

### Developer → Consultant (Code Review)

```bash
# In Developer CLAUDE.md oder direkt:
REVIEW=$(./control/spawn-consultant.sh review src/helix/new_feature.py)

if echo "$REVIEW" | grep -q "KRITISCH\|BUG\|FEHLER"; then
    echo "⚠️ Review hat kritische Issues gefunden"
    echo "$REVIEW"
    # Fix issues...
else
    echo "✅ Review OK"
fi
```

### Developer → Consultant (Architektur-Frage)

```bash
# Bevor neues Modul erstellt wird:
ANALYSIS=$(./control/spawn-consultant.sh analyze "
Ich möchte ein Caching-Layer für LLM Responses implementieren.
- Wo sollte es in der Architektur sitzen?
- Redis vs. In-Memory?
- Wie cache key designen?
")
echo "$ANALYSIS"
```

### Integrator → Consultant (Integration Verification)

```bash
# Sub-Agent Freigabe Test
RESPONSE=$(curl -s -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"helix-consultant","messages":[{"role":"user","content":"Test"}]}')

if [ $(echo "$RESPONSE" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('choices',[{}])[0].get('message',{}).get('content','')))") -gt 50 ]; then
    echo "✅ Sub-Agent OK"
else
    echo "❌ Sub-Agent FAILED"
    exit 1
fi
```

## Best Practices

### 1. Klare Prompts

```bash
# ❌ Schlecht
./control/spawn-consultant.sh "Schau mal drüber"

# ✅ Gut
./control/spawn-consultant.sh review src/helix/new_module.py
```

### 2. Output validieren

```bash
RESULT=$(./control/spawn-consultant.sh analyze "...")

# Prüfe ob Antwort sinnvoll
if [ ${#RESULT} -lt 100 ]; then
    echo "Sub-Agent hat nicht richtig geantwortet"
    exit 1
fi
```

### 3. Kontext mitgeben

```bash
# Für komplexe Analysen: Kontext-Dateien mitgeben
./control/spawn-consultant.sh "
Analysiere diese Architektur:

$(cat docs/ARCHITECTURE-MODULES.md)

Frage: Wo passt ein neues Caching-Modul am besten rein?
"
```

## Integration in Ralph Controller

Im Ralph Controller CLAUDE.md:

```markdown
## Phase 3: Code Review (Sub-Agent)

Vor dem Integration Test, hole ein Code Review:

\`\`\`bash
REVIEW=$(./control/spawn-consultant.sh review src/helix/new_feature.py)

# Wenn kritische Issues:
if echo "$REVIEW" | grep -qi "kritisch\|bug\|security"; then
    echo "Review hat Issues gefunden - fixe sie"
    # ... fix code ...
    # Retry Review
fi
\`\`\`

Wenn Review OK → Weiter zu Integration Test.
```

## Rollen und ihre Sub-Agents

| Parent Agent | Sub-Agent | Zweck |
|--------------|-----------|-------|
| Developer | Consultant | Code Review, Architektur-Fragen |
| Integrator | Consultant (via API) | Integration Verification |
| Reviewer | - | Kein Sub-Agent nötig |
| Dokumentierer | Consultant | Docstring-Vorschläge |

## Technische Details

### spawn-consultant.sh

- Nutzt `claude --print` für synchrone Ausführung
- System Prompt definiert Consultant-Rolle
- Output-Format: text (kein JSON)
- Timeout: Kein explizites Limit (Claude's Default)

### API Call

- Asynchron möglich mit `stream: true`
- Session-Tracking via `X-OpenWebUI-Chat-Id`
- Rate Limits beachten

## Troubleshooting

### Sub-Agent antwortet nicht

```bash
# Prüfe ob Claude verfügbar
claude --version

# Prüfe ob API läuft
curl http://localhost:8001/health
```

### Antwort zu kurz

```bash
# Mehr Kontext geben
./control/spawn-consultant.sh "
KONTEXT:
$(cat relevant_file.py)

FRAGE:
Was sollte verbessert werden?
"
```

### Timeout

```bash
# Für lange Analysen: Timeout erhöhen
timeout 300 ./control/spawn-consultant.sh analyze "Komplexes Thema..."
```
