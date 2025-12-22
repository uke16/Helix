"""Pytest configuration for evolution ADR system tests.

This conftest.py documents the testing setup for the ADR evolution project.

IMPORTANT: Run tests with --import-mode=importlib to properly resolve imports:
    pytest tests/adr/ -v --import-mode=importlib

Or run from this directory:
    cd projects/evolution/adr-system/new
    python -m pytest tests/adr/ -v --rootdir=. --import-mode=importlib

The import mode is needed because:
1. The evolution project has its own helix package in new/src/ with adr and quality_gates
2. The importlib mode properly handles the package namespace during test collection
"""

import sys
from pathlib import Path

# Set up import paths
_test_dir = Path(__file__).parent
_new_src = _test_dir.parent.parent / "src"

# Add new src so helix.adr is found
if str(_new_src) not in sys.path:
    sys.path.insert(0, str(_new_src))
