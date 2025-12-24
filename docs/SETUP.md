# HELIX v4 Server Setup

> Vollständige Anleitung für die Installation von HELIX v4 auf einem neuen Server.

---

## Voraussetzungen

### System
- Ubuntu 22.04+ oder Debian 12+
- Python 3.11+
- Node.js 20+
- Git

### Accounts
- Anthropic API Key (für Claude Code CLI)

---

## 1. Basis-Installation

```bash
# Repository klonen
git clone https://github.com/your-org/helix-v4.git
cd helix-v4

# Python Environment
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Dependencies
pip install -r requirements.txt
```

---

## 2. Claude Code CLI

```bash
# Claude Code installieren
npm install -g @anthropic-ai/claude-code

# Verifizieren
claude --version

# Login (einmalig)
claude login
```

---

## 3. LSP Support (Empfohlen)

LSP ermöglicht Code-Intelligence für Claude Agents.

### 3.1 Python LSP (Pyright)

```bash
# Pyright installieren
pip install pyright

# Claude Code Plugin Marketplace
claude /plugin marketplace add boostvolt/claude-code-lsps

# Python LSP Plugin
claude /plugin install pyright@claude-code-lsps
```

### 3.2 Environment Variable

```bash
# In ~/.bashrc oder ~/.zshrc
echo 'export ENABLE_LSP_TOOL=1' >> ~/.bashrc
source ~/.bashrc
```

### 3.3 Verifizieren

```bash
claude
# In Claude Code Session:
# > Nutze LSP documentSymbol auf src/helix/__init__.py
# Sollte Symbole auflisten
```

### 3.4 Weitere Sprachen (Optional)

```bash
# TypeScript/JavaScript
npm install -g @vtsls/language-server typescript
claude /plugin install vtsls@claude-code-lsps

# Go
go install golang.org/x/tools/gopls@latest
claude /plugin install gopls@claude-code-lsps
```

---

## 4. MCP Server (Optional)

Für erweiterte Tool-Integration:

```bash
# SSH MCP (für Remote-Zugriff)
# Konfiguration in ~/.claude/settings.json
```

---

## 5. Konfiguration

### 5.1 HELIX Config

```bash
# Konfiguration prüfen
cat config/orchestrator.yaml

# Anpassen falls nötig
vim config/orchestrator.yaml
```

### 5.2 Claude Code Settings

```bash
# User-weite Settings
cat ~/.claude/settings.json

# Projekt-spezifische Settings
cat .claude/settings.json
```

---

## 6. Verifizierung

```bash
# HELIX CLI testen
helix --help

# Projekt erstellen
helix project create test-setup --type simple

# Status prüfen
helix project status test-setup
```

---

## 7. Checkliste

### Basis
- [ ] Python 3.11+ installiert
- [ ] Node.js 20+ installiert
- [ ] HELIX Repository geklont
- [ ] Python Dependencies installiert

### Claude Code
- [ ] Claude Code CLI installiert
- [ ] Claude Login erfolgreich
- [ ] API Key konfiguriert

### LSP (Empfohlen)
- [ ] `ENABLE_LSP_TOOL=1` in Environment
- [ ] Pyright installiert (`pip install pyright`)
- [ ] Claude Code LSP Plugin Marketplace hinzugefügt
- [ ] pyright@claude-code-lsps Plugin installiert
- [ ] LSP Test erfolgreich (documentSymbol funktioniert)

### Optional
- [ ] Weitere LSP Plugins (TypeScript, Go, etc.)
- [ ] MCP Server konfiguriert
- [ ] SSH Access für Remote-Entwicklung

---

## Troubleshooting

### LSP Tool nicht verfügbar

```bash
# Prüfen ob Environment Variable gesetzt
echo $ENABLE_LSP_TOOL
# Sollte "1" ausgeben

# Falls nicht:
export ENABLE_LSP_TOOL=1
```

### Plugin nicht gefunden

```bash
# In Claude Code:
/plugin list
# Sollte pyright@claude-code-lsps zeigen

# Falls nicht:
/plugin marketplace add boostvolt/claude-code-lsps
/plugin install pyright@claude-code-lsps
```

### Pyright Fehler

```bash
# Prüfen ob installiert
which pyright
pyright --version

# Falls nicht gefunden:
pip install pyright
```

---

## Referenzen

- [Claude Code Dokumentation](https://code.claude.com/docs)
- [Claude Code LSP Plugins](https://github.com/boostvolt/claude-code-lsps)
- [docs/LSP-INTEGRATION.md](LSP-INTEGRATION.md) - LSP Details
- [ONBOARDING.md](../ONBOARDING.md) - HELIX Konzept

---

*Zuletzt aktualisiert: 2024-12-24*
