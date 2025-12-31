---
adr_id: "039"
title: "Code Quality & Documentation Cleanup"
status: Proposed
date: 2024-12-31

project_type: helix_internal
component_type: CONFIG
classification: FIX
change_scope: major

domain: helix
language: python
skills:
  - helix
  - infrastructure

files:
  create:
    - src/helix/config/paths.py
    - docs/LSP-SETUP.md
  modify:
    - src/helix/api/routes/openai.py
    - src/helix/api/session_manager.py
    - src/helix/claude_runner.py
    - src/helix/template_engine.py
    - src/helix/context_manager.py
    - src/helix/llm_client.py
    - src/helix/phase_loader.py
    - src/helix/consultant/expert_manager.py
    - src/helix/evolution/deployer.py
    - src/helix/evolution/integrator.py
    - src/helix/evolution/validator.py
    - src/helix/evolution/project.py
    - config/helix.yaml
    - templates/consultant/session.md.j2
    - adr/INDEX.md
  docs:
    - docs/LSP-SETUP.md
    - adr/014-documentation-architecture.md
    - adr/018-lsp-integration.md

depends_on:
  - "018"  # LSP Integration
  - "014"  # Documentation Architecture

related_to:
  - "019"  # Documentation as Code
  - "020"  # Intelligent Documentation Discovery
---

# ADR-039: Code Quality & Documentation Cleanup

## Status

Proposed

---

## Kontext

### Problem 1: Hardcoded Pfade (30+ Stellen)

Der gesamte HELIX-Code enthält hardcoded Pfade zu `/home/aiuser01/helix-v4`:

```python
# Beispiele aus dem Code
HELIX_ROOT = Path("/home/aiuser01/helix-v4")
DEFAULT_CLAUDE_CMD = "/home/aiuser01/.nvm/versions/node/v20.19.6/bin/claude"
DEFAULT_TEMPLATES_DIR = Path("/home/aiuser01/helix-v4/templates")
TEST_ROOT = Path("/home/aiuser01/helix-v4-test")
```

**Betroffene Module:**
| Modul | Anzahl hardcoded Pfade |
|-------|------------------------|
| `openai.py` | 5 |
| `claude_runner.py` | 4 |
| `evolution/*.py` | 8 |
| `template_engine.py` | 2 |
| `context_manager.py` | 2 |
| `llm_client.py` | 2 |
| Weitere | 7+ |

**Konsequenzen:**
- Test-System (`helix-v4-test`) kann nicht korrekt funktionieren
- Keine Portabilität auf andere Maschinen
- CI/CD nicht möglich

### Problem 2: LSP nicht konfiguriert (ADR-018 nicht umgesetzt)

ADR-018 ist als "Proposed" markiert, aber:
- `pyright` Binary ist installiert
- Claude Code LSP Plugin ist **NICHT** installiert
- `ENABLE_LSP_TOOL=1` wird nirgends gesetzt
- Kein LSP Skill existiert

Aktueller Stand:
```bash
$ which pyright
/home/aiuser01/.nvm/versions/node/v20.19.6/bin/pyright

$ claude /plugin list  # Fehlt LSP Plugin
```

### Problem 3: Doku-ADRs nicht integriert

| ADR | Deklarierter Status | Real-Status |
|-----|---------------------|-------------|
| 014 | Proposed | Teilweise (Tools existieren, Pipeline läuft nicht) |
| 018 | Proposed | Nicht umgesetzt |
| 019 | Proposed | Blockiert durch 018 |
| 020 | Proposed | Blockiert durch 019 |

Die Doku-Pipeline (ADR-014) ist nicht aktiv:
- `docs_compiler.py` existiert
- `docs_coverage.py` existiert
- **Aber**: Kein Pre-Commit Hook, keine CI-Integration

### Problem 4: Consultant Context überladen

Der Consultant lädt potenziell 3210+ Zeilen Kontext:

| Datei | Zeilen | Nutzung |
|-------|--------|---------|
| `session.md.j2` | 452 | Template (immer geladen) |
| `SKILL.md` (helix) | 1620 | Oft überflüssig |
| `ARCHITECTURE-MODULES.md` | 910 | Selten nötig |
| `CONCEPT.md` | 228 | Grundlegend |

**Probleme:**
- Keine Smart-Selection (ADR-020 nicht umgesetzt)
- `ConsultantMeeting`-Klasse ist aktuell "Dead Code"
- Template sagt "MUSS LESEN" für 12 Dateien ohne Priorisierung

### Problem 5: Global State & Testbarkeit

```python
# src/helix/api/session_manager.py:450
session_manager = SessionManager()  # Global singleton
```

- Erschwert Unit-Testing
- Kein Dependency Injection
- Macht Mocking kompliziert

---

## Entscheidung

### 1. Zentrale Pfad-Konfiguration

Neues Modul `src/helix/config/paths.py`:

```python
"""Zentrale Pfad-Konfiguration für HELIX.

Alle Pfade werden aus Environment-Variablen oder Config-Datei geladen.
NIEMALS hardcoded Pfade im Code!

ADR-039: Code Quality & Documentation Cleanup
"""
from pathlib import Path
import os

class HelixPaths:
    """Zentrale Pfad-Verwaltung.

    Lädt Pfade aus:
    1. Environment-Variablen (Priorität)
    2. config/helix.yaml
    3. Fallback: Relative zu diesem Modul
    """

    def __init__(self):
        self._root = self._resolve_root()

    def _resolve_root(self) -> Path:
        """Ermittelt HELIX_ROOT."""
        # 1. Environment
        if env_root := os.environ.get("HELIX_ROOT"):
            return Path(env_root)

        # 2. Relativ zu diesem Modul
        # src/helix/config/paths.py -> helix-v4/
        return Path(__file__).parent.parent.parent.parent

    @property
    def root(self) -> Path:
        return self._root

    @property
    def templates(self) -> Path:
        return self._root / "templates"

    @property
    def skills(self) -> Path:
        return self._root / "skills"

    @property
    def config(self) -> Path:
        return self._root / "config"

    @property
    def projects(self) -> Path:
        return self._root / "projects"

    @property
    def adr(self) -> Path:
        return self._root / "adr"

    @property
    def venv(self) -> Path:
        return self._root / ".venv"

    @property
    def claude_cmd(self) -> str:
        """Claude CLI Pfad."""
        if env_cmd := os.environ.get("CLAUDE_CMD"):
            return env_cmd

        # nvm-basierter Default
        nvm_path = os.environ.get(
            "NVM_BIN",
            os.path.expanduser("~/.nvm/versions/node/v20.19.6/bin")
        )
        return f"{nvm_path}/claude"


# Singleton für einfachen Import
paths = HelixPaths()
```

### 2. LSP Setup ausführen (ADR-018 implementieren)

```bash
# 1. Claude Code LSP Marketplace hinzufügen
claude /plugin marketplace add boostvolt/claude-code-lsps

# 2. Python LSP Plugin installieren
claude /plugin install pyright@claude-code-lsps

# 3. Dokumentieren in docs/LSP-SETUP.md
```

### 3. Consultant Template optimieren

Reduziere `session.md.j2` auf das Wesentliche:

```markdown
# HELIX Consultant Session

## Pflicht-Lektüre (NUR wenn ADR erstellt wird)
- `../../adr/INDEX.md` - Nächste ADR-Nummer
- `../../skills/helix/adr/SKILL.md` - ADR-Format

## Bei Bedarf (NICHT automatisch lesen!)
- Skills: Nur laden wenn Domain relevant
- Architecture: Nur bei technischen Fragen
```

Von 452 auf ~150 Zeilen reduzieren.

### 4. ADR-Status korrigieren

```markdown
# adr/INDEX.md Korrekturen

| ADR | Alt | Neu | Begründung |
|-----|-----|-----|------------|
| 014 | 📋 Proposed | ⚠️ Partial | Tools existieren, Pipeline nicht aktiv |
| 018 | 📋 Proposed | 📋 Proposed | Wird mit diesem ADR implementiert |
```

### 5. ConsultantMeeting dokumentieren

Die `ConsultantMeeting`-Klasse in `src/helix/consultant/meeting.py` ist **nicht Dead Code**, sondern **für Multi-Expert-Szenarien reserviert**.

Hinzufügen in Docstring:

```python
"""ConsultantMeeting für Multi-Expert-Szenarien.

HINWEIS: Diese Klasse wird aktuell nicht verwendet.
Sie wird relevant wenn mehrere Domain-Experten (PDM, Encoder, etc.)
in einem Meeting zusammenarbeiten.

Aktuell nutzt der Consultant den direkten Claude-Runner (openai.py).
Siehe ADR-005: Consultant Topology für Details.
"""
```

---

## Implementation

### Phase 1: Pfad-Refactoring (Kritisch)

1. **Erstelle** `src/helix/config/paths.py`
2. **Refactore** alle Module:
   - `openai.py`: `HELIX_ROOT` → `paths.root`
   - `claude_runner.py`: `DEFAULT_CLAUDE_CMD` → `paths.claude_cmd`
   - `template_engine.py`: `DEFAULT_TEMPLATES_DIR` → `paths.templates`
   - etc.
3. **Teste** mit Environment-Variable: `HELIX_ROOT=/tmp/test python -m pytest`

### Phase 2: LSP aktivieren

1. **Ausführen**:
   ```bash
   claude /plugin marketplace add boostvolt/claude-code-lsps
   claude /plugin install pyright@claude-code-lsps
   ```
2. **Dokumentieren**: `docs/LSP-SETUP.md`
3. **ADR-018 Status**: `Proposed` → `Implemented`

### Phase 3: Dokumentation bereinigen

1. **`session.md.j2`**: Auf 150 Zeilen reduzieren
2. **ADR-014 Status**: `Proposed` → `Partial`
3. **ConsultantMeeting**: Docstring hinzufügen
4. **INDEX.md**: Status-Korrekturen

### Phase 4: Testing

1. **Unit Tests** für `paths.py`
2. **Integration Test**: Testsystem mit `HELIX_ROOT=/home/aiuser01/helix-v4-test`
3. **LSP Test**: `claude` mit Python-Datei öffnen, LSP-Operationen ausführen

---

## Akzeptanzkriterien

### Kritisch (Must Have)

- [ ] Keine hardcoded Pfade mehr in `src/helix/`
- [ ] `HELIX_ROOT` Environment-Variable funktioniert
- [ ] Testsystem (`helix-v4-test`) läuft mit eigenem `HELIX_ROOT`
- [ ] LSP Plugin installiert und funktioniert
- [ ] `docs/LSP-SETUP.md` existiert

### Wichtig (Should Have)

- [ ] `session.md.j2` auf ~150 Zeilen reduziert
- [ ] ADR-STATUS in INDEX.md korrigiert (014, 018)
- [ ] ConsultantMeeting Docstring hinzugefügt

### Nice-to-Have

- [ ] Pre-Commit Hook für Pfad-Check (keine hardcoded `/home/aiuser01`)
- [ ] CI-Test für Portabilität

---

## Konsequenzen

### Positiv

1. **Portabilität**: HELIX kann auf jeder Maschine laufen
2. **Testbarkeit**: Testsystem funktioniert korrekt
3. **Developer Experience**: LSP für alle aktiviert
4. **Transparenz**: ADR-Status reflektiert Realität
5. **Wartbarkeit**: Zentrale Pfad-Konfiguration

### Negativ

1. **Migration**: Alle Module müssen angepasst werden
2. **Breaking Change**: Alte Deployments brauchen `HELIX_ROOT` Environment-Variable

### Risiken

| Risiko | Wahrscheinlichkeit | Mitigation |
|--------|-------------------|------------|
| Import-Fehler nach Refactoring | Mittel | Schrittweise Migration, Tests |
| LSP Plugin inkompatibel | Niedrig | Fallback auf manuelles pyright |
| Testsystem hat andere Probleme | Mittel | Separates Debugging |

---

## Dokumentation

### Zu aktualisierende Dokumente

| Dokument | Änderung |
|----------|----------|
| `docs/LSP-SETUP.md` | Neu erstellen - Setup-Anleitung für LSP |
| `adr/INDEX.md` | Status-Korrekturen für ADR-014 und ADR-018 |
| `adr/018-lsp-integration.md` | Status auf "Implemented" setzen |
| `templates/consultant/session.md.j2` | Optimierung auf ~150 Zeilen |

### Self-Documentation

- Docstrings in `paths.py` erklären die Pfad-Resolution
- ConsultantMeeting Docstring erklärt den Multi-Expert-Use-Case

---

## Referenzen

- ADR-014: Documentation Architecture
- ADR-018: LSP Integration
- ADR-019: Documentation as Code
- ADR-020: Intelligent Documentation Discovery
- [Claude Code LSP Plugins](https://github.com/boostvolt/claude-code-lsps)
