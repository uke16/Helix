# Sub-Phase 14.4: Deployer & Validator

## Ziel

Module für Deploy ins Test-System und Validation.

## Aufgabe

### deployer.py

```python
class Deployer:
    test_system_path = /home/aiuser01/helix-v4-test
    
    async def pre_deploy_sync()  # Git fetch + reset
    async def deploy(project: EvolutionProject)  # Copy new/ and modified/
    async def restart_test_system()  # Control script restart
    async def rollback()  # Reset test system
```

### validator.py

```python
class Validator:
    async def syntax_check(files: list[Path]) -> ValidationResult
    async def run_unit_tests(test_path: Path) -> ValidationResult
    async def run_e2e_tests(api_url: str) -> ValidationResult
    async def full_validation(project: EvolutionProject) -> ValidationResult
```

## Output

- `output/deployer.py`
- `output/validator.py`
- `output/test_deployer.py`
- `output/test_validator.py`
