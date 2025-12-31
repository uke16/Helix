#!/bin/bash
# verify-with-consultant.sh - Automatische Checks + Consultant Review
#
# Usage: ./control/verify-with-consultant.sh adr/039-*.md
#
# 1. Führt automatische Checks aus
# 2. Spawnt Consultant der ADR liest und prüft ob ALLES erfüllt ist

set -euo pipefail

HELIX_ROOT="${HELIX_ROOT:-/home/aiuser01/helix-v4}"
cd "$HELIX_ROOT"

ADR_FILE="${1:-}"
if [ -z "$ADR_FILE" ] || [ ! -f "$ADR_FILE" ]; then
    echo "Usage: $0 <adr-file.md>"
    echo "Example: $0 adr/039-code-quality-hardening---paths-lsp-documentation.md"
    exit 1
fi

ADR_ID=$(basename "$ADR_FILE" | grep -oE '^[0-9]+' || echo "XXX")

echo "═══════════════════════════════════════════════════════════"
echo "  ADR-$ADR_ID Verifikation mit Consultant"
echo "═══════════════════════════════════════════════════════════"
echo ""

# ─────────────────────────────────────────────────────────────────
# TEIL 1: Automatische Checks (was wir automatisieren können)
# ─────────────────────────────────────────────────────────────────
AUTO_RESULTS=""

echo "▶ Automatische Checks"
echo ""

# Check 1: Hardcoded Paths
HARDCODED=$(grep -r "/home/aiuser01" src/ --include="*.py" 2>/dev/null | grep -v "__pycache__" | wc -l)
if [ "$HARDCODED" -eq 0 ]; then
    echo "  ✅ Keine hardcoded paths in src/"
    AUTO_RESULTS+="✅ Keine hardcoded paths in src/\n"
else
    echo "  ❌ $HARDCODED hardcoded paths gefunden"
    AUTO_RESULTS+="❌ $HARDCODED hardcoded paths gefunden\n"
fi

# Check 2: Unit Tests
export PYTHONPATH="$HELIX_ROOT/src"
if python3 -m pytest tests/unit/ -q --tb=no 2>/dev/null | grep -q "passed"; then
    PASSED=$(python3 -m pytest tests/unit/ -q --tb=no 2>/dev/null | grep -oE '[0-9]+ passed' | head -1)
    echo "  ✅ Unit Tests: $PASSED"
    AUTO_RESULTS+="✅ Unit Tests: $PASSED\n"
else
    echo "  ❌ Unit Tests failed"
    AUTO_RESULTS+="❌ Unit Tests failed\n"
fi

# Check 3: Files aus YAML Header
echo ""
echo "  Files aus ADR Header:"
# Extrahiere files.create aus YAML
FILES_CREATE=$(sed -n '/^files:/,/^[a-z]/p' "$ADR_FILE" | grep -A100 "create:" | grep "^\s*-" | sed 's/.*- //' | head -20)
for FILE in $FILES_CREATE; do
    if [ -f "$FILE" ]; then
        echo "    ✅ $FILE"
        AUTO_RESULTS+="✅ $FILE existiert\n"
    else
        echo "    ❌ $FILE fehlt"
        AUTO_RESULTS+="❌ $FILE fehlt\n"
    fi
done

echo ""

# ─────────────────────────────────────────────────────────────────
# TEIL 2: Consultant prüft ALLES (inkl. textuelle Anforderungen)
# ─────────────────────────────────────────────────────────────────
echo "▶ Consultant Review"
echo ""

# Lese ADR Inhalt
ADR_CONTENT=$(cat "$ADR_FILE")

# Erstelle Prompt für Consultant
PROMPT="Du bist der HELIX Verifikations-Consultant.

AUFGABE: Prüfe ob ADR-$ADR_ID VOLLSTÄNDIG implementiert ist.

═══════════════════════════════════════════════════════════
AUTOMATISCHE CHECK-ERGEBNISSE:
═══════════════════════════════════════════════════════════
$(echo -e "$AUTO_RESULTS")

═══════════════════════════════════════════════════════════
ADR INHALT:
═══════════════════════════════════════════════════════════
$ADR_CONTENT

═══════════════════════════════════════════════════════════
DEINE AUFGABE:
═══════════════════════════════════════════════════════════
1. Lies die Akzeptanzkriterien und alle Anforderungen im ADR
2. Vergleiche mit den automatischen Check-Ergebnissen
3. Identifiziere was die automatischen Checks NICHT geprüft haben
4. Gib ein Verdict:

Falls ALLES erfüllt:
  VERDICT: PASSED
  <promise>ADR_${ADR_ID}_COMPLETE</promise>

Falls etwas fehlt:
  VERDICT: FAILED
  FEHLEND:
  - [Liste was noch fehlt]
  
Sei präzise und prüfe JEDE Anforderung im ADR!"

# Spawne Consultant
echo "  Spawne Consultant für Review..."
echo ""

# Nutze spawn-consultant.sh oder direkten Claude Call
if [ -x "$HELIX_ROOT/control/spawn-consultant.sh" ]; then
    VERDICT=$("$HELIX_ROOT/control/spawn-consultant.sh" "$PROMPT" 2>/dev/null)
else
    # Fallback: Direkter Claude Call
    export PATH="/home/aiuser01/.nvm/versions/node/v20.19.6/bin:$PATH"
    VERDICT=$(claude --print --dangerously-skip-permissions "$PROMPT" 2>/dev/null)
fi

echo "═══════════════════════════════════════════════════════════"
echo "  CONSULTANT VERDICT"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "$VERDICT"
echo ""

# Prüfe ob PASSED
if echo "$VERDICT" | grep -q "VERDICT: PASSED"; then
    echo "═══════════════════════════════════════════════════════════"
    echo "  ✅ VERIFIKATION BESTANDEN"
    echo "═══════════════════════════════════════════════════════════"
    exit 0
else
    echo "═══════════════════════════════════════════════════════════"
    echo "  ❌ VERIFIKATION FEHLGESCHLAGEN"
    echo "═══════════════════════════════════════════════════════════"
    exit 1
fi
