# LSP Code Navigation Skill

> Nutze Language Server Protocol für präzise Code-Navigation und Anti-Halluzination.

---

## Überblick

Du hast Zugriff auf das **LSP Tool** mit 5 Operations für Code-Intelligence.
Diese helfen dir, Code besser zu verstehen und Fehler zu vermeiden.

**Wann nutzen?**
- Bevor du eine Funktion aufrufst → Prüfe ob sie existiert
- Bevor du refactorst → Finde alle Referenzen
- Wenn du unsicher bist → Hole Dokumentation

---

## LSP Operations

### 1. Go to Definition

Finde wo ein Symbol definiert ist.

```
LSP goToDefinition: "calculate_total"
→ src/billing/calculator.py:45
```

**Nutze wenn:** Du wissen willst wo eine Funktion/Klasse implementiert ist.

### 2. Find References

Finde alle Stellen wo ein Symbol verwendet wird.

```
LSP findReferences: "UserService"
→ src/api/routes.py:12
→ src/api/routes.py:89
→ tests/test_api.py:34
```

**Nutze wenn:** Du ein Symbol umbenennen oder ändern willst.

### 3. Hover

Zeigt Dokumentation und Type-Information.

```
LSP hover: "process_request"
→ def process_request(data: dict) -> Response
→ "Processes incoming API request and returns response."
```

**Nutze wenn:** Du die Signatur oder Doku einer Funktion brauchst.

### 4. Document Symbols

Listet alle Symbole in einer Datei.

```
LSP documentSymbol: "src/handlers.py"
→ class RequestHandler (line 10)
→   def __init__ (line 15)
→   def process (line 25)
→ class ResponseHandler (line 50)
```

**Nutze wenn:** Du einen Überblick über eine Datei brauchst.

### 5. Workspace Symbol

Sucht Symbole im gesamten Projekt.

```
LSP workspaceSymbol: "*Handler"
→ RequestHandler in src/handlers.py:10
→ ResponseHandler in src/handlers.py:50
→ ErrorHandler in src/errors.py:20
```

**Nutze wenn:** Du nach einem Symbol suchst ohne die Datei zu kennen.

---

## Best Practices

### Vor Code-Änderungen

1. **Existenz prüfen**: Bevor du eine Funktion aufrufst
   ```
   LSP goToDefinition: "helper_function"
   → Wenn nicht gefunden: Funktion existiert nicht!
   ```

2. **Impact analysieren**: Bevor du änderst
   ```
   LSP findReferences: "old_function_name"
   → Zeigt alle Stellen die aktualisiert werden müssen
   ```

### Bei Refactorings

```
Aufgabe: Benenne "get_data" zu "fetch_data" um

Schritt 1: Alle Referenzen finden
LSP findReferences: "get_data"
→ src/api.py:12 (Definition)
→ src/api.py:45 (Usage)
→ tests/test_api.py:8

Schritt 2: Alle Stellen aktualisieren
[Editiere jede gefundene Stelle]

Schritt 3: Verifizieren
LSP findReferences: "get_data"
→ Keine Referenzen ✓
LSP findReferences: "fetch_data"
→ 3 Referenzen ✓
```

### Nach Code-Änderungen

- Diagnostics werden automatisch angezeigt
- Behebe alle Errors bevor du weitermachst
- Warnings sind optional aber empfohlen

---

## Anti-Halluzination Checkliste

Bevor du Code schreibst der externe Funktionen nutzt:

- [ ] `goToDefinition` → Symbol existiert?
- [ ] `hover` → Signatur korrekt?
- [ ] Imports vorhanden?

**Beispiel:**
```python
# FALSCH: Annahme dass Funktion existiert
result = calculate_total(items)  # Existiert das?

# RICHTIG: Erst prüfen
# LSP goToDefinition: "calculate_total"
# → src/billing.py:45 ✓
# LSP hover: "calculate_total"
# → def calculate_total(items: list[Item]) -> Decimal ✓
result = calculate_total(items)  # Jetzt sicher!
```

---

## Diagnostics

LSP zeigt automatisch Errors und Warnings:

```
Error [Pyright]: "undefined_var" is not defined (line 42)
Warning [Pyright]: "unused_import" is imported but never used
```

**Reagiere auf Errors** - sie blockieren die Ausführung.
Warnings kannst du ignorieren, aber besser ist sie zu fixen.

---

## Limitationen

- LSP Server muss für die Sprache installiert sein (pyright für Python)
- Nur für Sprachen mit installiertem LSP Plugin verfügbar
- Bei sehr großen Projekten kann Indexing etwas dauern

---

## Siehe auch

- [docs/LSP-INTEGRATION.md](../../docs/LSP-INTEGRATION.md) - Setup-Anleitung
- [Claude Code LSP Plugins](https://github.com/boostvolt/claude-code-lsps) - Verfügbare Plugins
