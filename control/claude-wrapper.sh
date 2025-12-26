#!/bin/bash
# claude-wrapper.sh - Run Claude CLI with configurable output
#
# Reads config from config/claude-cli.conf if available

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$PROJECT_ROOT/config/claude-cli.conf"

# Load NVM and set PATH
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
export PATH="/home/aiuser01/.nvm/versions/node/v20.19.6/bin:$PATH"

# Default values
OUTPUT_DIR="./logs"
MODEL="${CLAUDE_MODEL:-opus}"

# Load config if exists
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
fi

# Apply defaults from config or fallback
BASE_FLAGS="${CLAUDE_BASE_FLAGS:---dangerously-skip-permissions}"
OUTPUT_FORMAT="${CLAUDE_OUTPUT_FORMAT:-stream-json}"
PRINT_MODE="${CLAUDE_PRINT_MODE:-true}"
VERBOSE="${CLAUDE_VERBOSE:-true}"

# Parse command line options (override config)
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
        --no-stream)
            OUTPUT_FORMAT="text"
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS] -- [CLAUDE_ARGS...]"
            echo ""
            echo "Options:"
            echo "  -o, --output DIR    Log output directory (default: ./logs)"
            echo "  -m, --model MODEL   Claude model to use"
            echo "  --no-stream         Disable stream-json output"
            echo ""
            echo "Config file: $CONFIG_FILE"
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
CLAUDE_CMD=(claude)

# Add base flags
for flag in $BASE_FLAGS; do
    CLAUDE_CMD+=("$flag")
done

# Add output format
if [[ "$OUTPUT_FORMAT" == "stream-json" ]]; then
    CLAUDE_CMD+=(--output-format stream-json)
    
    # stream-json + print requires verbose
    if [[ "$PRINT_MODE" == "true" ]]; then
        CLAUDE_CMD+=(--print --verbose)
    fi
else
    if [[ "$PRINT_MODE" == "true" ]]; then
        CLAUDE_CMD+=(--print)
    fi
fi

# Add model if specified
if [[ -n "$MODEL" ]]; then
    CLAUDE_CMD+=(--model "$MODEL")
fi

# Add remaining arguments
CLAUDE_CMD+=("$@")

# Log the command for debugging
echo "# Command: ${CLAUDE_CMD[*]}" >> "$LOG_FILE"
echo "# Timestamp: $(date)" >> "$LOG_FILE"

# Run Claude
"${CLAUDE_CMD[@]}" 2>&1 | tee -a "$LOG_FILE"

exit ${PIPESTATUS[0]}
