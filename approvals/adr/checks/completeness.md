# Check: ADR Vollständigkeit

> Prüft ob das ADR alle erforderlichen Sections und Inhalte enthält.

---

## Zu prüfende Kriterien

### 1. YAML Header (Pflichtfelder)

Prüfe ob folgende Felder im YAML-Header vorhanden und gültig sind:

- [ ] `adr_id` vorhanden (z.B. "015")
- [ ] `title` vorhanden (beschreibender Titel)
- [ ] `status` vorhanden und gültig
  - Erlaubte Werte: `Proposed`, `Accepted`, `Implemented`, `Superseded`, `Rejected`

### 2. YAML Header (Empfohlene Felder)

Diese Felder sollten vorhanden sein (Warning wenn fehlend):

- [ ] `component_type` - Art der Komponente (TOOL, NODE, AGENT, PROCESS, SERVICE, SKILL, PROMPT, CONFIG, DOCS, MISC)
- [ ] `classification` - Art der Änderung (NEW, UPDATE, FIX, REFACTOR, DEPRECATE)
- [ ] `change_scope` - Umfang (major, minor, config, docs, hotfix)
- [ ] `files` - Betroffene Dateien
  - `create` - Neue Dateien
  - `modify` - Zu ändernde Dateien

### 3. Pflicht-Sections

Alle folgenden Sections müssen vorhanden sein (H2 = ##):

- [ ] `## Kontext` - Warum diese Änderung nötig ist
- [ ] `## Entscheidung` - Was wird entschieden
- [ ] `## Implementation` - Konkrete Umsetzungsdetails
- [ ] `## Dokumentation` - Zu aktualisierende Dokumente
- [ ] `## Akzeptanzkriterien` - Checkboxen mit Kriterien
- [ ] `## Konsequenzen` - Vor- und Nachteile

### 4. Inhaltliche Qualität

Prüfe für jede Section:

| Section | Min. Länge | Inhaltliche Anforderung |
|---------|------------|-------------------------|
| Kontext | 100 Zeichen | Erklärt das "Warum", nicht nur "Was" |
| Entscheidung | 100 Zeichen | Klar formuliert, enthält "Wir entscheiden uns für..." |
| Implementation | 200 Zeichen | Enthält konkrete Schritte oder Code-Beispiele |
| Dokumentation | 50 Zeichen | Listet zu aktualisierende Dokumente |
| Akzeptanzkriterien | - | Mindestens 3 Checkboxen |
| Konsequenzen | 100 Zeichen | Enthält Vorteile UND Nachteile |

### 5. Akzeptanzkriterien

- [ ] Mindestens 3 Akzeptanzkriterien definiert
- [ ] Kriterien sind mit Checkboxen formatiert: `- [ ]` oder `- [x]`
- [ ] Kriterien sind messbar/verifizierbar
- [ ] Keine zu vagen Kriterien wie "funktioniert gut"

### 6. Zusätzliche Prüfungen bei change_scope: major

Wenn `change_scope: major` gesetzt ist:

- [ ] Section `## Migration` vorhanden
- [ ] Migrations-Schritte oder Phasen definiert
- [ ] Rollback-Strategie dokumentiert
- [ ] Akzeptanzkriterien enthalten "migration" oder "rollback"

---

## Severity-Mapping

| Kriterium | Bei Fehlen |
|-----------|------------|
| YAML Pflichtfelder (adr_id, title, status) | **ERROR** |
| Pflicht-Sections | **ERROR** |
| Empfohlene YAML-Felder | WARNING |
| Inhaltliche Qualität (zu kurz) | WARNING |
| Akzeptanzkriterien < 3 | WARNING |
| Akzeptanzkriterien = 0 | **ERROR** |
| Migration bei major fehlt | **ERROR** |

---

## Beispiel-Findings

### Error-Beispiel

```json
{
  "severity": "error",
  "check": "completeness",
  "message": "Pflicht-Section fehlt: ## Kontext",
  "location": "Markdown body"
}
```

### Warning-Beispiel

```json
{
  "severity": "warning",
  "check": "completeness",
  "message": "Section zu kurz: ## Dokumentation (45 Zeichen, empfohlen: 50)",
  "location": "Dokumentation"
}
```

---

## Prüfanleitung

1. **Öffne das ADR** aus `input/`
2. **Prüfe YAML Header** auf Pflichtfelder
3. **Zähle die Sections** - alle 6 vorhanden?
4. **Lies jede Section** - ist sie aussagekräftig?
5. **Zähle Akzeptanzkriterien** - mindestens 3?
6. **Bei major**: Migration-Section vorhanden?
7. **Dokumentiere alle Findings**
