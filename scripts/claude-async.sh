#!/bin/bash
# Async Claude Code CLI wrapper with status polling

WORK_DIR="/home/aiuser01/helix-v4"
LOG_DIR="$WORK_DIR/.claude-async"
mkdir -p "$LOG_DIR"

case "$1" in
    start)
        # Start Claude CLI in background with prompt
        PROMPT="$2"
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        RUN_DIR="$LOG_DIR/$TIMESTAMP"
        mkdir -p "$RUN_DIR"
        
        echo "$PROMPT" > "$RUN_DIR/prompt.txt"
        echo "running" > "$RUN_DIR/status"
        echo "$TIMESTAMP" > "$LOG_DIR/current_run"
        
        cd "$WORK_DIR"
        source config/env.sh 2>/dev/null || true
        
        # Run claude in background, capture both stdout and stderr
        nohup bash -c "
            cd '$WORK_DIR'
            source config/env.sh 2>/dev/null || true
            claude --dangerously-skip-permissions -p \"\$(cat '$RUN_DIR/prompt.txt')\" > '$RUN_DIR/output.log' 2>&1
            EXIT_CODE=\$?
            if [ \$EXIT_CODE -eq 0 ]; then
                echo 'completed' > '$RUN_DIR/status'
            else
                echo \"failed:\$EXIT_CODE\" > '$RUN_DIR/status'
            fi
            echo \"\$(date): Finished with exit code \$EXIT_CODE\" >> '$RUN_DIR/output.log'
        " > /dev/null 2>&1 &
        
        echo $! > "$RUN_DIR/pid"
        sleep 1
        
        # Get the actual claude process PID
        CLAUDE_PID=$(pgrep -f "claude.*dangerously-skip-permissions" | tail -1)
        if [ -n "$CLAUDE_PID" ]; then
            echo "$CLAUDE_PID" > "$RUN_DIR/pid"
        fi
        
        echo "Started run $TIMESTAMP (PID: $(cat $RUN_DIR/pid))"
        echo "Poll with: $0 status"
        echo "Logs: tail -f $RUN_DIR/output.log"
        ;;
        
    status)
        if [ ! -f "$LOG_DIR/current_run" ]; then
            echo "No active run"
            exit 0
        fi
        CURRENT=$(cat "$LOG_DIR/current_run")
        RUN_DIR="$LOG_DIR/$CURRENT"
        
        STATUS=$(cat "$RUN_DIR/status" 2>/dev/null || echo "unknown")
        PID=$(cat "$RUN_DIR/pid" 2>/dev/null || echo "?")
        
        echo "=== Run: $CURRENT ==="
        echo "Status: $STATUS"
        echo "PID: $PID"
        
        # Check if process still running
        if [ "$STATUS" = "running" ]; then
            # Check for any claude process
            if pgrep -f "claude.*dangerously-skip-permissions" > /dev/null 2>&1; then
                echo "Process: ALIVE"
                echo ""
                echo "=== Last 30 lines of output ==="
                tail -30 "$RUN_DIR/output.log" 2>/dev/null
            else
                # Check log for completion
                if [ -s "$RUN_DIR/output.log" ]; then
                    echo "Process: COMPLETED (checking log)"
                    echo ""
                    echo "=== Final output (last 50 lines) ==="
                    tail -50 "$RUN_DIR/output.log" 2>/dev/null
                else
                    echo "Process: DEAD (zombie run?)"
                    echo "failed:process_died" > "$RUN_DIR/status"
                fi
            fi
        else
            echo ""
            echo "=== Final output (last 50 lines) ==="
            tail -50 "$RUN_DIR/output.log" 2>/dev/null
        fi
        ;;
        
    tail)
        CURRENT=$(cat "$LOG_DIR/current_run" 2>/dev/null)
        if [ -n "$CURRENT" ]; then
            tail -f "$LOG_DIR/$CURRENT/output.log"
        else
            echo "No active run"
        fi
        ;;
        
    kill)
        CURRENT=$(cat "$LOG_DIR/current_run" 2>/dev/null)
        if [ -n "$CURRENT" ]; then
            pkill -f "claude.*dangerously-skip-permissions" 2>/dev/null && echo "Killed claude process" || echo "No claude process found"
            echo "killed" > "$LOG_DIR/$CURRENT/status"
        fi
        ;;
        
    list)
        echo "=== All runs ==="
        ls -lt "$LOG_DIR" | head -20
        ;;
        
    *)
        echo "Usage: $0 {start \"prompt\"|status|tail|kill|list}"
        exit 1
        ;;
esac
