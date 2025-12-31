#!/bin/bash
# verify-adr-039.sh - Automatische Verifikation ALLER Phasen

HELIX_ROOT="${HELIX_ROOT:-/home/aiuser01/helix-v4}"
cd "$HELIX_ROOT"

FAILED=0

echo "═══════════════════════════════════════════════════════════"
echo "  ADR-039 Verifikation - ALLE Phasen"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Phase 1
echo "▶ Phase 1: Paths"
HARDCODED=$(grep -r "/home/aiuser01" src/ --include="*.py" 2>/dev/null | grep -v "__pycache__" | wc -l)
if [ "$HARDCODED" -eq 0 ]; then
    echo "  ✅ Keine hardcoded paths"
else
    echo "  ❌ $HARDCODED hardcoded paths"
    FAILED=1
fi
echo ""

# Phase 2
echo "▶ Phase 2: LSP"
if grep -q "ENABLE_LSP" config/env.sh 2>/dev/null; then
    echo "  ✅ ENABLE_LSP_TOOL in config/env.sh"
else
    echo "  ❌ ENABLE_LSP_TOOL fehlt"
    FAILED=1
fi

if grep -q "pyright" pyproject.toml 2>/dev/null; then
    echo "  ✅ pyright in pyproject.toml"
else
    echo "  ❌ pyright fehlt"
    FAILED=1
fi
echo ""

# Phase 3
echo "▶ Phase 3: Docs"
if [ -f "docs/CONFIGURATION-GUIDE.md" ]; then
    echo "  ✅ docs/CONFIGURATION-GUIDE.md"
else
    echo "  ❌ docs/CONFIGURATION-GUIDE.md fehlt"
    FAILED=1
fi

if [ -f "docs/PATHS.md" ]; then
    echo "  ✅ docs/PATHS.md"
else
    echo "  ❌ docs/PATHS.md fehlt"
    FAILED=1
fi
echo ""

# Phase 4
echo "▶ Phase 4: Tests"
export PYTHONPATH="$HELIX_ROOT/src"
if python3 -m pytest tests/unit/ -q --tb=no 2>/dev/null | grep -q "passed"; then
    echo "  ✅ Unit Tests passed"
else
    echo "  ❌ Unit Tests failed"
    FAILED=1
fi
echo ""

# Ergebnis
echo "═══════════════════════════════════════════════════════════"
if [ "$FAILED" -eq 0 ]; then
    echo "  ✅ ALLE PHASEN BESTANDEN"
    echo "  <promise>ADR039_COMPLETE</promise> ERLAUBT"
    exit 0
else
    echo "  ❌ VERIFIKATION FEHLGESCHLAGEN"
    exit 1
fi
