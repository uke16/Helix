"""Tests for Planning Agent module.

Tests dynamic phase generation and phase file creation.
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import tempfile
import shutil
import yaml

from helix.planning.agent import PlanningAgent, PlannedPhase, ProjectPlan
from helix.planning.phase_generator import PhaseGenerator


class TestPlannedPhase:
    """Tests for PlannedPhase dataclass."""

    def test_create_phase(self):
        """Test creating a planned phase."""
        phase = PlannedPhase(
            id="dev-1",
            name="Data Layer",
            type="development",
            description="Implement data models",
            estimated_sessions=1,
            dependencies=[],
        )
        assert phase.id == "dev-1"
        assert phase.name == "Data Layer"
        assert phase.type == "development"
        assert phase.estimated_sessions == 1

    def test_phase_with_dependencies(self):
        """Test phase with dependencies."""
        phase = PlannedPhase(
            id="dev-2",
            name="API Layer",
            type="development",
            description="Build API",
            dependencies=["dev-1"],
        )
        assert "dev-1" in phase.dependencies


class TestProjectPlan:
    """Tests for ProjectPlan dataclass."""

    def test_create_plan(self):
        """Test creating a project plan."""
        phases = [
            PlannedPhase(id="dev-1", name="Phase 1", type="development", description="", estimated_sessions=1),
            PlannedPhase(id="dev-2", name="Phase 2", type="development", description="", estimated_sessions=2),
        ]
        plan = ProjectPlan(phases=phases, feasibility_needed=False)

        assert len(plan.phases) == 2
        assert plan.total_estimated_sessions == 3  # 1 + 2

    def test_plan_with_feasibility(self):
        """Test plan that needs feasibility study."""
        plan = ProjectPlan(
            phases=[PlannedPhase(id="dev-1", name="P1", type="development", description="")],
            feasibility_needed=True,
            reasoning="Unclear requirements",
        )
        assert plan.feasibility_needed is True


class TestPlanningAgent:
    """Tests for PlanningAgent class."""

    def test_init_default_max_phases(self):
        """Test agent initializes with default max_phases."""
        agent = PlanningAgent()
        assert agent.max_phases == 5

    def test_init_custom_max_phases(self):
        """Test agent with custom max_phases."""
        agent = PlanningAgent(max_phases=3)
        assert agent.max_phases == 3

    def test_init_caps_at_5(self):
        """Test max_phases is capped at 5."""
        agent = PlanningAgent(max_phases=10)
        assert agent.max_phases == 5

    @pytest.mark.asyncio
    async def test_analyze_and_plan(self):
        """Test analyzing project and generating plan."""
        agent = PlanningAgent(max_phases=3)

        mock_result = MagicMock()
        mock_result.stdout = '''
```yaml
feasibility_needed: false
reasoning: "Simple project with clear scope"
phases:
  - id: dev-1
    name: "Implementation"
    type: development
    description: "Implement the feature"
    estimated_sessions: 1
    dependencies: []
```
'''
        mock_result.output_json = None

        with patch.object(agent.runner, "run_phase", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_result

            plan = await agent.analyze_and_plan("Add a new button")

            assert len(plan.phases) == 1
            assert plan.phases[0].name == "Implementation"
            assert plan.feasibility_needed is False

    @pytest.mark.asyncio
    async def test_analyze_with_feasibility(self):
        """Test plan that recommends feasibility."""
        agent = PlanningAgent()

        mock_result = MagicMock()
        mock_result.stdout = '''
```yaml
feasibility_needed: true
reasoning: "Complex integration with unclear scope"
phases:
  - id: dev-1
    name: "Core System"
    type: development
    description: "Build core"
    estimated_sessions: 2
    dependencies: []
  - id: dev-2
    name: "Integration"
    type: development
    description: "Integrate systems"
    estimated_sessions: 2
    dependencies: [dev-1]
```
'''
        mock_result.output_json = None

        with patch.object(agent.runner, "run_phase", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_result

            plan = await agent.analyze_and_plan("Migrate entire system")

            assert plan.feasibility_needed is True
            assert len(plan.phases) == 2

    def test_extract_yaml(self):
        """Test YAML extraction from text."""
        agent = PlanningAgent()

        text = '''Some text
```yaml
key: value
```
More text'''

        yaml_content = agent._extract_yaml(text)
        assert yaml_content == "key: value"

    def test_extract_yaml_no_block(self):
        """Test extraction when no YAML block."""
        agent = PlanningAgent()

        text = "Just plain text"
        assert agent._extract_yaml(text) is None

    def test_data_to_plan(self):
        """Test converting data dict to ProjectPlan."""
        agent = PlanningAgent(max_phases=2)

        data = {
            "feasibility_needed": True,
            "reasoning": "Test reasoning",
            "phases": [
                {"id": "p1", "name": "Phase 1", "type": "development", "description": "Desc 1"},
                {"id": "p2", "name": "Phase 2", "type": "test", "description": "Desc 2"},
                {"id": "p3", "name": "Phase 3", "type": "docs", "description": "Desc 3"},
            ],
        }

        plan = agent._data_to_plan(data)

        # Should be capped at max_phases=2
        assert len(plan.phases) == 2
        assert plan.feasibility_needed is True
        assert plan.reasoning == "Test reasoning"

    def test_estimate_complexity_high(self):
        """Test complexity estimation for high complexity."""
        agent = PlanningAgent()

        desc = "Refactor the entire architecture for distributed scalability"
        assert agent.estimate_complexity(desc) == "high"

    def test_estimate_complexity_medium(self):
        """Test complexity estimation for medium complexity."""
        agent = PlanningAgent()

        desc = "Add authentication to the API"
        assert agent.estimate_complexity(desc) == "medium"

    def test_estimate_complexity_low(self):
        """Test complexity estimation for low complexity."""
        agent = PlanningAgent()

        desc = "Fix the button color"
        assert agent.estimate_complexity(desc) == "low"


class TestPhaseGenerator:
    """Tests for PhaseGenerator class."""

    def setup_method(self):
        """Create temp directory for tests."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Cleanup temp directory."""
        shutil.rmtree(self.temp_dir)

    def test_generate_phases_yaml(self):
        """Test generating phases.yaml file."""
        generator = PhaseGenerator()

        plan = ProjectPlan(
            phases=[
                PlannedPhase(id="dev-1", name="Phase 1", type="development", description="Desc 1"),
            ],
            feasibility_needed=False,
        )

        phases_path = generator.generate_phases_yaml(plan, self.temp_dir)

        assert phases_path.exists()
        content = phases_path.read_text()
        data = yaml.safe_load(content.split("---", 1)[-1])  # Skip header

        assert data["project"]["type"] == "complex"
        assert data["project"]["generated"] is True
        assert len(data["phases"]) >= 3  # dev-1 + verify + documentation

    def test_generate_phases_yaml_with_feasibility(self):
        """Test phases.yaml includes feasibility when needed."""
        generator = PhaseGenerator()

        plan = ProjectPlan(
            phases=[
                PlannedPhase(id="dev-1", name="Phase 1", type="development", description="Desc"),
            ],
            feasibility_needed=True,
        )

        phases_path = generator.generate_phases_yaml(plan, self.temp_dir)

        content = phases_path.read_text()
        data = yaml.safe_load(content.split("---", 1)[-1])

        # First phase should be feasibility
        assert data["phases"][0]["id"] == "feasibility"
        assert data["phases"][0]["optional"] is True

    def test_generate_phase_claudes(self):
        """Test generating CLAUDE.md files."""
        generator = PhaseGenerator()

        plan = ProjectPlan(
            phases=[
                PlannedPhase(id="dev-1", name="Phase 1", type="development", description="First phase"),
                PlannedPhase(id="dev-2", name="Phase 2", type="test", description="Second phase", dependencies=["dev-1"]),
            ],
            feasibility_needed=False,
        )

        claude_paths = generator.generate_phase_claudes(plan, self.temp_dir)

        assert len(claude_paths) == 2

        # Check first phase
        phase1_claude = self.temp_dir / "phases" / "1" / "CLAUDE.md"
        assert phase1_claude.exists()
        content1 = phase1_claude.read_text()
        assert "Phase 1" in content1
        assert "First phase" in content1

        # Check second phase has dependency
        phase2_claude = self.temp_dir / "phases" / "2" / "CLAUDE.md"
        content2 = phase2_claude.read_text()
        assert "dev-1" in content2

    def test_generate_phase_claudes_with_feasibility(self):
        """Test CLAUDE.md generation includes feasibility."""
        generator = PhaseGenerator()

        plan = ProjectPlan(
            phases=[
                PlannedPhase(id="dev-1", name="Development", type="development", description="Dev"),
            ],
            feasibility_needed=True,
        )

        claude_paths = generator.generate_phase_claudes(plan, self.temp_dir)

        # Should have feasibility + dev phase
        assert len(claude_paths) == 2

        # Phase 1 should be feasibility
        phase1_claude = self.temp_dir / "phases" / "1" / "CLAUDE.md"
        content = phase1_claude.read_text()
        assert "Feasibility" in content

    def test_generate_decomposed_yaml(self):
        """Test generating decomposed-phases.yaml."""
        generator = PhaseGenerator()

        plan = ProjectPlan(
            phases=[
                PlannedPhase(id="dev-1", name="P1", type="development", description="D1", estimated_sessions=2),
            ],
            feasibility_needed=True,
            reasoning="Test reasoning",
        )

        decomposed_path = generator.generate_decomposed_yaml(plan, self.temp_dir)

        assert decomposed_path.exists()
        data = yaml.safe_load(decomposed_path.read_text())

        assert data["feasibility_needed"] is True
        assert data["reasoning"] == "Test reasoning"
        assert len(data["phases"]) == 1

    def test_output_directories_created(self):
        """Test that output directories are created."""
        generator = PhaseGenerator()

        plan = ProjectPlan(
            phases=[
                PlannedPhase(id="dev-1", name="Phase", type="development", description=""),
            ],
        )

        generator.generate_phase_claudes(plan, self.temp_dir)

        # Check directories exist
        assert (self.temp_dir / "phases" / "1").is_dir()
        assert (self.temp_dir / "phases" / "1" / "output").is_dir()


class TestIntegration:
    """Integration tests for the planning system."""

    def setup_method(self):
        """Create temp directory."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Cleanup."""
        shutil.rmtree(self.temp_dir)

    @pytest.mark.asyncio
    async def test_full_planning_workflow(self):
        """Test complete planning and generation workflow."""
        agent = PlanningAgent(max_phases=3)
        generator = PhaseGenerator()

        # Mock the LLM call
        mock_result = MagicMock()
        mock_result.stdout = '''
```yaml
feasibility_needed: false
reasoning: "Clear requirements"
phases:
  - id: dev-1
    name: "Implementation"
    type: development
    description: "Implement feature"
    estimated_sessions: 1
    dependencies: []
```
'''
        mock_result.output_json = None

        with patch.object(agent.runner, "run_phase", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_result

            # Generate plan
            plan = await agent.analyze_and_plan("Add new feature")

            # Generate files
            phases_yaml = generator.generate_phases_yaml(plan, self.temp_dir)
            claude_files = generator.generate_phase_claudes(plan, self.temp_dir)
            decomposed = generator.generate_decomposed_yaml(plan, self.temp_dir)

            # Verify all files created
            assert phases_yaml.exists()
            assert len(claude_files) == 1
            assert decomposed.exists()

            # Verify phases.yaml is valid
            content = phases_yaml.read_text()
            data = yaml.safe_load(content.split("---", 1)[-1])
            assert data["project"]["generated"] is True
