# Sub-Phase 14.5: Integrator & RAG Sync

## Ziel

Integration in Production und RAG-Datenbank Synchronisation.

## Aufgabe

### integrator.py

```python
class Integrator:
    production_path = /home/aiuser01/helix-v4
    
    async def pre_integration_backup()  # Git tag
    async def integrate(project: EvolutionProject)  # Copy to main
    async def post_integration_restart()  # Restart production
    async def rollback()  # Git reset
```

### rag_sync.py

```python
class RAGSync:
    """Sync Qdrant embeddings from production to test."""
    
    async def sync_collections()
    async def get_sync_status() -> dict
```

## Output

- `output/integrator.py`
- `output/rag_sync.py`
- `output/test_integrator.py`
