# ADR Template v2 for HELIX v4

> **Basiert auf ADR-086** aus HELIX v3
>
> Dieses Template definiert die Standard-Struktur für Architecture Decision Records in HELIX v4.

---

## Warum ADRs?

Architecture Decision Records (ADRs) dokumentieren wichtige Architektur-Entscheidungen:

1. **Traceability** - Nachvollziehbare Entscheidungshistorie
2. **Knowledge Transfer** - Wissen bleibt erhalten wenn Entwickler wechseln
3. **Automatische Validierung** - Quality Gates prüfen ADR-Konformität
4. **Self-Documentation** - HELIX Claude Code Instanzen verstehen die Architektur

---

## Template Struktur

Ein ADR besteht aus zwei Teilen:

1. **YAML Frontmatter** - Strukturierte Metadaten
2. **Markdown Body** - Dokumentation der Entscheidung

### Minimal-Beispiel

```markdown
---
adr_id: "001"
title: Kurzer, präziser Titel
status: Proposed
---

# ADR-001: Kurzer, präziser Titel

## Kontext

Warum brauchen wir diese Änderung?

## Entscheidung

Was wird entschieden?

## Implementation

Konkrete Umsetzungshinweise.

## Dokumentation

Welche Dokumentation muss aktualisiert werden?

## Akzeptanzkriterien

- [ ] Kriterium 1 erfüllt
- [ ] Kriterium 2 erfüllt
- [ ] Kriterium 3 erfüllt

## Konsequenzen

Vorteile, Nachteile, Risiken.
```

---

## Vollständiges Template

Kopiere dieses Template und fülle es aus:

```markdown
---
adr_id: "NNN"
title: Kurzer, präziser Titel
status: Proposed  # Proposed | Accepted | Implemented | Superseded | Rejected

project_type: helix_internal  # helix_internal | external
component_type: TOOL          # TOOL | NODE | AGENT | PROCESS | SERVICE | SKILL | PROMPT | CONFIG | DOCS | MISC
classification: NEW           # NEW | UPDATE | FIX | REFACTOR | DEPRECATE
change_scope: minor           # major | minor | config | docs | hotfix

files:
  create:
    - path/to/new/file.py
  modify:
    - path/to/existing/file.py
  docs:
    - docs/architecture/feature-x.md

depends_on:
  - ADR-0YY
  - ADR-0ZZ
---

# ADR-NNN: Kurzer, präziser Titel

## Status

📋 Proposed

---

## Kontext

### Was ist das Problem?

[Beschreibe das aktuelle Problem oder die Situation]

### Warum muss es gelöst werden?

[Erkläre die Motivation und Dringlichkeit]

### Was passiert wenn wir nichts tun?

[Konsequenzen der Nicht-Entscheidung]

---

## Entscheidung

### Wir entscheiden uns für:

[Die konkrete Entscheidung in 1-2 Sätzen]

### Diese Entscheidung beinhaltet:

1. [Aspekt 1]
2. [Aspekt 2]
3. [Aspekt 3]

### Warum diese Lösung?

[Begründung, warum diese Alternative gewählt wurde]

### Welche Alternativen wurden betrachtet?

1. **Alternative A**: [Beschreibung] - Nicht gewählt weil: [Grund]
2. **Alternative B**: [Beschreibung] - Nicht gewählt weil: [Grund]

---

## Implementation

### 1. Dateien erstellen/ändern

**Neue Datei:** `path/to/new_module.py`

```python
# path/to/new_module.py

from typing import Any

class NewClass:
    """Beschreibung der Klasse."""

    def new_method(self, arg: str) -> Any:
        """Beschreibung der Methode.

        Args:
            arg: Beschreibung des Arguments.

        Returns:
            Beschreibung des Rückgabewertes.
        """
        pass
```

### 2. Bestehende Dateien anpassen

**Änderung in:** `path/to/existing.py`

```python
# Füge hinzu:
from .new_module import NewClass

# Ändere in Zeile XX:
...
```

### 3. Konfiguration

**Änderung in:** `config/settings.yaml`

```yaml
new_feature:
  enabled: true
  option: value
```

### 4. Tests

**Neue Testdatei:** `tests/test_new_module.py`

```python
import pytest
from path.to.new_module import NewClass

def test_new_method():
    instance = NewClass()
    result = instance.new_method("test")
    assert result is not None
```

---

## Dokumentation

### Zu aktualisierende Dokumente

| Dokument | Änderung |
|----------|----------|
| `docs/ARCHITECTURE-MODULES.md` | Neues Modul beschreiben |
| `docs/sources/*.yaml` | **PFLICHT bei neuen Modulen** - Single Source of Truth |
| `ONBOARDING.md` | Section für neues Feature |
| `CLAUDE.md` | Arbeitsanweisungen aktualisieren |
| `skills/helix/*/SKILL.md` | Skill aktualisieren falls relevant |

### Neue Dokumentation

- [ ] `docs/FEATURE-X.md` erstellen (falls nötig)
- [ ] API-Dokumentation in Docstrings

---

## Akzeptanzkriterien

### 1. Funktionalität

- [ ] Feature X ist implementiert und funktioniert
- [ ] Alle Edge Cases werden behandelt
- [ ] Fehlerbehandlung ist vollständig

### 2. Qualität

- [ ] Unit Tests vorhanden und grün
- [ ] Integration Tests vorhanden
- [ ] Code Review durchgeführt

### 3. Dokumentation

- [ ] ARCHITECTURE-MODULES.md aktualisiert
- [ ] CLAUDE.md aktualisiert (falls relevant)
- [ ] Docstrings für alle public API

### 4. Integration

- [ ] Quality Gate `adr_valid` besteht
- [ ] Keine Breaking Changes (oder dokumentiert)

---

## Konsequenzen

### Vorteile

- [Vorteil 1]
- [Vorteil 2]
- [Vorteil 3]

### Nachteile / Risiken

- [Nachteil/Risiko 1]
- [Nachteil/Risiko 2]

### Mitigation

- [Wie werden Risiken minimiert?]

---

## Referenzen

- ADR-XXX: [Referenziertes ADR]
- [Externe Dokumentation oder Links]
```

---

## YAML Header Felder

### Pflichtfelder

| Feld | Beschreibung | Beispiel |
|------|--------------|----------|
| `adr_id` | Eindeutige ID (muss mit Dateinamen übereinstimmen) | `"086"` |
| `title` | Kurzer, präziser Titel | `"ADR-Template v2"` |
| `status` | Aktueller Status | `Proposed` |

### Empfohlene Felder

| Feld | Beschreibung | Werte |
|------|--------------|-------|
| `project_type` | Projekttyp | `helix_internal`, `external` |
| `component_type` | Betroffener Komponententyp | `TOOL`, `NODE`, `AGENT`, `PROCESS`, `SERVICE`, `SKILL`, `PROMPT`, `CONFIG`, `DOCS`, `MISC` |
| `classification` | Art der Änderung | `NEW`, `UPDATE`, `FIX`, `REFACTOR`, `DEPRECATE` |
| `change_scope` | Umfang der Änderung | `major`, `minor`, `config`, `docs`, `hotfix` |

### Optionale Felder

| Feld | Beschreibung | Beispiel |
|------|--------------|----------|
| `files.create` | Neue Dateien | `- src/new_file.py` |
| `files.modify` | Geänderte Dateien | `- src/existing.py` |
| `files.docs` | Dokumentation | `- docs/feature.md` |
| `depends_on` | ADR-Abhängigkeiten | `- ADR-067` |

---

## Status-Werte

| Status | Bedeutung |
|--------|-----------|
| `Proposed` | Entwurf, in Diskussion |
| `Accepted` | Entscheidung getroffen, bereit zur Umsetzung |
| `Implemented` | Vollständig umgesetzt und validiert |
| `Superseded` | Durch neueres ADR ersetzt |
| `Rejected` | Entscheidung abgelehnt |

---

## Markdown Sections

### Pflicht-Sections

Jedes ADR **muss** diese Sections enthalten:

1. `## Kontext` - Warum wird die Änderung benötigt?
2. `## Entscheidung` - Was wird entschieden?
3. `## Implementation` - Konkrete Umsetzungshinweise mit Code-Beispielen
4. `## Dokumentation` - Welche Dokumentation muss aktualisiert werden?
5. `## Akzeptanzkriterien` - Checkbox-Liste mit Kriterien
6. `## Konsequenzen` - Vorteile, Nachteile, Risiken

### Optionale Sections

- `## Status` - Visueller Status-Indikator
- `## Referenzen` - Verweise auf andere ADRs oder Dokumente

---

## Akzeptanzkriterien Format

Akzeptanzkriterien werden als Markdown-Checkboxen geschrieben:

```markdown
## Akzeptanzkriterien

### 1. Kategorie

- [ ] Kriterium 1
- [ ] Kriterium 2
- [x] Bereits erfülltes Kriterium

### 2. Andere Kategorie

- [ ] Weiteres Kriterium
```

**Regeln:**

- Mindestens 3 Kriterien empfohlen
- Kriterien sollten überprüfbar sein
- Bei Umsetzung: Checkboxen abhaken (`[x]`)

---

## Quality Gate: `adr_valid`

Das `adr_valid` Quality Gate validiert ADRs automatisch:

```yaml
# phases.yaml
quality_gate:
  type: adr_valid
  file: output/feature-adr.md
```

**Was wird geprüft?**

1. YAML Header enthält Pflichtfelder
2. Alle Pflicht-Sections sind vorhanden
3. Sections haben Inhalt (nicht leer)
4. Akzeptanzkriterien sind definiert
5. Konsistenz zwischen Header und Body

**Fehler vs. Warnungen:**

- **Fehler**: Fehlende Pflichtfelder/Sections → ADR ist ungültig
- **Warnungen**: Fehlende empfohlene Felder → ADR ist gültig, aber verbesserbar

---

## Best Practices

### 1. Titel wählen

- ✅ "User Authentication via JWT"
- ✅ "Migration von REST zu GraphQL"
- ❌ "Änderungen am Login" (zu vage)
- ❌ "ADR für neues Feature" (nicht beschreibend)

### 2. Implementation-Section

- Konkrete Dateipfade angeben
- Code-Beispiele mit Typ-Hints
- API-Signaturen definieren
- Tests beschreiben

### 3. Akzeptanzkriterien

- Überprüfbare Kriterien
- Kategorien verwenden
- Bei komplexen Features: mehr Kriterien

### 4. Konsistenz

- `files.docs` sollte mit Dokumentation-Section übereinstimmen
- ADR-ID sollte im Dateinamen enthalten sein: `086-adr-template.md`

---

## Beispiele

### Gutes ADR

- Klarer Kontext mit Problem-Beschreibung
- Konkrete Entscheidung mit Begründung
- Code-Beispiele in Implementation
- Vollständige Akzeptanzkriterien

### Zu verbesserndes ADR

- Vage Beschreibungen ohne Details
- Fehlende Alternativen-Diskussion
- Keine Code-Beispiele
- Weniger als 3 Akzeptanzkriterien

---

## Siehe auch

- [docs/ARCHITECTURE-MODULES.md](ARCHITECTURE-MODULES.md) - Modul-Dokumentation
- [skills/helix/adr/SKILL.md](../skills/helix/adr/SKILL.md) - ADR Skill für Claude Code
- HELIX v3: `adr/086-adr-template-v2.md` - Original Template

---

*Erstellt: 2025-12-22*
*Basiert auf: ADR-086 Template v2*
