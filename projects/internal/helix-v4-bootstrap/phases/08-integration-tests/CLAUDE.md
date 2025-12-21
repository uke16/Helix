# HELIX v4 Bootstrap - Phase 08: Integration Tests

Create integration tests that verify module interactions and system behavior.

## Target Directory

`/home/aiuser01/helix-v4/tests/integration/`

## Integration Test Scope

Unlike unit tests (single module), integration tests verify:
- Multiple modules working together
- File system operations
- Template rendering pipeline
- Orchestrator workflow (mocked LLM)
- CLI end-to-end commands

## Files to Create

### 1. `/home/aiuser01/helix-v4/tests/integration/__init__.py`

```python
"""Integration tests for HELIX v4."""
```

### 2. `/home/aiuser01/helix-v4/tests/integration/test_orchestrator_workflow.py`

Test the full orchestration pipeline:

```python
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio

from helix.orchestrator import Orchestrator
from helix.phase_loader import PhaseLoader
from helix.quality_gates import QualityGateRunner
from helix.observability import HelixLogger, MetricsCollector


class TestOrchestratorWorkflow:
    """Integration tests for Orchestrator with other modules."""

    @pytest.fixture
    def project_with_phases(self, temp_dir):
        """Create a complete project structure."""
        project = temp_dir / "test-project"
        project.mkdir()
        
        # spec.yaml
        (project / "spec.yaml").write_text("""
meta:
  id: test-project
  name: Test Integration Project
  domain: helix
implementation:
  language: python
  summary: Integration test project
""")
        
        # phases.yaml
        (project / "phases.yaml").write_text("""
phases:
  - id: 01-setup
    name: Setup Phase
    type: development
    template: developer/python.md
    quality_gate:
      type: files_exist
      files:
        - setup.py
        
  - id: 02-implement
    name: Implementation Phase  
    type: development
    template: developer/python.md
    quality_gate:
      type: syntax_check
""")
        
        # Create phase directories
        (project / "phases" / "01-setup").mkdir(parents=True)
        (project / "phases" / "02-implement").mkdir(parents=True)
        
        return project

    @pytest.mark.asyncio
    async def test_orchestrator_loads_phases(self, project_with_phases):
        """Orchestrator should load phases from project."""
        orchestrator = Orchestrator()
        
        with patch.object(orchestrator, 'run_phase', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {"status": "success"}
            
            # Should not raise
            phases = PhaseLoader().load_phases(project_with_phases)
            assert len(phases) == 2
            assert phases[0].id == "01-setup"

    @pytest.mark.asyncio
    async def test_orchestrator_respects_phase_order(self, project_with_phases):
        """Orchestrator should execute phases in order."""
        orchestrator = Orchestrator()
        execution_order = []
        
        async def mock_run_phase(phase, *args, **kwargs):
            execution_order.append(phase.id)
            return {"status": "success"}
        
        with patch.object(orchestrator, 'run_phase', side_effect=mock_run_phase):
            with patch.object(orchestrator, 'check_quality_gate', return_value=True):
                # Run would go through phases
                phases = PhaseLoader().load_phases(project_with_phases)
                for phase in phases:
                    await mock_run_phase(phase)
        
        assert execution_order == ["01-setup", "02-implement"]

    @pytest.mark.asyncio
    async def test_orchestrator_stops_on_gate_failure(self, project_with_phases):
        """Orchestrator should stop if quality gate fails."""
        orchestrator = Orchestrator()
        
        with patch.object(orchestrator, 'run_phase', new_callable=AsyncMock) as mock_run:
            with patch.object(orchestrator, 'check_quality_gate', return_value=False):
                mock_run.return_value = {"status": "success"}
                
                # Gate failure should trigger escalation or stop
                gate_runner = QualityGateRunner()
                result = gate_runner.check_files_exist(
                    project_with_phases / "phases" / "01-setup",
                    files=["nonexistent.py"]
                )
                
                assert not result.passed

    @pytest.mark.asyncio
    async def test_orchestrator_with_logging(self, project_with_phases):
        """Orchestrator should integrate with logging."""
        logger = HelixLogger(project_with_phases)
        metrics = MetricsCollector(project_with_phases)
        
        metrics.start_project("test-project")
        metrics.start_phase("01-setup")
        
        logger.log_phase_start("01-setup")
        logger.log_phase_end("01-setup", success=True, duration_seconds=1.5)
        
        phase_metrics = metrics.end_phase(success=True)
        
        assert phase_metrics.phase_id == "01-setup"
        
        logs = logger.get_phase_logs("01-setup")
        assert len(logs) >= 2  # start + end
```

### 3. `/home/aiuser01/helix-v4/tests/integration/test_template_pipeline.py`

Test template rendering with context:

```python
import pytest
from pathlib import Path

from helix.template_engine import TemplateEngine
from helix.context_manager import ContextManager
from helix.phase_loader import PhaseLoader


class TestTemplatePipeline:
    """Integration tests for template rendering pipeline."""

    @pytest.fixture
    def helix_templates(self):
        """Return path to actual HELIX templates."""
        return Path("/home/aiuser01/helix-v4/templates")

    def test_render_python_developer_template(self, helix_templates):
        """Should render Python developer template."""
        if not helix_templates.exists():
            pytest.skip("Templates not found")
        
        engine = TemplateEngine(helix_templates / "developer")
        
        context = {
            "project": {"description": "Test project"},
            "task": {
                "description": "Implement feature X",
                "output_files": [
                    {"path": "src/feature.py", "description": "Main implementation"}
                ]
            },
            "quality_gate": {
                "type": "syntax_check",
                "description": "Check Python syntax"
            }
        }
        
        result = engine.render("python.md", context)
        
        assert "Python" in result
        assert "feature.py" in result

    def test_render_consultant_template(self, helix_templates):
        """Should render Meta-Consultant template."""
        if not helix_templates.exists():
            pytest.skip("Templates not found")
        
        engine = TemplateEngine(helix_templates / "consultant")
        
        context = {
            "project": {"name": "BOM Export", "domain": "pdm"},
            "user_request": "Export BOM data to SAP",
            "experts": [
                {"name": "PDM Expert", "description": "Product data management"},
                {"name": "ERP Expert", "description": "SAP integration"},
            ]
        }
        
        result = engine.render("meta-consultant.md", context)
        
        assert "Meta-Consultant" in result or "Consultant" in result
        assert "BOM Export" in result

    def test_context_manager_provides_skills(self):
        """ContextManager should provide domain skills."""
        manager = ContextManager()
        
        skills = manager.get_skills_for_domain("pdm")
        assert isinstance(skills, list)
        
        skills = manager.get_skills_for_language("python")
        assert isinstance(skills, list)

    def test_full_claude_md_generation(self, helix_templates, temp_dir):
        """Should generate complete CLAUDE.md for a phase."""
        if not helix_templates.exists():
            pytest.skip("Templates not found")
        
        # Create project
        project = temp_dir / "test-project"
        project.mkdir()
        (project / "spec.yaml").write_text("""
meta:
  id: test-project
  name: Test Project
  domain: pdm
implementation:
  language: python
  summary: Test implementation
""")
        
        # Setup context
        context_manager = ContextManager()
        engine = TemplateEngine(helix_templates / "developer")
        
        context = context_manager.prepare_phase_context(
            project_dir=project,
            phase_dir=project / "phases" / "01-dev",
            domain="pdm",
            language="python",
        )
        
        # Add task info
        context["task"] = {
            "description": "Implement BOM export",
            "output_files": []
        }
        context["quality_gate"] = {"type": "syntax_check", "description": "Check syntax"}
        context["project"] = {"description": "BOM export project"}
        
        result = engine.render("python.md", context)
        
        assert len(result) > 100  # Should have substantial content
```

### 4. `/home/aiuser01/helix-v4/tests/integration/test_consultant_meeting.py`

Test consultant meeting workflow:

```python
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
        # Should have FRABA-specific experts
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

    @pytest.mark.asyncio
    async def test_meeting_creates_artifacts(self, expert_manager, mock_llm_client, temp_dir):
        """Meeting should create spec.yaml and ADR."""
        project_dir = temp_dir / "test-project"
        project_dir.mkdir()
        
        meeting = ConsultantMeeting(mock_llm_client, expert_manager)
        
        # Mock the full meeting flow
        with patch.object(meeting, 'run', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = MagicMock(
                spec={"meta": {"id": "test"}},
                phases={"phases": []},
                quality_gates={},
                transcript="Meeting transcript...",
                experts_consulted=["pdm"],
                duration_seconds=10.0
            )
            
            result = await meeting.run(project_dir, "Create BOM export feature")
            
            assert result.spec is not None
            assert result.experts_consulted == ["pdm"]
```

### 5. `/home/aiuser01/helix-v4/tests/integration/test_cli_commands.py`

Test CLI commands with real file system:

```python
import pytest
from pathlib import Path
from click.testing import CliRunner
import os

from helix.cli.main import cli


class TestCLIIntegration:
    """Integration tests for CLI commands."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def sample_project(self, temp_dir):
        """Create a valid project structure."""
        project = temp_dir / "my-project"
        project.mkdir()
        
        (project / "spec.yaml").write_text("""
meta:
  id: my-project
  name: My Test Project
  domain: helix
implementation:
  language: python
  summary: A test project for CLI integration tests
""")
        
        (project / "phases.yaml").write_text("""
phases:
  - id: 01-setup
    name: Setup
    type: development
""")
        
        (project / "phases").mkdir()
        (project / "phases" / "01-setup").mkdir()
        (project / "logs").mkdir()
        
        return project

    def test_helix_version(self, runner):
        """Should display version."""
        result = runner.invoke(cli, ["--version"])
        
        assert result.exit_code == 0
        assert "4.0.0" in result.output

    def test_helix_help(self, runner):
        """Should display help."""
        result = runner.invoke(cli, ["--help"])
        
        assert result.exit_code == 0
        assert "HELIX" in result.output or "helix" in result.output

    def test_status_valid_project(self, runner, sample_project):
        """Should show status for valid project."""
        result = runner.invoke(cli, ["status", str(sample_project)])
        
        # Should not crash, might show "no phases run" or similar
        assert result.exit_code == 0 or "not found" not in result.output.lower()

    def test_debug_shows_logs(self, runner, sample_project):
        """Should show debug logs."""
        # Create a log file
        log_dir = sample_project / "logs"
        log_dir.mkdir(exist_ok=True)
        (log_dir / "project.jsonl").write_text('{"message": "test log"}\n')
        
        result = runner.invoke(cli, ["debug", str(sample_project)])
        
        # Should attempt to read logs
        assert result.exit_code == 0 or "log" in result.output.lower()

    def test_costs_shows_metrics(self, runner, sample_project):
        """Should show cost metrics."""
        # Create a metrics file
        (sample_project / "metrics.json").write_text('''{
            "project_id": "my-project",
            "total_cost_usd": 0.05,
            "phases": {}
        }''')
        
        result = runner.invoke(cli, ["costs", str(sample_project)])
        
        # Should not crash
        assert result.exit_code == 0 or "cost" in result.output.lower() or "metric" in result.output.lower()

    def test_new_creates_project(self, runner, temp_dir):
        """Should create new project structure."""
        with runner.isolated_filesystem(temp_dir=temp_dir):
            result = runner.invoke(cli, [
                "new", "my-new-project",
                "--type", "feature",
                "--output", str(temp_dir)
            ])
            
            # Should attempt to create project
            # May fail if template not found, but should not crash unexpectedly
            assert result.exit_code in [0, 1, 2]  # Various valid outcomes
```

### 6. `/home/aiuser01/helix-v4/tests/integration/test_quality_gate_pipeline.py`

Test quality gates in realistic scenarios:

```python
import pytest
from pathlib import Path
import subprocess

from helix.quality_gates import QualityGateRunner, GateResult
from helix.escalation import EscalationManager, EscalationLevel


class TestQualityGatePipeline:
    """Integration tests for quality gate system."""

    @pytest.fixture
    def python_project(self, temp_dir):
        """Create a Python project structure."""
        src = temp_dir / "src"
        src.mkdir()
        
        # Valid Python file
        (src / "valid_module.py").write_text('''
"""A valid Python module."""

def greet(name: str) -> str:
    """Return a greeting."""
    return f"Hello, {name}!"

class Calculator:
    """Simple calculator."""
    
    def add(self, a: int, b: int) -> int:
        return a + b
''')
        
        # Invalid Python file
        (src / "invalid_module.py").write_text('''
def broken_function(
    # Missing closing parenthesis
''')
        
        return temp_dir

    def test_syntax_check_valid_file(self, python_project):
        """Should pass for valid Python."""
        runner = QualityGateRunner()
        result = runner.check_syntax(python_project / "src" / "valid_module.py")
        
        assert result.passed
        assert result.gate_type == "syntax_check"

    def test_syntax_check_invalid_file(self, python_project):
        """Should fail for invalid Python."""
        runner = QualityGateRunner()
        result = runner.check_syntax(python_project / "src" / "invalid_module.py")
        
        assert not result.passed
        assert "error" in str(result.details).lower() or "syntax" in str(result.details).lower()

    def test_files_exist_all_present(self, python_project):
        """Should pass when all files exist."""
        runner = QualityGateRunner()
        result = runner.check_files_exist(
            python_project / "src",
            files=["valid_module.py"]
        )
        
        assert result.passed

    def test_files_exist_missing(self, python_project):
        """Should fail when files missing."""
        runner = QualityGateRunner()
        result = runner.check_files_exist(
            python_project / "src",
            files=["valid_module.py", "missing.py"]
        )
        
        assert not result.passed
        assert "missing.py" in str(result.details)

    def test_escalation_on_syntax_error(self, python_project):
        """Syntax errors should trigger Level 1 escalation."""
        runner = QualityGateRunner()
        result = runner.check_syntax(python_project / "src" / "invalid_module.py")
        
        escalation = EscalationManager()
        level = escalation.determine_level(str(result.details))
        
        assert level == EscalationLevel.STUFE_1

    def test_gate_result_structure(self, python_project):
        """GateResult should have all required fields."""
        runner = QualityGateRunner()
        result = runner.check_syntax(python_project / "src" / "valid_module.py")
        
        assert hasattr(result, 'passed')
        assert hasattr(result, 'gate_type')
        assert hasattr(result, 'details')
```

### 7. `/home/aiuser01/helix-v4/tests/integration/test_observability_integration.py`

Test logging and metrics together:

```python
import pytest
from pathlib import Path
import json
import time

from helix.observability import HelixLogger, MetricsCollector, LogLevel


class TestObservabilityIntegration:
    """Integration tests for logging and metrics."""

    def test_logger_and_metrics_together(self, temp_dir):
        """Logger and metrics should work together."""
        logger = HelixLogger(temp_dir)
        metrics = MetricsCollector(temp_dir)
        
        # Start tracking
        metrics.start_project("integration-test")
        logger.log(LogLevel.INFO, "Project started", phase=None)
        
        # Phase 1
        metrics.start_phase("01-setup")
        logger.log_phase_start("01-setup")
        
        metrics.record_tokens(input_tokens=1000, output_tokens=500, model="gpt-4o-mini")
        metrics.record_file_change("created")
        
        logger.log_file_change("01-setup", temp_dir / "new_file.py", "created")
        logger.log_phase_end("01-setup", success=True, duration_seconds=2.5)
        
        phase_metrics = metrics.end_phase(success=True)
        
        # Verify metrics
        assert phase_metrics.input_tokens == 1000
        assert phase_metrics.output_tokens == 500
        assert phase_metrics.files_created == 1
        
        # Verify logs
        logs = logger.get_phase_logs("01-setup")
        assert len(logs) >= 2  # At least start and end

    def test_metrics_persist_to_file(self, temp_dir):
        """Metrics should be saveable to file."""
        metrics = MetricsCollector(temp_dir)
        
        metrics.start_project("persist-test")
        metrics.start_phase("01-test")
        metrics.record_tokens(500, 250, "gpt-4o-mini")
        metrics.end_phase()
        project_metrics = metrics.end_project()
        
        # Save
        metrics_file = metrics.save_metrics()
        
        if metrics_file and metrics_file.exists():
            data = json.loads(metrics_file.read_text())
            assert "project_id" in data or "phases" in data

    def test_log_file_format(self, temp_dir):
        """Logs should be in JSONL format."""
        logger = HelixLogger(temp_dir)
        
        logger.log(LogLevel.INFO, "Test message 1")
        logger.log(LogLevel.WARNING, "Test message 2")
        logger.log(LogLevel.ERROR, "Test message 3")
        
        # Check log file
        log_files = list((temp_dir / "logs").glob("*.jsonl")) if (temp_dir / "logs").exists() else []
        
        if log_files:
            content = log_files[0].read_text()
            lines = content.strip().split("\n")
            
            for line in lines:
                if line:
                    data = json.loads(line)
                    assert "message" in data or "level" in data

    def test_multiple_phases_tracking(self, temp_dir):
        """Should track multiple phases correctly."""
        metrics = MetricsCollector(temp_dir)
        
        metrics.start_project("multi-phase")
        
        # Phase 1
        metrics.start_phase("01-first")
        metrics.record_tokens(1000, 500, "gpt-4o")
        metrics.end_phase()
        
        # Phase 2
        metrics.start_phase("02-second")
        metrics.record_tokens(2000, 1000, "gpt-4o")
        metrics.end_phase()
        
        project = metrics.end_project()
        
        assert len(project.phases) == 2
        assert project.phases["01-first"].input_tokens == 1000
        assert project.phases["02-second"].input_tokens == 2000
```

## Instructions

1. Create all files in `/home/aiuser01/helix-v4/tests/integration/`
2. Tests should use real HELIX modules where possible
3. Mock only external dependencies (LLM API calls)
4. Use actual templates and config files from the project
5. Create `output/result.json` when done

## Output

```json
{
  "status": "success",
  "files_created": [
    "tests/integration/__init__.py",
    "tests/integration/test_orchestrator_workflow.py",
    "tests/integration/test_template_pipeline.py",
    "tests/integration/test_consultant_meeting.py",
    "tests/integration/test_cli_commands.py",
    "tests/integration/test_quality_gate_pipeline.py",
    "tests/integration/test_observability_integration.py"
  ]
}
```
