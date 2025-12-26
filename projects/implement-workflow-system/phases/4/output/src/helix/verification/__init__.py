"""HELIX Verification Module.

Provides sub-agent verification with feedback loop for phase outputs.
"""

from .sub_agent import SubAgentVerifier, VerificationResult
from .feedback import FeedbackChannel

__all__ = [
    "SubAgentVerifier",
    "VerificationResult",
    "FeedbackChannel",
]
