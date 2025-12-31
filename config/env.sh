#!/bin/bash
# HELIX v4 Environment Configuration
# Source this file: source config/env.sh

# NVM and Node.js
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# Fallback: Direct path to node
export PATH="/home/aiuser01/.nvm/versions/node/v20.19.6/bin:$PATH"

# Python path for HELIX modules
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}/home/aiuser01/helix-v4/src"

# HELIX specific
export HELIX_ROOT="/home/aiuser01/helix-v4"
export HELIX_MODEL="${HELIX_MODEL:-sonnet}"

# Verify
if command -v claude &> /dev/null; then
    echo "✅ Claude CLI: $(claude --version 2>/dev/null || echo 'available')"
else
    echo "❌ Claude CLI not found"
fi

if command -v python3 &> /dev/null; then
    echo "✅ Python: $(python3 --version)"
else
    echo "❌ Python not found"
fi

# Load .env if exists (for CLAUDE_MODEL etc.)
if [ -f "$HELIX_ROOT/.env" ]; then
    set -a
    source "$HELIX_ROOT/.env"
    set +a
fi

# Export CLAUDE_MODEL for Claude CLI
export CLAUDE_MODEL="${CLAUDE_MODEL:-opus}"

# LSP Tool Configuration (ADR-039)
export ENABLE_LSP_TOOL="${ENABLE_LSP_TOOL:-1}"
