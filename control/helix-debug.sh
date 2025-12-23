#!/bin/bash
# helix-debug.sh - Start a HELIX debug session with live dashboard
#
# This script starts a Claude CLI session with debug output and optionally
# launches a live terminal dashboard or web dashboard for monitoring.
#
# Usage:
#   ./helix-debug.sh [OPTIONS] [PHASE_DIR]
#
# Options:
#   -d, --dashboard     Launch terminal dashboard
#   -w, --web           Launch web dashboard (SSE)
#   -p, --port PORT     Web dashboard port (default: 8080)
#   -m, --model MODEL   Model to use (default: claude-sonnet-4)
#   -o, --output DIR    Output directory (default: PHASE_DIR/logs)
#   -h, --help          Show this help message
#
# Arguments:
#   PHASE_DIR           Phase directory to run (default: current directory)
#
# Examples:
#   ./helix-debug.sh phases/01-analysis
#   ./helix-debug.sh -d phases/02-implementation
#   ./helix-debug.sh -w -p 9000 phases/03-testing

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default values
PHASE_DIR="."
DASHBOARD=false
WEB_DASHBOARD=false
WEB_PORT=8080
MODEL="${CLAUDE_MODEL:-claude-sonnet-4}"
OUTPUT_DIR=""

# Parse options
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--dashboard)
            DASHBOARD=true
            shift
            ;;
        -w|--web)
            WEB_DASHBOARD=true
            shift
            ;;
        -p|--port)
            WEB_PORT="$2"
            shift 2
            ;;
        -m|--model)
            MODEL="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS] [PHASE_DIR]"
            echo ""
            echo "Start a HELIX debug session with live monitoring."
            echo ""
            echo "Options:"
            echo "  -d, --dashboard     Launch terminal dashboard"
            echo "  -w, --web           Launch web dashboard (SSE)"
            echo "  -p, --port PORT     Web dashboard port (default: 8080)"
            echo "  -m, --model MODEL   Model to use (default: claude-sonnet-4)"
            echo "  -o, --output DIR    Output directory (default: PHASE_DIR/logs)"
            echo "  -h, --help          Show this help message"
            echo ""
            echo "Arguments:"
            echo "  PHASE_DIR           Phase directory to run (default: .)"
            exit 0
            ;;
        -*)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
        *)
            PHASE_DIR="$1"
            shift
            ;;
    esac
done

# Resolve phase directory
PHASE_DIR="$(cd "$PHASE_DIR" && pwd)"

# Set output directory
if [[ -z "$OUTPUT_DIR" ]]; then
    OUTPUT_DIR="$PHASE_DIR/logs"
fi

# Extract phase ID from directory name
PHASE_ID="$(basename "$PHASE_DIR")"

# Ensure directories exist
mkdir -p "$OUTPUT_DIR"

# Timestamp for this session
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
SESSION_LOG="$OUTPUT_DIR/session-${TIMESTAMP}.log"
STREAM_LOG="$OUTPUT_DIR/stream-${TIMESTAMP}.jsonl"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  HELIX Debug Session                                          ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Phase:     $PHASE_ID"
echo "║  Directory: $PHASE_DIR"
echo "║  Model:     $MODEL"
echo "║  Output:    $OUTPUT_DIR"
echo "║  Dashboard: $DASHBOARD"
echo "║  Web:       $WEB_DASHBOARD (port: $WEB_PORT)"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Check for CLAUDE.md
if [[ ! -f "$PHASE_DIR/CLAUDE.md" ]]; then
    echo "WARNING: No CLAUDE.md found in $PHASE_DIR"
    echo ""
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Cleaning up..."

    # Kill background processes
    if [[ -n "${DASHBOARD_PID:-}" ]]; then
        kill "$DASHBOARD_PID" 2>/dev/null || true
    fi
    if [[ -n "${WEB_PID:-}" ]]; then
        kill "$WEB_PID" 2>/dev/null || true
    fi

    echo "Session logs saved to: $OUTPUT_DIR"
}
trap cleanup EXIT

# Start web dashboard if requested
if $WEB_DASHBOARD; then
    echo "Starting web dashboard on port $WEB_PORT..."

    # Create a simple Python server for the web dashboard
    python3 -c "
import asyncio
from helix.debug.live_dashboard import create_debug_router, SSEDashboard
try:
    from fastapi import FastAPI
    import uvicorn
except ImportError:
    print('ERROR: FastAPI/uvicorn not installed. Run: pip install fastapi uvicorn')
    exit(1)

app = FastAPI(title='HELIX Debug Dashboard')
dashboard = SSEDashboard(phase_id='$PHASE_ID')
app.include_router(create_debug_router(dashboard))

print(f'Web dashboard running at http://localhost:$WEB_PORT/debug/stream')
uvicorn.run(app, host='0.0.0.0', port=$WEB_PORT, log_level='warning')
" &
    WEB_PID=$!

    # Wait for server to start
    sleep 2

    echo "Web dashboard available at: http://localhost:$WEB_PORT/debug/stream"
    echo ""
fi

# Build Claude command
CLAUDE_CMD=(
    stdbuf -oL -eL
    claude
    --output-format stream-json
    --verbose
    --print
    --dangerously-skip-permissions
)

# Add model
if [[ -n "$MODEL" ]]; then
    CLAUDE_CMD+=(--model "$MODEL")
fi

# Run with or without terminal dashboard
if $DASHBOARD; then
    echo "Starting Claude with terminal dashboard..."
    echo ""

    # Use Python dashboard for terminal display
    python3 -c "
import asyncio
import subprocess
import sys

async def run_dashboard():
    from helix.debug.live_dashboard import TerminalDashboard

    # Start Claude process
    proc = await asyncio.create_subprocess_exec(
        *${CLAUDE_CMD[@]@Q},
        cwd='$PHASE_DIR',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    # Run dashboard
    dashboard = TerminalDashboard(
        phase_id='$PHASE_ID',
        model='$MODEL',
    )

    summary = await dashboard.run(proc.stdout)

    # Save summary
    import json
    with open('$OUTPUT_DIR/summary-$TIMESTAMP.json', 'w') as f:
        json.dump(summary, f, indent=2, default=str)

    print()
    print('═' * 66)
    print('Session Summary:')
    print(f\"  Tool calls: {summary['tool_stats']['total_calls']}\")
    print(f\"  Cost: \${summary['cost_summary']['total_cost_usd']:.4f}\")
    print(f\"  Saved to: $OUTPUT_DIR/summary-$TIMESTAMP.json\")
    print('═' * 66)

asyncio.run(run_dashboard())
" 2>&1 | tee "$SESSION_LOG"

else
    echo "Starting Claude (streaming to log)..."
    echo "Output: $STREAM_LOG"
    echo ""

    # Run Claude directly, saving output
    cd "$PHASE_DIR"
    "${CLAUDE_CMD[@]}" 2>&1 | tee "$STREAM_LOG"

    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "Session complete. Stream saved to: $STREAM_LOG"
    echo ""
    echo "Analyze with:"
    echo "  python -m helix.debug.analyze $STREAM_LOG"
    echo "═══════════════════════════════════════════════════════════════"
fi
