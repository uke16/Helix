#!/bin/bash
# HELIX v4 Bootstrap - Phase starten

PHASE=${1:-01-foundation}
PHASE_DIR="/home/aiuser01/helix-v4/projects/internal/helix-v4-bootstrap/phases/$PHASE"

if [ ! -d "$PHASE_DIR" ]; then
    echo "❌ Phase nicht gefunden: $PHASE"
    exit 1
fi

# NVM laden
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# Kein API Key (nutzt OAuth)
unset ANTHROPIC_API_KEY

echo "=== HELIX v4 Bootstrap ==="
echo "Phase: $PHASE"
echo "Verzeichnis: $PHASE_DIR"
echo ""
echo "Starte Claude Code..."
echo ""

cd "$PHASE_DIR"
claude --permission-mode acceptEdits
