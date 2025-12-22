# Sub-Phase 14.3: Evolution Project Manager

## Ziel

Python-Modul zur Verwaltung von Evolution-Projekten.

## Aufgabe

Erstelle `output/project.py` mit:

```python
class EvolutionProject:
    """Represents a single evolution project."""
    session_id: str
    name: str
    status: str  # pending/developing/ready/deployed/integrated/failed
    path: Path
    
    def get_new_files() -> list[Path]
    def get_modified_files() -> list[Path]
    def update_status(status: str)

class EvolutionProjectManager:
    """Manages evolution projects."""
    base_path: Path = projects/evolution/
    
    def list_projects() -> list[EvolutionProject]
    def get_project(name: str) -> EvolutionProject
    def create_project(name: str, spec: dict, phases: dict) -> EvolutionProject
```

Erstelle auch `output/test_project.py` mit Unit Tests.

## Output

- `output/project.py`
- `output/test_project.py`
