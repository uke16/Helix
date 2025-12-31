# Ralph Wiggum Pattern - Kontext für ADR

## Was ist Ralph?

Ralph ist ein iteratives AI-Entwicklungsmuster basierend auf Geoffrey Huntley's Technik:
- Eine `while true` Loop die denselben Prompt wiederholt
- Claude arbeitet iterativ bis ein "Completion Promise" erfüllt ist
- Vorherige Arbeit ist in Dateien/Git sichtbar
- Selbst-Korrektur durch Iteration

## Wie funktioniert es?

```bash
/ralph-loop "<prompt>" --max-iterations <n> --completion-promise "<text>"
```

Claude iteriert bis:
1. Die Aufgabe erfüllt ist
2. Das Promise als `<promise>TEXT</promise>` ausgegeben wird
3. Oder max-iterations erreicht ist

## Bewährte Patterns aus ADR-039

### Developer Pattern
```
Completion Promise: UNIT_TESTS_PASSED
Kriterien:
- Alle Unit Tests grün
- Syntax Check OK
- Keine Linter Errors
```

### Integrator Pattern
```
Completion Promise: INTEGRATION_TEST_PASSED
Kriterien:
- API startet
- Smoke Test: Consultant antwortet
- Response > 50 Zeichen, kein nur STEP-Marker
```

### Sub-Agent Freigabe Konzept

Der Clou: Der Integration Test ist selbst ein API-Call an den Consultant.
Das heißt: Ein Claude (Controller) ruft einen anderen Claude (Consultant) auf.
Nur wenn der Sub-Agent funktioniert, ist die Integration erfolgreich.

```
Controller (Ralph Loop)
    ↓
Implementiert Code
    ↓
Startet API
    ↓
Ruft Consultant auf (Sub-Agent)
    ↓
Consultant antwortet? → Integration OK
    ↓
<promise>INTEGRATION_TEST_PASSED</promise>
```

## Offene Fragen für ADR

1. Soll jedes ADR eine "Ralph Section" haben?
2. Welche Completion Promises sind Standard?
3. Wie definiert man Sub-Agent Freigabe Kriterien?
4. Gibt es universelle Patterns (Reviewer, Dokumentierer)?
