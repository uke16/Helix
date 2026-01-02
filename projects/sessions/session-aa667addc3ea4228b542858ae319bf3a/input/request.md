# User Request

WICHTIG: Du bist jetzt ein Debugging-Experte. Es gibt einen kritischen Streaming-Bug:

## Symptome:
1. User schickt Nachricht an Consultant (via Open WebUI)
2. User sieht nur "[Starte Claude Code...]" und "[Read]"
3. Connection bricht nach ~20 Sekunden ab
4. Claude-Prozess läuft im Hintergrund WEITER und produziert vollständige Antwort
5. Diese Antwort erreicht den User NIE

## Architektur:
- Caddy (Port 8443) -> Open WebUI (Port 8090) -> HELIX API (Port 8001) -> Claude CLI
- SSE Streaming mit asyncio Queue
- Heartbeat alle 25s (funktioniert scheinbar nicht)

## Verdacht:
- Caddy hat keine expliziten SSE-Timeout Settings
- Open WebUI HTTP Client Timeout?
- asyncio.gather() blockiert den Generator?

Bitte analysiere:
1. Lies src/helix/api/routes/openai.py (die _run_consultant_streaming Funktion)
2. Lies src/helix/claude_runner.py (run_phase_streaming Methode)
3. Prüfe /home/aiuser01/Caddyfile
4. Erstelle eine Root-Cause Analyse mit konkretem Fix-Vorschlag
