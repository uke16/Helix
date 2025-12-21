import pytest

from helix.spec_validator import SpecValidator


class TestSpecValidator:
    """Tests for SpecValidator."""

    def test_valid_spec(self, sample_spec):
        """Should validate correct spec."""
        validator = SpecValidator()
        result = validator.validate(sample_spec)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_missing_meta_id(self, sample_spec):
        """Should fail if meta.id missing."""
        del sample_spec["meta"]["id"]

        validator = SpecValidator()
        result = validator.validate(sample_spec)

        assert not result.is_valid
        assert any("id" in str(e).lower() for e in result.errors)

    def test_missing_implementation(self, sample_spec):
        """Should fail if implementation missing."""
        del sample_spec["implementation"]

        validator = SpecValidator()
        result = validator.validate(sample_spec)

        assert not result.is_valid

    def test_validate_from_file(self, sample_project):
        """Should validate spec from file."""
        validator = SpecValidator()
        result = validator.validate_file(sample_project / "spec.yaml")

        assert result.is_valid
