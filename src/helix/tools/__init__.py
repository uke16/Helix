"""HELIX Tools - Utilities for Claude Code to call during development.

Tools:
- adr_tool: Validate and finalize ADRs
- verify_phase: Verify phase outputs (coming soon)
"""

# Lazy imports to avoid circular dependencies
def validate_adr(adr_path):
    """Validate an ADR file. See adr_tool.validate_adr for details."""
    from .adr_tool import validate_adr as _validate
    return _validate(adr_path)

def finalize_adr(adr_path, force=False):
    """Finalize an ADR. See adr_tool.finalize_adr for details."""
    from .adr_tool import finalize_adr as _finalize
    return _finalize(adr_path, force)

def get_next_adr_number():
    """Get next available ADR number."""
    from .adr_tool import get_next_adr_number as _next
    return _next()

__all__ = [
    "validate_adr",
    "finalize_adr",
    "get_next_adr_number",
]
