#!/bin/bash
# HELIX v4 - Claude Code Phase Runner v2
# Runs from project root for better file access

PHASE_DIR="$1"
LOG_FILE="$2"

# NVM laden
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
nvm use 20 > /dev/null 2>&1

# OAuth (kein API Key)
unset ANTHROPIC_API_KEY

# Run from helix-v4 root, but read CLAUDE.md from phase
cd /home/aiuser01/helix-v4

echo "=== Claude Code startet ===" >> "$LOG_FILE"
echo "Working dir: $(pwd)" >> "$LOG_FILE"
echo "Phase: $PHASE_DIR" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# Read CLAUDE.md and execute
CLAUDE_MD="$PHASE_DIR/CLAUDE.md"
claude --print --permission-mode acceptEdits -p "Read the file $CLAUDE_MD and execute all instructions. Create all files as specified." >> "$LOG_FILE" 2>&1

echo "" >> "$LOG_FILE"
echo "=== EXIT_CODE: $? ===" >> "$LOG_FILE"
