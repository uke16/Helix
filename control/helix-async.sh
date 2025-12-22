#!/bin/bash
# HELIX v4 Async Helper - Verhindert SSH Timeouts bei langen Operationen
# Usage: ./control/helix-async.sh <command> [args...]

HELIX_URL="http://localhost:8001"
LOG_DIR="/home/aiuser01/helix-v4/logs"
ASYNC_LOG="$LOG_DIR/async-commands.log"
JOB_FILE="/tmp/helix-v4-current-job.txt"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$ASYNC_LOG"
    echo "$*"
}

case "$1" in
    # Execute phases (non-blocking)
    execute)
        PROJECT="${2:-projects/evolution/adr-system}"
        PHASES="$3"  # Optional: "2" or "2,3" or empty for all
        
        if [ -n "$PHASES" ]; then
            PHASE_JSON="[\"$PHASES\"]"
            RESULT=$(curl -s -X POST "$HELIX_URL/helix/execute" \
                -H "Content-Type: application/json" \
                -d "{\"project_path\": \"$PROJECT\", \"phase_filter\": $PHASE_JSON}")
        else
            RESULT=$(curl -s -X POST "$HELIX_URL/helix/execute" \
                -H "Content-Type: application/json" \
                -d "{\"project_path\": \"$PROJECT\"}")
        fi
        
        JOB_ID=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('job_id',''))" 2>/dev/null)
        if [ -n "$JOB_ID" ]; then
            echo "$JOB_ID" > "$JOB_FILE"
            log "Started execute: $JOB_ID for $PROJECT"
        fi
        echo "$RESULT" | python3 -m json.tool 2>/dev/null || echo "$RESULT"
        ;;
    
    # Check job status
    status|s)
        JOB_ID="${2:-$(cat $JOB_FILE 2>/dev/null)}"
        [ -z "$JOB_ID" ] && echo "No job. Usage: $0 status <job_id>" && exit 1
        curl -s "$HELIX_URL/helix/jobs/$JOB_ID" | python3 -m json.tool
        ;;
    
    # Quick one-line status
    quick|q)
        JOB_ID="${2:-$(cat $JOB_FILE 2>/dev/null)}"
        curl -s "$HELIX_URL/helix/jobs/$JOB_ID" 2>/dev/null | \
            python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{d[\"status\"]} | phase {d.get(\"current_phase\",\"?\")} | {len(d.get(\"phases\",[]))} done')" 2>/dev/null || echo "No status"
        ;;
    
    # Wait for job completion (with timeout)
    wait|w)
        JOB_ID="${2:-$(cat $JOB_FILE 2>/dev/null)}"
        TIMEOUT="${3:-600}"  # 10 min default
        [ -z "$JOB_ID" ] && echo "No job" && exit 1
        
        echo "Waiting for $JOB_ID (max ${TIMEOUT}s)..."
        START=$(date +%s)
        while true; do
            STATUS=$(curl -s "$HELIX_URL/helix/jobs/$JOB_ID" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','unknown'))" 2>/dev/null)
            ELAPSED=$(($(date +%s) - START))
            
            case "$STATUS" in
                completed|failed)
                    echo "Job $STATUS after ${ELAPSED}s"
                    curl -s "$HELIX_URL/helix/jobs/$JOB_ID" | python3 -m json.tool
                    exit 0
                    ;;
                *)
                    if [ $ELAPSED -gt $TIMEOUT ]; then
                        echo "Timeout after ${TIMEOUT}s (status: $STATUS)"
                        exit 1
                    fi
                    echo -n "."
                    sleep 10
                    ;;
            esac
        done
        ;;
    
    # Deploy project
    deploy|d)
        PROJECT="${2:-adr-system}"
        curl -s -X POST "$HELIX_URL/helix/evolution/projects/$PROJECT/deploy" | python3 -m json.tool
        ;;
    
    # Validate project
    validate|v)
        PROJECT="${2:-adr-system}"
        curl -s -X POST "$HELIX_URL/helix/evolution/projects/$PROJECT/validate" | python3 -m json.tool
        ;;
    
    # Integrate project
    integrate|i)
        PROJECT="${2:-adr-system}"
        curl -s -X POST "$HELIX_URL/helix/evolution/projects/$PROJECT/integrate" | python3 -m json.tool
        ;;
    
    # Full pipeline (execute all -> deploy -> validate -> integrate)
    run|r)
        PROJECT="${2:-adr-system}"
        curl -s -X POST "$HELIX_URL/helix/evolution/projects/$PROJECT/run" | python3 -m json.tool
        ;;
    
    # Project info
    info)
        PROJECT="${2:-adr-system}"
        curl -s "$HELIX_URL/helix/evolution/projects/$PROJECT" | python3 -m json.tool
        ;;
    
    # List all projects
    list|l)
        curl -s "$HELIX_URL/helix/evolution/projects" | python3 -m json.tool
        ;;
    
    # API health
    health|h)
        curl -s "$HELIX_URL/health"
        echo ""
        ;;
    
    # Show logs
    logs)
        LINES="${2:-30}"
        tail -n "$LINES" "$LOG_DIR/helix-v4.log"
        ;;
    
    *)
        echo "HELIX v4 Async Helper"
        echo ""
        echo "Execute:"
        echo "  execute <project> [phase]  - Start phase execution"
        echo "  status [job_id]            - Full job status"
        echo "  quick [job_id]             - One-line status"
        echo "  wait [job_id] [timeout]    - Wait for completion"
        echo ""
        echo "Evolution:"
        echo "  deploy [project]           - Deploy to test"
        echo "  validate [project]         - Run tests"
        echo "  integrate [project]        - Integrate to prod"
        echo "  run [project]              - Full pipeline"
        echo ""
        echo "Info:"
        echo "  info [project]             - Project details"
        echo "  list                       - All projects"
        echo "  health                     - API health"
        echo "  logs [lines]               - Show logs"
        ;;
esac
