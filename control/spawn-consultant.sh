#!/bin/bash
# spawn-consultant.sh - Spawnt Consultant als Sub-Agent
#
# Usage: 
#   ./spawn-consultant.sh "Frage"                    # Einfache Frage
#   ./spawn-consultant.sh review src/foo.py          # Code Review
#   ./spawn-consultant.sh analyze "Thema"            # Analyse
#   ./spawn-consultant.sh adr "Titel"                # ADR Draft

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HELIX_ROOT="$(dirname "$SCRIPT_DIR")"

# NVM laden
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
export PATH="/home/aiuser01/.nvm/versions/node/v20.19.6/bin:$PATH"

# Consultant System Prompt
CONSULTANT_PROMPT="Du bist der HELIX Consultant - ein Experte für Software-Architektur.

WICHTIG: Antworte IMMER mit <!-- STEP: done --> am Ende.

Du hilfst bei:
- Code Reviews (Bugs, Verbesserungen, Best Practices)
- Architektur-Entscheidungen
- ADR-Erstellung im HELIX Format
- Technische Analysen

Sei präzise, konstruktiv und hilfreich."

MODE="${1:-ask}"
shift || true

case "$MODE" in
  review)
    # Code Review
    FILE="$1"
    if [[ -f "$FILE" ]]; then
      CODE=$(cat "$FILE")
      USER_PROMPT="Mache ein Code Review für diese Datei:

Datei: $FILE

\`\`\`
$CODE
\`\`\`

Gib Feedback zu:
1. Bugs/Fehler
2. Code Style
3. Verbesserungsvorschläge
4. Security Issues (falls relevant)"
    else
      echo "Datei nicht gefunden: $FILE"
      exit 1
    fi
    ;;
    
  analyze)
    # Analyse
    TOPIC="$*"
    USER_PROMPT="Analysiere folgendes Thema für HELIX:

$TOPIC

Gib eine strukturierte Analyse mit:
1. Ist-Zustand
2. Probleme/Herausforderungen
3. Lösungsoptionen
4. Empfehlung"
    ;;
    
  adr)
    # ADR Draft
    TITLE="$*"
    USER_PROMPT="Erstelle einen ADR-Entwurf für:

$TITLE

Nutze das HELIX ADR Format mit:
- YAML Header (adr_id, title, status, component_type, classification, files)
- ## Kontext
- ## Entscheidung
- ## Akzeptanzkriterien
- ## Konsequenzen
- ## Ralph Automation (mit Completion Promises)"
    ;;
    
  *)
    # Einfache Frage
    USER_PROMPT="$MODE $*"
    ;;
esac

# Spawne Claude als Consultant
claude --print \
  --dangerously-skip-permissions \
  --system-prompt "$CONSULTANT_PROMPT" \
  --output-format text \
  "$USER_PROMPT"
