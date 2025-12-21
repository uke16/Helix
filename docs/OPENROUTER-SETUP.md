# HELIX v4 - OpenRouter Setup

## Übersicht

HELIX v4 nutzt **OpenRouter** über einen lokalen **y-router** Proxy um Claude Code 
mit verschiedenen LLM-Models zu nutzen.

```
╔═══════════════════════════════════════════════════════════════════════╗
║                    HELIX v4 LLM Architektur                          ║
╠═══════════════════════════════════════════════════════════════════════╣
║                                                                        ║
║   ┌─────────────────┐                                                  ║
║   │  Claude Code    │  (Agent Runtime)                                ║
║   │  CLI            │                                                  ║
║   └────────┬────────┘                                                  ║
║            │ Anthropic API Format                                      ║
║            ▼                                                           ║
║   ┌─────────────────┐                                                  ║
║   │   y-router      │  Docker Container                               ║
║   │   localhost:8787│  (Format-Konvertierung)                          ║
║   └────────┬────────┘                                                  ║
║            │ OpenAI API Format                                         ║
║            ▼                                                           ║
║   ┌─────────────────┐                                                  ║
║   │   OpenRouter    │  openrouter.ai                                  ║
║   │   (Cloud)       │  (€20 Credits = ~100k+ Calls)                    ║
║   └────────┬────────┘                                                  ║
║            │                                                           ║
║      ┌─────┴─────┬─────────┬─────────┬─────────┐                      ║
║      ▼           ▼         ▼         ▼         ▼                      ║
║   ┌──────┐  ┌────────┐ ┌───────┐ ┌──────┐ ┌───────┐                  ║
║   │GPT-4o│  │ Claude │ │Gemini │ │ Grok │ │ Llama │                  ║
║   └──────┘  └────────┘ └───────┘ └──────┘ └───────┘                  ║
║                                                                        ║
╚═══════════════════════════════════════════════════════════════════════╝
```

## Voraussetzungen

1. **Docker** installiert und läuft
2. **OpenRouter Account** mit Credits (https://openrouter.ai)
3. **API Key** in `.env`: `HELIX_OPENROUTER_API_KEY=sk-or-v1-...`

## Quick Start

```bash
cd /home/aiuser01/helix-v4

# 1. y-router starten (einmalig, bleibt laufen)
./scripts/start-y-router.sh

# 2. Phase mit Model starten
./start-phase-openrouter.sh 01-foundation openai/gpt-4o
```

## Verfügbare Models

| Model | OpenRouter ID | Kosten/1M Token | Empfohlen für |
|-------|---------------|-----------------|---------------|
| GPT-4o Mini | `openai/gpt-4o-mini` | ~$0.15 | Schnelle Tests |
| GPT-4o | `openai/gpt-4o` | ~$5.00 | Allrounder |
| Claude Sonnet 4 | `anthropic/claude-sonnet-4` | ~$6.00 | Coding |
| Gemini 2.0 Flash | `google/gemini-2.0-flash-001` | ~$0.10 | Schnell & günstig |
| Llama 3.3 70B | `meta-llama/llama-3.3-70b-instruct` | ~$0.50 | Open Source |

## Beispiele

```bash
# Mit GPT-4o (Default)
./start-phase-openrouter.sh 01-foundation

# Mit Claude Sonnet 4
./start-phase-openrouter.sh 01-foundation anthropic/claude-sonnet-4

# Mit Gemini (günstig)
./start-phase-openrouter.sh 01-foundation google/gemini-2.0-flash-001

# Mit GPT-4o Mini (schnell & günstig)
./start-phase-openrouter.sh 01-foundation openai/gpt-4o-mini
```

## Scripts

| Script | Funktion |
|--------|----------|
| `scripts/start-y-router.sh` | y-router Docker starten |
| `scripts/stop-y-router.sh` | y-router Docker stoppen |
| `start-phase-openrouter.sh` | Phase mit OpenRouter Model starten |
| `start-phase.sh` | Phase mit OAuth (Claude Max) starten |

## Troubleshooting

### y-router startet nicht
```bash
# Logs prüfen
cd y-router && docker compose logs

# Neu starten
docker compose down && docker compose up -d
```

### API Key Fehler
```bash
# Key prüfen
grep HELIX_OPENROUTER_API_KEY .env

# Direkt testen
curl -H "Authorization: Bearer $HELIX_OPENROUTER_API_KEY" \
  https://openrouter.ai/api/v1/models | head -c 200
```

### Model nicht verfügbar
```bash
# Verfügbare Models anzeigen
curl -s https://openrouter.ai/api/v1/models | python3 -c "
import sys,json
for m in json.load(sys.stdin)['data'][:20]:
    print(m['id'])
"
```

## Kosten-Tracking

OpenRouter zeigt Kosten im Dashboard: https://openrouter.ai/activity

---

*Erstellt: 2025-12-21*
*y-router: https://github.com/luohy15/y-router*
