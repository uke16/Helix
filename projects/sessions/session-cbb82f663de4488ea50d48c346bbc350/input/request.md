# User Request

# Consultant Request: Streaming Completion Signal - Aufräumen & ADR

## Kontext

Wir haben ein Problem mit dem Streaming-System entdeckt und analysiert:

### Das Problem
1. stdout vom Claude CLI Prozess kann vorzeitig schließen (Bug)
2. Die API nutzte stdout-Ende als "fertig"-Signal
3. Das führte zu unvollständigen Responses

### Was wir rausgefunden haben
1. Die API schreibt status.json, NICHT Claude
2. Der `step` Wert (what/why/constraints/generate/done) wird von einem FALLBACK auf "done" gesetzt wenn kein Step-Marker gefunden wird
3. Das ist SUGAR COATING - es versteckt das Problem statt es zu lösen

### Die Lösung
Claude CLI hat einen `SessionEnd` Hook. Wir haben einen Hook erstellt:
```bash
~/.claude/hooks/session-end.sh
# Schreibt output/.done wenn Claude WIRKLICH fertig ist
```

Die API sollte auf diese Datei warten, nicht auf stdout-Ende.

## Aufgaben

### 1. ADR erstellen
Erstelle ein ADR das beschreibt:
- Das Problem (stdout disconnect, step="done" Fallback als Sugar Coating)
- Die Lösung (SessionEnd Hook + .done Datei als Completion-Signal)
- Was entfernt werden soll

### 2. Identifiziere zu löschenden Code

Finde alles was Sugar Coating ist:
- StepMarkerValidator Fallback (default "done")
- _infer_step() Funktion
- Eventuell das ganze STEP-System wenn nicht anderweitig gebraucht

Fragen:
- Wird `step` in status.json für irgendwas wichtiges gebraucht?
- Welche ADRs haben den Sugar Coating Code eingeführt?
- Können wir selektiv git revert machen?

### 3. Git History analysieren

Welche Commits haben den Fallback-Code eingeführt?
- ADR-038: Deterministic LLM Response Enforcement
- ADR-034: Consultant Flow Refactoring

Können wir diese teilweise reverten?

## Dateien zum Anschauen

- `/home/aiuser01/helix-v4/src/helix/enforcement/validators/step_marker.py` - StepMarkerValidator mit Fallback
- `/home/aiuser01/helix-v4/src/helix/enforcement/response_enforcer.py` - Response Enforcer
- `/home/aiuser01/helix-v4/src/helix/api/routes/openai.py` - API Routes
- `/home/aiuser01/helix-v4/adr/034-consultant-flow-refactoring-llm-native.md`
- `/home/aiuser01/helix-v4/adr/038-*.md`

## Erwartetes Ergebnis

1. Ein ADR das die Architekturänderung beschreibt
2. Liste der zu löschenden/vereinfachenden Code-Teile
3. Empfehlung ob git revert oder manuelles Aufräumen
