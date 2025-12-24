#!/bin/bash
# claude-wrapper.sh - Run Claude CLI with stream-json output for debugging
#
# Loads NVM and runs Claude Code CLI

set -euo pipefail

# Load NVM and set PATH
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# Fallback: direct path if nvm.sh doesn't work
export PATH="/home/aiuser01/.nvm/versions/node/v20.19.6/bin:$PATH"

# Default values
OUTPUT_DIR="./logs"
MODEL="${CLAUDE_MODEL:-claude-sonnet-4}"
VERBOSE=false

# Parse options
while [[ $# -gt 0 ]]; do
    case $1 in
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -m|--model)
            MODEL="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS] -- [CLAUDE_ARGS...]"
            exit 0
            ;;
        --)
            shift
            break
            ;;
        *)
            break
            ;;
    esac
done

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"

# Timestamp for log files
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$OUTPUT_DIR/claude-stream-${TIMESTAMP}.jsonl"

# Build Claude command
CLAUDE_CMD=(
    claude
    --output-format stream-json
    --dangerously-skip-permissions
)

# Add model if specified
if [[ -n "$MODEL" ]]; then
    CLAUDE_CMD+=(--model "$MODEL")
fi

# Add remaining arguments
CLAUDE_CMD+=("$@")

# Run Claude
if $VERBOSE; then
    echo "Running: ${CLAUDE_CMD[*]}"
    "${CLAUDE_CMD[@]}" 2>&1 | tee "$LOG_FILE"
else
    "${CLAUDE_CMD[@]}" > "$LOG_FILE" 2>&1
fi

exit ${PIPESTATUS[0]}
