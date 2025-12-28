"""HELIX Evolution System - Self-modification capabilities.

Components:
- Deployer: Deploy evolution projects to test system
- Validator: Run tests in test system
- Integrator: Integrate to production
- PhaseVerifier: Verify phase outputs (ADR-011)
- EvolutionProjectManager: Manage evolution projects
- RAGSync: Sync evolution docs to RAG system
"""

from .project import (
    EvolutionProject,
    EvolutionProjectManager,
    EvolutionStatus,
    EvolutionError,
)
from .deployer import Deployer
from .validator import Validator
from .integrator import Integrator
from .verification import PhaseVerifier, VerificationResult
from .rag_sync import RAGSync

__all__ = [
    # Project Management
    "EvolutionProject",
    "EvolutionProjectManager",
    "EvolutionStatus",
    "EvolutionError",
    # Deploy/Validate/Integrate
    "Deployer",
    "Validator",
    "Integrator",
    # Verification (ADR-011)
    "PhaseVerifier",
    "VerificationResult",
    # RAG Integration
    "RAGSync",
]

# Additional exports for API routes and tests
from .deployer import DeployResult
from .validator import ValidationResult, ValidationLevel
from .integrator import IntegrationResult
from .rag_sync import SyncResult, SyncStatus
