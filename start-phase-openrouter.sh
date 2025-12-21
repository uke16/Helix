#!/bin/bash
# HELIX v4 - Phase mit OpenRouter Model starten
#
# Nutzung:
#   ./start-phase-openrouter.sh 01-foundation                    # Mit GPT-4o (default)
#   ./start-phase-openrouter.sh 01-foundation openai/gpt-4o      # Mit GPT-4o
#   ./start-phase-openrouter.sh 01-foundation anthropic/claude-sonnet-4  # Mit Claude
#   ./start-phase-openrouter.sh 01-foundation google/gemini-2.0-flash-001  # Mit Gemini

PHASE=${1:-01-foundation}
MODEL=${2:-openai/gpt-4o}  # Default: GPT-4o

PHASE_DIR="/home/aiuser01/helix-v4/projects/internal/helix-v4-bootstrap/phases/$PHASE"

if [ ! -d "$PHASE_DIR" ]; then
    echo "❌ Phase nicht gefunden: $PHASE"
    echo ""
    echo "Verfügbare Phasen:"
    ls /home/aiuser01/helix-v4/projects/internal/helix-v4-bootstrap/phases/
    exit 1
fi

# NVM laden
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# .env laden
set -a
source /home/aiuser01/helix-v4/.env
set +a

# y-router sicherstellen
/home/aiuser01/helix-v4/scripts/start-y-router.sh

# OpenRouter via lokalem y-router
export ANTHROPIC_BASE_URL="http://localhost:8787"
export ANTHROPIC_API_KEY="$HELIX_OPENROUTER_API_KEY"
export ANTHROPIC_CUSTOM_HEADERS="x-api-key: $ANTHROPIC_API_KEY"
export ANTHROPIC_MODEL="$MODEL"

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  HELIX v4 - Phase via OpenRouter                             ║"
echo "╠═══════════════════════════════════════════════════════════════╣"
echo "║  Phase:  $PHASE"
echo "║  Model:  $MODEL"
echo "║  Router: http://localhost:8787 (lokal)"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

cd "$PHASE_DIR"
claude --permission-mode acceptEdits
