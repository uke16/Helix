#!/bin/bash
# Test: Claude Code über OpenRouter mit verschiedenen Models

# NVM laden
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# OpenRouter API Key aus .env oder Parameter
if [ -n "$1" ]; then
    OPENROUTER_API_KEY="$1"
elif [ -f .env ]; then
    source .env
fi

if [ -z "$OPENROUTER_API_KEY" ]; then
    echo "❌ Kein OPENROUTER_API_KEY gefunden!"
    echo ""
    echo "Nutzung:"
    echo "  ./test-openrouter.sh sk-or-v1-dein-key"
    echo ""
    echo "Oder in .env:"
    echo "  OPENROUTER_API_KEY=sk-or-v1-dein-key"
    exit 1
fi

# Model auswählen (default: GPT-4o)
MODEL=${2:-openai/gpt-4o}

echo "=== OpenRouter Test ==="
echo "Model: $MODEL"
echo ""

# Test-Verzeichnis
cd /home/aiuser01/helix-v4/test-claude-code
rm -f hello.py result.json

# Claude Code mit OpenRouter
# Wichtig: ANTHROPIC_BASE_URL auf OpenRouter setzen
export ANTHROPIC_BASE_URL="https://openrouter.ai/api/v1"
export ANTHROPIC_API_KEY=""  # Muss leer sein!
export OPENROUTER_API_KEY="$OPENROUTER_API_KEY"
export ANTHROPIC_MODEL="$MODEL"

echo "Starte Claude Code..."
echo ""

claude --print --permission-mode acceptEdits -p "Erstelle hello.py mit print('Hello from $MODEL via OpenRouter!') und result.json mit {\"model\": \"$MODEL\", \"status\": \"success\"}"

echo ""
echo "=== Ergebnis ==="
echo ""
echo "hello.py:"
cat hello.py 2>/dev/null || echo "Nicht erstellt"
echo ""
echo "result.json:"
cat result.json 2>/dev/null || echo "Nicht erstellt"
