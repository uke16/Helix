"""E2E Tests for HELIX Workflow System.

Tests the complete workflow system including:
- Workflow template loading
- Sub-agent verification
- Dynamic phase generation
- Consultant workflow selection

These tests require the HELIX API to be running.
Start with: PYTHONPATH=src python3 -m helix.api.main
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import tempfile
import shutil
import yaml


# ═══════════════════════════════════════════════════════════════════════════════
# Test: Workflow Templates (ADR-023)
# ═══════════════════════════════════════════════════════════════════════════════


class TestWorkflowTemplates:
    """Tests for workflow template loading and validation."""

    TEMPLATES_DIR = Path(__file__).parent.parent.parent.parent.parent / "templates" / "workflows"

    def test_intern_simple_template_exists(self):
        """Test intern-simple.yaml exists and is valid."""
        template_path = self.TEMPLATES_DIR / "intern-simple.yaml"
        assert template_path.exists(), f"Template not found: {template_path}"

        data = yaml.safe_load(template_path.read_text())
        assert data["name"] == "intern-simple"
        assert data["project_type"] == "helix_internal"
        assert data["complexity"] == "simple"
        assert data["max_retries"] == 3

    def test_intern_complex_template_exists(self):
        """Test intern-complex.yaml exists and is valid."""
        template_path = self.TEMPLATES_DIR / "intern-complex.yaml"
        assert template_path.exists()

        data = yaml.safe_load(template_path.read_text())
        assert data["name"] == "intern-complex"
        assert data["complexity"] == "complex"
        assert "dynamic_phase_template" in data

    def test_extern_simple_template_exists(self):
        """Test extern-simple.yaml exists and is valid."""
        template_path = self.TEMPLATES_DIR / "extern-simple.yaml"
        assert template_path.exists()

        data = yaml.safe_load(template_path.read_text())
        assert data["project_type"] == "external"

    def test_extern_complex_template_exists(self):
        """Test extern-complex.yaml exists and is valid."""
        template_path = self.TEMPLATES_DIR / "extern-complex.yaml"
        assert template_path.exists()

        data = yaml.safe_load(template_path.read_text())
        assert data["complexity"] == "complex"

    def test_all_templates_have_required_fields(self):
        """Test all templates have required fields."""
        required_fields = ["name", "project_type", "complexity", "max_retries", "phases"]

        for template_file in self.TEMPLATES_DIR.glob("*.yaml"):
            data = yaml.safe_load(template_file.read_text())
            for field in required_fields:
                assert field in data, f"Missing {field} in {template_file.name}"

    def test_phases_have_verify_agent_flag(self):
        """Test phases have verify_agent configuration."""
        template_path = self.TEMPLATES_DIR / "intern-simple.yaml"
        data = yaml.safe_load(template_path.read_text())

        phases_with_verify = [p for p in data["phases"] if p.get("verify_agent")]
        assert len(phases_with_verify) > 0, "No phases have verify_agent=true"


# ═══════════════════════════════════════════════════════════════════════════════
# Test: Sub-Agent Verification (ADR-025)
# ═══════════════════════════════════════════════════════════════════════════════


class TestSubAgentVerification:
    """Tests for sub-agent verification system."""

    def setup_method(self):
        """Create temp directory for tests."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Cleanup temp directory."""
        shutil.rmtree(self.temp_dir)

    @pytest.mark.asyncio
    async def test_verification_success(self):
        """Test successful verification passes."""
        from helix.verification.sub_agent import SubAgentVerifier, VerificationResult

        verifier = SubAgentVerifier(max_retries=3)

        # Mock successful verification
        with patch.object(
            verifier, "verify_phase", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = VerificationResult(
                success=True,
                checks_passed=["All checks passed"],
            )

            result, attempts = await verifier.verify_with_retries(
                phase_output=self.temp_dir,
                quality_gate={"type": "files_exist"},
            )

            assert result.success is True
            assert attempts == 1

    @pytest.mark.asyncio
    async def test_verification_retry_on_failure(self):
        """Test verification retries on failure."""
        from helix.verification.sub_agent import SubAgentVerifier, VerificationResult

        verifier = SubAgentVerifier(max_retries=3)
        call_count = 0

        async def mock_verify(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return VerificationResult(success=False, feedback="Not yet")
            return VerificationResult(success=True)

        with patch.object(verifier, "verify_phase", side_effect=mock_verify):
            result, attempts = await verifier.verify_with_retries(
                phase_output=self.temp_dir,
                quality_gate={"type": "files_exist"},
            )

            assert result.success is True
            assert attempts == 3

    @pytest.mark.asyncio
    async def test_verification_exhausted_retries(self):
        """Test verification fails after max retries."""
        from helix.verification.sub_agent import SubAgentVerifier, VerificationResult

        verifier = SubAgentVerifier(max_retries=3)

        with patch.object(
            verifier, "verify_phase", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = VerificationResult(
                success=False,
                feedback="Always fails",
                errors=["Permanent error"],
            )

            result, attempts = await verifier.verify_with_retries(
                phase_output=self.temp_dir,
                quality_gate={"type": "files_exist"},
            )

            assert result.success is False
            assert attempts == 3
            assert mock_verify.call_count == 3

    @pytest.mark.asyncio
    async def test_feedback_channel_creates_file(self):
        """Test feedback channel creates feedback.md."""
        from helix.verification.feedback import FeedbackChannel

        channel = FeedbackChannel(self.temp_dir)
        success = await channel.send("Fix the error", attempt=1)

        assert success is True
        assert channel.feedback_path.exists()
        content = channel.feedback_path.read_text()
        assert "Fix the error" in content
        assert "Attempt**: 1/3" in content

    def test_feedback_channel_clear(self):
        """Test feedback channel clears file."""
        from helix.verification.feedback import FeedbackChannel

        channel = FeedbackChannel(self.temp_dir)
        channel.feedback_path.write_text("test")

        channel.clear()
        assert not channel.feedback_path.exists()

    @pytest.mark.asyncio
    async def test_escalation_creates_file(self):
        """Test escalation handler creates report."""
        from helix.verification.feedback import EscalationHandler

        handler = EscalationHandler(self.temp_dir)
        success = await handler.escalate(
            phase_id="dev-1",
            errors=["Error 1", "Error 2"],
            attempts=3,
        )

        assert success is True
        assert handler.escalation_path.exists()
        content = handler.escalation_path.read_text()
        assert "dev-1" in content
        assert "Error 1" in content


# ═══════════════════════════════════════════════════════════════════════════════
# Test: Dynamic Phase Generation (ADR-026)
# ═══════════════════════════════════════════════════════════════════════════════


class TestDynamicPhaseGeneration:
    """Tests for dynamic phase generation system."""

    def setup_method(self):
        """Create temp directory for tests."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Cleanup temp directory."""
        shutil.rmtree(self.temp_dir)

    @pytest.mark.asyncio
    async def test_planning_agent_generates_phases(self):
        """Test planning agent generates 1-5 phases."""
        from helix.planning.agent import PlanningAgent

        agent = PlanningAgent(max_phases=5)

        mock_result = MagicMock()
        mock_result.stdout = '''
```yaml
feasibility_needed: false
reasoning: "Clear requirements"
phases:
  - id: dev-1
    name: "Data Layer"
    type: development
    description: "Implement data models"
    estimated_sessions: 1
    dependencies: []
  - id: dev-2
    name: "API Layer"
    type: development
    description: "Build API"
    estimated_sessions: 2
    dependencies: [dev-1]
```
'''
        mock_result.output_json = None

        with patch.object(agent.runner, "run_phase", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_result

            plan = await agent.analyze_and_plan(
                "Build data pipeline with ETL"
            )

            assert 1 <= len(plan.phases) <= 5
            assert plan.phases[0].id == "dev-1"
            assert "dev-1" in plan.phases[1].dependencies

    @pytest.mark.asyncio
    async def test_planning_agent_recommends_feasibility(self):
        """Test planning agent recommends feasibility for unclear scope."""
        from helix.planning.agent import PlanningAgent

        agent = PlanningAgent(max_phases=5)

        mock_result = MagicMock()
        mock_result.stdout = '''
```yaml
feasibility_needed: true
reasoning: "Complex integration with unclear scope"
phases:
  - id: dev-1
    name: "Core"
    type: development
    description: "Build core"
    estimated_sessions: 2
    dependencies: []
```
'''
        mock_result.output_json = None

        with patch.object(agent.runner, "run_phase", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_result

            plan = await agent.analyze_and_plan(
                "Migrate entire system to new architecture"
            )

            assert plan.feasibility_needed is True

    def test_phase_generator_creates_yaml(self):
        """Test phase generator creates valid phases.yaml."""
        from helix.planning.agent import ProjectPlan, PlannedPhase
        from helix.planning.phase_generator import PhaseGenerator

        generator = PhaseGenerator()
        plan = ProjectPlan(
            phases=[
                PlannedPhase(id="dev-1", name="Phase 1", type="development", description="Desc"),
            ],
            feasibility_needed=False,
        )

        phases_path = generator.generate_phases_yaml(plan, self.temp_dir)

        assert phases_path.exists()
        content = phases_path.read_text()
        data = yaml.safe_load(content.split("---", 1)[-1])

        assert data["project"]["generated"] is True
        assert any(p["id"] == "dev-1" for p in data["phases"])

    def test_phase_generator_creates_claude_md(self):
        """Test phase generator creates CLAUDE.md files."""
        from helix.planning.agent import ProjectPlan, PlannedPhase
        from helix.planning.phase_generator import PhaseGenerator

        generator = PhaseGenerator()
        plan = ProjectPlan(
            phases=[
                PlannedPhase(id="dev-1", name="Implementation", type="development", description="Build it"),
            ],
        )

        claude_paths = generator.generate_phase_claudes(plan, self.temp_dir)

        assert len(claude_paths) == 1
        assert claude_paths[0].exists()

        content = claude_paths[0].read_text()
        assert "Implementation" in content
        assert "Build it" in content

    def test_complexity_estimation(self):
        """Test complexity estimation heuristics."""
        from helix.planning.agent import PlanningAgent

        agent = PlanningAgent()

        # High complexity
        assert agent.estimate_complexity("Refactor distributed architecture") == "high"

        # Medium complexity
        assert agent.estimate_complexity("Add authentication API") == "medium"

        # Low complexity
        assert agent.estimate_complexity("Fix button color") == "low"


# ═══════════════════════════════════════════════════════════════════════════════
# Test: Consultant Workflow Knowledge (ADR-024)
# ═══════════════════════════════════════════════════════════════════════════════


class TestConsultantWorkflowKnowledge:
    """Tests for consultant workflow integration."""

    CONSULTANT_TEMPLATE = Path(__file__).parent.parent.parent.parent.parent / "templates" / "consultant" / "session.md.j2"
    WORKFLOW_GUIDE = Path(__file__).parent.parent.parent.parent.parent / "templates" / "consultant" / "workflow-guide.md"

    def test_consultant_template_has_workflow_section(self):
        """Test consultant template includes workflow section."""
        assert self.CONSULTANT_TEMPLATE.exists()

        content = self.CONSULTANT_TEMPLATE.read_text()
        assert "Workflows starten" in content
        assert "intern-simple" in content
        assert "intern-complex" in content
        assert "extern-simple" in content
        assert "extern-complex" in content

    def test_consultant_template_has_api_docs(self):
        """Test consultant template documents API endpoints."""
        content = self.CONSULTANT_TEMPLATE.read_text()
        assert "/helix/execute" in content
        assert "/helix/jobs" in content

    def test_workflow_guide_exists(self):
        """Test workflow-guide.md exists."""
        assert self.WORKFLOW_GUIDE.exists()

        content = self.WORKFLOW_GUIDE.read_text()
        assert "Workflow-Matrix" in content
        assert "Entscheidungslogik" in content

    def test_workflow_guide_has_examples(self):
        """Test workflow guide has example dialogs."""
        content = self.WORKFLOW_GUIDE.read_text()
        assert "Beispiel" in content or "Example" in content


# ═══════════════════════════════════════════════════════════════════════════════
# Integration Test: Full Workflow
# ═══════════════════════════════════════════════════════════════════════════════


class TestFullWorkflow:
    """Integration tests for complete workflow execution."""

    def setup_method(self):
        """Create temp directory for tests."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Cleanup temp directory."""
        shutil.rmtree(self.temp_dir)

    @pytest.mark.asyncio
    async def test_complete_simple_workflow_setup(self):
        """Test setting up a complete simple workflow."""
        from helix.planning.agent import PlanningAgent, PlannedPhase, ProjectPlan
        from helix.planning.phase_generator import PhaseGenerator
        from helix.verification.sub_agent import SubAgentVerifier, VerificationResult
        from helix.verification.feedback import FeedbackChannel

        # 1. Create project structure
        project_dir = self.temp_dir / "test-project"
        project_dir.mkdir()

        # 2. Generate phases (simulating planning)
        plan = ProjectPlan(
            phases=[
                PlannedPhase(
                    id="dev-1",
                    name="Implementation",
                    type="development",
                    description="Implement the feature",
                    estimated_sessions=1,
                ),
            ],
            feasibility_needed=False,
        )

        generator = PhaseGenerator()
        phases_yaml = generator.generate_phases_yaml(plan, project_dir)
        claude_files = generator.generate_phase_claudes(plan, project_dir)

        assert phases_yaml.exists()
        assert len(claude_files) == 1

        # 3. Simulate verification
        verifier = SubAgentVerifier(max_retries=3)
        feedback = FeedbackChannel(project_dir / "phases" / "1")

        with patch.object(
            verifier, "verify_phase", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = VerificationResult(success=True)

            result, attempts = await verifier.verify_with_retries(
                phase_output=project_dir / "phases" / "1" / "output",
                quality_gate={"type": "files_exist"},
            )

            assert result.success is True

        # 4. Verify project structure
        assert (project_dir / "phases.yaml").exists()
        assert (project_dir / "phases" / "1" / "CLAUDE.md").exists()
        assert (project_dir / "phases" / "1" / "output").is_dir()


# ═══════════════════════════════════════════════════════════════════════════════
# Smoke Tests (API not required)
# ═══════════════════════════════════════════════════════════════════════════════


class TestSmokeTests:
    """Quick smoke tests that don't require API."""

    def test_verification_module_imports(self):
        """Test verification module can be imported."""
        from helix.verification import SubAgentVerifier, VerificationResult, FeedbackChannel
        assert SubAgentVerifier is not None
        assert VerificationResult is not None
        assert FeedbackChannel is not None

    def test_planning_module_imports(self):
        """Test planning module can be imported."""
        from helix.planning import PlanningAgent, PlannedPhase, ProjectPlan, PhaseGenerator
        assert PlanningAgent is not None
        assert PlannedPhase is not None
        assert ProjectPlan is not None
        assert PhaseGenerator is not None

    def test_workflow_templates_directory_exists(self):
        """Test templates/workflows directory exists."""
        templates_dir = Path(__file__).parent.parent.parent.parent.parent / "templates" / "workflows"
        assert templates_dir.is_dir()

    def test_all_four_workflow_templates_exist(self):
        """Test all four workflow templates exist."""
        templates_dir = Path(__file__).parent.parent.parent.parent.parent / "templates" / "workflows"

        expected = [
            "intern-simple.yaml",
            "intern-complex.yaml",
            "extern-simple.yaml",
            "extern-complex.yaml",
        ]

        for template_name in expected:
            assert (templates_dir / template_name).exists(), f"Missing: {template_name}"
