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
