"""Quality Gate System for HELIX v4.

Provides deterministic quality checks for phase validation.
"""

import asyncio
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class GateResult:
    """Result of a quality gate check.

    Attributes:
        passed: Whether the gate check passed.
        gate_type: Type of gate that was checked.
        message: Human-readable result message.
        details: Additional details about the check result.
    """
    passed: bool
    gate_type: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


class QualityGateRunner:
    """Runs deterministic quality gate checks.

    Quality gates are used to verify that a phase has completed
    successfully before moving to the next phase. Gates include
    file existence checks, syntax validation, and test execution.

    Example:
        runner = QualityGateRunner()
        result = runner.check_files_exist(
            phase_dir=Path("/project/phases/01-foundation"),
            expected=["output/result.json", "src/main.py"]
        )
        if not result.passed:
            print(f"Gate failed: {result.message}")
    """

    SUPPORTED_LANGUAGES = {"python", "typescript", "javascript", "go", "rust"}

    def check_files_exist(
        self, phase_dir: Path, expected: list[str]
    ) -> GateResult:
        """Check if expected files exist in the phase directory.

        Args:
            phase_dir: Path to the phase directory.
            expected: List of relative file paths expected to exist.

        Returns:
            GateResult indicating pass/fail with details of missing files.
        """
        missing = []
        existing = []

        for file_path in expected:
            full_path = phase_dir / file_path
            if full_path.exists():
                existing.append(file_path)
            else:
                missing.append(file_path)

        if missing:
            return GateResult(
                passed=False,
                gate_type="files_exist",
                message=f"Missing {len(missing)} expected file(s)",
                details={
                    "missing": missing,
                    "existing": existing,
                    "total_expected": len(expected),
                },
            )

        return GateResult(
            passed=True,
            gate_type="files_exist",
            message=f"All {len(expected)} expected files exist",
            details={
                "existing": existing,
                "total_expected": len(expected),
            },
        )

    def check_syntax(self, phase_dir: Path, language: str) -> GateResult:
        """Check syntax of source files in the phase directory.

        Args:
            phase_dir: Path to the phase directory.
            language: Programming language to check (python, typescript, etc.).

        Returns:
            GateResult indicating pass/fail with syntax error details.
        """
        language = language.lower()

        if language not in self.SUPPORTED_LANGUAGES:
            return GateResult(
                passed=False,
                gate_type="syntax_check",
                message=f"Unsupported language: {language}",
                details={"supported": list(self.SUPPORTED_LANGUAGES)},
            )

        if language == "python":
            return self._check_python_syntax(phase_dir)
        elif language in ("typescript", "javascript"):
            return self._check_js_ts_syntax(phase_dir, language)
        elif language == "go":
            return self._check_go_syntax(phase_dir)
        elif language == "rust":
            return self._check_rust_syntax(phase_dir)

        return GateResult(
            passed=True,
            gate_type="syntax_check",
            message=f"No syntax check implemented for {language}",
            details={},
        )

    def _check_python_syntax(self, phase_dir: Path) -> GateResult:
        """Check Python syntax using py_compile."""
        errors = []
        checked = []

        for py_file in phase_dir.rglob("*.py"):
            checked.append(str(py_file.relative_to(phase_dir)))
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    source = f.read()
                compile(source, str(py_file), "exec")
            except SyntaxError as e:
                errors.append({
                    "file": str(py_file.relative_to(phase_dir)),
                    "line": e.lineno,
                    "offset": e.offset,
                    "message": str(e.msg),
                })

        if errors:
            return GateResult(
                passed=False,
                gate_type="syntax_check",
                message=f"Syntax errors in {len(errors)} file(s)",
                details={
                    "errors": errors,
                    "files_checked": len(checked),
                },
            )

        return GateResult(
            passed=True,
            gate_type="syntax_check",
            message=f"All {len(checked)} Python files have valid syntax",
            details={"files_checked": checked},
        )

    def _check_js_ts_syntax(self, phase_dir: Path, language: str) -> GateResult:
        """Check JavaScript/TypeScript syntax using node."""
        ext = "ts" if language == "typescript" else "js"
        files = list(phase_dir.rglob(f"*.{ext}"))

        if not files:
            return GateResult(
                passed=True,
                gate_type="syntax_check",
                message=f"No {language} files to check",
                details={"files_checked": 0},
            )

        try:
            if language == "typescript":
                result = subprocess.run(
                    ["npx", "tsc", "--noEmit", "--skipLibCheck"],
                    cwd=phase_dir,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
            else:
                result = subprocess.run(
                    ["node", "--check"] + [str(f) for f in files[:10]],
                    cwd=phase_dir,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

            if result.returncode != 0:
                return GateResult(
                    passed=False,
                    gate_type="syntax_check",
                    message=f"{language} syntax check failed",
                    details={
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "files_checked": len(files),
                    },
                )
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            return GateResult(
                passed=False,
                gate_type="syntax_check",
                message=f"Failed to run {language} syntax check: {e}",
                details={"error": str(e)},
            )

        return GateResult(
            passed=True,
            gate_type="syntax_check",
            message=f"All {len(files)} {language} files have valid syntax",
            details={"files_checked": len(files)},
        )

    def _check_go_syntax(self, phase_dir: Path) -> GateResult:
        """Check Go syntax using go build."""
        files = list(phase_dir.rglob("*.go"))

        if not files:
            return GateResult(
                passed=True,
                gate_type="syntax_check",
                message="No Go files to check",
                details={"files_checked": 0},
            )

        try:
            result = subprocess.run(
                ["go", "build", "-n", "./..."],
                cwd=phase_dir,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                return GateResult(
                    passed=False,
                    gate_type="syntax_check",
                    message="Go syntax check failed",
                    details={
                        "stderr": result.stderr,
                        "files_checked": len(files),
                    },
                )
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            return GateResult(
                passed=False,
                gate_type="syntax_check",
                message=f"Failed to run Go syntax check: {e}",
                details={"error": str(e)},
            )

        return GateResult(
            passed=True,
            gate_type="syntax_check",
            message=f"All {len(files)} Go files have valid syntax",
            details={"files_checked": len(files)},
        )

    def _check_rust_syntax(self, phase_dir: Path) -> GateResult:
        """Check Rust syntax using cargo check."""
        cargo_toml = phase_dir / "Cargo.toml"

        if not cargo_toml.exists():
            files = list(phase_dir.rglob("*.rs"))
            return GateResult(
                passed=True,
                gate_type="syntax_check",
                message="No Cargo.toml found, skipping Rust syntax check",
                details={"files_found": len(files)},
            )

        try:
            result = subprocess.run(
                ["cargo", "check"],
                cwd=phase_dir,
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                return GateResult(
                    passed=False,
                    gate_type="syntax_check",
                    message="Rust syntax check failed",
                    details={"stderr": result.stderr},
                )
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            return GateResult(
                passed=False,
                gate_type="syntax_check",
                message=f"Failed to run Rust syntax check: {e}",
                details={"error": str(e)},
            )

        return GateResult(
            passed=True,
            gate_type="syntax_check",
            message="Rust project compiles successfully",
            details={},
        )

    async def check_tests_pass(self, phase_dir: Path, command: str) -> GateResult:
        """Run tests and check if they pass.

        Args:
            phase_dir: Path to the phase directory.
            command: Test command to run (e.g., "pytest", "npm test").

        Returns:
            GateResult indicating pass/fail with test output.
        """
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=phase_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=300,
            )

            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            if process.returncode != 0:
                return GateResult(
                    passed=False,
                    gate_type="tests_pass",
                    message=f"Tests failed with exit code {process.returncode}",
                    details={
                        "command": command,
                        "exit_code": process.returncode,
                        "stdout": stdout_str[-5000:],
                        "stderr": stderr_str[-2000:],
                    },
                )

            return GateResult(
                passed=True,
                gate_type="tests_pass",
                message="All tests passed",
                details={
                    "command": command,
                    "stdout": stdout_str[-2000:],
                },
            )

        except asyncio.TimeoutError:
            return GateResult(
                passed=False,
                gate_type="tests_pass",
                message="Test command timed out after 300 seconds",
                details={"command": command},
            )
        except Exception as e:
            return GateResult(
                passed=False,
                gate_type="tests_pass",
                message=f"Failed to run tests: {e}",
                details={"command": command, "error": str(e)},
            )

    def check_review_approved(
        self, phase_dir: Path, review_file: str = "review.json"
    ) -> GateResult:
        """Check if a review has been approved.

        Args:
            phase_dir: Path to the phase directory.
            review_file: Name of the review JSON file.

        Returns:
            GateResult indicating if review is approved.
        """
        import json

        review_path = phase_dir / review_file

        if not review_path.exists():
            return GateResult(
                passed=False,
                gate_type="review_approved",
                message=f"Review file not found: {review_file}",
                details={"expected_path": str(review_path)},
            )

        try:
            with open(review_path, "r", encoding="utf-8") as f:
                review_data = json.load(f)
        except json.JSONDecodeError as e:
            return GateResult(
                passed=False,
                gate_type="review_approved",
                message=f"Invalid JSON in review file: {e}",
                details={"file": review_file},
            )

        approved = review_data.get("approved", False)
        reviewer = review_data.get("reviewer", "unknown")

        if not approved:
            return GateResult(
                passed=False,
                gate_type="review_approved",
                message="Review not approved",
                details={
                    "reviewer": reviewer,
                    "comments": review_data.get("comments", []),
                    "status": review_data.get("status", "pending"),
                },
            )

        return GateResult(
            passed=True,
            gate_type="review_approved",
            message=f"Review approved by {reviewer}",
            details={
                "reviewer": reviewer,
                "approved_at": review_data.get("approved_at"),
            },
        )

    async def run_gate(
        self, phase_dir: Path, gate_config: dict[str, Any]
    ) -> GateResult:
        """Run a quality gate based on configuration.

        Args:
            phase_dir: Path to the phase directory.
            gate_config: Gate configuration dictionary.

        Returns:
            GateResult from the appropriate gate check.
        """
        gate_type = gate_config.get("type")

        if gate_type == "files_exist":
            expected = gate_config.get("files", [])
            return self.check_files_exist(phase_dir, expected)

        elif gate_type == "syntax_check":
            language = gate_config.get("language", "python")
            return self.check_syntax(phase_dir, language)

        elif gate_type == "tests_pass":
            command = gate_config.get("command", "pytest")
            return await self.check_tests_pass(phase_dir, command)

        elif gate_type == "review_approved":
            review_file = gate_config.get("file", "review.json")
            return self.check_review_approved(phase_dir, review_file)

        else:
            return GateResult(
                passed=False,
                gate_type=gate_type or "unknown",
                message=f"Unknown gate type: {gate_type}",
                details={"config": gate_config},
            )
