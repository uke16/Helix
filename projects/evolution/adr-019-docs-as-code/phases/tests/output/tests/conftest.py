"""Pytest configuration for ADR-019 Documentation as Code tests.

This conftest.py sets up the import paths for testing the helix.docs module.

Usage:
    cd projects/evolution/adr-019-docs-as-code/phases/tests/output
    python -m pytest tests/ -v
"""

import sys
from pathlib import Path

# Set up import paths
_test_dir = Path(__file__).parent
_src_dir = _test_dir.parent / "src"

# Add src so helix.docs is found
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))
