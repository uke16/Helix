# src/helix/phase_status.py

"""Phase status enumeration with Python 3.10 compatibility.

This module provides a StrEnum backport for Python 3.10 and the PhaseStatus
enumeration used throughout the pipeline.

ADR-030: Evolution Pipeline Reliability - Fix 3
"""

import sys
from enum import Enum

if sys.version_info >= (3, 11):
    from enum import StrEnum
else:
    # Backport for Python 3.10
    class StrEnum(str, Enum):
        """String enumeration compatible with Python 3.10+."""

        def __str__(self) -> str:
            return self.value

        def __repr__(self) -> str:
            return f"{self.__class__.__name__}.{self.name}"


class PhaseStatus(StrEnum):
    """Status of a pipeline phase."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class JobStatus(StrEnum):
    """Status of a HELIX job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
