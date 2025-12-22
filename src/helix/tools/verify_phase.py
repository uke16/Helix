"""Verification tool for Claude to check phase outputs.

This tool allows Claude to verify that all expected files exist
before completing a phase. It integrates with the PhaseVerifier
and can be run from the command line or imported as a function.

Usage (CLI):
    python -m helix.tools.verify_phase
    python -m helix.tools.verify_phase --expected src/module.py tests/test_module.py
    python -m helix.tools.verify_phase --phase-dir phases/2

Usage (Python):
    from helix.tools import verify_phase_output
    
    result = verify_phase_output()
    if not result["success"]:
        print("Missing:", result["missing"])
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional


def verify_phase_output(
    expected_files: Optional[list[str]] = None,
    phase_dir: Optional[str] = None,
    project_dir: Optional[str] = None,
) -> dict:
    """Verify that expected phase outputs exist.
    
    Call this tool before ending your session to ensure all
    expected files have been created.
    
    Args:
        expected_files: List of expected file paths. If None,
            attempts to read from phases.yaml or ADR.
        phase_dir: Phase working directory. Defaults to current
            directory or auto-detected from path.
        project_dir: Project root directory. Defaults to
            auto-detected from phase_dir.
    
    Returns:
        Dict with verification results:
        - success: bool - True if all files found and valid
        - missing: list - Files that were expected but not found
        - syntax_errors: dict - File paths to their syntax errors
        - found: list - Files that were found
        - message: str - Human-readable summary
    
    Example:
        >>> verify_phase_output()
        {"success": True, "missing": [], "found": ["src/module.py"], ...}
        
        >>> verify_phase_output(expected_files=["src/missing.py"])
        {"success": False, "missing": ["src/missing.py"], ...}
    """
    from helix.evolution.verification import PhaseVerifier
    
    # Determine phase directory
    if phase_dir:
        phase_path = Path(phase_dir).resolve()
    else:
        phase_path = Path.cwd()
    
    # Determine project directory
    if project_dir:
        project_path = Path(project_dir).resolve()
    else:
        # Try to find project root by looking for phases.yaml
        project_path = _find_project_root(phase_path)
    
    # If no expected files provided, try to load from phases.yaml
    if expected_files is None:
        expected_files = _load_expected_files(project_path, phase_path)
    
    # Create verifier and run
    verifier = PhaseVerifier(project_path)
    
    # Determine phase_id from path
    phase_id = phase_path.name if phase_path.name.isdigit() else "current"
    
    result = verifier.verify_phase_output(
        phase_id=phase_id,
        phase_dir=phase_path,
        expected_files=expected_files,
    )
    
    return {
        "success": result.success,
        "missing": result.missing_files,
        "syntax_errors": result.syntax_errors,
        "found": result.found_files,
        "message": result.message,
    }


def _find_project_root(phase_path: Path) -> Path:
    """Find project root by looking for phases.yaml or ADR files.
    
    Walks up the directory tree looking for project indicators.
    """
    current = phase_path
    
    for _ in range(10):  # Max 10 levels up
        # Check for phases.yaml
        if (current / "phases.yaml").exists():
            return current
        
        # Check for ADR files
        if list(current.glob("ADR-*.md")):
            return current
        
        # Check for status.json (evolution project marker)
        if (current / "status.json").exists():
            return current
        
        # Go up one level
        parent = current.parent
        if parent == current:
            break
        current = parent
    
    # Fallback to phase_path parent
    return phase_path.parent


def _load_expected_files(project_path: Path, phase_path: Path) -> Optional[list[str]]:
    """Load expected files from phases.yaml.
    
    Finds the current phase in phases.yaml and returns its output files.
    """
    phases_file = project_path / "phases.yaml"
    if not phases_file.exists():
        return None
    
    try:
        import yaml
        
        with open(phases_file) as f:
            data = yaml.safe_load(f)
        
        # Determine current phase ID
        phase_id = phase_path.name
        
        # Find phase in phases list
        phases = data.get("phases", [])
        for phase in phases:
            if str(phase.get("id")) == phase_id:
                return phase.get("output", [])
        
        return None
        
    except Exception:
        return None


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Verify phase outputs before completing"
    )
    parser.add_argument(
        "--expected", "-e",
        nargs="+",
        help="Expected file paths"
    )
    parser.add_argument(
        "--phase-dir", "-p",
        help="Phase working directory (default: current)"
    )
    parser.add_argument(
        "--project-dir",
        help="Project root directory (default: auto-detect)"
    )
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output as JSON"
    )
    
    args = parser.parse_args()
    
    result = verify_phase_output(
        expected_files=args.expected,
        phase_dir=args.phase_dir,
        project_dir=args.project_dir,
    )
    
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        # Human-readable output
        if result["success"]:
            print(f"✅ {result['message']}")
            if result["found"]:
                print(f"\nFound {len(result['found'])} files:")
                for f in result["found"]:
                    print(f"  ✓ {f}")
        else:
            print(f"❌ {result['message']}")
            
            if result["missing"]:
                print(f"\n🔍 Missing files ({len(result['missing'])}):")
                for f in result["missing"]:
                    print(f"  ✗ {f}")
            
            if result["syntax_errors"]:
                print(f"\n⚠️ Syntax errors ({len(result['syntax_errors'])}):")
                for path, error in result["syntax_errors"].items():
                    print(f"  {path}: {error}")
            
            print("\n💡 Fix these issues before completing the phase.")
    
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
