"""Sub-Agent Verification with Feedback Loop.

Verifies phase output using a dedicated sub-agent and provides
feedback for corrections if verification fails.

Example:
    verifier = SubAgentVerifier(max_retries=3)
    result = await verifier.verify_phase(
        phase_output=Path("phases/2/output"),
        quality_gate={"type": "syntax_check"},
    )
    if not result.success:
        print(f"Feedback: {result.feedback}")
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Any
import json

from helix.claude_runner import ClaudeRunner


@dataclass
class VerificationResult:
    """Result from sub-agent verification.

    Attributes:
        success: Whether verification passed.
        feedback: Specific feedback for fixing issues (if failed).
        errors: List of error messages.
        checks_passed: List of checks that passed.
    """

    success: bool
    feedback: Optional[str] = None
    errors: list[str] = field(default_factory=list)
    checks_passed: list[str] = field(default_factory=list)


class SubAgentVerifier:
    """Verifies phase output using a sub-agent.

    The verifier spawns a lightweight Claude instance (Haiku)
    to check phase output against quality criteria. This provides
    an independent verification layer that can catch issues early.

    Attributes:
        max_retries: Maximum verification attempts per phase.
        runner: ClaudeRunner instance for executing verification.
    """

    VERIFICATION_PROMPT = '''You are a verification agent. Check the phase output in the current directory.

Quality Gate Type: {quality_gate_type}
Expected Files: {expected_files}

Your task:
1. Check that all expected files exist
2. Validate file syntax (Python files should be syntactically correct, YAML should parse, etc.)
3. Verify the quality gate criteria are met

Based on the quality gate type:
- files_exist: Just verify files exist
- syntax_check: Verify files exist AND have valid syntax
- tests_pass: Verify test files exist and would pass
- adr_valid: Verify ADR has required sections

After checking, output your result as JSON:

```json
{{
  "success": true,
  "errors": [],
  "checks_passed": ["File exists: src/module.py", "Syntax valid: src/module.py"],
  "feedback": null
}}
```

Or if verification fails:

```json
{{
  "success": false,
  "errors": ["Missing file: tests/test_module.py", "Syntax error in src/module.py line 42"],
  "checks_passed": ["File exists: src/module.py"],
  "feedback": "Please create tests/test_module.py and fix the syntax error on line 42 of src/module.py"
}}
```

IMPORTANT: Output ONLY the JSON block, nothing else.
'''

    def __init__(self, max_retries: int = 3):
        """Initialize verifier.

        Args:
            max_retries: Maximum verification attempts per phase.
        """
        self.max_retries = max_retries
        self.runner = ClaudeRunner()

    async def verify_phase(
        self,
        phase_output: Path,
        quality_gate: dict[str, Any],
        expected_files: list[str] | None = None,
    ) -> VerificationResult:
        """Verify phase output with sub-agent.

        Spawns a Haiku model instance to independently verify
        that the phase output meets quality criteria.

        Args:
            phase_output: Path to phase output directory.
            quality_gate: Quality gate configuration from phases.yaml.
            expected_files: Optional list of expected file paths.

        Returns:
            VerificationResult with success status and feedback.
        """
        prompt = self.VERIFICATION_PROMPT.format(
            quality_gate_type=quality_gate.get("type", "files_exist"),
            expected_files=expected_files or [],
        )

        result = await self.runner.run_phase(
            phase_dir=phase_output,
            prompt=prompt,
            timeout=120,  # 2 minutes for verification
            env_overrides={"CLAUDE_MODEL": "claude-3-haiku-20240307"},
        )

        return self._parse_result(result)

    def _parse_result(self, claude_result: Any) -> VerificationResult:
        """Parse Claude result into VerificationResult.

        Attempts to extract JSON from the Claude output.
        Falls back to exit code if no structured output.

        Args:
            claude_result: Result from ClaudeRunner.

        Returns:
            Parsed VerificationResult.
        """
        # Try to use parsed JSON output
        if claude_result.output_json:
            return VerificationResult(
                success=claude_result.output_json.get("success", False),
                feedback=claude_result.output_json.get("feedback"),
                errors=claude_result.output_json.get("errors", []),
                checks_passed=claude_result.output_json.get("checks_passed", []),
            )

        # Try to parse JSON from stdout
        if claude_result.stdout:
            try:
                # Find JSON block in output
                stdout = claude_result.stdout
                json_start = stdout.find("```json")
                if json_start != -1:
                    json_end = stdout.find("```", json_start + 7)
                    if json_end != -1:
                        json_str = stdout[json_start + 7 : json_end].strip()
                        data = json.loads(json_str)
                        return VerificationResult(
                            success=data.get("success", False),
                            feedback=data.get("feedback"),
                            errors=data.get("errors", []),
                            checks_passed=data.get("checks_passed", []),
                        )
            except (json.JSONDecodeError, KeyError):
                pass

        # Fallback: Check exit code
        return VerificationResult(
            success=claude_result.success,
            feedback="Verification agent did not return structured output.",
            errors=[claude_result.stderr] if claude_result.stderr else [],
        )

    async def verify_with_retries(
        self,
        phase_output: Path,
        quality_gate: dict[str, Any],
        expected_files: list[str] | None = None,
    ) -> tuple[VerificationResult, int]:
        """Verify phase output with multiple retry attempts.

        Args:
            phase_output: Path to phase output directory.
            quality_gate: Quality gate configuration.
            expected_files: Optional list of expected file paths.

        Returns:
            Tuple of (final VerificationResult, attempts used).
        """
        last_result = VerificationResult(success=False, feedback="No verification run")

        for attempt in range(1, self.max_retries + 1):
            result = await self.verify_phase(
                phase_output=phase_output,
                quality_gate=quality_gate,
                expected_files=expected_files,
            )

            if result.success:
                return result, attempt

            last_result = result

        return last_result, self.max_retries
