"""Integration tests for ADR-034: Consultant Flow Refactoring - LLM-Native.

Tests the new LLM-native consultant flow where:
- Step detection is done by the LLM, not Python
- LLM sets step markers in its response (<!-- STEP: X -->)
- Python extracts and logs the step, doesn't control flow
- Users can navigate the conversation naturally (one-shot, iterative, backtracking)

Test Scenarios (per ADR-034 Phase 05):
1. One-shot: User gives all information in one message
2. Iterative: User answers questions step by step
3. Backtracking: User wants to go back
4. ADR creation without trigger words
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import sys
import importlib.util

# ADR-034: Import modified modules directly from phase output files
# This bypasses Python's package resolution to test the modified code
PHASES_DIR = Path(__file__).parent.parent.parent.parent.parent
PHASE_02_SESSION_MGR = PHASES_DIR / "02" / "output" / "modified" / "src" / "helix" / "api" / "session_manager.py"
PHASE_04_EXPERT_MGR = PHASES_DIR / "04" / "output" / "modified" / "src" / "helix" / "consultant" / "expert_manager.py"
HELIX_SRC = PHASES_DIR.parent.parent.parent.parent / "src"

# Add helix src for base dependencies (pydantic, etc.)
sys.path.insert(0, str(HELIX_SRC))


def _load_module_from_file(name: str, file_path: Path):
    """Load a Python module directly from a file path."""
    spec = importlib.util.spec_from_file_location(name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Load the modified SessionManager from phase 02
_session_manager_module = _load_module_from_file(
    "helix_adr034_session_manager",
    PHASE_02_SESSION_MGR
)
SessionManager = _session_manager_module.SessionManager
SessionState = _session_manager_module.SessionState

# Load the modified ExpertManager from phase 04
_expert_manager_module = _load_module_from_file(
    "helix_adr034_expert_manager",
    PHASE_04_EXPERT_MGR
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def temp_session_dir():
    """Provide a temporary directory for session tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def session_manager(temp_session_dir):
    """Create a SessionManager with temporary storage."""
    return SessionManager(base_path=temp_session_dir)


# =============================================================================
# Test: extract_state_from_messages (ADR-034 Simplified)
# =============================================================================

class TestExtractStateFromMessages:
    """Tests for the simplified extract_state_from_messages function.

    ADR-034: This function no longer performs step detection.
    It only extracts basic metadata (original_request, message_count).
    """

    def test_extracts_original_request(self, session_manager):
        """Should extract the first user message as original request."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "I want to build a new feature"},
            {"role": "assistant", "content": "What kind of feature?"},
            {"role": "user", "content": "A login system"},
        ]

        state = session_manager.extract_state_from_messages(messages)

        assert state["original_request"] == "I want to build a new feature"
        assert state["message_count"] == 4

    def test_handles_empty_messages(self, session_manager):
        """Should handle empty message list gracefully."""
        messages = []

        state = session_manager.extract_state_from_messages(messages)

        assert state["original_request"] == ""
        assert state["message_count"] == 0

    def test_handles_no_user_messages(self, session_manager):
        """Should handle case with no user messages."""
        messages = [
            {"role": "system", "content": "System prompt"},
            {"role": "assistant", "content": "Hello!"},
        ]

        state = session_manager.extract_state_from_messages(messages)

        assert state["original_request"] == ""
        assert state["message_count"] == 2

    def test_does_not_include_step(self, session_manager):
        """ADR-034: State should NOT include step - that's the LLM's job."""
        messages = [
            {"role": "user", "content": "Create an ADR for me please"},
        ]

        state = session_manager.extract_state_from_messages(messages)

        # Step should NOT be in the state
        assert "step" not in state
        # These should be present
        assert "original_request" in state
        assert "message_count" in state

    def test_no_trigger_word_detection(self, session_manager):
        """ADR-034: Should NOT detect trigger words like 'create', 'adr', etc."""
        messages = [
            {"role": "user", "content": "erstelle mir ein ADR bitte"},
        ]

        state = session_manager.extract_state_from_messages(messages)

        # Old behavior would detect "erstelle" + "adr" as finalize trigger
        # New behavior should NOT set any step
        assert "step" not in state

    def test_no_index_based_logic(self, session_manager):
        """ADR-034: Should NOT use message count for step determination."""
        # Many messages - old logic would set step="generate" after 4+ messages
        messages = [
            {"role": "user", "content": "I want a feature"},
            {"role": "assistant", "content": "What feature?"},
            {"role": "user", "content": "A dashboard"},
            {"role": "assistant", "content": "Why do you need it?"},
            {"role": "user", "content": "To see metrics"},
            {"role": "assistant", "content": "Any constraints?"},
            {"role": "user", "content": "Must use React"},
        ]

        state = session_manager.extract_state_from_messages(messages)

        # Should NOT have step field regardless of message count
        assert "step" not in state
        assert state["message_count"] == 7


# =============================================================================
# Test: extract_step_from_response (ADR-034 New Function)
# =============================================================================

class TestExtractStepFromResponse:
    """Tests for extracting step markers from LLM responses.

    ADR-034: The LLM sets step markers at the end of its response:
    <!-- STEP: what|why|constraints|generate|finalize|done -->
    """

    def test_extracts_step_marker(self, session_manager):
        """Should extract step marker from LLM response."""
        response = """
        Here's my answer to your question about the feature.

        Let me know more details.

        <!-- STEP: what -->
        """

        step = session_manager.extract_step_from_response(response)

        assert step == "what"

    def test_extracts_all_valid_steps(self, session_manager):
        """Should extract all valid step values."""
        steps = ["what", "why", "constraints", "generate", "finalize", "done"]

        for expected_step in steps:
            response = f"Some response text\n<!-- STEP: {expected_step} -->"
            step = session_manager.extract_step_from_response(response)
            assert step == expected_step, f"Failed to extract step: {expected_step}"

    def test_returns_none_without_marker(self, session_manager):
        """Should return None if no step marker present."""
        response = "Here's a response without any step marker."

        step = session_manager.extract_step_from_response(response)

        assert step is None

    def test_handles_whitespace_variations(self, session_manager):
        """Should handle whitespace variations in marker."""
        variations = [
            "text <!-- STEP: why -->",
            "text <!--STEP:why-->",
            "text <!--  STEP:  why  -->",
            "text <!-- STEP:why -->",
        ]

        for response in variations:
            step = session_manager.extract_step_from_response(response)
            assert step == "why", f"Failed for: {response}"

    def test_case_insensitive_step_value(self, session_manager):
        """Step values should be normalized to lowercase."""
        response = "text <!-- STEP: GENERATE -->"

        step = session_manager.extract_step_from_response(response)

        assert step == "generate"

    def test_extracts_first_marker_only(self, session_manager):
        """Should extract only the first step marker if multiple present."""
        response = """
        Some text
        <!-- STEP: what -->
        More text
        <!-- STEP: why -->
        """

        step = session_manager.extract_step_from_response(response)

        assert step == "what"

    def test_marker_at_end_of_response(self, session_manager):
        """Should handle marker at very end of response."""
        response = "This is the response text.<!-- STEP: constraints -->"

        step = session_manager.extract_step_from_response(response)

        assert step == "constraints"


# =============================================================================
# Test: One-Shot Flow (User gives everything at once)
# =============================================================================

class TestOneShotFlow:
    """Tests for one-shot consultant flow.

    User provides all information in a single message.
    LLM should recognize this and jump directly to ADR generation.
    """

    def test_one_shot_message_extraction(self, session_manager, temp_session_dir):
        """Should extract info from comprehensive single message."""
        comprehensive_message = """
        I need a new feature for HELIX that adds dark mode support.

        What: Toggle for dark/light theme in the UI
        Why: Users requested it for better usability at night
        Constraints:
        - Must use CSS variables
        - Must persist preference in localStorage
        - Should support system preference detection
        """

        messages = [{"role": "user", "content": comprehensive_message}]
        state = session_manager.extract_state_from_messages(messages)

        assert state["original_request"] == comprehensive_message
        assert state["message_count"] == 1

    def test_one_shot_with_session_creation(self, session_manager, temp_session_dir):
        """Should create session for one-shot request."""
        message = "Build me a login system with OAuth2, I need it because we have external users, use Python and FastAPI"

        session_id, session_state = session_manager.get_or_create_session(
            first_message=message,
            conversation_id="one-shot-test-123"
        )

        assert session_id.startswith("conv-")
        assert session_state.status == "discussing"
        assert session_state.original_request == message

    def test_one_shot_llm_response_with_generate_step(self, session_manager):
        """LLM should respond with 'generate' step for comprehensive requests."""
        # Simulated LLM response that recognized all info was provided
        llm_response = """
        Great! You've provided all the information needed. Let me create the ADR.

        ## ADR Summary
        - Feature: Dark Mode Support
        - Reason: User request for night usability
        - Tech: CSS variables, localStorage, system preference

        I'll generate the full ADR now.

        <!-- STEP: generate -->
        """

        step = session_manager.extract_step_from_response(llm_response)

        assert step == "generate"


# =============================================================================
# Test: Iterative Flow (User answers questions step by step)
# =============================================================================

class TestIterativeFlow:
    """Tests for iterative consultant flow.

    User provides information incrementally in response to questions.
    LLM guides the conversation through what/why/constraints phases.
    """

    def test_iterative_message_history(self, session_manager, temp_session_dir):
        """Should track conversation history correctly."""
        session_id, _ = session_manager.get_or_create_session(
            first_message="I need a new feature",
            conversation_id="iterative-test-456"
        )

        messages = [
            {"role": "user", "content": "I need a new feature"},
            {"role": "assistant", "content": "What kind of feature do you need?\n<!-- STEP: what -->"},
            {"role": "user", "content": "A dashboard for metrics"},
            {"role": "assistant", "content": "Why do you need this dashboard?\n<!-- STEP: why -->"},
            {"role": "user", "content": "To monitor system health"},
        ]

        session_manager.save_messages(session_id, messages)

        # Verify messages were saved
        messages_file = temp_session_dir / session_id / "context" / "messages.json"
        assert messages_file.exists()

        loaded = json.loads(messages_file.read_text())
        assert len(loaded) == 5

    def test_iterative_step_progression(self, session_manager):
        """LLM responses should progress through steps naturally."""
        responses = [
            ("What do you want to build?\n<!-- STEP: what -->", "what"),
            ("Why is this needed?\n<!-- STEP: why -->", "why"),
            ("Any technical constraints?\n<!-- STEP: constraints -->", "constraints"),
            ("Here's the ADR draft:\n<!-- STEP: generate -->", "generate"),
        ]

        for response_text, expected_step in responses:
            step = session_manager.extract_step_from_response(response_text)
            assert step == expected_step

    def test_iterative_context_building(self, session_manager, temp_session_dir):
        """Should allow context to be built incrementally."""
        session_id, _ = session_manager.get_or_create_session(
            first_message="New feature request",
            conversation_id="context-test-789"
        )

        # Build context incrementally
        session_manager.save_context(session_id, "what", "A metrics dashboard")
        session_manager.save_context(session_id, "why", "To monitor system health")
        session_manager.save_context(session_id, "constraints", "Must use React, must be real-time")

        # Verify all context is available
        context = session_manager.get_context(session_id)

        assert "what" in context
        assert "why" in context
        assert "constraints" in context
        assert "metrics dashboard" in context["what"]


# =============================================================================
# Test: Backtracking Flow (User wants to go back)
# =============================================================================

class TestBacktrackingFlow:
    """Tests for backtracking in consultant flow.

    User can say things like "wait, let me change that" or "go back".
    LLM should recognize this and adjust the conversation naturally.
    """

    def test_backtracking_message_does_not_trigger_python_logic(self, session_manager):
        """Backtracking messages should not trigger any Python step detection."""
        backtracking_messages = [
            "Wait, I want to change the requirements",
            "Actually, go back to the previous question",
            "Nein, doch nicht so - ich will das anders machen",
            "Let me reconsider the constraints",
        ]

        for message in backtracking_messages:
            messages = [{"role": "user", "content": message}]
            state = session_manager.extract_state_from_messages(messages)

            # Should NOT have step - LLM decides how to handle backtracking
            assert "step" not in state

    def test_llm_handles_backtracking(self, session_manager):
        """LLM can respond to backtracking with appropriate step."""
        # User said "wait, go back to requirements"
        llm_response = """
        No problem! Let's revisit the requirements.

        What exactly do you want to change about the feature?

        <!-- STEP: what -->
        """

        step = session_manager.extract_step_from_response(llm_response)

        # LLM correctly went back to "what" phase
        assert step == "what"

    def test_context_can_be_overwritten(self, session_manager, temp_session_dir):
        """Context files should be overwritable for backtracking."""
        session_id, _ = session_manager.get_or_create_session(
            first_message="Feature request",
            conversation_id="backtrack-context-test"
        )

        # Initial context
        session_manager.save_context(session_id, "what", "Old requirements")

        # User backtracked - new context
        session_manager.save_context(session_id, "what", "New revised requirements")

        context = session_manager.get_context(session_id)

        assert context["what"] == "New revised requirements"


# =============================================================================
# Test: ADR Creation Without Trigger Words
# =============================================================================

class TestADRCreationWithoutTriggers:
    """Tests for ADR creation without explicit trigger words.

    ADR-034: Users should be able to request ADR creation naturally,
    without needing exact words like "erstelle", "create", "generiere".
    """

    def test_no_trigger_detection_in_python(self, session_manager):
        """Python should NOT detect ADR creation triggers."""
        adr_requests = [
            "I think we have enough info, let's document this",
            "Can you write up the architecture decision?",
            "Time to formalize this into a spec",
            "Bitte das als ADR aufschreiben",
            "Make the ADR now",
        ]

        for request in adr_requests:
            messages = [{"role": "user", "content": request}]
            state = session_manager.extract_state_from_messages(messages)

            # Python should NOT set step - this is LLM's job
            assert "step" not in state

    def test_llm_recognizes_adr_intent(self, session_manager):
        """LLM should recognize ADR creation intent and set appropriate step."""
        # User said "I think we can write it up now"
        llm_response = """
        Perfect! I have all the information I need. Let me create the ADR for you.

        Creating ADR-XXX: New Feature Implementation...

        <!-- STEP: generate -->
        """

        step = session_manager.extract_step_from_response(llm_response)

        assert step == "generate"

    def test_false_positive_prevention(self, session_manager):
        """Should NOT trigger ADR creation for innocent mentions."""
        # Old system would trigger on "I started VS Code"
        innocent_messages = [
            "I started VS Code to look at the code",
            "The ADR process seems complex",
            "Can you explain how ADRs work?",
            "I'm creating a test file",
        ]

        for message in innocent_messages:
            messages = [{"role": "user", "content": message}]
            state = session_manager.extract_state_from_messages(messages)

            # No step detection should happen
            assert "step" not in state


# =============================================================================
# Test: State Update from LLM Response
# =============================================================================

class TestStateUpdateFromResponse:
    """Tests for updating session state from LLM response.

    ADR-034: After LLM responds, we extract the step marker and
    update the session state for observability.
    """

    def test_update_state_with_step(self, session_manager, temp_session_dir):
        """Should update session state with extracted step."""
        session_id, _ = session_manager.get_or_create_session(
            first_message="Test request",
            conversation_id="state-update-test"
        )

        # Simulate LLM response with step marker
        llm_response = "Here's my response\n<!-- STEP: why -->"
        step = session_manager.extract_step_from_response(llm_response)

        # Update state
        if step:
            session_manager.update_state(session_id, step=step)

        # Verify state was updated
        state = session_manager.get_state(session_id)
        assert state.step == "why"

    def test_state_persists_across_manager_instances(self, temp_session_dir):
        """Updated state should persist across manager instances."""
        session_id = None

        # First manager instance
        manager1 = SessionManager(base_path=temp_session_dir)
        session_id, _ = manager1.get_or_create_session(
            first_message="Test",
            conversation_id="persist-test"
        )
        manager1.update_state(session_id, step="constraints")

        # New manager instance (simulates server restart)
        manager2 = SessionManager(base_path=temp_session_dir)
        state = manager2.get_state(session_id)

        assert state.step == "constraints"


# =============================================================================
# Test: Expert Manager (Advisory Mode)
# =============================================================================

class TestExpertManagerAdvisory:
    """Tests for expert manager in advisory mode.

    ADR-034: Expert selection is now advisory, not mandatory.
    The LLM decides which domain knowledge is relevant.
    """

    def test_suggest_experts_method_exists(self):
        """suggest_experts() should exist as the new advisory method."""
        # Use the modified ExpertManager from phase 04
        ExpertManager = _expert_manager_module.ExpertManager

        manager = ExpertManager()

        assert hasattr(manager, "suggest_experts")
        assert callable(manager.suggest_experts)

    def test_suggest_experts_returns_suggestions(self):
        """suggest_experts() should return list of suggestions."""
        # Use the modified ExpertManager from phase 04
        ExpertManager = _expert_manager_module.ExpertManager

        manager = ExpertManager()
        suggestions = manager.suggest_experts("I need help with Docker deployment")

        assert isinstance(suggestions, list)
        assert len(suggestions) > 0

    def test_select_experts_is_alias(self):
        """select_experts() should work as alias for backward compatibility."""
        # Use the modified ExpertManager from phase 04
        ExpertManager = _expert_manager_module.ExpertManager

        manager = ExpertManager()

        # Both methods should exist
        assert hasattr(manager, "select_experts")
        assert hasattr(manager, "suggest_experts")

        # Should return same results
        request = "Database optimization needed"
        assert manager.select_experts(request) == manager.suggest_experts(request)


# =============================================================================
# Test: Template Marker Requirements
# =============================================================================

class TestTemplateMarkerRequirements:
    """Tests to verify the template correctly instructs about step markers."""

    def test_valid_step_values(self, session_manager):
        """All valid step values should be extractable."""
        valid_steps = ["what", "why", "constraints", "generate", "finalize", "done"]

        for step in valid_steps:
            response = f"Response text <!-- STEP: {step} -->"
            extracted = session_manager.extract_step_from_response(response)
            assert extracted == step, f"Failed to extract valid step: {step}"

    def test_invalid_step_values(self, session_manager):
        """Invalid step values should still be extracted (for logging)."""
        # LLM might make mistakes - we extract anyway for debugging
        response = "Response <!-- STEP: invalid_step -->"

        extracted = session_manager.extract_step_from_response(response)

        # We extract the value even if not in expected set
        assert extracted == "invalid_step"


# =============================================================================
# Test: Full Flow Integration
# =============================================================================

class TestFullFlowIntegration:
    """Integration tests simulating full consultant conversations."""

    def test_complete_iterative_flow(self, session_manager, temp_session_dir):
        """Simulate a complete iterative consultant flow."""
        # Create session
        session_id, _ = session_manager.get_or_create_session(
            first_message="I need a feature",
            conversation_id="full-flow-test"
        )

        # Simulate conversation
        conversation = [
            # Turn 1: What
            {"role": "user", "content": "I need a feature"},
            {"role": "assistant", "content": "What feature?\n<!-- STEP: what -->", "step": "what"},

            # Turn 2: What answered
            {"role": "user", "content": "A dashboard"},
            {"role": "assistant", "content": "Why do you need it?\n<!-- STEP: why -->", "step": "why"},

            # Turn 3: Why answered
            {"role": "user", "content": "To monitor metrics"},
            {"role": "assistant", "content": "Any constraints?\n<!-- STEP: constraints -->", "step": "constraints"},

            # Turn 4: Constraints answered
            {"role": "user", "content": "Use React and TypeScript"},
            {"role": "assistant", "content": "Creating ADR...\n<!-- STEP: generate -->", "step": "generate"},
        ]

        # Process each assistant response
        for msg in conversation:
            if msg["role"] == "assistant":
                step = session_manager.extract_step_from_response(msg["content"])
                assert step == msg["step"], f"Expected {msg['step']}, got {step}"
                session_manager.update_state(session_id, step=step)

        # Verify final state
        final_state = session_manager.get_state(session_id)
        assert final_state.step == "generate"

    def test_one_shot_to_generate_flow(self, session_manager, temp_session_dir):
        """Simulate one-shot request that goes directly to generate."""
        message = """
        Build a REST API endpoint for user authentication.
        We need it because we're adding external user access.
        Must use OAuth2, Python/FastAPI, and integrate with existing user DB.
        """

        session_id, _ = session_manager.get_or_create_session(
            first_message=message,
            conversation_id="one-shot-full-test"
        )

        # LLM recognizes all info is present
        llm_response = """
        You've provided complete requirements. Creating ADR now.

        ## ADR-XXX: User Authentication API
        ...

        <!-- STEP: generate -->
        """

        step = session_manager.extract_step_from_response(llm_response)
        session_manager.update_state(session_id, step=step)

        state = session_manager.get_state(session_id)
        assert state.step == "generate"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
