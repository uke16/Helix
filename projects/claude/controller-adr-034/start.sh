#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SESSION_NAME="controller-adr-034"
NODE_DIR="/home/aiuser01/.nvm/versions/node/v20.19.6/bin"

if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "Läuft bereits: tmux attach -t $SESSION_NAME"
    exit 1
fi

tmux new-session -d -s "$SESSION_NAME" -c "$SCRIPT_DIR" \
  "export PATH=$NODE_DIR:\$PATH; claude --dangerously-skip-permissions; exec bash"

sleep 3
tmux send-keys -t "$SESSION_NAME" Down Enter

echo "✅ Controller ADR-034 gestartet"
echo "Anhängen: tmux attach -t $SESSION_NAME"
echo "Stoppen:  tmux kill-session -t $SESSION_NAME"
