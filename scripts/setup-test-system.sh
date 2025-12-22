#!/bin/bash
# HELIX v4 Test System Setup Script
# Part of Phase 14: Self-Evolution System

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HELIX_V4_DIR="$(dirname "$SCRIPT_DIR")"
HELIX_V4_TEST_DIR="/home/aiuser01/helix-v4-test"
DOCKER_TEST_DIR="$HELIX_V4_DIR/docker/test"

echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}  ${BOLD}HELIX v4 Test System Setup${NC}                              ${CYAN}║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# ==========================================================================
# Step 1: Clone or Update helix-v4-test
# ==========================================================================
echo -e "${CYAN}Step 1: Setting up helix-v4-test directory...${NC}"

if [ -d "$HELIX_V4_TEST_DIR" ]; then
    echo -e "${YELLOW}  Directory exists, updating...${NC}"
    cd "$HELIX_V4_TEST_DIR"
    
    # Check if it's a git repo
    if [ -d ".git" ]; then
        git fetch origin 2>/dev/null || true
        git reset --hard origin/main 2>/dev/null || git reset --hard HEAD
    else
        echo -e "${YELLOW}  Not a git repo, removing and re-cloning...${NC}"
        cd ..
        rm -rf "$HELIX_V4_TEST_DIR"
        git clone "$HELIX_V4_DIR" "$HELIX_V4_TEST_DIR"
    fi
else
    echo -e "${CYAN}  Cloning helix-v4...${NC}"
    git clone "$HELIX_V4_DIR" "$HELIX_V4_TEST_DIR"
fi

echo -e "${GREEN}  ✓ helix-v4-test directory ready${NC}"
echo ""

# ==========================================================================
# Step 2: Copy API Keys from Production
# ==========================================================================
echo -e "${CYAN}Step 2: Setting up environment...${NC}"

if [ -f "$HELIX_V4_DIR/.env" ]; then
    # Extract API keys from production .env
    echo -e "${CYAN}  Extracting API keys from production...${NC}"
    
    # Create test .env by combining .env.test template with production API keys
    cp "$DOCKER_TEST_DIR/.env.test" "$HELIX_V4_TEST_DIR/.env"
    
    # Append API keys from production
    echo "" >> "$HELIX_V4_TEST_DIR/.env"
    echo "# API Keys (copied from production)" >> "$HELIX_V4_TEST_DIR/.env"
    grep "API_KEY" "$HELIX_V4_DIR/.env" >> "$HELIX_V4_TEST_DIR/.env" 2>/dev/null || true
    grep "PERPLEXITY" "$HELIX_V4_DIR/.env" >> "$HELIX_V4_TEST_DIR/.env" 2>/dev/null || true
    
    echo -e "${GREEN}  ✓ Environment configured with API keys${NC}"
else
    echo -e "${YELLOW}  ⚠ No production .env found, using defaults${NC}"
    cp "$DOCKER_TEST_DIR/.env.test" "$HELIX_V4_TEST_DIR/.env"
fi
echo ""

# ==========================================================================
# Step 3: Create logs directory
# ==========================================================================
echo -e "${CYAN}Step 3: Creating logs directory...${NC}"
mkdir -p "$HELIX_V4_TEST_DIR/logs"
echo -e "${GREEN}  ✓ Logs directory created${NC}"
echo ""

# ==========================================================================
# Step 4: Start Docker containers
# ==========================================================================
echo -e "${CYAN}Step 4: Starting Docker infrastructure...${NC}"

cd "$DOCKER_TEST_DIR"

# Check if docker-compose is available
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
elif command -v docker &> /dev/null && docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    echo -e "${RED}  ✗ Docker Compose not found!${NC}"
    exit 1
fi

# Start containers
$COMPOSE_CMD up -d

echo -e "${CYAN}  Waiting for services to be ready...${NC}"
sleep 10

echo -e "${GREEN}  ✓ Docker containers started${NC}"
echo ""

# ==========================================================================
# Step 5: Health Checks
# ==========================================================================
echo -e "${CYAN}Step 5: Running health checks...${NC}"

check_service() {
    local name=$1
    local port=$2
    if nc -z localhost "$port" 2>/dev/null; then
        echo -e "${GREEN}  ✓${NC} $name (port $port)"
        return 0
    else
        echo -e "${RED}  ✗${NC} $name (port $port)"
        return 1
    fi
}

all_ok=true
check_service "PostgreSQL" 5433 || all_ok=false
check_service "Neo4j HTTP" 7475 || all_ok=false
check_service "Neo4j Bolt" 7688 || all_ok=false
check_service "Qdrant" 6335 || all_ok=false
check_service "Redis" 6380 || all_ok=false

echo ""

if [ "$all_ok" = true ]; then
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  Test System Setup Complete!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${BOLD}Test System Location:${NC} $HELIX_V4_TEST_DIR"
    echo -e "  ${BOLD}API Port:${NC} 9001"
    echo ""
    echo -e "  ${CYAN}To start the Test API:${NC}"
    echo -e "    cd $HELIX_V4_TEST_DIR"
    echo -e "    ./control/helix-control.sh start"
    echo ""
    echo -e "  ${CYAN}To check status:${NC}"
    echo -e "    ./control/helix-control.sh status"
    echo ""
else
    echo -e "${RED}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}  Some services failed to start!${NC}"
    echo -e "${RED}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  Check Docker logs:"
    echo -e "    docker logs helix-test-postgres"
    echo -e "    docker logs helix-test-neo4j"
    echo ""
    exit 1
fi
