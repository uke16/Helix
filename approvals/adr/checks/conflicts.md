# Check: ADR Konflikte

> Prüft ob das ADR mit anderen ADRs in Konflikt steht oder Abhängigkeiten korrekt referenziert.

---

## Wann ist dieser Check relevant?

Dieser Check ist **immer relevant**, aber besonders wichtig wenn:

- `depends_on` im YAML-Header nicht leer ist
- ADR modifiziert bestehende Dateien (`files.modify`)
- ADR supersedes ein anderes ADR

---

## Zu prüfende Kriterien

### 1. Abhängigkeiten (depends_on)

Wenn `depends_on` nicht leer:

- [ ] Alle referenzierten ADRs existieren
- [ ] Referenzierte ADRs werden im Content erwähnt (ADR-XXX Format)
- [ ] Status der abhängigen ADRs ist kompatibel (nicht Rejected)

**Wie prüfen:**
```bash
# Prüfe ob referenziertes ADR existiert
ls adr/002-*.md
grep "adr_id.*002" adr/*.md
```

### 2. Datei-Konflikte

Wenn `files.modify` nicht leer:

- [ ] Zu modifizierende Dateien existieren tatsächlich
- [ ] Keine anderen pending ADRs modifizieren dieselben Dateien
- [ ] Änderungen sind mit bestehendem Code kompatibel

**Wie prüfen:**
```bash
# Prüfe ob zu modifizierende Datei existiert
ls src/helix/quality_gates.py

# Suche nach anderen ADRs die dieselbe Datei modifizieren
grep -r "quality_gates.py" adr/*.md
```

### 3. Supersedes-Beziehung

Wenn ADR ein anderes superseded:

- [ ] Supersedetes ADR existiert
- [ ] Supersedetes ADR wird als Referenz genannt
- [ ] Begründung für Supersedes vorhanden

### 4. related_to Referenzen

Wenn `related_to` nicht leer:

- [ ] Referenzierte ADRs existieren
- [ ] Beziehung wird im Content erklärt

### 5. Inhaltliche Konflikte

Prüfe ob das ADR inhaltlich mit bestehenden ADRs kollidiert:

- [ ] Keine widersprüchlichen Entscheidungen zu bestehenden ADRs
- [ ] Keine doppelten Implementierungen (gleiche Funktionalität)
- [ ] Patterns konsistent mit bestehender Architektur

---

## Severity-Mapping

| Kriterium | Severity |
|-----------|----------|
| depends_on ADR existiert nicht | **ERROR** |
| files.modify Datei existiert nicht | **ERROR** |
| Supersedetes ADR existiert nicht | **ERROR** |
| Abhängiges ADR ist Rejected | **ERROR** |
| Abhängigkeit nicht im Content erwähnt | WARNING |
| Konflikt mit anderem pending ADR | WARNING |
| related_to ADR existiert nicht | WARNING |

---

## Beispiel-Findings

### Error: Abhängiges ADR existiert nicht

```json
{
  "severity": "error",
  "check": "conflicts",
  "message": "depends_on referenziert nicht-existentes ADR: 099",
  "location": "YAML header: depends_on"
}
```

### Error: Zu modifizierende Datei existiert nicht

```json
{
  "severity": "error",
  "check": "conflicts",
  "message": "files.modify referenziert nicht-existente Datei: src/helix/missing.py",
  "location": "YAML header: files.modify"
}
```

### Warning: Abhängigkeit nicht erwähnt

```json
{
  "severity": "warning",
  "check": "conflicts",
  "message": "depends_on: 002 wird im Content nicht erwähnt (empfohlen: ADR-002)",
  "location": "Content"
}
```

---

## Prüfanleitung

1. **Extrahiere depends_on** aus YAML-Header
2. **Für jedes ADR in depends_on:**
   - Prüfe ob Datei existiert: `ls adr/XXX-*.md`
   - Prüfe ob im Content erwähnt: `grep "ADR-XXX" input/*.md`
   - Prüfe Status des ADRs
3. **Extrahiere files.modify** aus YAML-Header
4. **Für jede Datei in files.modify:**
   - Prüfe ob existiert: `ls <path>`
   - Suche nach Konflikten: `grep "<filename>" adr/*.md`
5. **Prüfe auf Supersedes-Beziehung**
6. **Dokumentiere alle Findings**

---

## Codebase-Verifizierung

### ADR-Existenz prüfen

```bash
# Alle ADRs mit bestimmter ID finden
grep -l "adr_id.*015" adr/*.md

# ADR-Index prüfen
cat adr/INDEX.md
```

### Datei-Existenz prüfen

```bash
# Prüfe Verzeichnisstruktur
ls -la src/helix/

# Prüfe spezifische Datei
test -f src/helix/adr/validator.py && echo "exists"
```

### Konflikt-Suche

```bash
# Suche nach ADRs die dieselbe Datei referenzieren
grep -r "validator.py" adr/*.md

# Suche nach pending ADRs (Status: Proposed)
grep -l "status.*Proposed" adr/*.md
```

---

## Kontext: Warum ist das wichtig?

Ohne Konflikt-Prüfung können folgende Probleme auftreten:

- **Race Conditions**: Zwei ADRs modifizieren dieselbe Datei
- **Broken Dependencies**: ADR baut auf nicht-existentem ADR auf
- **Architektur-Inkonsistenz**: Widersprüchliche Entscheidungen
- **Orphaned ADRs**: Supersedetes ADR wird nicht gefunden
