# Ralph Controller für ADR-039: Code Quality Hardening

## 🔴 KRITISCH: Verifikations-Pflicht

**DU DARFST `<promise>ADR039_COMPLETE</promise>` NUR AUSGEBEN WENN:**

```bash
./control/verify-adr-039.sh
```

**Exit code 0 = ALLE PHASEN OK → Promise erlaubt**
**Exit code 1 = Mindestens eine Phase fehlt → KEIN Promise!**

Führe das Script nach JEDER Änderung aus um zu sehen was noch fehlt.

---

## Status Check

Führe zuerst aus:
```bash
./control/verify-adr-039.sh
```

Das zeigt dir welche Phasen noch fehlen.

---

## Offene Phasen

### Phase 2: LSP aktivieren

```bash
# 1. config/env.sh erweitern
echo 'export ENABLE_LSP_TOOL=1' >> config/env.sh

# 2. pyproject.toml erweitern
# Unter [tool.poetry.group.dev.dependencies] hinzufügen:
# pyright = "^1.1.0"
```

### Phase 3: Dokumentation

**Erstelle `docs/CONFIGURATION-GUIDE.md`:**
```markdown
# HELIX Configuration Guide

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| HELIX_ROOT | auto-detect | Root directory of HELIX |
| HELIX_VENV | $HELIX_ROOT/.venv | Virtual environment path |
| CLAUDE_MODEL | opus | Default Claude model |
| ENABLE_LSP_TOOL | 0 | Enable LSP diagnostics |

## PathConfig

All paths are centralized in `src/helix/config/paths.py`.

### Available Paths

- `PathConfig.HELIX_ROOT` - Project root
- `PathConfig.VENV_PATH` - Virtual environment
- `PathConfig.CLAUDE_CMD` - Claude CLI wrapper
- `PathConfig.DOMAIN_EXPERTS_CONFIG` - Domain experts YAML
- `PathConfig.LLM_PROVIDERS_CONFIG` - LLM providers YAML
- `PathConfig.TEMPLATES_DIR` - Jinja2 templates
- `PathConfig.SKILLS_DIR` - Skills directory
```

**Erstelle `docs/PATHS.md`:**
```markdown
# PathConfig API Reference

## Overview

`PathConfig` provides centralized path management for HELIX.

## Usage

```python
from helix.config.paths import PathConfig

# Get paths
root = PathConfig.HELIX_ROOT
config = PathConfig.DOMAIN_EXPERTS_CONFIG

# Validate all paths exist
PathConfig.validate()

# Show path info
PathConfig.info()
```

## Properties

| Property | Type | Description |
|----------|------|-------------|
| HELIX_ROOT | Path | Project root directory |
| VENV_PATH | Path | Virtual environment |
| CLAUDE_CMD | Path | Claude CLI wrapper script |
| NVM_PATH | Path | Node.js via NVM |
| DOMAIN_EXPERTS_CONFIG | Path | config/domain-experts.yaml |
| LLM_PROVIDERS_CONFIG | Path | config/llm-providers.yaml |
| TEMPLATES_DIR | Path | templates/ directory |
| TEMPLATES_PHASES | Path | templates/phases/ |
| SKILLS_DIR | Path | skills/ directory |
```

---

## Workflow

1. Führe `./control/verify-adr-039.sh` aus
2. Sieh welche Phasen ❌ sind
3. Fixe die fehlenden Phasen
4. Führe verify-script erneut aus
5. Wiederhole bis "ALLE PHASEN BESTANDEN"
6. Erst dann: `<promise>ADR039_COMPLETE</promise>`

---

## NIEMALS das Promise ausgeben wenn:

- `./control/verify-adr-039.sh` exit code != 0
- Das Script zeigt "❌ FAILED"
- Irgendeine Phase noch offen ist
