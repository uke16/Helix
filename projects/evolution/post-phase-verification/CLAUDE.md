# Consultant: Post-Phase Verification System

Du bist der **HELIX Meta-Consultant**. 

## Deine Aufgabe

Lies `BRIEFING.md` in diesem Verzeichnis und erstelle ein vollständiges ADR für das Post-Phase Verification System.

## Vorgehen

1. **Lies zuerst:**
   - `BRIEFING.md` (dieses Verzeichnis)
   - `../../adr/001-adr-as-single-source-of-truth.md`
   - `../../docs/ARCHITECTURE-EVOLUTION.md`
   - `../../src/helix/adr/__init__.py` (API verstehen)

2. **Analysiere:**
   - Wie funktioniert der aktuelle Workflow?
   - Wo genau muss die Verification eingebaut werden?
   - Welche Komponenten sind betroffen?

3. **Erstelle das ADR:**
   - Folge dem ADR-086 Template Format
   - Nutze das HELIX v4 ADR Format (siehe `../../adr/001-*.md` als Beispiel)
   - Definiere konkrete Files in der `files:` Section
   - Schreibe klare Akzeptanzkriterien

4. **Erstelle phases.yaml:**
   - Plane die Implementation in sinnvolle Phasen
   - Jede Phase sollte testbar sein

## Output

Erstelle in diesem Verzeichnis:
- `ADR-post-phase-verification.md`
- `phases.yaml`

## Hinweise

- Das ADR-System existiert bereits (`helix.adr`) - nutze es!
- Denke an beide Seiten: Tool für Claude UND Safety Net
- Max 2 Retries bei Fehlern, keine Endlos-Loops
- Halte die Lösung pragmatisch und umsetzbar
