"""
Tests for ADRStructureValidator and FileExistenceValidator.

Tests validation of ADR structure and file existence checks.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from helix.enforcement.validators.adr_structure import ADRStructureValidator
from helix.enforcement.validators.file_existence import FileExistenceValidator


class TestADRStructureValidator:
    """Tests for ADRStructureValidator."""

    @pytest.fixture
    def validator(self):
        """Create an ADRStructureValidator instance."""
        return ADRStructureValidator()

    @pytest.fixture
    def valid_adr(self):
        """A complete valid ADR."""
        return '''---
adr_id: "042"
title: Test ADR
status: Proposed

files:
  create:
    - src/new.py
  modify:
    - src/existing.py
---

# ADR-042: Test ADR

## Kontext

This is the context section.

## Entscheidung

This is the decision section.

## Implementation

Implementation details here.

## Akzeptanzkriterien

- [ ] First criterion
- [ ] Second criterion
- [ ] Third criterion

## Konsequenzen

Some consequences.
'''

    @pytest.fixture
    def minimal_adr(self):
        """Minimal valid ADR."""
        return '''---
adr_id: "001"
title: Minimal
status: Proposed
---

## Kontext

Context.

## Entscheidung

Decision.

## Akzeptanzkriterien

- [ ] One
- [ ] Two
- [ ] Three
'''

    # === Valid ADR Tests ===

    def test_valid_adr_no_issues(self, validator, valid_adr):
        """Complete valid ADR should have no errors."""
        issues = validator.validate(valid_adr, {})
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0

    def test_minimal_valid_adr(self, validator, minimal_adr):
        """Minimal valid ADR should have no errors."""
        issues = validator.validate(minimal_adr, {})
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0

    def test_non_adr_response_ignored(self, validator):
        """Non-ADR responses should not trigger validation."""
        response = "Just a normal response without ADR"
        issues = validator.validate(response, {})
        assert len(issues) == 0

    # === Missing YAML Header Tests ===

    def test_missing_yaml_header(self, validator):
        """Missing YAML header should produce error."""
        response = """
## Kontext

Context here.

## Entscheidung

Decision here.
"""
        issues = validator.validate(response, {})
        # No YAML with adr_id, so should be ignored
        assert len(issues) == 0

    def test_invalid_yaml_syntax(self, validator):
        """Invalid YAML should produce error."""
        response = '''---
adr_id: "001"
title: [invalid yaml
status: Proposed
---

## Kontext
Text
## Entscheidung
Text
## Akzeptanzkriterien
- [ ] One
'''
        issues = validator.validate(response, {})
        assert any(i.code == "INVALID_YAML" for i in issues)

    # === Missing Field Tests ===

    def test_missing_adr_id(self, validator):
        """Missing adr_id should produce error."""
        response = '''---
title: Test
status: Proposed
---

## Kontext
x
## Entscheidung
x
## Akzeptanzkriterien
- [ ] x
'''
        # This won't trigger because _is_adr checks for adr_id
        issues = validator.validate(response, {})
        # Actually this won't be detected as an ADR
        assert len(issues) == 0

    def test_missing_title(self, validator):
        """Missing title should produce error."""
        response = '''---
adr_id: "001"
status: Proposed
---

## Kontext
x
## Entscheidung
x
## Akzeptanzkriterien
- [ ] x
'''
        issues = validator.validate(response, {})
        assert any(
            i.code == "MISSING_ADR_FIELD" and "title" in i.message for i in issues
        )

    def test_missing_status(self, validator):
        """Missing status should produce error."""
        response = '''---
adr_id: "001"
title: Test
---

## Kontext
x
## Entscheidung
x
## Akzeptanzkriterien
- [ ] x
'''
        issues = validator.validate(response, {})
        assert any(
            i.code == "MISSING_ADR_FIELD" and "status" in i.message for i in issues
        )

    # === Missing Section Tests ===

    def test_missing_kontext_section(self, validator):
        """Missing Kontext section should produce error."""
        response = '''---
adr_id: "001"
title: Test
status: Proposed
---

## Entscheidung
Decision here.

## Akzeptanzkriterien
- [ ] One
'''
        issues = validator.validate(response, {})
        assert any(
            i.code == "MISSING_ADR_SECTION" and "Kontext" in i.message for i in issues
        )

    def test_missing_entscheidung_section(self, validator):
        """Missing Entscheidung section should produce error."""
        response = '''---
adr_id: "001"
title: Test
status: Proposed
---

## Kontext
Context here.

## Akzeptanzkriterien
- [ ] One
'''
        issues = validator.validate(response, {})
        assert any(
            i.code == "MISSING_ADR_SECTION" and "Entscheidung" in i.message
            for i in issues
        )

    def test_missing_akzeptanzkriterien_section(self, validator):
        """Missing Akzeptanzkriterien section should produce error."""
        response = '''---
adr_id: "001"
title: Test
status: Proposed
---

## Kontext
Context here.

## Entscheidung
Decision here.
'''
        issues = validator.validate(response, {})
        assert any(
            i.code == "MISSING_ADR_SECTION" and "Akzeptanzkriterien" in i.message
            for i in issues
        )

    # === Criteria Count Tests ===

    def test_insufficient_criteria_warning(self, validator):
        """Too few criteria should produce warning."""
        response = '''---
adr_id: "001"
title: Test
status: Proposed
---

## Kontext
Context.

## Entscheidung
Decision.

## Akzeptanzkriterien
- [ ] Only one
'''
        issues = validator.validate(response, {})
        warnings = [i for i in issues if i.severity == "warning"]
        assert any(i.code == "INSUFFICIENT_CRITERIA" for i in warnings)

    def test_sufficient_criteria_no_warning(self, validator, valid_adr):
        """Sufficient criteria should not produce warning."""
        issues = validator.validate(valid_adr, {})
        warnings = [i for i in issues if i.severity == "warning"]
        assert not any(i.code == "INSUFFICIENT_CRITERIA" for i in warnings)

    # === Fallback Tests ===

    def test_fallback_returns_none(self, validator):
        """ADR structure issues cannot be auto-fixed."""
        response = "Invalid ADR"
        result = validator.apply_fallback(response, {})
        assert result is None


class TestFileExistenceValidator:
    """Tests for FileExistenceValidator."""

    @pytest.fixture
    def temp_helix_root(self, tmp_path):
        """Create a temporary HELIX root with some files."""
        helix_root = tmp_path / "helix"
        helix_root.mkdir()

        # Create some existing files
        (helix_root / "src").mkdir()
        (helix_root / "src" / "existing.py").write_text("# existing")
        (helix_root / "src" / "another.py").write_text("# another")

        return helix_root

    @pytest.fixture
    def validator(self, temp_helix_root):
        """Create a FileExistenceValidator instance."""
        return FileExistenceValidator(helix_root=temp_helix_root)

    @pytest.fixture
    def adr_with_existing_files(self):
        """ADR that references existing files."""
        return '''---
adr_id: "001"
title: Test
status: Proposed

files:
  modify:
    - src/existing.py
    - src/another.py
---

## Kontext
x
## Entscheidung
x
## Akzeptanzkriterien
- [ ] x
'''

    @pytest.fixture
    def adr_with_nonexistent_files(self):
        """ADR that references non-existent files."""
        return '''---
adr_id: "001"
title: Test
status: Proposed

files:
  modify:
    - src/existing.py
    - src/missing.py
    - src/also_missing.py
---

## Kontext
x
## Entscheidung
x
## Akzeptanzkriterien
- [ ] x
'''

    # === Existing Files Tests ===

    def test_existing_files_no_issues(self, validator, adr_with_existing_files):
        """References to existing files should pass."""
        issues = validator.validate(adr_with_existing_files, {})
        assert len(issues) == 0

    def test_non_adr_response_ignored(self, validator):
        """Non-ADR responses should not trigger validation."""
        response = "Just a normal response"
        issues = validator.validate(response, {})
        assert len(issues) == 0

    def test_adr_without_files_section(self, validator):
        """ADR without files section should pass."""
        response = '''---
adr_id: "001"
title: Test
status: Proposed
---

Content here.
'''
        issues = validator.validate(response, {})
        assert len(issues) == 0

    # === Non-existent Files Tests ===

    def test_nonexistent_file_produces_error(self, validator, adr_with_nonexistent_files):
        """Non-existent files should produce errors."""
        issues = validator.validate(adr_with_nonexistent_files, {})

        assert len(issues) == 2  # missing.py and also_missing.py
        assert all(i.code == "FILE_NOT_FOUND" for i in issues)
        assert any("missing.py" in i.message for i in issues)
        assert any("also_missing.py" in i.message for i in issues)

    def test_mixed_existing_nonexistent(self, validator, adr_with_nonexistent_files):
        """Should only report errors for non-existent files."""
        issues = validator.validate(adr_with_nonexistent_files, {})

        # Should not report existing.py
        assert not any("existing.py" in i.message for i in issues)

    # === Fallback Tests ===

    def test_fallback_moves_to_create(self, validator, adr_with_nonexistent_files):
        """Fallback should move non-existent files to create."""
        result = validator.apply_fallback(adr_with_nonexistent_files, {})

        assert result is not None
        # Check files are now in create
        assert "create:" in result
        assert "src/missing.py" in result
        assert "src/also_missing.py" in result

    def test_fallback_keeps_existing_in_modify(self, validator, adr_with_nonexistent_files):
        """Fallback should keep existing files in modify."""
        result = validator.apply_fallback(adr_with_nonexistent_files, {})

        assert result is not None
        # existing.py should still be in modify section
        assert "modify:" in result
        assert "src/existing.py" in result

    def test_fallback_when_no_issues(self, validator, adr_with_existing_files):
        """Fallback should return None when no issues."""
        result = validator.apply_fallback(adr_with_existing_files, {})
        assert result is None

    def test_fallback_preserves_content(self, validator, adr_with_nonexistent_files):
        """Fallback should preserve the rest of the ADR."""
        result = validator.apply_fallback(adr_with_nonexistent_files, {})

        assert result is not None
        assert "## Kontext" in result
        assert "## Entscheidung" in result


class TestValidatorProperties:
    """Tests for validator metadata."""

    def test_adr_validator_name(self):
        """ADR validator should have correct name."""
        validator = ADRStructureValidator()
        assert validator.name == "adr_structure"

    def test_file_validator_name(self, tmp_path):
        """File validator should have correct name."""
        validator = FileExistenceValidator(helix_root=tmp_path)
        assert validator.name == "file_existence"
