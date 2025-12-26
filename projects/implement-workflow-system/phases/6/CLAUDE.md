# Phase 6: Integration & E2E Testing

Du bist ein Claude Code Entwickler der das gesamte Workflow-System testet und integriert.

---

## 🎯 Ziel

1. Alle Outputs aus Phase 1-5 in HELIX integrieren
2. E2E Tests für jeden Workflow-Typ
3. Dokumentation finalisieren
4. Deploy to Test-System

---

## 📚 Zuerst lesen

1. Alle `output/` Verzeichnisse aus Phase 1-5
2. `tests/integration/` - Bestehende Tests
3. `src/helix/api/` - API Struktur
4. `scripts/deploy-test.sh` - Deploy Script

---

## 📋 Aufgaben

### 1. Integration

Kopiere alle Outputs an ihre finalen Orte:

```bash
# Phase 1: LSP
cp output/config/lsp.conf → config/
cp output/docs/LSP-SETUP.md → docs/

# Phase 2: Workflows
cp output/templates/workflows/* → templates/workflows/

# Phase 3: Consultant
cp output/templates/consultant/* → templates/consultant/

# Phase 4: Verification
cp output/src/helix/verification/* → src/helix/verification/

# Phase 5: Planning
cp output/src/helix/planning/* → src/helix/planning/

# ADRs finalisieren
python -m helix.tools.adr_tool finalize output/adr/023-*.md
python -m helix.tools.adr_tool finalize output/adr/024-*.md
python -m helix.tools.adr_tool finalize output/adr/025-*.md
python -m helix.tools.adr_tool finalize output/adr/026-*.md
```

### 2. E2E Tests erstellen

`tests/integration/test_workflow_system.py`:

```python
"""E2E Tests for Workflow System."""

import pytest
from pathlib import Path
import httpx

API_URL = "http://localhost:8001"

class TestWorkflowSystem:
    """End-to-end tests for the complete workflow system."""
    
    @pytest.fixture
    async def api_client(self):
        async with httpx.AsyncClient(base_url=API_URL) as client:
            yield client
    
    # ═══════════════════════════════════════════════════════════════
    # Test: Intern-Simple Workflow
    # ═══════════════════════════════════════════════════════════════
    
    async def test_intern_simple_workflow(self, api_client, tmp_path):
        """Test complete intern-simple workflow."""
        
        # Setup test project
        project_path = tmp_path / "test-intern-simple"
        project_path.mkdir()
        
        # Copy workflow template
        # ...
        
        # Start via API
        response = await api_client.post(
            "/helix/execute",
            json={"project_path": str(project_path), "phase": 1}
        )
        assert response.status_code == 200
        job_id = response.json()["job_id"]
        
        # Poll until complete
        # ...
        
        # Verify all phases completed
        assert (project_path / "phases/1/output").exists()
        # ...
    
    # ═══════════════════════════════════════════════════════════════
    # Test: Sub-Agent Verification
    # ═══════════════════════════════════════════════════════════════
    
    async def test_sub_agent_retry_on_fail(self, api_client):
        """Test that sub-agent retries on verification failure."""
        
        # Create project that will fail verification first time
        # ...
        
        # Verify retry happened
        # Verify feedback was sent
        # ...
    
    async def test_sub_agent_escalation(self, api_client):
        """Test escalation after 3 failures."""
        
        # Create project that always fails
        # Verify escalation to consultant
        # Verify final abort
        # ...
    
    # ═══════════════════════════════════════════════════════════════
    # Test: Dynamic Phase Generation
    # ═══════════════════════════════════════════════════════════════
    
    async def test_planning_agent_generates_phases(self, api_client):
        """Test that planning agent generates 1-5 phases."""
        
        from helix.planning.agent import PlanningAgent
        
        agent = PlanningAgent(max_phases=5)
        plan = await agent.analyze_and_plan(
            "Build a complex data pipeline with ETL and reporting"
        )
        
        assert 1 <= len(plan.phases) <= 5
        assert all(p.estimated_sessions >= 1 for p in plan.phases)
    
    # ═══════════════════════════════════════════════════════════════
    # Test: Consultant Workflow Selection
    # ═══════════════════════════════════════════════════════════════
    
    async def test_consultant_selects_correct_workflow(self, api_client):
        """Test consultant selects intern-simple for clear HELIX feature."""
        
        response = await api_client.post(
            "/v1/chat/completions",
            json={
                "model": "helix-consultant",
                "messages": [{
                    "role": "user",
                    "content": "Ich möchte einen neuen API Endpoint für HELIX"
                }]
            }
        )
        
        # Consultant should ask or suggest intern-simple
        content = response.json()["choices"][0]["message"]["content"]
        assert "intern" in content.lower() or "workflow" in content.lower()
```

### 3. Dokumentation finalisieren

Erstelle `docs/WORKFLOW-SYSTEM.md`:

```markdown
# HELIX Workflow System

## Übersicht

Das Workflow-System ermöglicht dem Consultant, vollständige
Entwicklungs-Workflows zu starten statt einzelne Tools aufzurufen.

## Projekt-Typen

| Typ | Workflow | Beschreibung |
|-----|----------|--------------|
| Intern + Leicht | `intern-simple` | 7 Phasen bis Deploy-Prod |
| Intern + Komplex | `intern-complex` | Planning-Agent + dynamisch |
| Extern + Leicht | `extern-simple` | 4 Phasen ohne Deploy |
| Extern + Komplex | `extern-complex` | Planning-Agent + dynamisch |

## Sub-Agent Verifikation

- Jede Phase wird nach Abschluss verifiziert
- Max 3 Retries mit Feedback
- Eskalation zu Consultant bei Fail
- Dann Abbruch

## Dynamische Phasen

Komplexe Projekte starten mit Planning-Agent:
- Analysiert Scope
- Generiert 1-5 Phasen
- Optional: Feasibility zuerst

## API Nutzung

```bash
# Workflow starten
curl -X POST http://localhost:8001/helix/execute \
  -d '{"project_path": "projects/...", "phase": 1}'

# Status prüfen
curl http://localhost:8001/helix/jobs/{id}

# Phase resetten
curl -X POST http://localhost:8001/helix/execute \
  -d '{"project_path": "...", "phase": N, "reset": true}'
```
```

### 4. Deploy to Test

```bash
# Syntax-Check
python -m py_compile src/helix/verification/*.py
python -m py_compile src/helix/planning/*.py

# Tests ausführen
pytest tests/integration/test_workflow_system.py -v

# Deploy to Test-System
./scripts/deploy-test.sh
```

---

## 📁 Output

| Datei | Beschreibung |
|-------|--------------|
| Integrierte Files in src/, templates/, etc. | Alle Module |
| `tests/integration/test_workflow_system.py` | E2E Tests |
| `docs/WORKFLOW-SYSTEM.md` | Finale Dokumentation |
| ADRs in `adr/023-026-*.md` | Finalisierte ADRs |

---

## ✅ Quality Gate

- [ ] Alle Module integriert (keine Reste in output/)
- [ ] Python Syntax valide
- [ ] E2E Tests bestehen:
  - [ ] intern-simple Workflow
  - [ ] extern-simple Workflow
  - [ ] Sub-Agent Retry
  - [ ] Sub-Agent Eskalation
  - [ ] Planning Agent
  - [ ] Consultant Workflow-Wahl
- [ ] ADRs finalisiert (023, 024, 025, 026)
- [ ] Deploy to Test erfolgreich

---

## 🔗 HELIX API Reference

| Endpoint | Methode | Zweck |
|----------|---------|-------|
| `POST /helix/execute` | Projekt/Phase starten | `{"project_path": "...", "phase": N}` |
| `GET /helix/jobs` | Alle Jobs listen | |
| `GET /helix/jobs/{id}` | Job Status | `status: pending/running/completed/failed` |
| `GET /helix/stream/{id}` | SSE Stream | Live Output |
| `POST /helix/execute` + `reset: true` | Phase Reset | |

## Async CLI (falls verfügbar)

```bash
helix run projects/xyz --phase 1
helix status {job_id}
helix logs {job_id}
helix reset projects/xyz --phase 2
```
