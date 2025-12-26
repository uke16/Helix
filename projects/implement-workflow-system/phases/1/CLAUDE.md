# Phase 1: LSP Integration (ADR-018)

Du bist ein Claude Code Entwickler der LSP (Language Server Protocol) für HELIX v4 aktiviert.

---

## 🎯 Ziel

Aktiviere LSP für alle Claude Code Sessions damit:
- Echtzeit Syntax-Fehler erkannt werden
- Go-to-definition funktioniert
- Find references funktioniert
- Bessere Code-Intelligence für alle folgenden Phasen

---

## 📚 Zuerst lesen

1. `adr/018-lsp-integration.md` - Das ADR mit allen Details
2. `skills/helix/SKILL.md` - HELIX Konventionen

---

## 📋 Aufgaben

### 1. LSP Environment aktivieren

```bash
# Prüfe ob ENABLE_LSP_TOOL gesetzt werden kann
export ENABLE_LSP_TOOL=1

# Teste ob LSP Tool verfügbar ist
claude --help | grep -i lsp
```

### 2. Plugin installieren (falls nötig)

Prüfe ob ein LSP Plugin für Python nötig ist:
- Pylance (Microsoft)
- Pyright
- python-lsp-server

```bash
# Check Claude Code Plugins
claude plugins list 2>/dev/null || echo "Plugin system prüfen"
```

### 3. Konfiguration persistent machen

Erstelle `config/lsp.conf`:
```bash
# LSP Configuration for HELIX v4
ENABLE_LSP_TOOL=1
LSP_PYTHON_SERVER=pyright  # oder pylance
```

### 4. Dokumentation erstellen

Erstelle `docs/LSP-SETUP.md`:
- Wie LSP aktiviert wird
- Welche Plugins nötig sind
- Troubleshooting

### 5. Testen

```bash
# Test: Syntaxfehler wird erkannt
echo "def foo(:" > /tmp/test_syntax.py
# LSP sollte Error melden

# Test: Type hints funktionieren
echo "def greet(name: str) -> str: return f'Hello {name}'" > /tmp/test_types.py
```

---

## 📁 Output

Schreibe nach `output/`:

| Datei | Beschreibung |
|-------|--------------|
| `output/config/lsp.conf` | LSP Konfiguration |
| `output/docs/LSP-SETUP.md` | Setup-Dokumentation |
| `output/test-results.md` | Testergebnisse |

---

## ✅ Quality Gate

Diese Phase ist erfolgreich wenn:
- [ ] `ENABLE_LSP_TOOL=1` funktioniert
- [ ] Syntax-Fehler werden erkannt
- [ ] Konfiguration ist dokumentiert
- [ ] Nächste Phasen können LSP nutzen

---

## 🔗 Nächste Phase

Nach erfolgreichem Abschluss:
- Phase 2 implementiert Workflow-Definitionen (ADR-023)
- LSP hilft bei Code-Qualität in allen folgenden Phasen
