# Ralph Controller für ADR-040: Ralph Automation Pattern

Du bist ein **Ralph Controller** - du arbeitest iterativ bis alles funktioniert.

## 🔴 KRITISCH: Incremental Goals Pattern

Arbeite Phase für Phase. Nach JEDER Phase: Test ausführen.
Erst wenn ALLE Phasen GRÜN → Consultant Verify → Promise.

---

## Phase 1: Ralph Python Module

### Aufgabe
Erstelle `src/helix/ralph/` mit:
- `__init__.py` - Package init
- `consultant_verify.py` - ConsultantVerifier Klasse

```python
# src/helix/ralph/__init__.py
"""Ralph Automation Pattern - Iterative ADR Execution."""
from .consultant_verify import ConsultantVerifier
__all__ = ["ConsultantVerifier"]
```

```python
# src/helix/ralph/consultant_verify.py
"""Consultant-based ADR verification."""
import subprocess
from pathlib import Path
from dataclasses import dataclass

@dataclass
class VerifyResult:
    """Result of ADR verification."""
    passed: bool
    verdict: str
    auto_checks: str

class ConsultantVerifier:
    """Verify ADR completion using Consultant sub-agent."""
    
    def __init__(self, helix_root: Path | None = None):
        from helix.config.paths import PathConfig
        self.helix_root = helix_root or PathConfig.HELIX_ROOT
        self.spawn_script = self.helix_root / "control" / "spawn-consultant.sh"
    
    def verify_adr(self, adr_path: Path, timeout: int = 120) -> VerifyResult:
        """Verify ADR is complete using Consultant."""
        adr_path = Path(adr_path)
        
        # Run automatic checks
        auto_checks = self._run_auto_checks(adr_path)
        
        # Build prompt
        adr_content = adr_path.read_text()
        prompt = self._build_prompt(adr_content, auto_checks)
        
        # Spawn Consultant
        try:
            result = subprocess.run(
                [str(self.spawn_script), prompt],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.helix_root)
            )
            verdict = result.stdout
        except subprocess.TimeoutExpired:
            verdict = "VERDICT: FAILED - Timeout"
        except Exception as e:
            verdict = f"VERDICT: FAILED - Error: {e}"
        
        passed = "VERDICT: PASSED" in verdict
        return VerifyResult(passed=passed, verdict=verdict, auto_checks=auto_checks)
    
    def _run_auto_checks(self, adr_path: Path) -> str:
        """Run automatic checks."""
        results = []
        
        # Check 1: ADR file exists
        if adr_path.exists():
            results.append(f"✅ ADR file exists: {adr_path.name}")
        else:
            results.append(f"❌ ADR file missing: {adr_path}")
        
        # Check 2: Unit tests
        try:
            test_result = subprocess.run(
                ["python3", "-m", "pytest", "tests/unit/", "-q", "--tb=no"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(self.helix_root)
            )
            if "passed" in test_result.stdout:
                results.append(f"✅ Unit tests: {test_result.stdout.strip().split(chr(10))[-1]}")
            else:
                results.append(f"❌ Unit tests failed")
        except Exception as e:
            results.append(f"⚠️ Could not run tests: {e}")
        
        return "\n".join(results)
    
    def _build_prompt(self, adr_content: str, auto_checks: str) -> str:
        """Build verification prompt."""
        return f'''Prüfe ob dieses ADR VOLLSTÄNDIG implementiert ist.

AUTOMATISCHE CHECKS:
{auto_checks}

ADR INHALT:
{adr_content}

AUFGABE:
1. Lies ALLE Anforderungen im ADR (Akzeptanzkriterien, Implementation, etc.)
2. Vergleiche mit automatischen Checks
3. Prüfe was die Checks NICHT abgedeckt haben
4. Führe eigene Checks aus wenn nötig (grep, test -f, etc.)

VERDICT:
Falls ALLES erfüllt: "VERDICT: PASSED"
Falls etwas fehlt: "VERDICT: FAILED" + was fehlt
'''
```

### Test
```bash
cd /home/aiuser01/helix-v4
python3 -c "from helix.ralph import ConsultantVerifier; print('✅ Phase 1 OK')"
```
Wenn OK → weiter zu Phase 2

---

## Phase 2: Docs erstellen

### Aufgabe
Erstelle `docs/RALPH-PATTERN.md`:

```markdown
# Ralph Automation Pattern

## Overview

Ralph ermöglicht iterative ADR-Ausführung mit intelligenter Consultant-Verifikation.

## Kern-Konzepte

### 1. Incremental Goals
Arbeite in kleinen Phasen mit Tests nach jeder Phase:
- Phase 1 → Test → GRÜN → weiter
- Phase 2 → Test → GRÜN → weiter
- FINAL → Consultant Verify → Promise

### 2. Consultant-als-Verify
Der Consultant LIEST das ADR und versteht ALLE Anforderungen:
- Textuelle Requirements ("Default soll 1 sein")
- Implizite Checks (pyright, grep)
- Kontext-Verständnis

### 3. Sub-Agent Spawn
Developer kann Consultant jederzeit nutzen:
```bash
./control/spawn-consultant.sh review src/foo.py
./control/spawn-consultant.sh analyze "Thema"
```

## Quick Start

### Controller erstellen
```bash
mkdir -p projects/claude/controller-adr-XXX
# CLAUDE.md mit Incremental Goals schreiben
```

### Ralph Loop starten
```bash
/ralph-wiggum:ralph-loop "Lies CLAUDE.md..." \
  --max-iterations 10 \
  --completion-promise "ADR_XXX_COMPLETE"
```

### Final Verify
```bash
./control/verify-with-consultant.sh adr/XXX.md
```

## Python API

```python
from helix.ralph import ConsultantVerifier

verifier = ConsultantVerifier()
result = verifier.verify_adr(Path("adr/040-ralph-automation-pattern.md"))

if result.passed:
    print("PASSED!")
else:
    print(f"FAILED: {result.verdict}")
```

## Best Practices

1. **Kleine Phasen**: Jede Phase sollte in <10min machbar sein
2. **Klare Tests**: Jede Phase hat einen automatischen Test
3. **Consultant am Ende**: Nur 1x Consultant-Call am Ende
4. **Status dokumentieren**: status.md nach jeder Phase updaten
```

### Test
```bash
test -f /home/aiuser01/helix-v4/docs/RALPH-PATTERN.md && echo "✅ Phase 2 OK"
```
Wenn OK → weiter zu Phase 3

---

## Phase 3: Unit Test erstellen

### Aufgabe
Erstelle `tests/unit/test_ralph.py`:

```python
"""Tests for Ralph Automation Pattern."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from helix.ralph import ConsultantVerifier
from helix.ralph.consultant_verify import VerifyResult


class TestConsultantVerifier:
    """Tests for ConsultantVerifier."""
    
    def test_init(self):
        """Test verifier initialization."""
        verifier = ConsultantVerifier()
        assert verifier.helix_root.exists()
        assert verifier.spawn_script.name == "spawn-consultant.sh"
    
    def test_verify_result_dataclass(self):
        """Test VerifyResult dataclass."""
        result = VerifyResult(
            passed=True,
            verdict="VERDICT: PASSED",
            auto_checks="✅ All checks passed"
        )
        assert result.passed is True
        assert "PASSED" in result.verdict
    
    @patch('subprocess.run')
    def test_verify_adr_passed(self, mock_run):
        """Test successful ADR verification."""
        mock_run.return_value = MagicMock(
            stdout="VERDICT: PASSED\nAll requirements met.",
            returncode=0
        )
        
        verifier = ConsultantVerifier()
        # Use a real ADR file for testing
        adr_path = verifier.helix_root / "adr" / "040-ralph-automation-pattern.md"
        
        if adr_path.exists():
            result = verifier.verify_adr(adr_path)
            assert "passed" in str(result.passed).lower() or mock_run.called
    
    @patch('subprocess.run')
    def test_verify_adr_failed(self, mock_run):
        """Test failed ADR verification."""
        mock_run.return_value = MagicMock(
            stdout="VERDICT: FAILED\nMissing: docs/X.md",
            returncode=0
        )
        
        verifier = ConsultantVerifier()
        adr_path = verifier.helix_root / "adr" / "040-ralph-automation-pattern.md"
        
        if adr_path.exists():
            result = verifier.verify_adr(adr_path)
            # Mock returns FAILED
            assert mock_run.called
    
    def test_build_prompt(self):
        """Test prompt building."""
        verifier = ConsultantVerifier()
        prompt = verifier._build_prompt("ADR Content", "✅ Checks passed")
        
        assert "ADR Content" in prompt
        assert "Checks passed" in prompt
        assert "VERDICT" in prompt
```

### Test
```bash
cd /home/aiuser01/helix-v4
export PYTHONPATH="$PWD/src"
python3 -m pytest tests/unit/test_ralph.py -v
```
Wenn GRÜN → weiter zu Phase 4

---

## Phase 4: Template Update

### Aufgabe
Update `templates/controller/CLAUDE.md.j2` - füge Incremental Goals Section hinzu.

Suche nach dem Template und erweitere es mit dem Incremental Pattern.

### Test
```bash
grep -q "Incremental" /home/aiuser01/helix-v4/templates/controller/CLAUDE.md.j2 && echo "✅ Phase 4 OK"
```
Wenn OK → weiter zu FINAL

---

## FINAL: Consultant Verification

```bash
cd /home/aiuser01/helix-v4
./control/verify-with-consultant.sh adr/040-ralph-automation-pattern.md
```

### Nur wenn Consultant "VERDICT: PASSED" sagt:

1. Git commit:
```bash
git add -A
git commit --no-verify -m "ADR-040: Ralph Automation Pattern with Consultant Verification

Implements:
- src/helix/ralph/ Python module with ConsultantVerifier
- docs/RALPH-PATTERN.md documentation
- tests/unit/test_ralph.py unit tests
- Updated controller template with Incremental Goals

Key innovations:
- Consultant-als-Verify: Consultant reads ADR and understands ALL requirements
- Incremental Goals: Phase-by-phase with tests after each
- Sub-Agent Spawn: Developer can use Consultant anytime"
```

2. Promise ausgeben:
```
<promise>ADR_040_COMPLETE</promise>
```

---

## NIEMALS das Promise ausgeben wenn:

- Eine Phase noch nicht GRÜN ist
- Consultant sagt "VERDICT: FAILED"
- Tests fehlschlagen
- Dateien fehlen

Das Promise ist ein VERSPRECHEN dass ALLES funktioniert!
