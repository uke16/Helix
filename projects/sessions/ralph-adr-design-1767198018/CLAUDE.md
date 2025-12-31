# Consultant Session: Ralph ADR Design

Du bist der HELIX Consultant. Entwirf ein ADR für die Ralph-Integration in den HELIX Evolution Workflow.

## Kontext

Lies `context/ralph-context.md` für Hintergrund zum Ralph Pattern.

## Aufgabe

Erstelle ein ADR-040 das definiert:

1. **Ralph Section in ADRs**
   - Jedes ADR bekommt eine "## Ralph Automation" Section
   - Dort stehen die Completion Promises für jede Rolle

2. **Standard Completion Promises**
   - Developer: `IMPLEMENTATION_COMPLETE`
   - Tester: `TESTS_PASSING`
   - Integrator: `INTEGRATION_VERIFIED`
   - Reviewer: `REVIEW_APPROVED`
   - Dokumentierer: `DOCS_COMPLETE`

3. **Sub-Agent Freigabe**
   - Wie der Integration Test als Sub-Agent Freigabe funktioniert
   - Kriterien für erfolgreiche Sub-Agent Response

4. **Universelle Patterns**
   - Reviewer: Checkliste abarbeiten
   - Dokumentierer: Alle Sections vorhanden

## Output

Schreibe das ADR nach `output/ADR-040-ralph-automation.md`

Nutze das Standard ADR Format mit YAML Header.
