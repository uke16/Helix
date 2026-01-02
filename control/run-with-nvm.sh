#!/bin/bash
# Wrapper to run commands with NVM environment

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# Run the command passed as arguments
exec "$@"
