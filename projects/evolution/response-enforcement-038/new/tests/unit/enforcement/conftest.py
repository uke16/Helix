"""
Fixtures for enforcement tests.

Provides mock runners and sample responses for testing.
"""

import pytest
from dataclasses import dataclass
from typing import Optional
from unittest.mock import AsyncMock, MagicMock

from helix.enforcement.validators.base import ResponseValidator, ValidationIssue


@dataclass
class MockRunResult:
    """Mock result from a runner execution."""

    stdout: str
    stderr: str = ""
    exit_code: int = 0
    success: bool = True


class MockValidator(ResponseValidator):
    """Configurable mock validator for testing."""

    def __init__(
        self,
        name: str = "mock_validator",
        issues: Optional[list[ValidationIssue]] = None,
        fallback_result: Optional[str] = None,
    ):
        self._name = name
        self._issues = issues or []
        self._fallback_result = fallback_result
        self.validate_call_count = 0
        self.fallback_call_count = 0

    @property
    def name(self) -> str:
        return self._name

    def validate(self, response: str, context: dict) -> list[ValidationIssue]:
        self.validate_call_count += 1
        # If this response is the fallback result, return no issues
        if self._fallback_result and response == self._fallback_result:
            return []
        return self._issues.copy()

    def apply_fallback(self, response: str, context: dict) -> Optional[str]:
        self.fallback_call_count += 1
        return self._fallback_result


@pytest.fixture
def mock_runner():
    """Create a mock runner that simulates ClaudeRunner."""
    runner = MagicMock()
    runner.run_session = AsyncMock()
    runner.continue_session = AsyncMock()
    return runner


@pytest.fixture
def success_runner(mock_runner):
    """Runner that always returns valid response."""
    mock_runner.run_session.return_value = MockRunResult(
        stdout="Valid response\n<!-- STEP: done -->"
    )
    return mock_runner


@pytest.fixture
def failing_then_success_runner(mock_runner):
    """Runner that fails first, then succeeds on retry."""
    mock_runner.run_session.return_value = MockRunResult(
        stdout="Response without marker"
    )
    mock_runner.continue_session.return_value = MockRunResult(
        stdout="Fixed response\n<!-- STEP: done -->"
    )
    return mock_runner


@pytest.fixture
def always_failing_runner(mock_runner):
    """Runner that always returns invalid response."""
    mock_runner.run_session.return_value = MockRunResult(
        stdout="Invalid response"
    )
    mock_runner.continue_session.return_value = MockRunResult(
        stdout="Still invalid"
    )
    return mock_runner


@pytest.fixture
def passing_validator():
    """Validator that always passes."""
    return MockValidator(name="passing", issues=[])


@pytest.fixture
def failing_validator():
    """Validator that always fails."""
    return MockValidator(
        name="failing",
        issues=[
            ValidationIssue(
                code="TEST_ERROR",
                message="Test error message",
                fix_hint="Fix the test error",
            )
        ],
    )


@pytest.fixture
def failing_with_fallback_validator():
    """Validator that fails but has a fallback."""
    return MockValidator(
        name="failing_with_fallback",
        issues=[
            ValidationIssue(
                code="FIXABLE_ERROR",
                message="Fixable error",
                fix_hint="Can be fixed",
            )
        ],
        fallback_result="Fixed by fallback\n<!-- STEP: done -->",
    )


@pytest.fixture
def sample_valid_response():
    """Sample valid response with step marker."""
    return "This is a valid response.\n\n<!-- STEP: done -->"


@pytest.fixture
def sample_invalid_response():
    """Sample invalid response without step marker."""
    return "This is an invalid response without a marker."


@pytest.fixture
def sample_adr_response():
    """Sample valid ADR response."""
    return '''---
adr_id: "042"
title: Test ADR
status: Proposed

files:
  create:
    - src/new_file.py
  modify: []
---

# ADR-042: Test ADR

## Kontext

This is the context.

## Entscheidung

This is the decision.

## Implementation

Implementation details.

## Akzeptanzkriterien

- [ ] First criterion
- [ ] Second criterion
- [ ] Third criterion

## Konsequenzen

The consequences.

<!-- STEP: generate -->'''
