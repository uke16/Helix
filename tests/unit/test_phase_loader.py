import pytest
from pathlib import Path

from helix.phase_loader import PhaseLoader, PhaseConfig


class TestPhaseLoader:
    """Tests for PhaseLoader."""

    def test_load_phases_from_yaml(self, sample_project):
        """Should load phases from phases.yaml."""
        loader = PhaseLoader()
        phases = loader.load_phases(sample_project)

        assert len(phases) >= 1
        assert isinstance(phases[0], PhaseConfig)
        assert phases[0].id == "01-test"

    def test_load_phases_missing_file(self, temp_dir):
        """Should raise error if phases.yaml missing."""
        with pytest.raises(FileNotFoundError):
            loader = PhaseLoader()
            loader.load_phases(temp_dir)

    def test_phase_config_attributes(self, sample_project):
        """PhaseConfig should have required attributes."""
        loader = PhaseLoader()
        phases = loader.load_phases(sample_project)
        phase = phases[0]

        assert hasattr(phase, "id")
        assert hasattr(phase, "name")
        assert hasattr(phase, "type")
