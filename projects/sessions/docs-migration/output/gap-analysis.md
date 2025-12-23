# Gap-Analyse: Manuelle vs. Generierte CLAUDE.md

## Übersicht

| Metrik | Manuell | Generiert | Differenz |
|--------|---------|-----------|-----------|
| Zeilen | 377 | 354 | -23 (-6%) |
| Sections | 16 | 15 | -1 |
| Code-Beispiele | 14 | 9 | -5 |

---

## Identifizierte Gaps

### Gap 1: Fehlende "Consultant-Rolle" Details

**Manuelle Version (Zeilen 162-211):**
```markdown
### Fragen-Schema
## Klärende Fragen

### Was genau soll gebaut werden?
[Warte auf User-Antwort]

### Warum wird das benötigt?
[Warte auf User-Antwort]

### Welche Constraints gibt es?
[Warte auf User-Antwort]

### Output generieren
**spec.yaml:**
name: Feature Name
type: feature
...

**phases.yaml:**
phases:
  - id: 01-analysis
    name: Analyse
    type: development
```

**Generierte Version (Zeilen 210-220):**
- Nur 4 Bullet Points ohne Details
- Kein Fragen-Schema
- Keine spec.yaml/phases.yaml Templates
- Nur Link zu `skills/helix/SKILL.md`

**Impact:** HOCH - Consultant-Instanzen wissen nicht wie sie arbeiten sollen

---

### Gap 2: Fehlende "Quality Gates Reference" Details

**Manuelle Version (Zeilen 65-126):**
- Vollständige Tabelle mit Beschreibungen
- Detaillierte `adr_valid` Section mit:
  - Was wird geprüft (3 Kategorien)
  - Fehler vs. Warnungen Erklärung
  - Beispiel-Verwendung mit YAML

**Generierte Version (Zeilen 76-149):**
- Tabelle ohne Beschreibungen (nur description_short)
- `adr_valid` Section fehlen:
  - "Fehler vs. Warnungen" Erklärung
  - Beispiel-Verwendung

**Impact:** MITTEL - Weniger Kontext, aber Links zu Docs vorhanden

---

### Gap 3: Leerzeilen-Probleme

**Generierte Version:**
- Zeilen 1-3: Leere Zeilen am Anfang
- Zeilen 39-50: Doppelte Leerzeilen zwischen Skills
- Zeilen 84-108: Viele Leerzeilen in der Tabelle
- Zeilen 124-130: Leerzeilen zwischen YAML-Feldern

**Impact:** NIEDRIG - Nur visuell, aber unprofessionell

---

### Gap 4: Pfeil-Zeichen Inkonsistenz

**Manuelle Version:** Verwendet `→` (Unicode)
```markdown
→ Schau in `phases.yaml` welche Output-Dateien erwartet werden.
```

**Generierte Version:** Verwendet `->` (ASCII)
```markdown
-> Schau in `phases.yaml` welche Output-Dateien erwartet werden.
```

**Impact:** NIEDRIG - Nur kosmetisch

---

### Gap 5: Fehlende Checkboxen bei DO/DON'T

**Manuelle Version:**
```markdown
### DO:
- ✅ Lies CLAUDE.md in deinem Verzeichnis
- ✅ Lies relevante Skills
...

### DON'T:
- ❌ Ändere keine Dateien außerhalb deines Verzeichnisses
```

**Generierte Version:**
```markdown
### DO:
- Lies CLAUDE.md in deinem Verzeichnis
- Lies relevante Skills
...

### DON'T:
- Ändere keine Dateien außerhalb deines Verzeichnisses
```

**Impact:** NIEDRIG - Nur visuell

---

### Gap 6: Fehlende Evolution Details

**Manuelle Version (Zeilen 257-306):**
- Vollständige Verzeichnisstruktur mit Comments
- Evolution API mit curl-Beispielen
- Safety Guarantees Liste (5 Items)

**Generierte Version (Zeilen 280-305):**
- Verzeichnisstruktur ohne Comments
- KEINE Evolution API
- KEINE Safety Guarantees

**Impact:** HOCH - Evolution-Feature unvollständig dokumentiert

---

### Gap 7: Fehlende Tool Python API

**Manuelle Version (Zeilen 352-367):**
```python
from helix.tools import validate_adr, finalize_adr, get_next_adr_number

# Validate
result = validate_adr("ADR-feature.md")
if not result.success:
    print(result.errors)

# Finalize
result = finalize_adr("ADR-feature.md")
print(result.final_path)  # → adr/013-feature.md
```

**Generierte Version:**
- Nur CLI-Befehle, keine Python API

**Impact:** MITTEL - Developer nutzen häufig Python API

---

### Gap 8: Projekt-Struktur unvollständig

**Manuelle Version:**
```
├── phases/
│   ├── 01-analysis/
│   │   ├── CLAUDE.md
│   │   └── output/
│   ├── 02-implementation/
│   └── 03-testing/
```

**Generierte Version:**
```
└── phases/
```

**Impact:** MITTEL - Zeigt nicht wie Phasen strukturiert sind

---

## Gap-Matrix mit Lösungsvorschlägen

| # | Gap | Schwere | Lösung | Ort |
|---|-----|---------|--------|-----|
| 1 | Consultant Details fehlen | HOCH | YAML Source | `consultant-workflow.yaml` |
| 2 | Quality Gates Details fehlen | MITTEL | Template erweitern | `CLAUDE.md.j2` |
| 3 | Leerzeilen | NIEDRIG | Template fix | `CLAUDE.md.j2` |
| 4 | Pfeil-Zeichen | NIEDRIG | Template fix | `CLAUDE.md.j2` |
| 5 | Checkboxen fehlen | NIEDRIG | Template fix | `CLAUDE.md.j2` |
| 6 | Evolution Details fehlen | HOCH | YAML Source | `evolution.yaml` |
| 7 | Python API fehlt | MITTEL | YAML Source | `tools.yaml` |
| 8 | Struktur unvollständig | MITTEL | Template fix | `CLAUDE.md.j2` |

---

## Empfehlungen

### Neue YAML Sources erstellen:

1. **`consultant-workflow.yaml`** - Fragen-Schema und Output-Templates
2. **`evolution.yaml`** - Evolution API und Safety Guarantees
3. **`tools.yaml`** - Tool-Dokumentation mit CLI + Python API

### Template verbessern:

1. Leerzeilen-Handling mit Jinja2 `{%-` und `-%}` Whitespace Control
2. Unicode-Pfeile statt ASCII
3. Checkboxen bei DO/DON'T
4. Vollständige Projekt-Struktur
5. "Fehler vs. Warnungen" Erklärung hardcoden

---

## Priorisierung

| Priorität | Gaps | Aufwand |
|-----------|------|---------|
| P1 (Sofort) | 1, 6 | 2h - Neue Sources |
| P2 (Wichtig) | 2, 7, 8 | 1h - Template + Source |
| P3 (Nice-to-have) | 3, 4, 5 | 30min - Template |

**Gesamt-Aufwand:** ~3.5 Stunden
