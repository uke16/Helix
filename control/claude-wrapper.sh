#!/bin/bash
# claude-wrapper.sh - Run Claude CLI with stream-json output for debugging
#
# This wrapper invokes the Claude CLI with the --output-format stream-json
# flag to enable structured output parsing for debugging and observability.
#
# Usage:
#   ./claude-wrapper.sh [OPTIONS] -- [CLAUDE_ARGS...]
#
# Options:
#   -o, --output DIR   Output directory for logs (default: ./logs)
#   -m, --model MODEL  Model to use (default: claude-sonnet-4)
#   -v, --verbose      Enable verbose output
#   -h, --help         Show this help message
#
# Examples:
#   ./claude-wrapper.sh -o ./debug-logs -- --print "Hello"
#   ./claude-wrapper.sh -m claude-opus-4 -- --print "Complex task"

set -euo pipefail

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
            echo ""
            echo "Options:"
            echo "  -o, --output DIR   Output directory for logs (default: ./logs)"
            echo "  -m, --model MODEL  Model to use (default: claude-sonnet-4)"
            echo "  -v, --verbose      Enable verbose output"
            echo "  -h, --help         Show this help message"
            exit 0
            ;;
        --)
            shift
            break
            ;;
        *)
            # Unknown option, pass through
            break
            ;;
    esac
done

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"

# Timestamp for log files
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$OUTPUT_DIR/claude-stream-${TIMESTAMP}.jsonl"

# Log start
if $VERBOSE; then
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║  HELIX Claude Wrapper - Debug Mode                           ║"
    echo "╠══════════════════════════════════════════════════════════════╣"
    echo "║  Model:  $MODEL"
    echo "║  Output: $LOG_FILE"
    echo "║  Args:   $*"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
fi

# Build Claude command
CLAUDE_CMD=(
    stdbuf -oL -eL
    claude
    --output-format stream-json
    --verbose
    --dangerously-skip-permissions
)

# Add model if specified
if [[ -n "$MODEL" ]]; then
    CLAUDE_CMD+=(--model "$MODEL")
fi

# Add remaining arguments
CLAUDE_CMD+=("$@")

# Run Claude and capture output
if $VERBOSE; then
    # Verbose: show output and save to file
    "${CLAUDE_CMD[@]}" 2>&1 | tee "$LOG_FILE"
else
    # Quiet: only save to file
    "${CLAUDE_CMD[@]}" > "$LOG_FILE" 2>&1
fi

EXIT_CODE=${PIPESTATUS[0]}

# Log completion
if $VERBOSE; then
    echo ""
    echo "══════════════════════════════════════════════════════════════"
    echo "Debug session complete."
    echo "Output saved to: $LOG_FILE"
    echo "Exit code: $EXIT_CODE"
    echo "══════════════════════════════════════════════════════════════"
fi

exit $EXIT_CODE
