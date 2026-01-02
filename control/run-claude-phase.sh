#!/bin/bash
# HELIX v4 - Claude Code Phase Runner v3
# WITH LIVE OUTPUT STREAMING

PHASE_DIR="$1"
LOG_FILE="$2"

# NVM laden
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
nvm use 20 > /dev/null 2>&1

# OAuth (kein API Key)
unset ANTHROPIC_API_KEY

# Run from helix-v4 root
cd /home/aiuser01/helix-v4

echo "=== Claude Code startet ===" | tee "$LOG_FILE"
echo "Working dir: $(pwd)" | tee -a "$LOG_FILE"
echo "Phase: $PHASE_DIR" | tee -a "$LOG_FILE"
echo "Time: $(date)" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Read CLAUDE.md and execute WITH LINE BUFFERING
CLAUDE_MD="$PHASE_DIR/CLAUDE.md"

# Option 1: stdbuf for line buffering + tee for dual output
stdbuf -oL -eL claude --print --permission-mode acceptEdits \
    -p "Read the file $CLAUDE_MD and execute all instructions. Create all files as specified." \
    2>&1 | tee -a "$LOG_FILE"

EXIT_CODE=${PIPESTATUS[0]}

echo "" | tee -a "$LOG_FILE"
echo "=== EXIT_CODE: $EXIT_CODE ===" | tee -a "$LOG_FILE"
echo "=== Finished: $(date) ===" | tee -a "$LOG_FILE"
