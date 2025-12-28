"""Post-phase verification for HELIX Evolution projects.

This module provides verification of phase outputs against ADR expectations.
It supports both self-verification (Claude calls the tool) and external
safety net verification (called by streaming.py after each phase).

Usage:
    from helix.evolution.verification import PhaseVerifier

    verifier = PhaseVerifier(project_path)
    result = verifier.verify_phase_output(
        phase_id="2",
        phase_dir=Path("phases/2"),
        expected_files=["src/module.py", "tests/test_module.py"]
    )
    
    if not result.success:
        retry_prompt = verifier.format_retry_prompt(result)
        # Write to VERIFICATION_ERRORS.md for Claude to fix
"""

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from helix.adr.parser import ADRDocument


@dataclass
class VerificationResult:
    """Result of a phase output verification.
    
    Attributes:
        success: Whether all expected files exist and are valid
        missing_files: List of files that were expected but not found
        syntax_errors: Dict mapping file paths to their syntax errors
        found_files: List of files that were found
        message: Human-readable summary of the verification
    """
    success: bool
    missing_files: list[str] = field(default_factory=list)
    syntax_errors: dict[str, str] = field(default_factory=dict)
    found_files: list[str] = field(default_factory=list)
    message: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "missing_files": self.missing_files,
            "syntax_errors": self.syntax_errors,
            "found_files": self.found_files,
            "message": self.message,
        }


class PhaseVerifier:
    """Verify phase outputs against ADR expectations.
    
    This class provides the core verification logic used by both:
    1. The verify_phase tool (for Claude to call during development)
    2. The streaming.py safety net (automatic check after each phase)
    
    Args:
        project_path: Path to the evolution project directory
        
    Example:
        verifier = PhaseVerifier(Path("projects/evolution/feature-x"))
        
        # Verify with explicit file list
        result = verifier.verify_phase_output(
            phase_id="2",
            phase_dir=Path("phases/2"),
            expected_files=["src/module.py"]
        )
        
        # Or verify using ADR metadata
        result = verifier.verify_phase_output(
            phase_id="2",
            phase_dir=Path("phases/2")
        )  # Uses files.create from ADR
    """
    
    def __init__(self, project_path: Path):
        """Initialize verifier for an evolution project.
        
        Args:
            project_path: Path to the evolution project directory
        """
        self.project_path = Path(project_path)
        self._adr: Optional["ADRDocument"] = None
        self._adr_loaded = False
    
    @property
    def adr(self) -> Optional["ADRDocument"]:
        """Lazily load and cache the project's ADR."""
        if not self._adr_loaded:
            self._adr = self._load_adr()
            self._adr_loaded = True
        return self._adr
    
    def _load_adr(self) -> Optional["ADRDocument"]:
        """Load ADR from project directory.
        
        Looks for ADR-*.md files in the project directory.
        
        Returns:
            Parsed ADRDocument or None if no ADR found
        """
        try:
            from helix.adr import ADRParser
            parser = ADRParser()
            
            # Find ADR file (ADR-*.md or NNN-*.md)
            adr_files = list(self.project_path.glob("ADR-*.md"))
            if not adr_files:
                adr_files = list(self.project_path.glob("[0-9][0-9][0-9]-*.md"))
            
            if not adr_files:
                return None
            
            return parser.parse_file(adr_files[0])
            
        except ImportError:
            return None
        except Exception:
            return None
    
    def verify_phase_output(
        self,
        phase_id: str,
        phase_dir: Path,
        expected_files: Optional[list[str]] = None,
    ) -> VerificationResult:
        """Verify that a phase produced expected outputs.
        
        Checks multiple candidate locations for each expected file:
        1. phase_dir/output/{file}
        2. phase_dir/{file}
        3. project_path/new/{file}
        4. project_path/{file}
        
        For Python files, also performs syntax validation using AST.
        
        Args:
            phase_id: ID of the phase (for logging/messages)
            phase_dir: Directory where the phase ran
            expected_files: List of expected file paths. If None, uses
                           ADR metadata (files.create)
        
        Returns:
            VerificationResult with details about found/missing files
        """
        phase_dir = Path(phase_dir)
        
        # Get expected files from ADR if not provided
        if expected_files is None and self.adr:
            expected_files = list(self.adr.metadata.files.create)
        
        if not expected_files:
            return VerificationResult(
                success=True,
                message=f"Phase {phase_id}: No expected files defined"
            )
        
        missing = []
        found = []
        syntax_errors = {}

        for file_path in expected_files:
            # Check if this is a glob pattern
            is_glob = any(c in file_path for c in ["*", "?", "["])

            # Normalize path (remove new/ or modified/ prefix for checking)
            clean_path = file_path
            for prefix in ["new/", "modified/", "output/"]:
                if clean_path.startswith(prefix):
                    clean_path = clean_path[len(prefix):]
                    break

            if is_glob:
                # Handle glob patterns - search in candidate directories
                glob_dirs = [
                    phase_dir / "output",
                    phase_dir,
                    self.project_path / "new",
                    self.project_path,
                ]

                matched_files = []
                for search_dir in glob_dirs:
                    if search_dir.exists():
                        matches = list(search_dir.glob(clean_path))
                        matched_files.extend(matches)

                if matched_files:
                    for match_path in matched_files:
                        found.append(str(match_path))
                        # Syntax check for Python files
                        if match_path.suffix == ".py":
                            error = self._check_python_syntax(match_path)
                            if error:
                                syntax_errors[str(match_path)] = error
                else:
                    missing.append(file_path)
            else:
                # Check multiple candidate locations for literal files
                candidates = [
                    phase_dir / "output" / clean_path,
                    phase_dir / "output" / file_path,
                    phase_dir / clean_path,
                    phase_dir / file_path,
                    self.project_path / "new" / clean_path,
                    self.project_path / file_path,
                ]

                found_path = None
                for candidate in candidates:
                    if candidate.exists() and candidate.is_file():
                        found_path = candidate
                        break

                if found_path:
                    found.append(str(found_path))

                    # Syntax check for Python files
                    if found_path.suffix == ".py":
                        error = self._check_python_syntax(found_path)
                        if error:
                            syntax_errors[str(found_path)] = error
                else:
                    missing.append(file_path)
        
        # Determine success
        success = len(missing) == 0 and len(syntax_errors) == 0
        
        # Build message
        total = len(expected_files)
        found_count = len(found)
        
        if success:
            message = f"Phase {phase_id}: ✅ All {total} files verified"
        else:
            parts = [f"Phase {phase_id}: ❌ Verification failed"]
            if missing:
                parts.append(f"Missing: {missing}")
            if syntax_errors:
                parts.append(f"Syntax errors in {len(syntax_errors)} files")
            message = " | ".join(parts)
        
        return VerificationResult(
            success=success,
            missing_files=missing,
            syntax_errors=syntax_errors,
            found_files=found,
            message=message,
        )
    
    def _check_python_syntax(self, file_path: Path) -> Optional[str]:
        """Check Python file syntax using AST.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            Error message if syntax error, None if valid
        """
        try:
            content = file_path.read_text(encoding="utf-8")
            ast.parse(content)
            return None
        except SyntaxError as e:
            return f"Line {e.lineno}: {e.msg}"
        except Exception as e:
            return f"Read error: {e}"
    
    def format_retry_prompt(
        self,
        result: VerificationResult,
        retry_number: int = 1,
        max_retries: int = 2,
    ) -> str:
        """Format a prompt for Claude to fix verification errors.
        
        This creates a VERIFICATION_ERRORS.md file content that tells
        Claude exactly what needs to be fixed.
        
        Args:
            result: Failed verification result
            retry_number: Current retry attempt (1 or 2)
            max_retries: Maximum retries allowed
            
        Returns:
            Markdown-formatted prompt for Claude
        """
        lines = [
            "# ⚠️ Verification Failed - Please Fix",
            "",
            f"**Retry {retry_number} of {max_retries}**",
            "",
            "The phase verification found issues that must be fixed:",
            "",
        ]
        
        if result.missing_files:
            lines.append("## Missing Files")
            lines.append("")
            lines.append("These files were expected but not found:")
            lines.append("")
            for f in result.missing_files:
                lines.append(f"- `{f}`")
            lines.append("")
            lines.append("**Action:** Create these files in the `output/` directory.")
            lines.append("")
        
        if result.syntax_errors:
            lines.append("## Syntax Errors")
            lines.append("")
            lines.append("These files have Python syntax errors:")
            lines.append("")
            for path, error in result.syntax_errors.items():
                lines.append(f"### `{path}`")
                lines.append(f"```")
                lines.append(error)
                lines.append(f"```")
                lines.append("")
            lines.append("**Action:** Fix the syntax errors in these files.")
            lines.append("")
        
        lines.extend([
            "---",
            "",
            "## How to Proceed",
            "",
            "1. Fix all issues listed above",
            "2. Run verification again: `python -m helix.tools.verify_phase`",
            "3. Only exit when verification passes",
            "",
        ])
        
        if retry_number >= max_retries:
            lines.extend([
                "⚠️ **This is your last retry.** If verification fails again,",
                "the phase will be marked as FAILED.",
                "",
            ])
        
        return "\n".join(lines)
    
    def write_retry_file(
        self,
        phase_dir: Path,
        result: VerificationResult,
        retry_number: int = 1,
    ) -> Path:
        """Write VERIFICATION_ERRORS.md for Claude to read.
        
        Args:
            phase_dir: Phase working directory
            result: Failed verification result
            retry_number: Current retry attempt
            
        Returns:
            Path to the created file
        """
        content = self.format_retry_prompt(result, retry_number)
        file_path = Path(phase_dir) / "VERIFICATION_ERRORS.md"
        file_path.write_text(content, encoding="utf-8")
        return file_path
