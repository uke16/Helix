#!/bin/bash
# =============================================================================
# HELIX v4 Test System Setup Script
# =============================================================================
# Erstellt und konfiguriert das isolierte Test-System fuer Evolution-Testing
#
# Usage:
#   ./setup-test-system.sh [--force]
#
# Optionen:
#   --force    Loescht existierendes Test-System und erstellt neu
# =============================================================================

set -e

# Konfiguration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HELIX_V4_DIR="/home/aiuser01/helix-v4"
TEST_SYSTEM_DIR="/home/aiuser01/helix-v4-test"
DOCKER_DIR="$TEST_SYSTEM_DIR/docker/test"

# Farben fuer Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging Funktionen
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Banner
print_banner() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║           HELIX v4 Test System Setup                          ║"
    echo "║           Evolution Testing Environment                        ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo ""
}

# Pruefe Voraussetzungen
check_prerequisites() {
    log_info "Pruefe Voraussetzungen..."

    # Pruefe ob helix-v4 existiert
    if [ ! -d "$HELIX_V4_DIR" ]; then
        log_error "helix-v4 Verzeichnis nicht gefunden: $HELIX_V4_DIR"
        exit 1
    fi

    # Pruefe ob Docker installiert ist
    if ! command -v docker &> /dev/null; then
        log_error "Docker ist nicht installiert"
        exit 1
    fi

    # Pruefe ob docker-compose installiert ist
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "docker-compose ist nicht installiert"
        exit 1
    fi

    # Pruefe ob git installiert ist
    if ! command -v git &> /dev/null; then
        log_error "git ist nicht installiert"
        exit 1
    fi

    log_success "Alle Voraussetzungen erfuellt"
}

# Erstelle Test-System Verzeichnis
create_test_system() {
    log_info "Erstelle Test-System Verzeichnis..."

    # Pruefe ob Test-System existiert
    if [ -d "$TEST_SYSTEM_DIR" ]; then
        if [ "$1" = "--force" ]; then
            log_warn "Loesche existierendes Test-System..."

            # Stoppe Container falls laufend
            if [ -f "$DOCKER_DIR/docker-compose.yaml" ]; then
                cd "$DOCKER_DIR"
                docker compose down --volumes 2>/dev/null || true
            fi

            rm -rf "$TEST_SYSTEM_DIR"
        else
            log_error "Test-System existiert bereits: $TEST_SYSTEM_DIR"
            log_info "Nutze --force um es zu ueberschreiben"
            exit 1
        fi
    fi

    # Clone helix-v4 nach helix-v4-test
    log_info "Clone helix-v4 nach helix-v4-test..."
    cp -r "$HELIX_V4_DIR" "$TEST_SYSTEM_DIR"

    # Entferne .git und initialisiere neu (isoliertes System)
    rm -rf "$TEST_SYSTEM_DIR/.git"
    cd "$TEST_SYSTEM_DIR"
    git init
    git add -A
    git commit -m "Initial test system setup"

    log_success "Test-System Verzeichnis erstellt"
}

# Konfiguriere Docker
configure_docker() {
    log_info "Konfiguriere Docker fuer Test-System..."

    # Erstelle docker/test Verzeichnis
    mkdir -p "$DOCKER_DIR"
    mkdir -p "$DOCKER_DIR/config"

    # Kopiere docker-compose.test.yaml
    if [ -f "$SCRIPT_DIR/docker-compose.test.yaml" ]; then
        cp "$SCRIPT_DIR/docker-compose.test.yaml" "$DOCKER_DIR/docker-compose.yaml"
        log_success "docker-compose.yaml kopiert"
    else
        log_error "docker-compose.test.yaml nicht gefunden in $SCRIPT_DIR"
        exit 1
    fi

    # Erstelle init-db.sql fuer PostgreSQL
    cat > "$DOCKER_DIR/config/init-db.sql" << 'EOF'
-- HELIX v4 Test System Database Initialization
-- Diese Datei wird beim ersten Start des PostgreSQL Containers ausgefuehrt

-- Erstelle Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Schema fuer HELIX
CREATE SCHEMA IF NOT EXISTS helix;

-- Basis-Tabellen (werden von HELIX beim Start erstellt/migriert)
-- Hier nur grundlegende Konfiguration
EOF

    log_success "Docker-Konfiguration erstellt"
}

# Konfiguriere Environment
configure_environment() {
    log_info "Konfiguriere Environment..."

    # Kopiere .env.test
    if [ -f "$SCRIPT_DIR/.env.test" ]; then
        cp "$SCRIPT_DIR/.env.test" "$DOCKER_DIR/.env"
        log_success ".env Datei kopiert"
    else
        log_error ".env.test nicht gefunden in $SCRIPT_DIR"
        exit 1
    fi

    # Kopiere API Keys von Production wenn vorhanden
    if [ -f "$HELIX_V4_DIR/.env" ]; then
        log_info "Kopiere API Keys von Production..."

        # Extrahiere und kopiere API Keys
        for key in OPENAI_API_KEY ANTHROPIC_API_KEY VOYAGE_API_KEY PERPLEXITY_API_KEY; do
            value=$(grep "^${key}=" "$HELIX_V4_DIR/.env" 2>/dev/null | cut -d'=' -f2- || echo "")
            if [ -n "$value" ]; then
                # Ersetze leeren Key mit Production-Wert
                sed -i "s|^${key}=.*|${key}=${value}|" "$DOCKER_DIR/.env"
                log_success "$key kopiert"
            fi
        done
    else
        log_warn "Production .env nicht gefunden, API Keys muessen manuell gesetzt werden"
    fi

    # Erstelle auch .env.test in Test-System Root
    cp "$DOCKER_DIR/.env" "$TEST_SYSTEM_DIR/.env.test"

    log_success "Environment konfiguriert"
}

# Erstelle Control Script
create_control_script() {
    log_info "Erstelle Control Script..."

    mkdir -p "$TEST_SYSTEM_DIR/control"

    cat > "$TEST_SYSTEM_DIR/control/helix-control.sh" << 'CONTROL_SCRIPT'
#!/bin/bash
# =============================================================================
# HELIX v4 Test System Control Script
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HELIX_DIR="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$HELIX_DIR/docker/test"

# Wechsle ins Docker-Verzeichnis
cd "$DOCKER_DIR"

# Bestimme docker compose Befehl
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

case "$1" in
    status)
        echo "=== HELIX v4 Test System Status ==="
        $COMPOSE_CMD ps
        ;;
    start)
        echo "Starte HELIX v4 Test System..."
        $COMPOSE_CMD up -d
        echo "Test System gestartet"
        echo "API erreichbar unter: http://localhost:9001"
        ;;
    stop)
        echo "Stoppe HELIX v4 Test System..."
        $COMPOSE_CMD stop
        echo "Test System gestoppt"
        ;;
    restart)
        echo "Starte HELIX v4 Test System neu..."
        $COMPOSE_CMD restart
        echo "Test System neu gestartet"
        ;;
    logs)
        shift
        $COMPOSE_CMD logs "$@"
        ;;
    docker-up)
        echo "Starte Docker Container..."
        $COMPOSE_CMD up -d
        ;;
    docker-down)
        echo "Stoppe Docker Container..."
        $COMPOSE_CMD down
        ;;
    health)
        echo "=== Health Check ==="
        echo ""
        echo "Checking services..."

        # HELIX API
        if curl -s -f http://localhost:9001/health > /dev/null 2>&1; then
            echo "[OK] HELIX API (Port 9001)"
        else
            echo "[FAIL] HELIX API (Port 9001)"
        fi

        # PostgreSQL
        if pg_isready -h localhost -p 5433 > /dev/null 2>&1; then
            echo "[OK] PostgreSQL (Port 5433)"
        else
            echo "[FAIL] PostgreSQL (Port 5433)"
        fi

        # Neo4j
        if curl -s -f http://localhost:7475 > /dev/null 2>&1; then
            echo "[OK] Neo4j (Port 7475)"
        else
            echo "[FAIL] Neo4j (Port 7475)"
        fi

        # Qdrant
        if curl -s -f http://localhost:6335/health > /dev/null 2>&1; then
            echo "[OK] Qdrant (Port 6335)"
        else
            echo "[FAIL] Qdrant (Port 6335)"
        fi

        # Redis
        if redis-cli -p 6380 ping > /dev/null 2>&1; then
            echo "[OK] Redis (Port 6380)"
        else
            echo "[FAIL] Redis (Port 6380)"
        fi
        ;;
    reset)
        echo "Setze Test-System zurueck..."
        $COMPOSE_CMD down --volumes
        git reset --hard HEAD
        git clean -fd
        echo "Test-System zurueckgesetzt"
        ;;
    *)
        echo "Usage: $0 {status|start|stop|restart|logs|docker-up|docker-down|health|reset}"
        echo ""
        echo "Commands:"
        echo "  status      Show status of all containers"
        echo "  start       Start the test system"
        echo "  stop        Stop the test system"
        echo "  restart     Restart the test system"
        echo "  logs        Show container logs (accepts container name)"
        echo "  docker-up   Start Docker containers"
        echo "  docker-down Stop Docker containers"
        echo "  health      Run health check on all services"
        echo "  reset       Reset test system to clean state"
        exit 1
        ;;
esac
CONTROL_SCRIPT

    chmod +x "$TEST_SYSTEM_DIR/control/helix-control.sh"
    log_success "Control Script erstellt"
}

# Erstelle Dockerfile falls nicht vorhanden
create_dockerfile() {
    log_info "Pruefe Dockerfile..."

    local dockerfile_dir="$TEST_SYSTEM_DIR/docker/helix-api"
    mkdir -p "$dockerfile_dir"

    if [ ! -f "$dockerfile_dir/Dockerfile" ]; then
        log_info "Erstelle Dockerfile fuer HELIX API..."

        cat > "$dockerfile_dir/Dockerfile" << 'DOCKERFILE'
# HELIX v4 API Dockerfile
FROM python:3.12-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Application code wird als Volume gemountet

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start command
CMD ["python", "-m", "uvicorn", "helix.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
DOCKERFILE

        log_success "Dockerfile erstellt"
    else
        log_info "Dockerfile existiert bereits"
    fi
}

# Starte Test-System
start_test_system() {
    log_info "Starte Test-System..."

    cd "$DOCKER_DIR"

    # Bestimme docker compose Befehl
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        COMPOSE_CMD="docker-compose"
    fi

    # Starte nur die Datenbank-Container initial
    log_info "Starte Datenbank-Container..."
    $COMPOSE_CMD up -d postgres neo4j qdrant redis minio minio-init

    # Warte auf Datenbanken
    log_info "Warte auf Datenbanken..."
    sleep 10

    log_success "Test-System bereit"
    echo ""
    echo "=== HELIX v4 Test System ==="
    echo ""
    echo "Verzeichnis: $TEST_SYSTEM_DIR"
    echo ""
    echo "Ports:"
    echo "  PostgreSQL: localhost:5433"
    echo "  Neo4j HTTP: localhost:7475"
    echo "  Neo4j Bolt: localhost:7688"
    echo "  Qdrant:     localhost:6335"
    echo "  Redis:      localhost:6380"
    echo "  MinIO API:  localhost:9020"
    echo "  MinIO UI:   localhost:9021"
    echo ""
    echo "Control Script: $TEST_SYSTEM_DIR/control/helix-control.sh"
    echo ""
    echo "Naechste Schritte:"
    echo "  1. HELIX API starten: ./control/helix-control.sh start"
    echo "  2. Health Check:      ./control/helix-control.sh health"
    echo ""
}

# Zeige Zusammenfassung
print_summary() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║           Setup abgeschlossen!                                 ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo ""
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    print_banner

    check_prerequisites
    create_test_system "$1"
    configure_docker
    configure_environment
    create_control_script
    create_dockerfile
    start_test_system

    print_summary
}

# Fuehre Main mit allen Argumenten aus
main "$@"
