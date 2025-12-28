"""Tests for baseline-based test evaluation module.

Tests the baseline comparison logic for the Evolution Pipeline as defined in ADR-030 Fix 5.
"""

import json
import pytest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, AsyncMock, MagicMock

from helix.evolution.test_baseline import (
    TestBaseline,
    TestEvaluationResult,
    evaluate_against_baseline,
    load_permanent_skips,
    _get_current_commit,
    _parse_pytest_text_output,
)


class TestTestBaseline:
    """Tests for TestBaseline dataclass."""

    def test_default_failed_tests(self):
        """Failed tests defaults to empty set."""
        baseline = TestBaseline(
            timestamp=datetime.now(),
            commit_sha="abc12345",
            total_tests=10,
            passed_tests=10,
        )
        assert baseline.failed_tests == set()

    def test_failure_rate_calculation(self):
        """Failure rate is calculated correctly."""
        baseline = TestBaseline(
            timestamp=datetime.now(),
            commit_sha="abc12345",
            total_tests=100,
            passed_tests=95,
            failed_tests={"test1", "test2", "test3", "test4", "test5"},
        )
        assert baseline.failure_rate == 5.0

    def test_failure_rate_zero_tests(self):
        """Failure rate handles zero tests gracefully."""
        baseline = TestBaseline(
            timestamp=datetime.now(),
            commit_sha="abc12345",
            total_tests=0,
            passed_tests=0,
        )
        assert baseline.failure_rate == 0.0

    def test_to_dict_serialization(self):
        """Baseline can be serialized to dict."""
        timestamp = datetime(2024, 1, 15, 10, 30, 0)
        baseline = TestBaseline(
            timestamp=timestamp,
            commit_sha="abc12345",
            total_tests=50,
            passed_tests=48,
            failed_tests={"tests/test_a.py::test_one", "tests/test_b.py::test_two"},
        )
        data = baseline.to_dict()

        assert data["timestamp"] == "2024-01-15T10:30:00"
        assert data["commit_sha"] == "abc12345"
        assert data["total_tests"] == 50
        assert data["passed_tests"] == 48
        # Failed tests should be sorted for deterministic output
        assert data["failed_tests"] == [
            "tests/test_a.py::test_one",
            "tests/test_b.py::test_two",
        ]

    def test_from_dict_deserialization(self):
        """Baseline can be deserialized from dict."""
        data = {
            "timestamp": "2024-01-15T10:30:00",
            "commit_sha": "abc12345",
            "total_tests": 50,
            "passed_tests": 48,
            "failed_tests": ["tests/test_a.py::test_one", "tests/test_b.py::test_two"],
        }
        baseline = TestBaseline.from_dict(data)

        assert baseline.timestamp == datetime(2024, 1, 15, 10, 30, 0)
        assert baseline.commit_sha == "abc12345"
        assert baseline.total_tests == 50
        assert baseline.passed_tests == 48
        assert baseline.failed_tests == {
            "tests/test_a.py::test_one",
            "tests/test_b.py::test_two",
        }

    def test_save_and_load(self):
        """Baseline can be saved and loaded from file."""
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "baseline.json"
            timestamp = datetime(2024, 1, 15, 10, 30, 0)
            original = TestBaseline(
                timestamp=timestamp,
                commit_sha="abc12345",
                total_tests=50,
                passed_tests=48,
                failed_tests={"tests/test_a.py::test_one"},
            )

            original.save(path)
            loaded = TestBaseline.load(path)

            assert loaded.timestamp == original.timestamp
            assert loaded.commit_sha == original.commit_sha
            assert loaded.total_tests == original.total_tests
            assert loaded.passed_tests == original.passed_tests
            assert loaded.failed_tests == original.failed_tests

    def test_round_trip_serialization(self):
        """Serialization round-trip preserves data."""
        timestamp = datetime(2024, 1, 15, 10, 30, 0)
        original = TestBaseline(
            timestamp=timestamp,
            commit_sha="deadbeef",
            total_tests=100,
            passed_tests=90,
            failed_tests={"test1::a", "test2::b", "test3::c"},
        )

        data = original.to_dict()
        restored = TestBaseline.from_dict(data)

        assert restored.timestamp == original.timestamp
        assert restored.commit_sha == original.commit_sha
        assert restored.total_tests == original.total_tests
        assert restored.passed_tests == original.passed_tests
        assert restored.failed_tests == original.failed_tests


class TestTestEvaluationResult:
    """Tests for TestEvaluationResult dataclass."""

    def test_passed_result_summary(self):
        """Passed result generates correct summary."""
        result = TestEvaluationResult(
            passed=True,
            total_tests=100,
            passed_tests=95,
            pre_existing=["test1", "test2", "test3", "test4", "test5"],
            regressions=[],
            new_test_failures=[],
            blocking_failures=[],
            ignored_failures=["test1", "test2", "test3", "test4", "test5"],
        )
        summary = result.summary
        assert "Tests passed: 95/100" in summary
        assert "5 pre-existing failures ignored" in summary

    def test_passed_result_no_ignored(self):
        """Passed result with no ignored failures."""
        result = TestEvaluationResult(
            passed=True,
            total_tests=100,
            passed_tests=100,
            pre_existing=[],
            regressions=[],
            new_test_failures=[],
            blocking_failures=[],
            ignored_failures=[],
        )
        summary = result.summary
        assert "Tests passed: 100/100" in summary
        assert "ignored" not in summary

    def test_failed_result_summary_regressions(self):
        """Failed result with regressions generates correct summary."""
        result = TestEvaluationResult(
            passed=False,
            total_tests=100,
            passed_tests=98,
            pre_existing=[],
            regressions=["tests/test_foo.py::test_bar"],
            new_test_failures=[],
            blocking_failures=["tests/test_foo.py::test_bar"],
            ignored_failures=[],
        )
        summary = result.summary
        assert "Tests failed: 1 blocking failures" in summary
        assert "Regressions" in summary

    def test_failed_result_summary_new_test_failures(self):
        """Failed result with new test failures generates correct summary."""
        result = TestEvaluationResult(
            passed=False,
            total_tests=100,
            passed_tests=98,
            pre_existing=[],
            regressions=[],
            new_test_failures=["tests/new_test.py::test_new"],
            blocking_failures=["tests/new_test.py::test_new"],
            ignored_failures=[],
        )
        summary = result.summary
        assert "Tests failed: 1 blocking failures" in summary
        assert "New test failures" in summary

    def test_to_dict_serialization(self):
        """Result can be serialized to dict."""
        result = TestEvaluationResult(
            passed=False,
            total_tests=100,
            passed_tests=95,
            pre_existing=["pre1", "pre2"],
            regressions=["reg1"],
            new_test_failures=["new1", "new2"],
            blocking_failures=["reg1", "new1", "new2"],
            ignored_failures=["pre1", "pre2"],
        )
        data = result.to_dict()

        assert data["passed"] is False
        assert data["total_tests"] == 100
        assert data["passed_tests"] == 95
        assert data["pre_existing"] == ["pre1", "pre2"]
        assert data["regressions"] == ["reg1"]
        assert data["new_test_failures"] == ["new1", "new2"]
        assert data["blocking_failures"] == ["reg1", "new1", "new2"]
        assert data["ignored_failures"] == ["pre1", "pre2"]


class TestEvaluateAgainstBaseline:
    """Tests for evaluate_against_baseline function."""

    def test_no_failures_passes(self):
        """No failures results in passed evaluation."""
        baseline = TestBaseline(
            timestamp=datetime.now(),
            commit_sha="abc12345",
            total_tests=100,
            passed_tests=100,
            failed_tests=set(),
        )

        result = evaluate_against_baseline(
            current_failures=set(),
            current_total=100,
            current_passed=100,
            baseline=baseline,
        )

        assert result.passed is True
        assert result.blocking_failures == []
        assert result.ignored_failures == []

    def test_pre_existing_failures_ignored(self):
        """Pre-existing failures are ignored."""
        baseline = TestBaseline(
            timestamp=datetime.now(),
            commit_sha="abc12345",
            total_tests=100,
            passed_tests=95,
            failed_tests={"tests/test_old.py::test_known_failure"},
        )

        result = evaluate_against_baseline(
            current_failures={"tests/test_old.py::test_known_failure"},
            current_total=100,
            current_passed=99,
            baseline=baseline,
        )

        assert result.passed is True
        assert result.pre_existing == ["tests/test_old.py::test_known_failure"]
        assert result.ignored_failures == ["tests/test_old.py::test_known_failure"]
        assert result.regressions == []
        assert result.blocking_failures == []

    def test_regression_blocks(self):
        """Regression (existing test now failing) blocks."""
        baseline = TestBaseline(
            timestamp=datetime.now(),
            commit_sha="abc12345",
            total_tests=100,
            passed_tests=100,
            failed_tests=set(),  # All tests passed in baseline
        )

        result = evaluate_against_baseline(
            current_failures={"tests/test_existing.py::test_was_passing"},
            current_total=100,
            current_passed=99,
            baseline=baseline,
        )

        assert result.passed is False
        assert result.regressions == ["tests/test_existing.py::test_was_passing"]
        assert result.blocking_failures == ["tests/test_existing.py::test_was_passing"]

    def test_new_test_failure_blocks(self):
        """New test failure from ADR blocks."""
        baseline = TestBaseline(
            timestamp=datetime.now(),
            commit_sha="abc12345",
            total_tests=100,
            passed_tests=100,
            failed_tests=set(),
        )

        result = evaluate_against_baseline(
            current_failures={"tests/new_feature/test_new.py::test_foo"},
            current_total=101,
            current_passed=100,
            baseline=baseline,
            adr_test_files=["tests/new_feature/test_new.py"],
        )

        assert result.passed is False
        assert result.new_test_failures == ["tests/new_feature/test_new.py::test_foo"]
        assert result.blocking_failures == ["tests/new_feature/test_new.py::test_foo"]
        assert result.regressions == []

    def test_mixed_failures_categorization(self):
        """Mixed failures are correctly categorized."""
        baseline = TestBaseline(
            timestamp=datetime.now(),
            commit_sha="abc12345",
            total_tests=100,
            passed_tests=98,
            failed_tests={"tests/test_old.py::test_flaky"},  # Pre-existing
        )

        current_failures = {
            "tests/test_old.py::test_flaky",  # Pre-existing
            "tests/test_core.py::test_regression",  # Regression
            "tests/adr_030/test_new.py::test_new_feature",  # New ADR test
        }

        result = evaluate_against_baseline(
            current_failures=current_failures,
            current_total=101,
            current_passed=98,
            baseline=baseline,
            adr_test_files=["tests/adr_030/test_new.py"],
        )

        assert result.passed is False
        assert "tests/test_old.py::test_flaky" in result.pre_existing
        assert "tests/test_core.py::test_regression" in result.regressions
        assert "tests/adr_030/test_new.py::test_new_feature" in result.new_test_failures
        assert len(result.blocking_failures) == 2
        assert len(result.ignored_failures) == 1

    def test_adr_test_file_matching(self):
        """ADR test file matching handles various path formats."""
        baseline = TestBaseline(
            timestamp=datetime.now(),
            commit_sha="abc12345",
            total_tests=100,
            passed_tests=100,
            failed_tests=set(),
        )

        # Test with leading ./ in adr_test_files
        result = evaluate_against_baseline(
            current_failures={"tests/new/test_feature.py::test_a"},
            current_total=101,
            current_passed=100,
            baseline=baseline,
            adr_test_files=["./tests/new/test_feature.py"],
        )

        assert "tests/new/test_feature.py::test_a" in result.new_test_failures

    def test_empty_adr_test_files(self):
        """All new failures are regressions when no ADR test files specified."""
        baseline = TestBaseline(
            timestamp=datetime.now(),
            commit_sha="abc12345",
            total_tests=100,
            passed_tests=100,
            failed_tests=set(),
        )

        result = evaluate_against_baseline(
            current_failures={"tests/test_foo.py::test_bar"},
            current_total=100,
            current_passed=99,
            baseline=baseline,
            adr_test_files=None,
        )

        assert result.regressions == ["tests/test_foo.py::test_bar"]
        assert result.new_test_failures == []

    def test_results_sorted(self):
        """Result lists are sorted for deterministic output."""
        baseline = TestBaseline(
            timestamp=datetime.now(),
            commit_sha="abc12345",
            total_tests=100,
            passed_tests=100,
            failed_tests=set(),
        )

        result = evaluate_against_baseline(
            current_failures={"z_test::a", "a_test::z", "m_test::m"},
            current_total=100,
            current_passed=97,
            baseline=baseline,
        )

        assert result.regressions == ["a_test::z", "m_test::m", "z_test::a"]


class TestParsePytestTextOutput:
    """Tests for pytest text output parsing."""

    def test_parse_summary_line(self):
        """Parse standard pytest summary line."""
        stdout = """
        tests/test_foo.py::test_one PASSED
        tests/test_foo.py::test_two FAILED
        =============== 1 passed, 1 failed in 0.05s ===============
        """
        total, passed, failed = _parse_pytest_text_output(stdout, "")
        assert total == 2
        assert passed == 1
        assert "tests/test_foo.py::test_two" in failed

    def test_parse_failed_pattern(self):
        """Parse FAILED pattern in output."""
        stdout = """
        FAILED tests/test_api.py::test_endpoint
        FAILED tests/test_db.py::test_query
        =============== 0 passed, 2 failed in 1.0s ===============
        """
        total, passed, failed = _parse_pytest_text_output(stdout, "")
        assert len(failed) == 2
        assert "tests/test_api.py::test_endpoint" in failed
        assert "tests/test_db.py::test_query" in failed

    def test_parse_with_errors(self):
        """Parse output with error count."""
        stdout = """
        =============== 5 passed, 2 failed, 1 error in 1.0s ===============
        """
        total, passed, failed_tests = _parse_pytest_text_output(stdout, "")
        assert total == 8  # passed + failed + error
        assert passed == 5

    def test_parse_empty_output(self):
        """Handle empty output gracefully."""
        total, passed, failed = _parse_pytest_text_output("", "")
        assert total == 0
        assert passed == 0
        assert failed == set()

    def test_parse_alternative_failed_pattern(self):
        """Parse alternative FAILED pattern (nodeid FAILED)."""
        stdout = """
        tests/test_foo.py::test_bar FAILED
        =============== 0 passed, 1 failed in 0.1s ===============
        """
        total, passed, failed = _parse_pytest_text_output(stdout, "")
        assert "tests/test_foo.py::test_bar" in failed


class TestGetCurrentCommit:
    """Tests for git commit retrieval."""

    def test_get_commit_in_git_repo(self):
        """Get commit SHA in a git repository."""
        with TemporaryDirectory() as tmpdir:
            # Initialize a git repo
            import subprocess
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "test@test.com"],
                cwd=tmpdir,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test"],
                cwd=tmpdir,
                capture_output=True,
            )
            # Create a commit
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("test")
            subprocess.run(["git", "add", "."], cwd=tmpdir, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "test"],
                cwd=tmpdir,
                capture_output=True,
            )

            commit = _get_current_commit(Path(tmpdir))
            assert len(commit) == 8
            assert commit != "unknown"

    def test_get_commit_not_git_repo(self):
        """Return 'unknown' when not in git repo."""
        with TemporaryDirectory() as tmpdir:
            commit = _get_current_commit(Path(tmpdir))
            assert commit == "unknown"


class TestLoadPermanentSkips:
    """Tests for permanent skip list loading."""

    def test_no_skip_file(self):
        """Return empty set when skip file doesn't exist."""
        with TemporaryDirectory() as tmpdir:
            skips = load_permanent_skips(Path(tmpdir))
            assert skips == set()

    def test_load_yaml_format(self):
        """Load skips from YAML format."""
        with TemporaryDirectory() as tmpdir:
            tests_dir = Path(tmpdir) / "tests"
            tests_dir.mkdir()
            skip_file = tests_dir / ".permanent_skips"
            skip_file.write_text("""
tests/test_flaky.py::test_slow: "Known slow test"
tests/test_external.py::test_api: "Requires external service"
""")
            skips = load_permanent_skips(Path(tmpdir))
            assert "tests/test_flaky.py::test_slow" in skips
            assert "tests/test_external.py::test_api" in skips

    def test_load_simple_format(self):
        """Load skips from simple line-based format."""
        with TemporaryDirectory() as tmpdir:
            tests_dir = Path(tmpdir) / "tests"
            tests_dir.mkdir()
            skip_file = tests_dir / ".permanent_skips"
            skip_file.write_text("""
# Comment line
tests/test_one.py::test_a: reason here
tests/test_two.py::test_b
""")
            skips = load_permanent_skips(Path(tmpdir))
            assert "tests/test_one.py::test_a" in skips
            assert "tests/test_two.py::test_b" in skips

    def test_ignore_invalid_lines(self):
        """Invalid lines are ignored."""
        with TemporaryDirectory() as tmpdir:
            tests_dir = Path(tmpdir) / "tests"
            tests_dir.mkdir()
            skip_file = tests_dir / ".permanent_skips"
            skip_file.write_text("""
# This is a comment
just some text without ::
tests/test_valid.py::test_ok

""")
            skips = load_permanent_skips(Path(tmpdir))
            # Only valid nodeid should be loaded
            assert "tests/test_valid.py::test_ok" in skips
            assert len(skips) == 1


class TestIntegrationScenarios:
    """Integration tests based on real-world scenarios from ADR-030."""

    def test_adr_020_scenario_preexisting_only(self):
        """
        ADR-020 scenario from ADR-030:
        510 passed, 1 failed - but the failure is a pre-existing StrEnum issue.
        Pipeline should PASS.
        """
        baseline = TestBaseline(
            timestamp=datetime.now(),
            commit_sha="61d0428",
            total_tests=453,
            passed_tests=450,
            failed_tests={
                "tests/legacy/test_old_export.py::test_deprecated",
                "tests/integration/test_external.py::test_flaky",
                "tests/docs/test_reverse_index.py::test_file_status_string_enum",
            },
        )

        # After ADR-020 changes - same failures still present
        result = evaluate_against_baseline(
            current_failures={
                "tests/legacy/test_old_export.py::test_deprecated",
                "tests/integration/test_external.py::test_flaky",
                "tests/docs/test_reverse_index.py::test_file_status_string_enum",
            },
            current_total=511,
            current_passed=508,
            baseline=baseline,
            adr_test_files=["tests/docs/test_skill_selector.py"],
        )

        assert result.passed is True
        assert len(result.ignored_failures) == 3
        assert "pre-existing failures ignored" in result.summary

    def test_adr_020_scenario_new_regression(self):
        """
        ADR-020 variant: The failure is a NEW regression (not pre-existing).
        Pipeline should FAIL.
        """
        baseline = TestBaseline(
            timestamp=datetime.now(),
            commit_sha="61d0428",
            total_tests=453,
            passed_tests=453,
            failed_tests=set(),  # No pre-existing failures
        )

        # New failure that wasn't in baseline
        result = evaluate_against_baseline(
            current_failures={
                "tests/docs/test_skill_selector.py::test_edge_case",
            },
            current_total=511,
            current_passed=510,
            baseline=baseline,
            adr_test_files=["tests/docs/test_skill_selector.py"],
        )

        assert result.passed is False
        assert len(result.new_test_failures) == 1
        assert "blocking" in result.summary.lower()

    def test_partial_fix_of_preexisting(self):
        """
        Scenario: Some pre-existing failures are fixed, some remain.
        The fixed ones should not affect the result.
        """
        baseline = TestBaseline(
            timestamp=datetime.now(),
            commit_sha="abc12345",
            total_tests=100,
            passed_tests=95,
            failed_tests={
                "tests/a.py::test_1",
                "tests/b.py::test_2",
                "tests/c.py::test_3",
                "tests/d.py::test_4",
                "tests/e.py::test_5",
            },
        )

        # Only 2 of 5 remain - 3 were fixed
        result = evaluate_against_baseline(
            current_failures={
                "tests/a.py::test_1",
                "tests/b.py::test_2",
            },
            current_total=100,
            current_passed=98,
            baseline=baseline,
        )

        assert result.passed is True
        assert len(result.pre_existing) == 2
        assert len(result.ignored_failures) == 2

    def test_all_preexisting_fixed(self):
        """
        Scenario: All pre-existing failures are now fixed.
        Should pass with no ignored failures.
        """
        baseline = TestBaseline(
            timestamp=datetime.now(),
            commit_sha="abc12345",
            total_tests=100,
            passed_tests=95,
            failed_tests={
                "tests/a.py::test_1",
                "tests/b.py::test_2",
            },
        )

        # All failures fixed
        result = evaluate_against_baseline(
            current_failures=set(),
            current_total=100,
            current_passed=100,
            baseline=baseline,
        )

        assert result.passed is True
        assert len(result.pre_existing) == 0
        assert len(result.ignored_failures) == 0

    def test_new_tests_added_all_pass(self):
        """
        Scenario: New tests are added and they all pass.
        Should pass.
        """
        baseline = TestBaseline(
            timestamp=datetime.now(),
            commit_sha="abc12345",
            total_tests=100,
            passed_tests=100,
            failed_tests=set(),
        )

        # 10 new tests added, all pass
        result = evaluate_against_baseline(
            current_failures=set(),
            current_total=110,
            current_passed=110,
            baseline=baseline,
            adr_test_files=["tests/new_feature/test_feature.py"],
        )

        assert result.passed is True
        assert len(result.blocking_failures) == 0

    def test_multiple_regressions(self):
        """
        Scenario: Multiple regressions introduced.
        All should be reported.
        """
        baseline = TestBaseline(
            timestamp=datetime.now(),
            commit_sha="abc12345",
            total_tests=100,
            passed_tests=100,
            failed_tests=set(),
        )

        result = evaluate_against_baseline(
            current_failures={
                "tests/core/test_a.py::test_1",
                "tests/core/test_b.py::test_2",
                "tests/utils/test_c.py::test_3",
            },
            current_total=100,
            current_passed=97,
            baseline=baseline,
        )

        assert result.passed is False
        assert len(result.regressions) == 3
        assert len(result.blocking_failures) == 3
