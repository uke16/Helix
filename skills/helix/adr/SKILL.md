# Skill: Architecture Decision Records (ADRs)

> **Für Claude Code Instanzen** die ADRs erstellen oder validieren müssen.

---

## Was ist ein ADR?

Ein **Architecture Decision Record (ADR)** dokumentiert eine wichtige Architektur-Entscheidung:

- **Kontext**: Warum wurde die Entscheidung getroffen?
- **Entscheidung**: Was wurde entschieden?
- **Konsequenzen**: Welche Auswirkungen hat die Entscheidung?

---

## Wann schreibe ich ein ADR?

Schreibe ein ADR wenn:

1. **Neue Komponenten** eingeführt werden (Tools, Services, etc.)
2. **Architektur-Entscheidungen** getroffen werden (Technologie-Wahl, Patterns)
3. **Breaking Changes** an bestehenden Systemen gemacht werden
4. **Wichtige Trade-offs** dokumentiert werden müssen

**Nicht nötig für:**

- Bug-Fixes
- Minor Refactoring
- Dokumentations-Updates
- Konfigurationsänderungen

---

## ADR Format (Template v2)

### YAML Header (Pflichtfelder)

```yaml
---
adr_id: "001"
title: Kurzer, präziser Titel
status: Proposed
---
```

### YAML Header (Empfohlene Felder)

```yaml
---
adr_id: "001"
title: Kurzer, präziser Titel
status: Proposed

project_type: helix_internal
component_type: TOOL        # TOOL|NODE|AGENT|PROCESS|SERVICE|SKILL|PROMPT|CONFIG|DOCS|MISC
classification: NEW         # NEW|UPDATE|FIX|REFACTOR|DEPRECATE
change_scope: minor         # major|minor|config|docs|hotfix

files:
  create:
    - src/new_file.py
  modify:
    - src/existing.py
  docs:
    - docs/feature.md

depends_on:
  - ADR-067
---
```

### Markdown Body (Pflicht-Sections)

```markdown
# ADR-001: Kurzer, präziser Titel

## Kontext

Beschreibe das Problem:
- Was ist die aktuelle Situation?
- Warum muss etwas geändert werden?
- Was passiert wenn nichts getan wird?

## Entscheidung

Beschreibe die Entscheidung:
- Was wird entschieden?
- Welche Alternative wurde gewählt?
- Warum diese Lösung?

## Implementation

Konkrete Umsetzungshinweise:
- Welche Dateien werden erstellt/geändert?
- Code-Beispiele mit Typ-Hints
- API-Signaturen

## Dokumentation

Welche Dokumentation muss aktualisiert werden:
- docs/ARCHITECTURE-MODULES.md
- CLAUDE.md (falls relevant)
- Skills (falls relevant)

## Akzeptanzkriterien

Checkbox-Liste mit überprüfbaren Kriterien:

- [ ] Funktionalität implementiert
- [ ] Tests vorhanden und grün
- [ ] Dokumentation aktualisiert

## Konsequenzen

Beschreibe die Auswirkungen:
- Vorteile
- Nachteile/Risiken
- Mitigation
```

---

## Quality Gate: `adr_valid`

HELIX validiert ADRs automatisch mit dem `adr_valid` Quality Gate:

```yaml
# phases.yaml
quality_gate:
  type: adr_valid
  file: output/feature-adr.md
```

### Was wird geprüft?

**Fehler (ADR ist ungültig):**
- Fehlende Pflichtfelder im YAML Header (`adr_id`, `title`, `status`)
- Fehlende Pflicht-Sections (`Kontext`, `Entscheidung`, etc.)
- Keine Akzeptanzkriterien definiert

**Warnungen (ADR ist gültig, aber verbesserbar):**
- Fehlende empfohlene Felder (`component_type`, `classification`, `change_scope`)
- Sections mit wenig Inhalt (< 10 Zeichen)
- Weniger als 3 Akzeptanzkriterien

---

## Python API

### ADR parsen

```python
from helix.adr import ADRParser
from pathlib import Path

parser = ADRParser()
adr = parser.parse_file(Path("adr/001-feature.md"))

print(f"ID: {adr.metadata.adr_id}")
print(f"Title: {adr.metadata.title}")
print(f"Status: {adr.metadata.status.value}")
print(f"Sections: {list(adr.sections.keys())}")
```

### ADR validieren

```python
from helix.adr import ADRValidator
from pathlib import Path

validator = ADRValidator()
result = validator.validate_file(Path("adr/001-feature.md"))

if result.valid:
    print("ADR ist gültig!")
else:
    for error in result.errors:
        print(f"ERROR: {error.message}")

for warning in result.warnings:
    print(f"WARNING: {warning.message}")
```

### Akzeptanzkriterien prüfen

```python
from helix.adr import ADRParser, ADRValidator
from pathlib import Path

parser = ADRParser()
validator = ADRValidator(parser)

adr = parser.parse_file(Path("adr/001-feature.md"))
status = validator.get_completion_status(adr)

print(f"Fortschritt: {status['completion_percent']}%")
print(f"Erledigt: {status['checked']}/{status['total']}")

# Offene Kriterien
unchecked = validator.get_unchecked_criteria(adr)
for criterion in unchecked:
    print(f"[ ] {criterion}")
```

---

## Beispiel: Gutes ADR

```markdown
---
adr_id: "042"
title: User Authentication via JWT
status: Proposed

component_type: SERVICE
classification: NEW
change_scope: major

files:
  create:
    - src/helix/auth/jwt_handler.py
    - src/helix/auth/middleware.py
  modify:
    - src/helix/api/routes.py
  docs:
    - docs/AUTHENTICATION.md
---

# ADR-042: User Authentication via JWT

## Kontext

Aktuell hat HELIX keine Benutzer-Authentifizierung. Das bedeutet:
- Jeder mit API-Zugang kann alle Aktionen ausführen
- Keine Audit-Logs wer was gemacht hat
- Keine Möglichkeit für Multi-Tenant Betrieb

Die Einführung von Authentifizierung ist notwendig bevor HELIX
in Produktionsumgebungen eingesetzt werden kann.

## Entscheidung

Wir implementieren JWT-basierte Authentifizierung weil:
- Stateless: Keine Session-Speicherung nötig
- Standard: Breite Unterstützung in Tools und Bibliotheken
- Flexibel: Kann mit verschiedenen Identity Providern genutzt werden

Alternative OAuth2 wurde verworfen weil es für interne APIs zu komplex ist.

## Implementation

### 1. JWT Handler

`src/helix/auth/jwt_handler.py`:

```python
from datetime import datetime, timedelta
from jose import jwt

class JWTHandler:
    """Erstellt und validiert JWT Tokens."""

    def __init__(self, secret: str, algorithm: str = "HS256"):
        self.secret = secret
        self.algorithm = algorithm

    def create_token(self, user_id: str, expires_delta: timedelta) -> str:
        """Erstellt ein JWT Token für einen Benutzer."""
        expire = datetime.utcnow() + expires_delta
        payload = {"sub": user_id, "exp": expire}
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def verify_token(self, token: str) -> str | None:
        """Validiert ein Token und gibt die User-ID zurück."""
        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])
            return payload.get("sub")
        except jwt.JWTError:
            return None
```

### 2. Middleware

`src/helix/auth/middleware.py`:

```python
from fastapi import Request, HTTPException

async def jwt_middleware(request: Request, call_next):
    """Prüft JWT Token in Authorization Header."""
    # Implementation...
```

## Dokumentation

| Dokument | Änderung |
|----------|----------|
| `docs/ARCHITECTURE-MODULES.md` | auth Package dokumentieren |
| `docs/AUTHENTICATION.md` | Neues Dokument erstellen |
| `CLAUDE.md` | Auth-Hinweise für Claude Code |

## Akzeptanzkriterien

### Funktionalität

- [ ] JWTHandler kann Tokens erstellen und validieren
- [ ] Middleware blockt unauthentifizierte Requests
- [ ] Token-Expiration wird korrekt geprüft

### Tests

- [ ] Unit Tests für JWTHandler
- [ ] Integration Tests für Middleware
- [ ] E2E Tests für geschützte Endpoints

### Dokumentation

- [ ] AUTHENTICATION.md erstellt
- [ ] ARCHITECTURE-MODULES.md aktualisiert
- [ ] Docstrings für alle public APIs

## Konsequenzen

### Vorteile

- Sichere API-Zugriffe
- Audit-fähig (wer hat was gemacht)
- Ermöglicht Multi-Tenant Betrieb

### Nachteile

- Zusätzliche Komplexität
- Token-Management erforderlich
- Breaking Change für existierende Clients

### Mitigation

- Übergangsphase mit optionaler Authentifizierung
- Migrationsdokumentation für Clients
```

---

## Checkliste für ADR-Erstellung

Bevor du ein ADR abgibst:

- [ ] **YAML Header** hat alle Pflichtfelder (`adr_id`, `title`, `status`)
- [ ] **Kontext** erklärt das Problem klar
- [ ] **Entscheidung** ist konkret und begründet
- [ ] **Implementation** hat Code-Beispiele
- [ ] **Dokumentation** listet zu aktualisierende Dokumente
- [ ] **Akzeptanzkriterien** hat mindestens 3 Checkbox-Items
- [ ] **Konsequenzen** beschreibt Vor- und Nachteile

---

## Häufige Fehler

### 1. Zu vage Beschreibungen

❌ "Wir verbessern die Performance"
✅ "Wir implementieren Caching mit Redis für API-Responses"

### 2. Fehlende Code-Beispiele

❌ "Erstelle eine neue Klasse für..."
✅ Code-Beispiel mit Signatur und Docstrings

### 3. Keine überprüfbaren Kriterien

❌ "System funktioniert besser"
✅ "Response-Zeit unter 100ms für 95% der Requests"

### 4. Inkonsistente Dateilisten

❌ `files.docs` enthält Dateien die nicht in Dokumentation-Section erwähnt sind
✅ Header und Body sind konsistent

---

## Referenzen

- [docs/ADR-TEMPLATE.md](../../../docs/ADR-TEMPLATE.md) - Vollständiges Template
- [docs/ARCHITECTURE-MODULES.md](../../../docs/ARCHITECTURE-MODULES.md) - helix.adr Package
- HELIX v3: `adr/086-adr-template-v2.md` - Original Template

---

*Skill Version: 1.0*
*Erstellt: 2025-12-22*
