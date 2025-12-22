"""HELIX Evolution System - Self-modification capabilities.

Components:
- Deployer: Deploy evolution projects to test system
- Validator: Run tests in test system
- Integrator: Integrate to production
- PhaseVerifier: Verify phase outputs (ADR-011)
- EvolutionProjectManager: Manage evolution projects
"""

from .project import EvolutionProject, EvolutionProjectManager
from .deployer import Deployer
from .validator import Validator
from .integrator import Integrator
from .verification import PhaseVerifier, VerificationResult

__all__ = [
    # Project Management
    "EvolutionProject",
    "EvolutionProjectManager",
    # Deploy/Validate/Integrate
    "Deployer",
    "Validator",
    "Integrator",
    # Verification (ADR-011)
    "PhaseVerifier",
    "VerificationResult",
]
