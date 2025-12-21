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


class TestConsultantMeeting:
    """Tests for ConsultantMeeting."""

    @pytest.mark.asyncio
    async def test_analyze_request(self):
        """Should analyze user request."""
        with patch("helix.consultant.meeting.LLMClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.complete = AsyncMock(return_value=type("Response", (), {
                "content": '{"experts": ["pdm"], "reasoning": "test"}'
            })())

            meeting = ConsultantMeeting(mock_client, ExpertManager())
            result = await meeting.analyze_request("Export BOM data")

            assert result is not None
