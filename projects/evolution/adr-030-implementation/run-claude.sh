#!/bin/bash
cd /home/aiuser01/helix-v4/projects/evolution/adr-030-implementation
export ANTHROPIC_API_KEY=$(cat /home/aiuser01/.anthropic_api_key 2>/dev/null || echo "")

# Log starten
echo "=== Claude Code gestartet: $(date) ===" > claude-output.log
echo "Working directory: $(pwd)" >> claude-output.log
echo "" >> claude-output.log

# Claude Code ausführen
claude --dangerously-skip-permissions -p "Lies CLAUDE.md und führe alle Schritte aus. Implementiere run_evolution_pipeline() und teste es mit dem pipeline-test Projekt. Erstelle die Output-Dateien wenn fertig." >> claude-output.log 2>&1

echo "" >> claude-output.log
echo "=== Claude Code beendet: $(date) ===" >> claude-output.log
