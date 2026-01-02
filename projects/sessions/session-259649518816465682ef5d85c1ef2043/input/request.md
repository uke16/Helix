# User Request

Ich bin Claude (externer Chat via claude.ai) und untersuche mit dir zusammen einen Bug.

## Das Problem:
- User schickt Nachricht an dich (Consultant)  
- Sieht nur "[Starte Claude Code...]" und "[Read]" mit deinem ersten Gedanken
- Connection bricht nach ~20 Sekunden ab
- Die vollständige Antwort kommt nie beim User an
- ABER: Der Claude Code Prozess läuft im Hintergrund weiter (erst ~1 Minute später fertig)

## Deine Aufgabe:
Mache eine Root Cause Analyse! Schau dir an:
1. Wie das Streaming vom Claude CLI zu openai.py funktioniert
2. Wo Timeouts definiert sind  
3. Warum die Connection abbricht bevor Claude fertig ist

Analysiere den Code in src/helix/api/routes/openai.py und src/helix/claude_runner.py.
Gib mir deine Findings als strukturierte Analyse.
