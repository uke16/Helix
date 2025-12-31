---
adr_id: "039"
title: "Code Quality Hardening - Paths, LSP, Documentation"
status: Proposed

component_type: PROCESS
classification: FIX
change_scope: major

domain: "helix"
language: "python"
skills:
  - helix
  - infrastructure

files:
  create:
    - docs/CONFIGURATION-GUIDE.md
    - docs/PATHS.md
    - src/helix/quality_gates/lsp_diagnostics.py
  modify:
    - src/helix/config/paths.py
    - src/helix/consultant/expert_manager.py
    - src/helix/llm_client.py
    - src/helix/template_engine.py
    - src/helix/phase_loader.py
    - src/helix/context_manager.py
    - src/helix/claude_runner.py
    - src/helix/api/main.py
    - src/helix/api/routes/openai.py
    - src/helix/evolution/deployer.py
    - src/helix/evolution/integrator.py
    - src/helix/evolution/validator.py
    - config/env.sh
    - pyproject.toml
  docs:
    - docs/ARCHITECTURE-MODULES.md
    - adr/018-lsp-integration.md
    - adr/020-intelligent-documentation-discovery.md
    - adr/INDEX.md

depends_on:
  - "035"
  - "018"
---

# ADR-039: Code Quality Hardening - Paths, LSP, Documentation

## Status
Proposed

## Kontext

Die kritische Code-Review des Consultant-Systems hat mehrere systematische Probleme aufgedeckt:

### 1. Hardcoded Paths (12 Dateien betroffen)

\`\`\`python
# Beispiele aus dem aktuellen Code:
DEFAULT_CONFIG_PATH = Path("/home/aiuser01/helix-v4/config/domain-experts.yaml")  # expert_manager.py:79
HELIX_ROOT = Path("/home/aiuser01/helix-v4")  # openai.py:50
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))  # openai.py:39
\`\`\`

**Impact:**
- Test-System funktioniert NICHT auf anderen Maschinen
- Keine Portabilität zu Docker/CI-Umgebungen
- \`PathConfig\` existiert (ADR-035), wird aber inkonsistent genutzt

### 2. LSP nicht aktiviert

ADR-018 existiert seit 24.12.2024 mit Status "Proposed", wurde aber nie implementiert:
- \`ENABLE_LSP_TOOL=1\` wird nirgends gesetzt
- Kein \`pyright\` via pip installiert (nur via npm)
- Kein LSP Quality Gate implementiert
- Entwickler haben keine Go-to-Definition, Find-References, etc.

### 3. Dokumentations-Gaps

| ADR | Status | Problem |
|-----|--------|---------|
| ADR-014 | Implemented | OK - Docs Architecture funktioniert |
| ADR-019 | Proposed | NICHT implementiert - validierbare Referenzen fehlen |
| ADR-020 | Proposed | NICHT implementiert - widersprüchlicher Status-Marker! |
| ADR-018 | Proposed | NICHT implementiert - LSP fehlt |

### 4. ConsultantMeeting undokumentiert

Die 4-Phasen-Architektur (\`Selection -> Analysis -> Synthesis -> Output\`) existiert, wird aber:
- Nicht aktiv genutzt (OpenAI-Route nutzt direkten ClaudeRunner)
- Nicht für Multi-Expert-Szenarien dokumentiert
- Soll laut User "wieder relevant werden bei mehreren Domain-Experten"

### 5. Context-Probleme

- ARCHITECTURE-MODULES.md: 910 Zeilen - teilweise zu detailliert
- Session-Details (108 Zeilen) sollten in separate Datei
- Fehlend: "Wann nutze ich X vs Y" Decision Trees

### 6. sys.path Anti-Pattern

\`\`\`python
# src/helix/api/main.py:27
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# src/helix/api/routes/openai.py:39
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
\`\`\`

Diese Manipulation des globalen Python-Paths ist ein Anti-Pattern und sollte durch korrektes Package-Setup ersetzt werden.

## Entscheidung

### Phase 1: Path Consolidation

**1.1 PathConfig erweitern** (\`src/helix/config/paths.py\`)

\`\`\`python
class PathConfig:
    # Bestehend (behalten):
    HELIX_ROOT: Path
    VENV_PATH: Path
    CLAUDE_CMD: Path
    NVM_PATH: Path

    # NEU hinzufügen:
    @property
    def DOMAIN_EXPERTS_CONFIG(self) -> Path:
        return self.HELIX_ROOT / "config" / "domain-experts.yaml"

    @property
    def LLM_PROVIDERS_CONFIG(self) -> Path:
        return self.HELIX_ROOT / "config" / "llm-providers.yaml"

    @property
    def SKILLS_DIR(self) -> Path:
        return self.HELIX_ROOT / "skills"

    @property
    def TEMPLATES_DIR(self) -> Path:
        return self.HELIX_ROOT / "templates"

    @property
    def TEMPLATES_PHASES(self) -> Path:
        return self.TEMPLATES_DIR / "phases"

    @property
    def TEST_ROOT(self) -> Path:
        return Path(os.environ.get("HELIX_TEST_ROOT", str(self.HELIX_ROOT) + "-test"))
\`\`\`

**1.2 Alle Module auf PathConfig umstellen**

| Datei | Aktuell | Neu |
|-------|---------|-----|
| \`expert_manager.py:79\` | \`Path("/home/aiuser01/...")\` | \`PathConfig().DOMAIN_EXPERTS_CONFIG\` |
| \`llm_client.py:78\` | \`Path("/home/aiuser01/...")\` | \`PathConfig().LLM_PROVIDERS_CONFIG\` |
| \`template_engine.py:34\` | \`Path("/home/aiuser01/...")\` | \`PathConfig().TEMPLATES_DIR\` |
| \`phase_loader.py:57\` | \`Path("/home/aiuser01/...")\` | \`PathConfig().TEMPLATES_PHASES\` |
| \`context_manager.py:32\` | \`Path("/home/aiuser01/...")\` | \`PathConfig().SKILLS_DIR\` |
| \`openai.py:50\` | \`Path("/home/aiuser01/...")\` | \`PathConfig().HELIX_ROOT\` |
| \`deployer.py:40-41\` | Class-Vars | Constructor mit PathConfig |
| \`integrator.py:39-40\` | Class-Vars | Constructor mit PathConfig |
| \`validator.py:176\` | Class-Var | Constructor mit PathConfig |

**1.3 sys.path Manipulation entfernen**

\`\`\`python
# ENTFERNEN aus main.py und openai.py:
sys.path.insert(0, ...)

# STATTDESSEN in pyproject.toml:
[project.scripts]
helix-api = "helix.api.main:main"
\`\`\`

### Phase 2: LSP Aktivierung

**2.1 Environment Variable setzen** (\`config/env.sh\`)

\`\`\`bash
# LSP für Claude Code aktivieren
export ENABLE_LSP_TOOL=1
\`\`\`

**2.2 pyright installieren** (\`pyproject.toml\`)

\`\`\`toml
[project.optional-dependencies]
dev = [
    "pyright>=1.1.350",
    "python-lsp-server[all]>=1.10.0",
]
\`\`\`

**2.3 PhaseExecutor erweitern** (optional, für automatische LSP-Aktivierung)

\`\`\`python
def _prepare_environment(self, phase_config: PhaseConfig) -> dict:
    env = os.environ.copy()
    if phase_config.type in ("development", "review", "integration"):
        env["ENABLE_LSP_TOOL"] = "1"
    return env
\`\`\`

**2.4 LSP Quality Gate** (optional, Phase 3)

\`\`\`python
# src/helix/quality_gates/lsp_diagnostics.py
class LSPDiagnosticsGate(QualityGate):
    """Quality Gate basierend auf LSP-Diagnostics."""

    def check(self, files: list[Path]) -> GateResult:
        # pyright --outputjson ausführen
        # Errors zählen
        # PASS wenn keine Errors
\`\`\`

### Phase 3: Dokumentation

**3.1 ADR-Status korrigieren**

| ADR | Aktuell | Aktion |
|-----|---------|--------|
| ADR-018 | Proposed | -> "Accepted" nach Implementation |
| ADR-020 | Proposed (mit falschem "Implemented" Kommentar) | -> Kommentar entfernen, Status klären |

**3.2 Neue Dokumentation**

- \`docs/CONFIGURATION-GUIDE.md\` - Alle Environment Variables und Pfad-Konfiguration
- \`docs/PATHS.md\` - PathConfig API Reference

**3.3 ConsultantMeeting dokumentieren** (\`docs/ARCHITECTURE-MODULES.md\`)

Neue Sektion hinzufügen:

\`\`\`markdown
### ConsultantMeeting - Multi-Expert Orchestration

Die \`ConsultantMeeting\`-Klasse implementiert eine 4-Phasen-Architektur für
komplexe Anfragen, die mehrere Domain-Experten erfordern:

1. **Selection**: Relevante Experten identifizieren
2. **Analysis**: Jeder Experte analysiert aus seiner Perspektive
3. **Synthesis**: Ergebnisse zusammenführen
4. **Output**: Finale Antwort generieren

#### Wann nutzen?

| Szenario | Empfehlung |
|----------|------------|
| Einfache Frage, 1 Domain | Direkter ClaudeRunner |
| Komplexe Frage, 2+ Domains | ConsultantMeeting |
| Escalation mit Kontext | ConsultantMeeting |
\`\`\`

**3.4 Context-Optimierung**

- Session-Details (ARCHITECTURE-MODULES.md Zeilen 349-457) -> `docs/SESSION-MANAGEMENT.md`
- API Middleware Details -> `docs/API-CONFIGURATION.md`

## Implementation

Die Implementation erfolgt in 4 Phasen (siehe `phases.yaml`):

### Phase 01: Path Consolidation
- `src/helix/config/paths.py` erweitern um neue Properties
- 12 Dateien migrieren auf PathConfig
- `sys.path.insert()` entfernen
- Quality Gate: `grep_forbidden` für "/home/aiuser01" und "sys.path.insert"

### Phase 02: LSP Activation
- `config/env.sh` mit `ENABLE_LSP_TOOL=1` erweitern
- `pyproject.toml` mit pyright und python-lsp-server erweitern
- `adr/018-lsp-integration.md` Status auf "Accepted" setzen
- Quality Gate: `pyright --version` erfolgreich

### Phase 03: Documentation
- `docs/CONFIGURATION-GUIDE.md` erstellen (Environment Variables, Pfade)
- `docs/PATHS.md` erstellen (PathConfig API Reference)
- `docs/ARCHITECTURE-MODULES.md` erweitern (ConsultantMeeting Sektion)
- `adr/020-intelligent-documentation-discovery.md` Status-Kommentar korrigieren
- `adr/INDEX.md` aktualisieren mit ADR-039
- Quality Gate: `files_exist`

### Phase 04: Verification
- Tests mit `HELIX_ROOT=/tmp/helix-test` ausführen
- Grep-Checks für verbotene Patterns
- LSP Go-to-Definition verifizieren
- Quality Gate: `tests_pass`

## Akzeptanzkriterien

### Paths
- [ ] Keine hardcoded "/home/aiuser01" Pfade mehr im Code
- [ ] Alle Module nutzen PathConfig
- [ ] Kein sys.path.insert() mehr
- [ ] Test-System läuft auf anderem Verzeichnis (via HELIX_ROOT env var)

### LSP
- [ ] \`ENABLE_LSP_TOOL=1\` in config/env.sh
- [ ] pyright in pyproject.toml dev dependencies
- [ ] LSP Go-to-Definition funktioniert für Python-Dateien

### Dokumentation
- [ ] docs/CONFIGURATION-GUIDE.md existiert
- [ ] docs/PATHS.md existiert mit PathConfig API Reference
- [ ] ConsultantMeeting in ARCHITECTURE-MODULES.md dokumentiert
- [ ] ADR-018 Status aktualisiert
- [ ] ADR-020 widersprüchlicher Kommentar entfernt

### Quality
- [ ] grep -r "/home/aiuser01" src/ findet nichts
- [ ] grep -r "sys.path.insert" src/ findet nichts
- [ ] pyright src/ hat keine Errors

## Konsequenzen

### Positiv
- Test-System funktioniert auf jeder Maschine
- Entwickler haben volle LSP-Unterstützung
- Dokumentation ist konsistent und vollständig
- ConsultantMeeting für Multi-Expert-Szenarien vorbereitet
- Keine fragilen sys.path Hacks mehr

### Negativ
- Einmalige Migration aller Module auf PathConfig
- Alle Entwickler müssen pyright installieren
- ARCHITECTURE-MODULES.md wird gekürzt (könnte Breaking Change für bestehende Referenzen sein)

### Neutral
- ADR-Status Updates erfordern Review
- Session-Details in separater Datei ist weder besser noch schlechter, nur anders strukturiert

## Referenzen

- [ADR-035: Consultant API Hardening](035-consultant-api-hardening.md) - Einführung PathConfig
- [ADR-018: LSP Integration](018-lsp-integration.md) - Ursprünglicher LSP-Plan
- [ADR-014: Documentation Architecture](014-documentation-architecture.md) - Doku-Struktur
- [PathConfig Source](../src/helix/config/paths.py) - Bestehende Implementation
