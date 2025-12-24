# Phase 1: UnifiedOrchestrator erstellen

## Deine Aufgabe

Erstelle `src/helix/api/orchestrator.py` - die EINE zentrale Orchestrator-Implementierung.

## Was du lesen musst

```bash
# 1. Das ADR das du implementierst
cat adr/022-unified-api-architecture.md

# 2. Bestehende Implementierungen (zum Konsolidieren)
cat src/helix/orchestrator_legacy.py      # Quality Gates, Escalation
cat src/helix/api/streaming.py            # Verification, SSE Events
cat src/helix/orchestrator/runner.py      # DataFlow (falls nützlich)

# 3. ADR-011 Verification (MUSS integriert werden)
cat src/helix/evolution/verification.py
```

## Was du erstellen musst

### 1. `output/src/helix/api/orchestrator.py`

```python
"""Unified Orchestrator - EINE Implementierung für alle Entry Points."""

class UnifiedOrchestrator:
    """Der einzige Orchestrator für HELIX.
    
    Konsolidiert:
    - orchestrator_legacy.py (Quality Gates, Escalation)
    - streaming.py (Verification, Events)
    
    Genutzt von:
    - API (/helix/execute)
    - CLI (via API)
    - Open WebUI (via API)
    """
    
    async def run_project(
        self,
        project_path: Path,
        on_event: Callable[[PhaseEvent], None] | None = None,
    ) -> ProjectResult:
        """Führe Projekt aus mit allen Features.
        
        Features:
        - Phase Execution via ClaudeRunner
        - Post-Phase Verification (ADR-011)
        - Quality Gates
        - Escalation (ADR-004)
        - Event Callbacks für SSE
        """
        ...
```

### 2. `output/tests/api/test_orchestrator.py`

Tests für:
- `UnifiedOrchestrator` Instanzierung
- `run_project()` mit Mock-Projekt
- Event Callbacks werden aufgerufen
- Verification wird ausgeführt
- Quality Gate Checks

## Erfolgskriterien

Bevor du fertig bist, prüfe:

```bash
# 1. Datei existiert
ls output/src/helix/api/orchestrator.py

# 2. Syntax OK
python3 -m py_compile output/src/helix/api/orchestrator.py

# 3. Tests existieren
ls output/tests/api/test_orchestrator.py

# 4. Tests laufen durch (im HELIX Projekt)
cd /home/aiuser01/helix-v4
cp output/src/helix/api/orchestrator.py src/helix/api/
cp -r output/tests/api tests/
PYTHONPATH=src pytest tests/api/test_orchestrator.py -v
```

## Checkliste

- [ ] `UnifiedOrchestrator` Klasse erstellt
- [ ] `run_project()` mit event callback
- [ ] `PhaseVerifier` aus ADR-011 integriert
- [ ] `QualityGateRunner` integriert
- [ ] `EscalationManager` integriert
- [ ] `PhaseEvent` dataclass für Events
- [ ] `ProjectResult` dataclass für Ergebnis
- [ ] Tests geschrieben
- [ ] Tests laufen durch

---

## 📝 Dokumentation (Code-Layer)

Du MUSST für jede Datei die du erstellst auch die Code-Layer Dokumentation erstellen.

### Format für Code-Layer Docs

Erstelle `output/docs/sources/api-orchestrator.yaml`:

```yaml
module:
  name: helix.api.orchestrator
  description: "Unified Orchestrator - Eine Implementierung für alle Entry Points"
  
classes:
  - name: UnifiedOrchestrator
    description: "Der einzige Orchestrator für HELIX"
    methods:
      - name: run_project
        signature: "async def run_project(project_path: Path, on_event: Callable | None = None) -> ProjectResult"
        description: "Führt ein Projekt aus mit allen Features"
        params:
          - name: project_path
            type: Path
            description: "Pfad zum Projekt-Verzeichnis"
          - name: on_event
            type: "Callable[[PhaseEvent], None] | None"
            description: "Callback für SSE Events"
        returns:
          type: ProjectResult
          description: "Ergebnis der Ausführung"
          
  - name: PhaseEvent
    description: "Event das während Phase-Ausführung emittiert wird"
    fields:
      - name: event_type
        type: str
        description: "phase_start, phase_complete, verification_failed, etc."
      - name: phase_id
        type: str
      - name: data
        type: dict

  - name: ProjectResult
    description: "Ergebnis einer Projekt-Ausführung"
    fields:
      - name: success
        type: bool
      - name: phases_completed
        type: int
      - name: phases_total
        type: int
      - name: errors
        type: "list[str]"
```

### Prüfen ob Docs kompilierbar sind

```bash
cd /home/aiuser01/helix-v4
PYTHONPATH=src python3 -m helix.tools.docs_compiler compile --source output/docs/sources/
```
