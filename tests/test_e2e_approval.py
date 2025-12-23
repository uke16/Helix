"""E2E Test für das Approval System.

Testet den kompletten Flow:
1. ADR erstellen (simuliert)
2. Pre-Checks (Layer 1-3)
3. Sub-Agent Approval (Layer 4) - MOCKED
4. Result validieren

Diese Tests sind so konzipiert, dass sie OHNE echten LLM-Call laufen.
Der ApprovalRunner wird gemockt, um echte Sub-Agent-Spawns zu vermeiden.

Usage:
    pytest output/tests/test_e2e_approval.py -v

    # Nur Unit-Tests (schnell):
    pytest output/tests/test_e2e_approval.py -v -k "not e2e"

    # E2E-Tests (mit Mocks):
    pytest output/tests/test_e2e_approval.py -v -k "e2e"
"""

import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "input"))
sys.path.insert(0, str(PROJECT_ROOT.parent.parent.parent / "src"))


# ============================================================================
# Mock Classes (for when real imports aren't available)
# ============================================================================

@dataclass
class MockADRSection:
    """Mock ADR section for testing."""
    name: str
    content: str


@dataclass
class MockADRMetadata:
    """Mock ADR metadata for testing."""
    adr_id: str = "999"
    title: str = "Test ADR"
    status: str = "Proposed"
    change_scope: str = "minor"
    classification: str = "ENHANCEMENT"
    component_type: str = "TOOL"
    domain: str = "helix"
    depends_on: list = None
    files: Any = None


@dataclass
class MockADRDocument:
    """Mock ADR document for testing."""
    metadata: MockADRMetadata
    sections: dict
    raw_content: str


# ============================================================================
# Test Data
# ============================================================================

SAMPLE_ADR_MINIMAL = """---
adr_id: "TEST-001"
title: "Test ADR - Minimal"
status: Proposed
change_scope: minor
classification: ENHANCEMENT
---

# ADR-TEST-001: Test ADR - Minimal

## Kontext

Dies ist ein Test-ADR für die E2E-Validierung.

## Entscheidung

Wir testen das Approval-System.

## Implementation

```python
print("Hello World")
```

## Dokumentation

- README.md

## Akzeptanzkriterien

- [ ] Test besteht
- [ ] Validation funktioniert
- [ ] Gate läuft durch

## Konsequenzen

### Vorteile
- System ist getestet

### Nachteile
- Keine
"""

SAMPLE_ADR_MAJOR_WITHOUT_MIGRATION = """---
adr_id: "TEST-002"
title: "Test ADR - Major ohne Migration"
status: Proposed
change_scope: major
classification: NEW
component_type: PROCESS
---

# ADR-TEST-002: Major Change ohne Migration

## Kontext

Dies ist ein major change ohne Migrationsplan.

## Entscheidung

Wir machen einen großen Change.

## Implementation

Viele Änderungen.

## Dokumentation

- Alles

## Akzeptanzkriterien

- [ ] Funktioniert

## Konsequenzen

### Vorteile
- Toll

### Nachteile
- Aufwand
"""

SAMPLE_ADR_MAJOR_WITH_MIGRATION = """---
adr_id: "TEST-003"
title: "Test ADR - Major mit Migration"
status: Proposed
change_scope: major
classification: NEW
---

# ADR-TEST-003: Major Change mit Migration

## Kontext

Dies ist ein major change mit Migrationsplan.

## Entscheidung

Wir machen einen großen Change.

## Implementation

Viele Änderungen.

## Migration

### Phase 1: Vorbereitung
1. Schritt 1: Backup erstellen
2. Schritt 2: Abhängigkeiten prüfen

### Phase 2: Rollout
1. Schritt 3: Deploy
2. Schritt 4: Validieren

### Rollback-Strategie
Bei Problemen: git revert

## Dokumentation

- Alles updaten

## Akzeptanzkriterien

- [ ] Migration dokumentiert
- [ ] Rollback möglich
- [ ] Tests grün

## Konsequenzen

### Vorteile
- Alles besser

### Nachteile
- Aufwand
"""

SAMPLE_CONCEPT = """# Konzept: Test Feature

## Kontext

Wir brauchen ein Test-Feature.

## Entscheidung

Wir implementieren es.

## Implementation

So machen wir es.

## Migration

Migrationsschritte hier.

## Dokumentation

Was aktualisiert werden muss.

## Akzeptanzkriterien

- Kriterium 1
- Kriterium 2

## Konsequenzen

Vorteile und Nachteile.

## Offene Fragen

Diese Section sollte ignoriert werden.
"""


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def minimal_adr_file(temp_dir):
    """Create a minimal ADR file."""
    adr_path = temp_dir / "ADR-TEST-001.md"
    adr_path.write_text(SAMPLE_ADR_MINIMAL, encoding="utf-8")
    return adr_path


@pytest.fixture
def major_adr_no_migration(temp_dir):
    """Create a major ADR without migration section."""
    adr_path = temp_dir / "ADR-TEST-002.md"
    adr_path.write_text(SAMPLE_ADR_MAJOR_WITHOUT_MIGRATION, encoding="utf-8")
    return adr_path


@pytest.fixture
def major_adr_with_migration(temp_dir):
    """Create a major ADR with migration section."""
    adr_path = temp_dir / "ADR-TEST-003.md"
    adr_path.write_text(SAMPLE_ADR_MAJOR_WITH_MIGRATION, encoding="utf-8")
    return adr_path


@pytest.fixture
def concept_file(temp_dir):
    """Create a concept file."""
    concept_path = temp_dir / "concept.md"
    concept_path.write_text(SAMPLE_CONCEPT, encoding="utf-8")
    return concept_path


@pytest.fixture
def mock_approval_result():
    """Create a mock approval result."""
    return {
        "result": "approved",
        "confidence": 0.95,
        "findings": [
            {
                "severity": "info",
                "check": "completeness",
                "message": "All sections present",
            }
        ],
        "recommendations": [],
    }


@pytest.fixture
def mock_rejected_result():
    """Create a mock rejected approval result."""
    return {
        "result": "rejected",
        "confidence": 0.8,
        "findings": [
            {
                "severity": "error",
                "check": "migration",
                "message": "Migration section missing for major change",
                "location": "YAML header",
            },
            {
                "severity": "warning",
                "check": "completeness",
                "message": "Few acceptance criteria",
            }
        ],
        "recommendations": [
            "Add migration section with rollback plan",
            "Add more acceptance criteria",
        ],
    }


# ============================================================================
# Unit Tests: CompletenessValidator
# ============================================================================

class TestCompletenessValidator:
    """Tests for the CompletenessValidator (Layer 2)."""

    def test_import_completeness_validator(self):
        """Verify CompletenessValidator can be imported."""
        try:
            from helix.adr.completeness import CompletenessValidator, CompletenessResult
            assert CompletenessValidator is not None
            assert CompletenessResult is not None
        except ImportError:
            pytest.skip("helix.adr.completeness not available")

    def test_validate_minimal_adr(self, minimal_adr_file):
        """Test validation of a minimal valid ADR."""
        try:
            from helix.adr.completeness import CompletenessValidator
            from helix.adr import ADRParser
        except ImportError:
            pytest.skip("helix.adr modules not available")

        parser = ADRParser()
        adr = parser.parse_file(minimal_adr_file)

        validator = CompletenessValidator()
        result = validator.check(adr)

        # Minimal ADR should pass (no major change_scope)
        assert result.passed is True or len([i for i in result.issues if hasattr(i, 'level') and i.level == "error"]) == 0

    def test_major_needs_migration_rule(self, major_adr_no_migration, temp_dir):
        """Test that major changes require migration section."""
        try:
            from helix.adr.completeness import CompletenessValidator
            from helix.adr import ADRParser
        except ImportError:
            pytest.skip("helix.adr modules not available")

        # Create rules file for testing
        rules_content = """
contextual_rules:
  - id: major-needs-migration
    name: "Major Changes erfordern Migrationsplan"
    when:
      change_scope: major
    require:
      sections:
        - name: "Migration"
          min_length: 50
    severity: error
    message: "change_scope=major erfordert einen Migrations-Plan"
"""
        rules_path = temp_dir / "rules.yaml"
        rules_path.write_text(rules_content, encoding="utf-8")

        parser = ADRParser()
        adr = parser.parse_file(major_adr_no_migration)

        validator = CompletenessValidator(rules_path=rules_path)
        result = validator.check(adr)

        # Should fail: major change without migration
        assert result.passed is False
        assert any("Migration" in str(issue.message) for issue in result.issues)


# ============================================================================
# Unit Tests: ConceptDiffer
# ============================================================================

class TestConceptDiffer:
    """Tests for the ConceptDiffer (Layer 3)."""

    def test_import_concept_differ(self):
        """Verify ConceptDiffer can be imported."""
        try:
            from helix.adr.concept_diff import ConceptDiffer, ConceptDiffResult
            assert ConceptDiffer is not None
            assert ConceptDiffResult is not None
        except ImportError:
            pytest.skip("helix.adr.concept_diff not available")

    def test_concept_coverage(self, major_adr_no_migration, concept_file):
        """Test concept-to-ADR comparison."""
        try:
            from helix.adr.concept_diff import ConceptDiffer
            from helix.adr import ADRParser
        except ImportError:
            pytest.skip("helix.adr modules not available")

        parser = ADRParser()
        adr = parser.parse_file(major_adr_no_migration)

        differ = ConceptDiffer()
        result = differ.compare(concept_file, adr)

        # ADR without migration should show Migration as missing
        assert result.has_missing_sections is True
        assert "Migration" in result.missing_in_adr or len(result.missing_in_adr) > 0

    def test_full_coverage(self, major_adr_with_migration, concept_file):
        """Test that ADR with all sections has full coverage."""
        try:
            from helix.adr.concept_diff import ConceptDiffer
            from helix.adr import ADRParser
        except ImportError:
            pytest.skip("helix.adr modules not available")

        parser = ADRParser()
        adr = parser.parse_file(major_adr_with_migration)

        differ = ConceptDiffer()
        result = differ.compare(concept_file, adr)

        # Should have high coverage (Migration is present)
        assert result.coverage_percent >= 80.0

    def test_nonexistent_concept(self, minimal_adr_file, temp_dir):
        """Test behavior when concept file doesn't exist."""
        try:
            from helix.adr.concept_diff import ConceptDiffer
            from helix.adr import ADRParser
        except ImportError:
            pytest.skip("helix.adr modules not available")

        parser = ADRParser()
        adr = parser.parse_file(minimal_adr_file)

        differ = ConceptDiffer()
        nonexistent = temp_dir / "nonexistent.md"
        result = differ.compare(nonexistent, adr)

        # Should handle gracefully
        assert result.coverage_percent == 100.0
        assert "not found" in result.warnings[0].lower()


# ============================================================================
# Unit Tests: ApprovalResult
# ============================================================================

class TestApprovalResult:
    """Tests for ApprovalResult dataclass."""

    def test_import_approval_result(self):
        """Verify ApprovalResult can be imported."""
        try:
            from helix.approval.result import ApprovalResult, Finding, Severity
            assert ApprovalResult is not None
            assert Finding is not None
            assert Severity is not None
        except ImportError:
            pytest.skip("helix.approval modules not available")

    def test_approved_result(self, mock_approval_result):
        """Test creating an approved result."""
        try:
            from helix.approval.result import ApprovalResult
        except ImportError:
            pytest.skip("helix.approval modules not available")

        result = ApprovalResult.from_dict(
            approval_id="test123",
            approval_type="adr",
            data=mock_approval_result,
        )

        assert result.approved is True
        assert result.rejected is False
        assert result.confidence == 0.95
        assert len(result.findings) == 1

    def test_rejected_result(self, mock_rejected_result):
        """Test creating a rejected result."""
        try:
            from helix.approval.result import ApprovalResult
        except ImportError:
            pytest.skip("helix.approval modules not available")

        result = ApprovalResult.from_dict(
            approval_id="test456",
            approval_type="adr",
            data=mock_rejected_result,
        )

        assert result.approved is False
        assert result.rejected is True
        assert result.error_count == 1
        assert result.warning_count == 1
        assert len(result.recommendations) == 2

    def test_to_dict_roundtrip(self, mock_approval_result):
        """Test serialization and deserialization."""
        try:
            from helix.approval.result import ApprovalResult
        except ImportError:
            pytest.skip("helix.approval modules not available")

        result = ApprovalResult.from_dict(
            approval_id="test789",
            approval_type="adr",
            data=mock_approval_result,
        )

        # Convert to dict and back
        data = result.to_dict()
        assert data["approval_id"] == "test789"
        assert data["result"] == "approved"
        assert data["confidence"] == 0.95


# ============================================================================
# E2E Tests (with Mocked ApprovalRunner)
# ============================================================================

class TestE2EApprovalFlow:
    """End-to-end tests for the complete approval flow.

    These tests mock the ApprovalRunner to avoid spawning real sub-agents.
    """

    @pytest.mark.asyncio
    async def test_e2e_minimal_adr_approval(self, minimal_adr_file, mock_approval_result):
        """E2E: Minimal ADR should pass pre-checks and get approved."""
        try:
            from helix.adr.completeness import CompletenessValidator
            from helix.adr import ADRParser
            from helix.approval.result import ApprovalResult
        except ImportError:
            pytest.skip("Required modules not available")

        # Step 1: Parse ADR
        parser = ADRParser()
        adr = parser.parse_file(minimal_adr_file)
        assert adr is not None

        # Step 2: Run pre-checks (Layer 2)
        validator = CompletenessValidator()
        precheck_result = validator.check(adr)

        # Minimal ADR should pass pre-checks (no major scope)
        errors = [i for i in precheck_result.issues if getattr(i, 'level', None) == "error"]
        assert len(errors) == 0 or precheck_result.passed

        # Step 3: Mock sub-agent approval (Layer 4)
        approval = ApprovalResult.from_dict(
            approval_id="e2e-test-1",
            approval_type="adr",
            data=mock_approval_result,
        )

        # Step 4: Validate result
        assert approval.approved is True
        assert approval.confidence >= 0.8

    @pytest.mark.asyncio
    async def test_e2e_major_without_migration_rejected(
        self,
        major_adr_no_migration,
        mock_rejected_result,
        temp_dir,
    ):
        """E2E: Major ADR without migration should be rejected."""
        try:
            from helix.adr.completeness import CompletenessValidator
            from helix.adr import ADRParser
            from helix.approval.result import ApprovalResult
        except ImportError:
            pytest.skip("Required modules not available")

        # Create rules file
        rules_content = """
contextual_rules:
  - id: major-needs-migration
    name: "Major Changes erfordern Migrationsplan"
    when:
      change_scope: major
    require:
      sections:
        - name: "Migration"
          min_length: 50
    severity: error
    message: "change_scope=major erfordert einen Migrations-Plan"
"""
        rules_path = temp_dir / "rules.yaml"
        rules_path.write_text(rules_content, encoding="utf-8")

        # Step 1: Parse ADR
        parser = ADRParser()
        adr = parser.parse_file(major_adr_no_migration)

        # Step 2: Run pre-checks (Layer 2)
        validator = CompletenessValidator(rules_path=rules_path)
        precheck_result = validator.check(adr)

        # Should fail pre-checks!
        assert precheck_result.passed is False
        migration_issues = [i for i in precheck_result.issues if "Migration" in i.message]
        assert len(migration_issues) >= 1

        # Step 3: Since pre-checks failed, we would NOT call the sub-agent
        # This saves cost and time (early exit)

        # Step 4: Create rejection result (simulating what would happen)
        approval = ApprovalResult.from_dict(
            approval_id="e2e-test-2",
            approval_type="adr",
            data=mock_rejected_result,
        )

        assert approval.rejected is True
        assert approval.error_count >= 1

    @pytest.mark.asyncio
    async def test_e2e_major_with_migration_approved(
        self,
        major_adr_with_migration,
        mock_approval_result,
        temp_dir,
    ):
        """E2E: Major ADR with migration should pass all checks."""
        try:
            from helix.adr.completeness import CompletenessValidator
            from helix.adr.concept_diff import ConceptDiffer
            from helix.adr import ADRParser
            from helix.approval.result import ApprovalResult
        except ImportError:
            pytest.skip("Required modules not available")

        # Create rules file
        rules_content = """
contextual_rules:
  - id: major-needs-migration
    name: "Major Changes erfordern Migrationsplan"
    when:
      change_scope: major
    require:
      sections:
        - name: "Migration"
          min_length: 50
    severity: error
    message: "change_scope=major erfordert einen Migrations-Plan"
"""
        rules_path = temp_dir / "rules.yaml"
        rules_path.write_text(rules_content, encoding="utf-8")

        # Step 1: Parse ADR
        parser = ADRParser()
        adr = parser.parse_file(major_adr_with_migration)

        # Step 2: Run pre-checks (Layer 2)
        validator = CompletenessValidator(rules_path=rules_path)
        precheck_result = validator.check(adr)

        # Should pass pre-checks (migration is present)
        errors = [i for i in precheck_result.issues if getattr(i, 'level', None) == "error"]
        assert len(errors) == 0

        # Step 3: Mock sub-agent approval (Layer 4)
        approval = ApprovalResult.from_dict(
            approval_id="e2e-test-3",
            approval_type="adr",
            data=mock_approval_result,
        )

        # Step 4: Validate final result
        assert approval.approved is True

    @pytest.mark.asyncio
    async def test_e2e_concept_diff_integration(
        self,
        major_adr_no_migration,
        concept_file,
    ):
        """E2E: Concept diff should detect missing sections."""
        try:
            from helix.adr.concept_diff import ConceptDiffer
            from helix.adr import ADRParser
        except ImportError:
            pytest.skip("Required modules not available")

        # Step 1: Parse ADR
        parser = ADRParser()
        adr = parser.parse_file(major_adr_no_migration)

        # Step 2: Run concept diff (Layer 3)
        differ = ConceptDiffer()
        diff_result = differ.compare(concept_file, adr)

        # Step 3: Validate that Migration is detected as missing
        assert diff_result.has_missing_sections is True
        # Migration should be in the missing sections
        missing_lower = [s.lower() for s in diff_result.missing_in_adr]
        assert "migration" in missing_lower or diff_result.coverage_percent < 100


# ============================================================================
# Integration Tests: ApprovalRunner (Mocked)
# ============================================================================

class TestApprovalRunnerMocked:
    """Tests for ApprovalRunner with mocked subprocess."""

    def test_import_approval_runner(self):
        """Verify ApprovalRunner can be imported."""
        try:
            from helix.approval.runner import ApprovalRunner, ApprovalConfig
            assert ApprovalRunner is not None
            assert ApprovalConfig is not None
        except ImportError:
            pytest.skip("helix.approval.runner not available")

    @pytest.mark.asyncio
    async def test_mocked_approval_run(self, temp_dir, mock_approval_result):
        """Test ApprovalRunner with mocked subprocess."""
        try:
            from helix.approval.runner import ApprovalRunner, ApprovalConfig
            from helix.approval.result import ApprovalResult
        except ImportError:
            pytest.skip("Required modules not available")

        # Setup approval directory structure
        approval_type = "adr"
        approval_dir = temp_dir / "approvals" / approval_type
        approval_dir.mkdir(parents=True)

        # Create CLAUDE.md
        claude_md = approval_dir / "CLAUDE.md"
        claude_md.write_text("# ADR Approval\n\nCheck the ADR.", encoding="utf-8")

        # Create input/output directories
        (approval_dir / "input").mkdir()
        (approval_dir / "output").mkdir()

        # Create mock result file
        result_file = approval_dir / "output" / "approval-result.json"
        result_file.write_text(json.dumps(mock_approval_result), encoding="utf-8")

        # Create runner with mocked spawn
        runner = ApprovalRunner(approvals_base=temp_dir / "approvals")

        # Mock the _spawn_agent method
        async def mock_spawn(*args, **kwargs):
            pass  # Do nothing - result file is already created

        runner._spawn_agent = mock_spawn

        # Create a test ADR file
        test_adr = temp_dir / "test-adr.md"
        test_adr.write_text(SAMPLE_ADR_MINIMAL, encoding="utf-8")

        # Run approval
        result = await runner.run_approval(
            approval_type="adr",
            input_files=[test_adr],
        )

        # Validate
        assert result.approved is True
        assert result.confidence == 0.95


# ============================================================================
# Main Entry Point
# ============================================================================

def run_tests():
    """Run all tests and display results."""
    print("=" * 60)
    print("HELIX Approval System E2E Tests")
    print("=" * 60)
    print()

    # Check if required modules are available
    modules_ok = True

    try:
        from helix.adr import ADRParser
        print("[OK] helix.adr.ADRParser")
    except ImportError as e:
        print(f"[SKIP] helix.adr.ADRParser: {e}")
        modules_ok = False

    try:
        from helix.adr.completeness import CompletenessValidator
        print("[OK] helix.adr.completeness.CompletenessValidator")
    except ImportError as e:
        print(f"[SKIP] helix.adr.completeness: {e}")
        modules_ok = False

    try:
        from helix.adr.concept_diff import ConceptDiffer
        print("[OK] helix.adr.concept_diff.ConceptDiffer")
    except ImportError as e:
        print(f"[SKIP] helix.adr.concept_diff: {e}")
        modules_ok = False

    try:
        from helix.approval.result import ApprovalResult, Finding, Severity
        print("[OK] helix.approval.result")
    except ImportError as e:
        print(f"[SKIP] helix.approval.result: {e}")
        modules_ok = False

    try:
        from helix.approval.runner import ApprovalRunner
        print("[OK] helix.approval.runner.ApprovalRunner")
    except ImportError as e:
        print(f"[SKIP] helix.approval.runner: {e}")
        modules_ok = False

    print()

    if not modules_ok:
        print("Some modules are not available.")
        print("Run from HELIX root directory or install helix package.")
        print()

    print("To run full test suite:")
    print("  pytest output/tests/test_e2e_approval.py -v")
    print()
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
