"""HELIX v4 - AI Development System Core Framework."""

__version__ = "4.0.0"

from .orchestrator import Orchestrator, ProjectResult, PhaseResult
from .template_engine import TemplateEngine
from .context_manager import ContextManager
from .quality_gates import QualityGateRunner, GateResult
from .phase_loader import PhaseLoader, PhaseConfig
from .spec_validator import SpecValidator, ValidationResult, ValidationError
from .llm_client import LLMClient, ModelConfig
from .claude_runner import ClaudeRunner, ClaudeResult
from .escalation import EscalationManager, EscalationState, EscalationAction

__all__ = [
    "__version__",
    "Orchestrator",
    "ProjectResult",
    "PhaseResult",
    "TemplateEngine",
    "ContextManager",
    "QualityGateRunner",
    "GateResult",
    "PhaseLoader",
    "PhaseConfig",
    "SpecValidator",
    "ValidationResult",
    "ValidationError",
    "LLMClient",
    "ModelConfig",
    "ClaudeRunner",
    "ClaudeResult",
    "EscalationManager",
    "EscalationState",
    "EscalationAction",
]
