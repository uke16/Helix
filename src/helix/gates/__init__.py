"""Quality Gate implementations for HELIX v4.

This package provides specialized quality gate checkers for phase validation.
Each gate type has its own module with dedicated checking logic.

Available Gates:
    - adr_complete: Complete ADR validation (Layer 1-4)
    - approval: Generic sub-agent approval gate

Example:
    >>> from helix.gates import check_adr_complete, check_approval
    >>> from pathlib import Path
    >>>
    >>> # Check ADR with full validation
    >>> result = await check_adr_complete(
    ...     phase_dir=Path("/project/phases/01-consultant"),
    ...     gate_config={"file": "output/ADR-*.md", "semantic": "auto"},
    ... )
    >>>
    >>> # Run generic approval
    >>> result = await check_approval(
    ...     phase_dir=Path("/project/phases/02-dev"),
    ...     gate_config={"approval_type": "code"},
    ... )

See Also:
    - ADR-015: Approval & Validation System
    - helix.quality_gates: Main QualityGateRunner
"""

from .adr_complete import check_adr_complete, ADRCompleteResult
from .approval import check_approval, ApprovalGateResult

__all__ = [
    "check_adr_complete",
    "ADRCompleteResult",
    "check_approval",
    "ApprovalGateResult",
]
