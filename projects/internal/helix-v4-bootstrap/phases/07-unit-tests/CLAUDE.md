# HELIX v4 Bootstrap - Phase 07: Unit Tests

Create comprehensive unit tests for all HELIX v4 modules.

## Target Directory

`/home/aiuser01/helix-v4/tests/unit/`

## Modules to Test

Located in `/home/aiuser01/helix-v4/src/helix/`:

### Core Modules
- `phase_loader.py` - PhaseLoader, PhaseConfig
- `context_manager.py` - ContextManager
- `template_engine.py` - TemplateEngine
- `spec_validator.py` - SpecValidator
- `quality_gates.py` - QualityGateRunner
- `escalation.py` - EscalationManager
- `llm_client.py` - LLMClient, ModelConfig
- `claude_runner.py` - ClaudeRunner
- `orchestrator.py` - Orchestrator

### Consultant Package
- `consultant/meeting.py` - ConsultantMeeting, MeetingResult
- `consultant/expert_manager.py` - ExpertManager, ExpertConfig

### Observability Package
- `observability/logger.py` - HelixLogger, LogEntry
- `observability/metrics.py` - MetricsCollector, PhaseMetrics

### CLI Package
- `cli/main.py` - CLI entry point
- `cli/commands.py` - All commands

## Files to Create

### 1. `/home/aiuser01/helix-v4/tests/__init__.py`
```python
"""HELIX v4 Test Suite."""
```

### 2. `/home/aiuser01/helix-v4/tests/unit/__init__.py`
```python
"""Unit tests for HELIX v4."""
```

### 3. `/home/aiuser01/helix-v4/tests/conftest.py`

Shared fixtures:

```python
import pytest
from pathlib import Path
import tempfile
import shutil

@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    path = Path(tempfile.mkdtemp())
    yield path
    shutil.rmtree(path, ignore_errors=True)

@pytest.fixture
def sample_project(temp_dir):
    """Create a sample project structure."""
    project = temp_dir / "test-project"
    project.mkdir()
    (project / "spec.yaml").write_text("""
meta:
  id: test-project
  name: Test Project
  domain: helix
implementation:
  language: python
  summary: A test project
""")
    (project / "phases.yaml").write_text("""
phases:
  - id: 01-test
    name: Test Phase
    type: development
""")
    return project

@pytest.fixture
def sample_spec():
    """Return sample spec dictionary."""
    return {
        "meta": {
            "id": "test-project",
            "name": "Test Project",
            "domain": "helix",
        },
        "implementation": {
            "language": "python",
            "summary": "A test project",
        },
    }

@pytest.fixture
def mock_llm_response():
    """Mock LLM response for testing."""
    return {
        "content": [{"type": "text", "text": "Test response"}],
        "usage": {"input_tokens": 100, "output_tokens": 50},
    }
```

### 4. `/home/aiuser01/helix-v4/tests/unit/test_phase_loader.py`

```python
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
```

### 5. `/home/aiuser01/helix-v4/tests/unit/test_spec_validator.py`

```python
import pytest

from helix.spec_validator import SpecValidator


class TestSpecValidator:
    """Tests for SpecValidator."""

    def test_valid_spec(self, sample_spec):
        """Should validate correct spec."""
        validator = SpecValidator()
        result = validator.validate(sample_spec)
        
        assert result.is_valid
        assert len(result.errors) == 0

    def test_missing_meta_id(self, sample_spec):
        """Should fail if meta.id missing."""
        del sample_spec["meta"]["id"]
        
        validator = SpecValidator()
        result = validator.validate(sample_spec)
        
        assert not result.is_valid
        assert any("id" in str(e).lower() for e in result.errors)

    def test_missing_implementation(self, sample_spec):
        """Should fail if implementation missing."""
        del sample_spec["implementation"]
        
        validator = SpecValidator()
        result = validator.validate(sample_spec)
        
        assert not result.is_valid

    def test_validate_from_file(self, sample_project):
        """Should validate spec from file."""
        validator = SpecValidator()
        result = validator.validate_file(sample_project / "spec.yaml")
        
        assert result.is_valid
```

### 6. `/home/aiuser01/helix-v4/tests/unit/test_template_engine.py`

```python
import pytest
from pathlib import Path

from helix.template_engine import TemplateEngine


class TestTemplateEngine:
    """Tests for TemplateEngine."""

    def test_render_simple_template(self, temp_dir):
        """Should render template with variables."""
        # Create test template
        template_dir = temp_dir / "templates"
        template_dir.mkdir()
        (template_dir / "test.md").write_text("Hello {{ name }}!")
        
        engine = TemplateEngine(template_dir)
        result = engine.render("test.md", {"name": "World"})
        
        assert result == "Hello World!"

    def test_render_with_missing_variable(self, temp_dir):
        """Should handle missing variables gracefully."""
        template_dir = temp_dir / "templates"
        template_dir.mkdir()
        (template_dir / "test.md").write_text("Hello {{ name }}!")
        
        engine = TemplateEngine(template_dir)
        # Should not raise, use undefined handling
        result = engine.render("test.md", {})
        assert "Hello" in result

    def test_template_inheritance(self, temp_dir):
        """Should support template inheritance."""
        template_dir = temp_dir / "templates"
        template_dir.mkdir()
        
        (template_dir / "_base.md").write_text("""
# Base
{% block content %}{% endblock %}
""")
        (template_dir / "child.md").write_text("""
{% extends "_base.md" %}
{% block content %}Child content{% endblock %}
""")
        
        engine = TemplateEngine(template_dir)
        result = engine.render("child.md", {})
        
        assert "Base" in result
        assert "Child content" in result
```

### 7. `/home/aiuser01/helix-v4/tests/unit/test_context_manager.py`

```python
import pytest
from pathlib import Path

from helix.context_manager import ContextManager


class TestContextManager:
    """Tests for ContextManager."""

    def test_get_skills_for_domain(self):
        """Should return skills for a domain."""
        manager = ContextManager()
        skills = manager.get_skills_for_domain("pdm")
        
        assert isinstance(skills, list)

    def test_get_skills_for_language(self):
        """Should return skills for a language."""
        manager = ContextManager()
        skills = manager.get_skills_for_language("python")
        
        assert isinstance(skills, list)

    def test_prepare_phase_context(self, sample_project, temp_dir):
        """Should prepare context for phase execution."""
        manager = ContextManager()
        phase_dir = temp_dir / "phase"
        phase_dir.mkdir()
        
        context = manager.prepare_phase_context(
            project_dir=sample_project,
            phase_dir=phase_dir,
            domain="helix",
            language="python",
        )
        
        assert "skills" in context
        assert "project" in context
```

### 8. `/home/aiuser01/helix-v4/tests/unit/test_quality_gates.py`

```python
import pytest
from pathlib import Path

from helix.quality_gates import QualityGateRunner, GateResult


class TestQualityGateRunner:
    """Tests for QualityGateRunner."""

    def test_files_exist_pass(self, temp_dir):
        """Should pass if all files exist."""
        (temp_dir / "test.py").write_text("# test")
        
        runner = QualityGateRunner()
        result = runner.check_files_exist(
            temp_dir,
            files=["test.py"],
        )
        
        assert result.passed
        assert result.gate_type == "files_exist"

    def test_files_exist_fail(self, temp_dir):
        """Should fail if files missing."""
        runner = QualityGateRunner()
        result = runner.check_files_exist(
            temp_dir,
            files=["missing.py"],
        )
        
        assert not result.passed
        assert "missing.py" in str(result.details)

    def test_syntax_check_python_valid(self, temp_dir):
        """Should pass for valid Python."""
        (temp_dir / "valid.py").write_text("def foo(): pass")
        
        runner = QualityGateRunner()
        result = runner.check_syntax(temp_dir / "valid.py")
        
        assert result.passed

    def test_syntax_check_python_invalid(self, temp_dir):
        """Should fail for invalid Python."""
        (temp_dir / "invalid.py").write_text("def foo(")
        
        runner = QualityGateRunner()
        result = runner.check_syntax(temp_dir / "invalid.py")
        
        assert not result.passed
```

### 9. `/home/aiuser01/helix-v4/tests/unit/test_llm_client.py`

```python
import pytest
from unittest.mock import AsyncMock, patch

from helix.llm_client import LLMClient, ModelConfig


class TestLLMClient:
    """Tests for LLMClient."""

    def test_resolve_model_openrouter(self):
        """Should resolve OpenRouter model string."""
        client = LLMClient()
        config = client.resolve_model("openrouter:gpt-4o")
        
        assert isinstance(config, ModelConfig)
        assert config.provider == "openrouter"
        assert "gpt-4o" in config.model_id

    def test_resolve_model_alias(self):
        """Should resolve model aliases."""
        client = LLMClient()
        config = client.resolve_model("opus")
        
        assert isinstance(config, ModelConfig)
        assert "opus" in config.model_id.lower() or "claude" in config.model_id.lower()

    def test_resolve_model_invalid(self):
        """Should raise for invalid model."""
        client = LLMClient()
        
        with pytest.raises(ValueError):
            client.resolve_model("invalid:model")

    @pytest.mark.asyncio
    async def test_complete_mock(self, mock_llm_response):
        """Should call LLM and return response."""
        client = LLMClient()
        
        with patch.object(client, "_call_api", new_callable=AsyncMock) as mock:
            mock.return_value = mock_llm_response
            
            result = await client.complete(
                model="openrouter:gpt-4o-mini",
                messages=[{"role": "user", "content": "Hello"}],
            )
            
            assert "Test response" in result.content
```

### 10. `/home/aiuser01/helix-v4/tests/unit/test_escalation.py`

```python
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
```

### 11. `/home/aiuser01/helix-v4/tests/unit/test_logger.py`

```python
import pytest
from pathlib import Path
import json

from helix.observability.logger import HelixLogger, LogLevel, LogEntry


class TestHelixLogger:
    """Tests for HelixLogger."""

    def test_log_creates_entry(self, temp_dir):
        """Should create log entry."""
        logger = HelixLogger(temp_dir)
        logger.log(LogLevel.INFO, "Test message", phase="01-test")
        
        entries = logger.get_phase_logs("01-test")
        assert len(entries) >= 1
        assert entries[-1].message == "Test message"

    def test_log_file_change(self, temp_dir):
        """Should log file changes."""
        logger = HelixLogger(temp_dir)
        logger.log_file_change("01-test", temp_dir / "new.py", "created")
        
        entries = logger.get_phase_logs("01-test")
        assert any("new.py" in str(e.details) for e in entries)

    def test_log_phase_timing(self, temp_dir):
        """Should log phase start and end."""
        logger = HelixLogger(temp_dir)
        logger.log_phase_start("01-test")
        logger.log_phase_end("01-test", success=True, duration_seconds=5.0)
        
        entries = logger.get_phase_logs("01-test")
        assert any("start" in e.message.lower() for e in entries)
        assert any("end" in e.message.lower() or "complete" in e.message.lower() for e in entries)

    def test_jsonl_format(self, temp_dir):
        """Should write logs as JSONL."""
        logger = HelixLogger(temp_dir)
        logger.log(LogLevel.INFO, "Test", phase="01-test")
        
        log_file = temp_dir / "logs" / "project.jsonl"
        if log_file.exists():
            line = log_file.read_text().strip().split("\n")[-1]
            data = json.loads(line)
            assert "message" in data
```

### 12. `/home/aiuser01/helix-v4/tests/unit/test_metrics.py`

```python
import pytest

from helix.observability.metrics import MetricsCollector, PhaseMetrics, ProjectMetrics


class TestMetricsCollector:
    """Tests for MetricsCollector."""

    def test_start_project(self, temp_dir):
        """Should start project tracking."""
        collector = MetricsCollector(temp_dir)
        collector.start_project("test-project")
        
        assert collector.current_project is not None
        assert collector.current_project.project_id == "test-project"

    def test_record_tokens(self, temp_dir):
        """Should record token usage."""
        collector = MetricsCollector(temp_dir)
        collector.start_project("test-project")
        collector.start_phase("01-test")
        collector.record_tokens(input_tokens=100, output_tokens=50, model="gpt-4o")
        
        assert collector.current_phase.input_tokens == 100
        assert collector.current_phase.output_tokens == 50

    def test_calculate_cost(self, temp_dir):
        """Should calculate costs correctly."""
        collector = MetricsCollector(temp_dir)
        collector.start_project("test-project")
        collector.start_phase("01-test")
        collector.record_tokens(input_tokens=1000000, output_tokens=500000, model="gpt-4o-mini")
        
        # gpt-4o-mini: $0.15/1M input, $0.60/1M output
        # Expected: 0.15 + 0.30 = 0.45
        assert collector.current_phase.cost_usd == pytest.approx(0.45, rel=0.1)

    def test_end_phase(self, temp_dir):
        """Should finalize phase metrics."""
        collector = MetricsCollector(temp_dir)
        collector.start_project("test-project")
        collector.start_phase("01-test")
        metrics = collector.end_phase(success=True)
        
        assert isinstance(metrics, PhaseMetrics)
        assert metrics.end_time is not None
```

### 13. `/home/aiuser01/helix-v4/tests/unit/test_consultant.py`

```python
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
```

### 14. `/home/aiuser01/helix-v4/tests/unit/test_cli.py`

```python
import pytest
from click.testing import CliRunner

from helix.cli.main import cli


class TestCLI:
    """Tests for CLI commands."""

    def test_cli_version(self):
        """Should show version."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        
        assert result.exit_code == 0
        assert "4.0.0" in result.output

    def test_cli_help(self):
        """Should show help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        
        assert result.exit_code == 0
        assert "HELIX" in result.output

    def test_new_command_help(self):
        """Should show new command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["new", "--help"])
        
        assert result.exit_code == 0
        assert "project" in result.output.lower()

    def test_status_missing_project(self):
        """Should error on missing project."""
        runner = CliRunner()
        result = runner.invoke(cli, ["status", "/nonexistent/path"])
        
        assert result.exit_code != 0
```

### 15. `/home/aiuser01/helix-v4/pytest.ini`

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
addopts = -v --tb=short
markers =
    slow: marks tests as slow
    integration: marks tests as integration tests
```

## Instructions

1. Create all test files in `/home/aiuser01/helix-v4/tests/`
2. Use pytest conventions
3. Mock external dependencies (LLM calls, file system where needed)
4. All tests should be runnable without API keys
5. Create `output/result.json` when done

## Output

```json
{
  "status": "success",
  "files_created": [
    "tests/__init__.py",
    "tests/unit/__init__.py",
    "tests/conftest.py",
    "tests/unit/test_phase_loader.py",
    "tests/unit/test_spec_validator.py",
    "tests/unit/test_template_engine.py",
    "tests/unit/test_context_manager.py",
    "tests/unit/test_quality_gates.py",
    "tests/unit/test_llm_client.py",
    "tests/unit/test_escalation.py",
    "tests/unit/test_logger.py",
    "tests/unit/test_metrics.py",
    "tests/unit/test_consultant.py",
    "tests/unit/test_cli.py",
    "pytest.ini"
  ]
}
```
