"""HELIX configuration module.

ADR-035 Fix 7: Provides centralized configuration for paths
and other settings with environment variable support.
"""

from .paths import PathConfig

__all__ = ["PathConfig"]
