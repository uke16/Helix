# Problem: Consultant weiß nicht welche Skills relevant sind

Der Consultant Agent muss aktuell ALLE Skills lesen (~5000 Zeilen) obwohl meist nur 1-2 relevant sind.

**Beispiel:**
User fragt nach "BOM Export für SAP" 
→ Consultant liest: helix/, encoder/, infrastructure/, pdm/, lsp/
→ Aber nur pdm/ und infrastructure/ wären relevant gewesen

**Weitere Probleme:**
- Es gibt keinen Überblick welche Skills überhaupt existieren
- Man weiß nicht welches ADR eine bestimmte Datei erstellt hat
- ADR Status kann falsch sein ("Implemented" obwohl Dateien fehlen)

Wir brauchen eine Lösung für intelligenteres Skill-Laden und bessere ADR-Traceability.

**Constraints:**
- Kein Embedding-Service (zu komplex/teuer)
- Muss auch ohne Matches funktionieren (Fallback)
- Integration mit bestehendem System
