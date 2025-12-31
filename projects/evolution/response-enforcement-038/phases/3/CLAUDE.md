# Phase 3: ADR Structure & File Existence Validators

## Aufgabe

Implementiere die beiden verbleibenden Validators:
1. ADRStructureValidator
2. FileExistenceValidator

## ADR Referenz

Lies `ADR-038.md` Sections "3. ADR Structure Validator" und "4. File Existence Validator".

## Input

- Phase 1 Output: Base Validator Interface
- Phase 2 Output: Step Marker Validator (als Referenz)

## Erwartete Output-Dateien

Erstelle in `output/new/`:

```
output/new/
├── src/helix/enforcement/validators/
│   ├── adr_structure.py
│   └── file_existence.py
└── tests/unit/enforcement/
    └── test_validators.py
```

## Implementation Details

### adr_structure.py

Prüft:
- YAML Header mit Pflichtfeldern (adr_id, title, status)
- Pflicht-Sections (Kontext, Entscheidung, Akzeptanzkriterien)
- Mindestens 3 Akzeptanzkriterien (Warning)

**Wichtig**: Nur validieren wenn Response ein ADR enthält (`---\nadr_id:`)

### file_existence.py

Prüft:
- `files.modify` Einträge existieren im Dateisystem
- **helix_root** muss im Konstruktor übergeben werden

Fallback:
- Nicht existierende Dateien von `files.modify` nach `files.create` verschieben

### test_validators.py

Teste beide Validators:

**ADRStructureValidator:**
- Vollständiges ADR wird akzeptiert
- Fehlendes YAML-Feld wird erkannt
- Fehlende Section wird erkannt
- Wenige Akzeptanzkriterien erzeugen Warning

**FileExistenceValidator:**
- Existierende Dateien werden akzeptiert
- Nicht-existierende Dateien werden erkannt
- Fallback verschiebt Dateien korrekt

## Quality Gate

- `pytest tests/unit/enforcement/ -v` muss bestehen

## Checkliste

- [ ] `adr_structure.py` prüft YAML Header
- [ ] `adr_structure.py` prüft Pflicht-Sections
- [ ] `adr_structure.py` prüft Akzeptanzkriterien
- [ ] `file_existence.py` prüft files.modify
- [ ] `file_existence.py` implementiert Fallback
- [ ] Tests für alle Validator-Funktionen
- [ ] Tests für Fallback-Mechanismen
