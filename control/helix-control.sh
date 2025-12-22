#!/bin/bash
# HELIX V4 Control Script
# Controls the HELIX v4 API and Docker infrastructure

# Auto-detect paths from script location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HELIX_ROOT="$(dirname "$SCRIPT_DIR")"

# If script is in control/, go up one level
if [[ "$SCRIPT_DIR" == */control ]]; then
    HELIX_ROOT="$(dirname "$SCRIPT_DIR")"
fi

# Detect instance type (production vs test) based on path
if [[ "$HELIX_ROOT" == *"helix-v4-test"* ]]; then
    INSTANCE="test"
    API_PORT=9001
    POSTGRES_PORT=5433
    NEO4J_HTTP_PORT=7475
    NEO4J_BOLT_PORT=7688
    QDRANT_PORT=6335
    REDIS_PORT=6380
    LOG_FILE="$HELIX_ROOT/logs/helix-v4-test.log"
else
    INSTANCE="production"
    API_PORT=8001
    POSTGRES_PORT=5432
    NEO4J_HTTP_PORT=7474
    NEO4J_BOLT_PORT=7687
    QDRANT_PORT=6333
    REDIS_PORT=6379
    LOG_FILE="$HELIX_ROOT/logs/helix-v4.log"
fi

LOG_DIR="$HELIX_ROOT/logs"
PID_FILE="$HELIX_ROOT/logs/helix-v4.pid"

# NVM Path for Claude CLI
NVM_PATH="/home/aiuser01/.nvm/versions/node/v20.19.6/bin"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

# Header
print_header() {
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}  ${BOLD}HELIX V4 Control${NC} - Instance: ${YELLOW}$INSTANCE${NC} (Port: ${GREEN}$API_PORT${NC})  ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Get API PID
get_api_pid() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "$pid"
            return 0
        fi
    fi
    # Fallback: find by process pattern
    pgrep -f "uvicorn.*helix\.api\.main.*$API_PORT" 2>/dev/null | head -1
}

# Check API health
check_health() {
    curl -s --max-time 5 "http://localhost:$API_PORT/health" 2>/dev/null
}

# Check Docker containers
check_docker_status() {
    local service=$1
    local port=$2

    # Check if port is listening
    if nc -z localhost "$port" 2>/dev/null; then
        echo -e "${GREEN}●${NC} $service (port $port)"
    else
        echo -e "${RED}○${NC} $service (port $port)"
    fi
}

# Start API
start_api() {
    echo -e "${CYAN}Starting HELIX v4 API...${NC}"

    # Check if already running
    local pid=$(get_api_pid)
    if [ -n "$pid" ]; then
        echo -e "${YELLOW}⚠ API already running (PID: $pid)${NC}"
        return 1
    fi

    # Ensure log directory exists
    mkdir -p "$LOG_DIR"

    # Set environment
    cd "$HELIX_ROOT"
    export PYTHONPATH="$HELIX_ROOT/src"
    export PORT=$API_PORT

    # Add NVM to PATH for Claude CLI
    if [[ ! "$PATH" == *"$NVM_PATH"* ]]; then
        export PATH="$NVM_PATH:$PATH"
    fi

    # Start uvicorn
    nohup python3 -m uvicorn helix.api.main:app \
        --host 0.0.0.0 \
        --port $API_PORT \
        > "$LOG_FILE" 2>&1 &

    local new_pid=$!
    echo "$new_pid" > "$PID_FILE"

    echo -e "${CYAN}Waiting for API to start...${NC}"
    sleep 3

    # Check if started successfully
    if check_health > /dev/null; then
        echo -e "${GREEN}✓ API started successfully (PID: $new_pid)${NC}"
        return 0
    else
        echo -e "${RED}✗ API failed to start${NC}"
        echo -e "${YELLOW}Check logs: $LOG_FILE${NC}"
        return 1
    fi
}

# Stop API
stop_api() {
    echo -e "${CYAN}Stopping HELIX v4 API...${NC}"

    local pid=$(get_api_pid)
    if [ -z "$pid" ]; then
        echo -e "${YELLOW}⚠ API not running${NC}"
        return 0
    fi

    # Graceful shutdown
    kill "$pid" 2>/dev/null

    # Wait for process to stop
    local count=0
    while ps -p "$pid" > /dev/null 2>&1 && [ $count -lt 10 ]; do
        sleep 1
        count=$((count + 1))
    done

    # Force kill if still running
    if ps -p "$pid" > /dev/null 2>&1; then
        echo -e "${YELLOW}Force killing...${NC}"
        kill -9 "$pid" 2>/dev/null
        sleep 1
    fi

    # Clean up PID file
    rm -f "$PID_FILE"

    echo -e "${GREEN}✓ API stopped${NC}"
}

# Restart API
restart_api() {
    echo -e "${CYAN}Restarting HELIX v4 API...${NC}"
    stop_api
    sleep 2
    start_api
}

# Show status
show_status() {
    print_header

    echo -e "${BOLD}API Status:${NC}"
    echo -e "─────────────────────────────────────────────────────────────"

    local pid=$(get_api_pid)
    if [ -n "$pid" ]; then
        echo -e "${GREEN}●${NC} HELIX v4 API running (PID: $pid)"

        # Show uptime
        local uptime=$(ps -p "$pid" -o etime= 2>/dev/null | tr -d ' ')
        if [ -n "$uptime" ]; then
            echo -e "  Uptime: $uptime"
        fi
    else
        echo -e "${RED}○${NC} HELIX v4 API not running"
    fi

    echo ""

    # Health check
    echo -e "${BOLD}Health Check:${NC}"
    echo -e "─────────────────────────────────────────────────────────────"
    local health=$(check_health)
    if [ -n "$health" ]; then
        echo -e "${GREEN}✓${NC} Health check passed"
        echo "  $health" | python3 -m json.tool 2>/dev/null || echo "  $health"
    else
        echo -e "${RED}✗${NC} Health check failed"
    fi

    echo ""

    # Docker services status
    echo -e "${BOLD}Infrastructure Services:${NC}"
    echo -e "─────────────────────────────────────────────────────────────"
    check_docker_status "PostgreSQL" "$POSTGRES_PORT"
    check_docker_status "Neo4j HTTP" "$NEO4J_HTTP_PORT"
    check_docker_status "Neo4j Bolt" "$NEO4J_BOLT_PORT"
    check_docker_status "Qdrant" "$QDRANT_PORT"
    check_docker_status "Redis" "$REDIS_PORT"

    echo ""
}

# Show logs
show_logs() {
    local lines=${1:-50}
    local follow=$2

    if [ ! -f "$LOG_FILE" ]; then
        echo -e "${YELLOW}No log file found: $LOG_FILE${NC}"
        return 1
    fi

    if [ "$follow" = "-f" ]; then
        echo -e "${CYAN}Following logs (Ctrl+C to exit)...${NC}"
        tail -f "$LOG_FILE"
    else
        echo -e "${CYAN}Last $lines lines of logs:${NC}"
        echo -e "─────────────────────────────────────────────────────────────"
        tail -n "$lines" "$LOG_FILE"
    fi
}

# Docker up
docker_up() {
    echo -e "${CYAN}Starting Docker containers...${NC}"

    # Check for docker-compose file
    local compose_file=""
    if [ "$INSTANCE" = "test" ]; then
        compose_file="$HELIX_ROOT/docker/test/docker-compose.yaml"
    else
        compose_file="$HELIX_ROOT/docker/production/docker-compose.yaml"
    fi

    if [ ! -f "$compose_file" ]; then
        echo -e "${YELLOW}⚠ Docker compose file not found: $compose_file${NC}"
        echo -e "${YELLOW}  Docker containers may be managed externally.${NC}"
        return 1
    fi

    docker-compose -f "$compose_file" up -d

    echo -e "${CYAN}Waiting for services to start...${NC}"
    sleep 5

    echo -e "${GREEN}✓ Docker containers started${NC}"
}

# Docker down
docker_down() {
    echo -e "${CYAN}Stopping Docker containers...${NC}"

    local compose_file=""
    if [ "$INSTANCE" = "test" ]; then
        compose_file="$HELIX_ROOT/docker/test/docker-compose.yaml"
    else
        compose_file="$HELIX_ROOT/docker/production/docker-compose.yaml"
    fi

    if [ ! -f "$compose_file" ]; then
        echo -e "${YELLOW}⚠ Docker compose file not found: $compose_file${NC}"
        return 1
    fi

    docker-compose -f "$compose_file" down

    echo -e "${GREEN}✓ Docker containers stopped${NC}"
}

# Health check
health_check() {
    print_header

    echo -e "${BOLD}Running Health Checks...${NC}"
    echo -e "─────────────────────────────────────────────────────────────"

    local all_ok=true

    # API Health
    local health=$(check_health)
    if [ -n "$health" ]; then
        echo -e "${GREEN}✓${NC} API Health Endpoint"
    else
        echo -e "${RED}✗${NC} API Health Endpoint"
        all_ok=false
    fi

    # PostgreSQL
    if nc -z localhost "$POSTGRES_PORT" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} PostgreSQL (port $POSTGRES_PORT)"
    else
        echo -e "${RED}✗${NC} PostgreSQL (port $POSTGRES_PORT)"
        all_ok=false
    fi

    # Neo4j
    if nc -z localhost "$NEO4J_HTTP_PORT" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Neo4j HTTP (port $NEO4J_HTTP_PORT)"
    else
        echo -e "${RED}✗${NC} Neo4j HTTP (port $NEO4J_HTTP_PORT)"
        all_ok=false
    fi

    # Qdrant
    if nc -z localhost "$QDRANT_PORT" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Qdrant (port $QDRANT_PORT)"
    else
        echo -e "${RED}✗${NC} Qdrant (port $QDRANT_PORT)"
        all_ok=false
    fi

    # Redis
    if nc -z localhost "$REDIS_PORT" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Redis (port $REDIS_PORT)"
    else
        echo -e "${RED}✗${NC} Redis (port $REDIS_PORT)"
        all_ok=false
    fi

    echo ""

    if [ "$all_ok" = true ]; then
        echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}  All health checks passed!${NC}"
        echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
        return 0
    else
        echo -e "${RED}═══════════════════════════════════════════════════════════${NC}"
        echo -e "${RED}  Some health checks failed!${NC}"
        echo -e "${RED}═══════════════════════════════════════════════════════════${NC}"
        return 1
    fi
}

# Show usage
show_usage() {
    print_header

    echo -e "${BOLD}Usage:${NC} $0 <command> [options]"
    echo ""
    echo -e "${BOLD}Commands:${NC}"
    echo -e "  ${GREEN}status${NC}       Show status of all components"
    echo -e "  ${GREEN}start${NC}        Start the HELIX API"
    echo -e "  ${GREEN}stop${NC}         Stop the HELIX API"
    echo -e "  ${GREEN}restart${NC}      Restart the HELIX API"
    echo -e "  ${GREEN}logs${NC} [N]     Show last N lines of logs (default: 50)"
    echo -e "  ${GREEN}logs -f${NC}      Follow log output"
    echo -e "  ${GREEN}docker-up${NC}    Start Docker containers"
    echo -e "  ${GREEN}docker-down${NC}  Stop Docker containers"
    echo -e "  ${GREEN}health${NC}       Run health checks"
    echo ""
    echo -e "${BOLD}Instance:${NC} $INSTANCE"
    echo -e "${BOLD}HELIX Root:${NC} $HELIX_ROOT"
    echo -e "${BOLD}API Port:${NC} $API_PORT"
    echo ""
}

# Main command handler
case "$1" in
    status)
        show_status
        ;;
    start)
        print_header
        start_api
        ;;
    stop)
        print_header
        stop_api
        ;;
    restart)
        print_header
        restart_api
        ;;
    logs)
        if [ "$2" = "-f" ]; then
            show_logs 50 "-f"
        else
            show_logs "${2:-50}"
        fi
        ;;
    docker-up)
        print_header
        docker_up
        ;;
    docker-down)
        print_header
        docker_down
        ;;
    health)
        health_check
        ;;
    *)
        show_usage
        ;;
esac
