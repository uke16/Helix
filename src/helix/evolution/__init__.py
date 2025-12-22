"""HELIX Self-Evolution System.

This module provides the capability for HELIX to safely evolve itself
through an isolated test system with controlled integration.

Architecture:
- helix-v4 (Production): Running system, never directly modified
- helix-v4-test (Test): Isolated test environment for validation
- projects/evolution/: Evolution project workspace

Workflow:
1. Evolution project created with spec.yaml and phases.yaml
2. Development phases run, generating new/ and modified/ files
3. Deploy to test system for validation
4. On success, integrate back to production

Key Principle: "Zettel statt Telefon"
Claude Code instances are short-lived. Communication happens through files
(spec.yaml, status.json), not real-time dialogue.
"""

from .project import (
    EvolutionProject,
    EvolutionProjectManager,
    EvolutionStatus,
    EvolutionError,
)
from .deployer import (
    Deployer,
    DeployResult,
)
from .validator import (
    Validator,
    ValidationResult,
    ValidationLevel,
    quick_validate,
)
from .integrator import (
    Integrator,
    IntegrationResult,
)
from .rag_sync import (
    RAGSync,
    SyncResult,
    SyncStatus,
)

__all__ = [
    # Project management
    "EvolutionProject",
    "EvolutionProjectManager",
    "EvolutionStatus",
    "EvolutionError",
    # Deployment
    "Deployer",
    "DeployResult",
    # Validation
    "Validator",
    "ValidationResult",
    "ValidationLevel",
    "quick_validate",
    # Integration
    "Integrator",
    "IntegrationResult",
    # RAG Sync
    "RAGSync",
    "SyncResult",
    "SyncStatus",
]
