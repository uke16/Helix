"""Baseline-based test evaluation for Evolution Pipeline.

This module implements diff-based test evaluation for the Evolution Pipeline.
Instead of failing on ANY test failure, it compares current failures against
a baseline captured before changes were made.

The key concept:
- Baseline: Test state BEFORE pipeline runs (on main branch)
- Current: Test state AFTER changes are applied
- Diff analysis categorizes failures as:
  - Pre-existing: Already failed in baseline → IGNORED
  - Regression: Existing test newly broken → BLOCKING
  - New test failure: New test from ADR fails → BLOCKING

This allows the pipeline to proceed when only pre-existing failures exist,
while still blocking on actual regressions introduced by the changes.

See ADR-030 for full rationale and design.
"""

import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class TestBaseline:
    """Snapshot of test results before changes.

    Captured at the START of pipeline execution, before any phases run.
    Used as reference to distinguish pre-existing failures from regressions.

    Attributes:
        timestamp: When the baseline was captured
        commit_sha: Git commit SHA (short form) of the baseline
        total_tests: Total number of tests discovered
        passed_tests: Number of tests that passed
        failed_tests: Set of test nodeids that failed (e.g., "tests/test_foo.py::test_bar")
    """

    timestamp: datetime
    commit_sha: str
    total_tests: int
    passed_tests: int
    failed_tests: set[str] = field(default_factory=set)

    def to_dict(self) -> dict:
        """Serialize baseline to dictionary for JSON storage."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "commit_sha": self.commit_sha,
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": sorted(self.failed_tests),  # Sorted for deterministic output
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TestBaseline":
        """Deserialize baseline from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            commit_sha=data["commit_sha"],
            total_tests=data["total_tests"],
            passed_tests=data["passed_tests"],
            failed_tests=set(data["failed_tests"]),
        )

    def save(self, path: Path) -> None:
        """Save baseline to JSON file."""
        path.write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: Path) -> "TestBaseline":
        """Load baseline from JSON file."""
        return cls.from_dict(json.loads(path.read_text()))

    @property
    def failure_rate(self) -> float:
        """Calculate failure rate as percentage."""
        if self.total_tests == 0:
            return 0.0
        return len(self.failed_tests) / self.total_tests * 100


@dataclass
class TestEvaluationResult:
    """Result of baseline comparison.

    Categorizes test failures into:
    - pre_existing: Failures that were already in baseline (OK to ignore)
    - regressions: Existing tests that newly fail (BLOCKING)
    - new_test_failures: New tests (from ADR) that fail (BLOCKING)

    Attributes:
        passed: Whether the evaluation passes (no blocking failures)
        total_tests: Total tests in current run
        passed_tests: Passed tests in current run
        pre_existing: Test nodeids that were already failing in baseline
        regressions: Test nodeids that are newly broken (were passing)
        new_test_failures: Test nodeids from new ADR tests that fail
        blocking_failures: Combined regressions + new_test_failures
        ignored_failures: Same as pre_existing (failures we ignore)
    """

    passed: bool
    total_tests: int
    passed_tests: int

    # Categorized failures
    pre_existing: list[str] = field(default_factory=list)
    regressions: list[str] = field(default_factory=list)
    new_test_failures: list[str] = field(default_factory=list)

    # Summary lists
    blocking_failures: list[str] = field(default_factory=list)
    ignored_failures: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        """Generate human-readable summary."""
        if self.passed:
            ignored = len(self.ignored_failures)
            suffix = f" ({ignored} pre-existing failures ignored)" if ignored else ""
            return f"✅ Tests passed: {self.passed_tests}/{self.total_tests}{suffix}"
        else:
            lines = [
                f"❌ Tests failed: {len(self.blocking_failures)} blocking failures",
            ]
            if self.regressions:
                lines.append(f"   Regressions: {self.regressions}")
            if self.new_test_failures:
                lines.append(f"   New test failures: {self.new_test_failures}")
            return "\n".join(lines)

    def to_dict(self) -> dict:
        """Serialize result to dictionary."""
        return {
            "passed": self.passed,
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "pre_existing": self.pre_existing,
            "regressions": self.regressions,
            "new_test_failures": self.new_test_failures,
            "blocking_failures": self.blocking_failures,
            "ignored_failures": self.ignored_failures,
        }


def _get_current_commit(project_root: Path) -> str:
    """Get current git commit SHA (short form).

    Args:
        project_root: Path to the git repository

    Returns:
        8-character commit SHA, or "unknown" if not a git repo
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()[:8]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return "unknown"


def _parse_pytest_text_output(stdout: str, stderr: str) -> tuple[int, int, set[str]]:
    """Parse pytest text output when JSON report is not available.

    Args:
        stdout: Standard output from pytest
        stderr: Standard error from pytest

    Returns:
        Tuple of (total_tests, passed_tests, failed_test_nodeids)
    """
    output = stdout + "\n" + stderr

    # Try to extract summary line like "X passed, Y failed"
    passed = 0
    failed = 0

    # Match patterns like "510 passed", "3 failed", "2 errors"
    passed_match = re.search(r"(\d+) passed", output)
    failed_match = re.search(r"(\d+) failed", output)
    error_match = re.search(r"(\d+) error", output)

    if passed_match:
        passed = int(passed_match.group(1))
    if failed_match:
        failed = int(failed_match.group(1))
    if error_match:
        failed += int(error_match.group(1))

    total = passed + failed

    # Extract failed test nodeids from output
    # Pattern: "FAILED tests/path/test_file.py::test_name"
    failed_tests: set[str] = set()
    for match in re.finditer(r"FAILED\s+([\w/._:-]+::\w+)", output):
        failed_tests.add(match.group(1))

    # Also try "::test_name FAILED" pattern
    for match in re.finditer(r"([\w/._:-]+::\w+)\s+FAILED", output):
        failed_tests.add(match.group(1))

    return total, passed, failed_tests


async def capture_baseline(
    project_root: Path,
    test_path: Optional[Path] = None,
) -> TestBaseline:
    """Capture test baseline from current state (before changes).

    Called at the START of pipeline execution, before any phases run.
    Uses pytest JSON output for reliable parsing when available.

    Args:
        project_root: Path to the project root (where tests/ is located)
        test_path: Optional specific test path to run

    Returns:
        TestBaseline snapshot of current test state
    """
    import asyncio

    # Build pytest command
    # Try to use pytest-json-report if available
    test_target = str(test_path) if test_path else "tests/"

    cmd = [
        "python3", "-m", "pytest",
        test_target,
        "-q",  # Quiet output for faster execution
        "--tb=no",  # No tracebacks for speed
    ]

    # Try with JSON report first
    json_cmd = cmd + ["--json-report", "--json-report-file=-"]

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{project_root}/src:{env.get('PYTHONPATH', '')}"

    process = await asyncio.create_subprocess_exec(
        *json_cmd,
        cwd=project_root,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    stdout, stderr = await asyncio.wait_for(
        process.communicate(),
        timeout=300,  # 5 minute timeout for tests
    )

    stdout_str = stdout.decode() if stdout else ""
    stderr_str = stderr.decode() if stderr else ""

    # Try to parse JSON report
    try:
        report = json.loads(stdout_str)

        failed = {
            test["nodeid"]
            for test in report.get("tests", [])
            if test.get("outcome") == "failed"
        }

        summary = report.get("summary", {})
        total = summary.get("total", 0)
        passed = summary.get("passed", 0)

    except (json.JSONDecodeError, KeyError):
        # Fallback: run pytest without JSON and parse text output
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=project_root,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=300,
        )

        stdout_str = stdout.decode() if stdout else ""
        stderr_str = stderr.decode() if stderr else ""

        total, passed, failed = _parse_pytest_text_output(stdout_str, stderr_str)

    return TestBaseline(
        timestamp=datetime.now(),
        commit_sha=_get_current_commit(project_root),
        total_tests=total,
        passed_tests=passed,
        failed_tests=failed,
    )


def capture_baseline_sync(
    project_root: Path,
    test_path: Optional[Path] = None,
) -> TestBaseline:
    """Synchronous version of capture_baseline for non-async contexts.

    Args:
        project_root: Path to the project root
        test_path: Optional specific test path to run

    Returns:
        TestBaseline snapshot of current test state
    """
    import asyncio
    return asyncio.run(capture_baseline(project_root, test_path))


def evaluate_against_baseline(
    current_failures: set[str],
    current_total: int,
    current_passed: int,
    baseline: TestBaseline,
    adr_test_files: Optional[list[str]] = None,
) -> TestEvaluationResult:
    """Compare current test results against baseline.

    Categorizes failures into:
    - Pre-existing: Already in baseline (ignored, not blocking)
    - Regression: Newly broken existing tests (blocking)
    - New test failure: Tests from ADR that fail (blocking)

    Args:
        current_failures: Set of failed test nodeids from current run
        current_total: Total tests in current run
        current_passed: Passed tests in current run
        baseline: Baseline captured before changes
        adr_test_files: Test files created by this ADR (from files.create)
                       Used to identify which failing tests are "new"

    Returns:
        TestEvaluationResult with categorized failures
    """
    adr_test_files = adr_test_files or []

    # Pre-existing: failures that were already in baseline
    pre_existing = current_failures & baseline.failed_tests

    # New failures: not in baseline
    new_failures = current_failures - baseline.failed_tests

    # Split new failures: from ADR tests vs regressions in existing tests
    new_test_failures: list[str] = []
    regressions: list[str] = []

    for failure in new_failures:
        # Extract test file from nodeid (e.g., "tests/foo/test_bar.py::test_baz" -> "tests/foo/test_bar.py")
        test_file = failure.split("::")[0]

        # Check if this test file was created by the ADR
        is_adr_test = any(
            test_file.endswith(adr_file.lstrip("./"))
            for adr_file in adr_test_files
        )

        if is_adr_test:
            new_test_failures.append(failure)
        else:
            regressions.append(failure)

    # Blocking = regressions + new test failures
    blocking = regressions + new_test_failures

    return TestEvaluationResult(
        passed=len(blocking) == 0,
        total_tests=current_total,
        passed_tests=current_passed,
        pre_existing=sorted(pre_existing),
        regressions=sorted(regressions),
        new_test_failures=sorted(new_test_failures),
        blocking_failures=sorted(blocking),
        ignored_failures=sorted(pre_existing),
    )


def load_permanent_skips(project_root: Path) -> set[str]:
    """Load permanent skip list from tests/.permanent_skips.

    These tests are ALWAYS ignored, regardless of baseline.
    Use sparingly - prefer automatic baseline detection.

    Supports two formats:
    1. YAML dictionary: {nodeid: reason, ...}
    2. Simple line-based: one nodeid per line (with optional ": reason")

    Args:
        project_root: Path to the project root

    Returns:
        Set of test nodeids to always skip
    """
    skip_file = project_root / "tests" / ".permanent_skips"

    if not skip_file.exists():
        return set()

    content = skip_file.read_text()
    skips: set[str] = set()

    # Try YAML format first
    try:
        import yaml
        data = yaml.safe_load(content)
        if isinstance(data, dict):
            return set(data.keys())
    except Exception:
        pass

    # Fallback: simple line-based format
    for line in content.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            # Handle "nodeid: reason" format - split only on first ": "
            if ": " in line:
                nodeid = line.split(": ", 1)[0].strip()
            else:
                nodeid = line.strip()
            if "::" in nodeid:  # Valid nodeid contains ::
                skips.add(nodeid)

    return skips
