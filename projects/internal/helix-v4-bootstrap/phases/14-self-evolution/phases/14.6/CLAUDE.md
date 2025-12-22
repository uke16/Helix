# Sub-Phase 14.6: API Endpoints & Consultant Update

## Ziel

REST API für Evolution-Workflow und Consultant-Awareness.

## Aufgabe

### routes/evolution.py

```python
router = APIRouter(prefix="/helix/evolution")

@router.get("/projects")
@router.get("/projects/{name}")
@router.post("/projects/{name}/deploy")
@router.post("/projects/{name}/validate")
@router.post("/projects/{name}/integrate")
@router.post("/projects/{name}/rollback")
@router.post("/sync-rag")
```

### Consultant Template Update

Erweitere `templates/consultant/session.md.j2`:
- Consultant kennt Evolution-Projekte
- Kann type: evolution Projekte erstellen
- Weiß über den Deploy/Validate/Integrate Workflow

## Output

- `output/evolution.py` (API Routes)
- `output/test_evolution.py`
