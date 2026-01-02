#!/bin/bash
#
# Anti-Pattern Detector für HELIX
# Warnt bei verdächtigen Code-Patterns
#

set -e

RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

FOUND_ISSUES=0

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
    FOUND_ISSUES=$((FOUND_ISSUES + 1))
}

error() {
    echo -e "${RED}[ANTI-PATTERN]${NC} $1"
    FOUND_ISSUES=$((FOUND_ISSUES + 1))
}

echo "Scanning for anti-patterns in src/helix/..."
echo ""

# Pattern 1: Index-basierte Message-Logik
if grep -rn "if len(.*messages" src/helix/ --include="*.py" 2>/dev/null | grep -v test | grep -v __pycache__; then
    error "Index-based message logic found (len(messages) >= N)"
    echo "  → Consider: Let the LLM analyze content, not count messages"
    echo ""
fi

# Pattern 2: Hardcoded Trigger/Keyword Listen
if grep -rn "triggers\s*=\s*\[" src/helix/ --include="*.py" 2>/dev/null | grep -v test | grep -v __pycache__; then
    warn "Hardcoded trigger list found"
    echo "  → Consider: LLM-based intent detection instead"
    echo ""
fi

# Pattern 3: String Matching für Intent
if grep -rn "in .*\.lower()" src/helix/ --include="*.py" 2>/dev/null | grep -v test | grep -v __pycache__ | head -5; then
    warn "String matching on lowercased text (possible intent detection)"
    echo "  → Consider: Semantic analysis via LLM"
    echo ""
fi

# Pattern 4: Step-basierte State Machines
if grep -rn 'step.*=.*["'"'"']' src/helix/ --include="*.py" 2>/dev/null | grep -v test | grep -v __pycache__; then
    error "Step-based state machine found"
    echo "  → Consider: Let the LLM manage conversation flow"
    echo ""
fi

# Zusammenfassung
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $FOUND_ISSUES -eq 0 ]; then
    echo -e "${YELLOW}No anti-patterns found${NC}"
else
    echo -e "${RED}Found $FOUND_ISSUES potential anti-patterns${NC}"
    echo ""
    echo "Read: /home/aiuser01/claude-memory/lessons/2025-12-30-anti-patterns-root-cause.md"
fi

exit 0  # Don't block commits, just warn
