#!/bin/bash
# Wrapper script for Claude CLI with proper node PATH

export NVM_DIR="$HOME/.nvm"
export PATH="/home/aiuser01/.nvm/versions/node/v20.19.6/bin:$PATH"

exec /home/aiuser01/.nvm/versions/node/v20.19.6/bin/claude "$@"
