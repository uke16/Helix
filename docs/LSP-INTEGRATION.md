# LSP Integration für HELIX v4

> Setup-Anleitung für Language Server Protocol Integration

---

## Überblick

HELIX v4 nutzt die native LSP-Unterstützung von Claude Code (seit v2.0.30+).
Dies ermöglicht:

- **Code Navigation**: Go to Definition, Find References
- **Echtzeit-Diagnostics**: Syntax-Errors sofort sichtbar
- **Anti-Halluzination**: Symbole verifizieren bevor sie genutzt werden

---

## Quick Setup (Python)

### 1. Pyright installieren

```bash
pip install pyright
```

### 2. Claude Code LSP Plugin installieren

```bash
# In Claude Code Session:
/plugin marketplace add boostvolt/claude-code-lsps
/plugin install pyright@claude-code-lsps
```

### 3. Environment Variable setzen

```bash
export ENABLE_LSP_TOOL=1
```

Oder in `~/.bashrc` / `~/.zshrc`:
```bash
echo 'export ENABLE_LSP_TOOL=1' >> ~/.bashrc
```

### 4. Verifizieren

```bash
claude
# In Claude Code:
# "Nutze LSP goToDefinition auf eine beliebige Funktion"
```

---

## HELIX Integration

HELIX setzt `ENABLE_LSP_TOOL=1` automatisch für:
- development Phasen
- review Phasen  
- integration Phasen

**Keine manuelle Konfiguration nötig** wenn Setup korrekt.

### Konfiguration (optional)

```yaml
# config/orchestrator.yaml
lsp:
  enabled: true
  enabled_phase_types:
    - development
    - review
    - integration
```

---

## Andere Sprachen

### TypeScript / JavaScript

```bash
npm install -g @vtsls/language-server typescript
/plugin install vtsls@claude-code-lsps
```

### Go

```bash
go install golang.org/x/tools/gopls@latest
# Sicherstellen dass ~/go/bin in PATH
/plugin install gopls@claude-code-lsps
```

### Rust

```bash
rustup component add rust-analyzer
/plugin install rust-analyzer@claude-code-lsps
```

### Java

```bash
brew install jdtls  # macOS
# Erfordert Java 21+
/plugin install jdtls@claude-code-lsps
```

---

## Troubleshooting

### LSP Tool nicht verfügbar

```
Error: LSP tool not found
```

**Lösung:**
```bash
export ENABLE_LSP_TOOL=1
# Dann Claude Code neu starten
```

### Pyright nicht gefunden

```
Error: Executable not found in $PATH
```

**Lösung:**
```bash
pip install pyright
# Oder mit pipx für globale Installation:
pipx install pyright
```

### Plugin nicht installiert

```
/plugin list
# Zeigt keine LSP Plugins
```

**Lösung:**
```bash
/plugin marketplace add boostvolt/claude-code-lsps
/plugin install pyright@claude-code-lsps
```

### Diagnostics erscheinen nicht

1. Prüfe ob LSP Server läuft: `/plugin errors`
2. Prüfe ob Dateiendung korrekt (.py für Python)
3. Warte kurz - Indexing kann bei großen Projekten dauern

---

## Debugging

### LSP Logs aktivieren

```bash
claude --enable-lsp-logging
# Logs in ~/.claude/debug/
```

### Plugin Status prüfen

```bash
# In Claude Code:
/plugin
# Zeigt installierte Plugins und Status
```

---

## Referenzen

- [Claude Code LSP Plugins](https://github.com/boostvolt/claude-code-lsps)
- [Claude Code Plugins Reference](https://code.claude.com/docs/en/plugins-reference)
- [skills/lsp/SKILL.md](../skills/lsp/SKILL.md) - Nutzung für Agents
- [ADR-018](../adr/draft/ADR-018-lsp-integration.md) - Design-Entscheidung
