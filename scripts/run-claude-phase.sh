#!/bin/bash
# HELIX v4 - Claude Code Phase Runner

PHASE_DIR="$1"
PROMPT="$2"
LOG_FILE="$3"

# NVM laden
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
nvm use 20 > /dev/null 2>&1

# OAuth (kein API Key)
unset ANTHROPIC_API_KEY

cd "$PHASE_DIR"
echo "=== Claude Code startet ===" >> "$LOG_FILE"
echo "Prompt: $PROMPT" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

claude --print --permission-mode acceptEdits -p "$PROMPT" >> "$LOG_FILE" 2>&1
echo "" >> "$LOG_FILE"
echo "=== EXIT_CODE: $? ===" >> "$LOG_FILE"
