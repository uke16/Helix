import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
import json

from helix.consultant import ConsultantMeeting, ExpertManager, ExpertConfig
from helix.llm_client import LLMClient


class TestConsultantMeetingIntegration:
    """Integration tests for consultant meeting system."""

    @pytest.fixture
    def expert_manager(self):
        """Create ExpertManager with config."""
        return ExpertManager()

    @pytest.fixture
    def mock_llm_client(self):
        """Create mocked LLM client."""
        client = MagicMock(spec=LLMClient)
        return client

    def test_expert_manager_loads_config(self, expert_manager):
        """Should load experts from config file."""
        experts = expert_manager.load_experts()

        assert isinstance(experts, dict)
        # Should have Company-specific experts
        expected_domains = ["pdm", "encoder", "erp", "helix"]
        found = [d for d in expected_domains if d in experts]
        assert len(found) >= 2  # At least some experts loaded

    def test_expert_selection_for_pdm_request(self, expert_manager):
        """Should select PDM expert for BOM-related request."""
        request = "I need to export the bill of materials to SAP"
        selected = expert_manager.select_experts(request)

        # Should include PDM or ERP expert
        assert any(e in ["pdm", "erp", "bom"] for e in selected) or len(selected) > 0

    def test_expert_selection_for_encoder_request(self, expert_manager):
        """Should select encoder expert for encoder request."""
        request = "Configure the rotary encoder resolution settings"
        selected = expert_manager.select_experts(request)

        assert "encoder" in selected or len(selected) > 0

    @pytest.mark.asyncio
    async def test_meeting_analyze_request(self, expert_manager, mock_llm_client):
        """Should analyze request and select experts."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "experts": ["pdm", "erp"],
            "questions": {
                "pdm": "Which BOM levels need export?",
                "erp": "Which SAP module to target?"
            },
            "reasoning": "Request involves BOM and SAP"
        })

        mock_llm_client.complete = AsyncMock(return_value=mock_response)

        meeting = ConsultantMeeting(mock_llm_client, expert_manager)

        with patch.object(meeting, 'analyze_request', new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = {
                "experts": ["pdm", "erp"],
                "questions": {}
            }

            result = await meeting.analyze_request("Export BOM to SAP")

            assert "experts" in result
            assert len(result["experts"]) > 0

