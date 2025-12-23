# Consultant Session: ADR-017 Phase Orchestrator

Du bist der HELIX Consultant. Erstelle ein ADR für den Phase Orchestrator.

## Kontext

Lies diese Dateien um den Kontext zu verstehen:

1. `input/VISION.md` - Langfristige Vision und Evolution v1-v4
2. `input/ARCHITECTURE-ORCHESTRATOR.md` - Technisches Design
3. `input/BACKLOG.md` - Bekannte Bugs und offene Punkte
4. `input/ADR-015.md` - Approval System (verwandt)
5. `input/ADR-TEMPLATE.md` - ADR Format

## Hintergrund

HELIX v4 hat ein Problem: Es gibt keinen automatischen Orchestrator.
Heute war Claude Opus (via claude.ai) der Orchestrator:
- Startete Claude Code CLI manuell
- Wartete und pollte
- Reviewte Outputs
- Kopierte Dateien
- Committete

Das soll automatisch passieren.

## Kernideen (aus ARCHITECTURE-ORCHESTRATOR.md)

1. **Consultant bestimmt Projekt-Typ**: simple | complex | exploratory
2. **Decompose-Regel**: 1-4 Phasen pro Planning
3. **Datenfluss**: Orchestrator kopiert outputs → inputs
4. **Quality Gates**: Fix pro Phase-Type, überschreibbar
5. **CLI + API**: Beide existieren schon

## Deine Aufgabe

Erstelle `output/ADR-017-phase-orchestrator.md` mit:

1. **YAML Header** komplett ausgefüllt:
   - adr_id: "017"
   - change_scope: major (neues Kernfeature)
   - classification: NEW
   - Alle files.create/modify/docs

2. **Kontext**: Warum brauchen wir das? Was ist das Problem?

3. **Entscheidung**: 
   - Was wird gebaut?
   - Welche Alternativen wurden betrachtet?
   - Warum diese Lösung?

4. **Implementation**: 
   - Konkrete Dateien und Code-Struktur
   - phases.yaml Schema-Erweiterung
   - Orchestrator-Klasse
   - CLI Integration

5. **Akzeptanzkriterien**: 
   - Mindestens 8 Checkboxen
   - Funktional, Qualität, Dokumentation

6. **Migration**: 
   - Wie migrieren wir? (Phasen)
   - Rückwärtskompatibilität?

## Qualitätskriterien

- ADR muss `adr_tool validate` bestehen
- Alle Sections mit substantiellem Inhalt
- Konkrete Code-Beispiele
- Realistische Aufwandsschätzung

## Output

Schreibe nach `output/ADR-017-phase-orchestrator.md`
