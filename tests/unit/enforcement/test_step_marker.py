"""
Tests for StepMarkerValidator.

Tests validation of STEP markers and fallback heuristics.
"""

import pytest

from helix.enforcement.validators.step_marker import (
    StepMarkerValidator,
    extract_step,
)


class TestStepMarkerValidator:
    """Tests for StepMarkerValidator."""

    @pytest.fixture
    def validator(self):
        """Create a StepMarkerValidator instance."""
        return StepMarkerValidator()

    # === Valid Step Marker Tests ===

    @pytest.mark.parametrize(
        "step",
        ["what", "why", "constraints", "generate", "finalize", "done"],
    )
    def test_valid_step_marker(self, validator, step):
        """Valid step markers should not produce issues."""
        response = f"Some response content\n\n<!-- STEP: {step} -->"
        issues = validator.validate(response, {})
        assert len(issues) == 0

    def test_step_marker_case_insensitive(self, validator):
        """Step names should be case insensitive."""
        response = "Content\n<!-- STEP: GENERATE -->"
        issues = validator.validate(response, {})
        # The regex captures the actual case, validation lowercases it
        assert len(issues) == 0

    def test_step_marker_with_extra_whitespace(self, validator):
        """Step markers should allow extra whitespace."""
        response = "Content\n<!--   STEP:   done   -->"
        issues = validator.validate(response, {})
        assert len(issues) == 0

    def test_step_marker_in_middle_of_response(self, validator):
        """Step marker can be anywhere in the response."""
        response = "Start\n<!-- STEP: what -->\nMore content"
        issues = validator.validate(response, {})
        assert len(issues) == 0

    # === Missing Step Marker Tests ===

    def test_missing_step_marker(self, validator):
        """Missing step marker should produce an error."""
        response = "Response without any marker"
        issues = validator.validate(response, {})

        assert len(issues) == 1
        assert issues[0].code == "MISSING_STEP_MARKER"
        assert issues[0].severity == "error"

    def test_empty_response(self, validator):
        """Empty response should produce missing marker error."""
        issues = validator.validate("", {})
        assert len(issues) == 1
        assert issues[0].code == "MISSING_STEP_MARKER"

    def test_similar_but_invalid_marker(self, validator):
        """Similar but invalid markers should not match."""
        # Missing STEP:
        response = "Content <!-- what -->"
        issues = validator.validate(response, {})
        assert issues[0].code == "MISSING_STEP_MARKER"

        # Wrong format
        response = "Content [STEP: what]"
        issues = validator.validate(response, {})
        assert issues[0].code == "MISSING_STEP_MARKER"

    # === Invalid Step Tests ===

    def test_invalid_step_name(self, validator):
        """Invalid step names should produce an error."""
        response = "Content\n<!-- STEP: invalid_step -->"
        issues = validator.validate(response, {})

        assert len(issues) == 1
        assert issues[0].code == "INVALID_STEP"
        assert "invalid_step" in issues[0].message

    def test_typo_in_step_name(self, validator):
        """Typos in step names should produce an error."""
        response = "Content\n<!-- STEP: generat -->"  # Missing 'e'
        issues = validator.validate(response, {})
        assert issues[0].code == "INVALID_STEP"

    # === Fallback Tests ===

    def test_fallback_adds_step_marker(self, validator):
        """Fallback should add a step marker to response."""
        response = "Response without marker"
        result = validator.apply_fallback(response, {})

        assert result is not None
        assert "<!-- STEP:" in result
        # Should end with the marker
        assert result.endswith("-->")

    def test_fallback_infers_generate_from_adr(self, validator):
        """Fallback should infer 'generate' when ADR is being created."""
        response = """Hier ist das ADR:

```yaml
---
adr_id: "042"
title: Test ADR
---
```

Das ADR wurde erstellt."""

        result = validator.apply_fallback(response, {})
        assert "<!-- STEP: generate -->" in result

    def test_fallback_infers_finalize(self, validator):
        """Fallback should infer 'finalize' when ADR is finalized."""
        response = "Das ADR-042 wurde finalisiert und gespeichert."
        result = validator.apply_fallback(response, {})
        assert "<!-- STEP: finalize -->" in result

    def test_fallback_infers_what_from_questions(self, validator):
        """Fallback should infer 'what' when response contains questions."""
        response = "Ich verstehe. Könntest du mir mehr über die Anforderungen sagen?"
        result = validator.apply_fallback(response, {})
        assert "<!-- STEP: what -->" in result

    def test_fallback_infers_constraints(self, validator):
        """Fallback should infer 'constraints' from constraint keywords."""
        response = "Die Rahmenbedingungen sind wie folgt: ..."
        result = validator.apply_fallback(response, {})
        assert "<!-- STEP: constraints -->" in result

    def test_fallback_infers_why(self, validator):
        """Fallback should infer 'why' from motivation keywords."""
        response = "Der Hintergrund für diese Entscheidung ist..."
        result = validator.apply_fallback(response, {})
        assert "<!-- STEP: why -->" in result

    def test_fallback_defaults_to_done(self, validator):
        """Fallback should default to 'done' for generic responses."""
        response = "Hier ist die Zusammenfassung der Diskussion."
        result = validator.apply_fallback(response, {})
        assert "<!-- STEP: done -->" in result

    def test_fallback_preserves_response_content(self, validator):
        """Fallback should preserve original response content."""
        response = "Original content here"
        result = validator.apply_fallback(response, {})
        assert "Original content here" in result

    def test_fallback_does_not_duplicate_marker(self, validator):
        """Fallback should not add marker if one exists."""
        response = "Content\n<!-- STEP: done -->"
        result = validator.apply_fallback(response, {})
        # Should return unchanged
        assert result == response


class TestExtractStep:
    """Tests for extract_step utility function."""

    def test_extract_step_found(self):
        """Should extract step name when present."""
        response = "Content\n<!-- STEP: generate -->"
        step = extract_step(response)
        assert step == "generate"

    def test_extract_step_not_found(self):
        """Should return None when no step marker."""
        response = "Content without marker"
        step = extract_step(response)
        assert step is None

    def test_extract_step_case_normalized(self):
        """Should return lowercase step name."""
        response = "Content\n<!-- STEP: GENERATE -->"
        step = extract_step(response)
        assert step == "generate"


class TestValidatorProperties:
    """Tests for validator metadata."""

    def test_validator_name(self):
        """Validator should have correct name."""
        validator = StepMarkerValidator()
        assert validator.name == "step_marker"

    def test_validator_repr(self):
        """Validator should have readable repr."""
        validator = StepMarkerValidator()
        assert "StepMarkerValidator" in repr(validator)
        assert "step_marker" in repr(validator)
