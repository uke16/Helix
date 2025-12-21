"""
HELIX v4 Consultant Meeting System.

This module provides the agentic meeting orchestration system that coordinates
domain experts to analyze user requests and generate project specifications.
"""

from .meeting import ConsultantMeeting, MeetingResult
from .expert_manager import ExpertManager, ExpertConfig

__all__ = [
    "ConsultantMeeting",
    "MeetingResult",
    "ExpertManager",
    "ExpertConfig",
]
