# Request: Intelligent Documentation Discovery

## Was wird benötigt?

Ein System für HELIX v4 das:

1. **Skill Index** - Automatisch generierter Index aller Skills mit Keywords
2. **Smart Skill Selection** - Consultant bekommt automatisch relevante Skills empfohlen
3. **Reverse Index (CODE → ADR)** - Für jede Datei wissen welches ADR sie erstellt hat
4. **ADR Status Auto-Detection** - Prüft ob "Implemented" wirklich implementiert ist

## Warum?

- Consultant liest aktuell ALLE Skills (teuer, langsam)
- Keine Übersicht welche Skills existieren
- Keine Traceability: "Warum gibt es diese Datei?"
- ADR Status kann falsch sein (sagt "Implemented", aber Dateien fehlen)

## Constraints

- Muss stabil und zuverlässig funktionieren
- Fallback wenn keine Matches
- Kein Embedding-Service (zu komplex)
- Integration mit bestehendem Docs-System (ADR-014, ADR-019)

## Bereits erarbeitete Konzepte

Siehe Elaboration in vorheriger Diskussion:
- Hybrid-Ansatz für Skill Selection (auto-extracted + manuelle aliases)
- On-Demand Generierung für Reverse Index
- Drei Kategorien: tracked/untracked/orphaned
