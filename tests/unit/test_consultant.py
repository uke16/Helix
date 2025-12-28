import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from helix.consultant import ConsultantMeeting, ExpertManager, ExpertConfig


class TestExpertManager:
    """Tests for ExpertManager."""

    def test_load_experts(self):
        """Should load expert configurations."""
        manager = ExpertManager()
        experts = manager.load_experts()

        assert isinstance(experts, dict)
        assert len(experts) > 0

    def test_select_experts_pdm(self):
        """Should select PDM expert for BOM request."""
        manager = ExpertManager()
        selected = manager.select_experts("I need to export the BOM to SAP")

        assert "pdm" in selected or "erp" in selected

    def test_select_experts_encoder(self):
        """Should select encoder expert for encoder request."""
        manager = ExpertManager()
        selected = manager.select_experts("Configure the rotary encoder settings")

        assert "encoder" in selected

    def test_expert_config_structure(self):
        """ExpertConfig should have required fields."""
        manager = ExpertManager()
        experts = manager.load_experts()

        for expert_id, config in experts.items():
            assert hasattr(config, "id")
            assert hasattr(config, "name")
            assert hasattr(config, "triggers")


