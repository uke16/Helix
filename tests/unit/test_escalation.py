import pytest

from helix.escalation import EscalationManager, EscalationLevel


class TestEscalationManager:
    """Tests for EscalationManager."""

    def test_determine_level_syntax_error(self):
        """Syntax errors should be Level 1."""
        manager = EscalationManager()
        level = manager.determine_level("SyntaxError: invalid syntax")

        assert level == EscalationLevel.STUFE_1

    def test_determine_level_permission_denied(self):
        """Permission errors should be Level 2."""
        manager = EscalationManager()
        level = manager.determine_level("Permission denied")

        assert level == EscalationLevel.STUFE_2

    def test_get_actions_stufe_1(self):
        """Should return autonomous actions for Level 1."""
        manager = EscalationManager()
        actions = manager.get_actions(EscalationLevel.STUFE_1)

        assert "model_switch" in [a.type for a in actions]
        assert "hint_generation" in [a.type for a in actions]

    def test_get_actions_stufe_2(self):
        """Should return human actions for Level 2."""
        manager = EscalationManager()
        actions = manager.get_actions(EscalationLevel.STUFE_2)

        assert "notification" in [a.type for a in actions]
        assert "pause" in [a.type for a in actions]
