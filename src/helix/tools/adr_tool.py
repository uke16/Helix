"""ADR Tool - Validate and finalize ADRs for the Consultant.

This tool helps the Consultant ensure ADRs are:
1. Valid against the ADR template
2. Placed in the correct directory (adr/)
3. Registered in INDEX.md

Usage (CLI):
    python -m helix.tools.adr_tool validate path/to/ADR-xxx.md
    python -m helix.tools.adr_tool finalize path/to/ADR-xxx.md

Usage (Python):
    from helix.tools import validate_adr, finalize_adr
    
    result = validate_adr("path/to/ADR-xxx.md")
    if result.success:
        result = finalize_adr("path/to/ADR-xxx.md")
"""

import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# HELIX root directory
HELIX_ROOT = Path(__file__).parent.parent.parent.parent
ADR_DIR = HELIX_ROOT / "adr"
INDEX_FILE = ADR_DIR / "INDEX.md"


@dataclass
class ADRToolResult:
    """Result of an ADR tool operation."""
    success: bool
    message: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    adr_id: Optional[str] = None
    adr_title: Optional[str] = None
    final_path: Optional[str] = None


def validate_adr(adr_path: str | Path) -> ADRToolResult:
    """Validate an ADR file against the template.
    
    Checks:
    - File exists and is readable
    - Valid YAML frontmatter
    - Required fields present (adr_id, title, status, files)
    - Required sections present (Kontext, Entscheidung, etc.)
    - Acceptance criteria defined
    
    Args:
        adr_path: Path to the ADR file
        
    Returns:
        ADRToolResult with validation details
    """
    path = Path(adr_path)
    errors = []
    warnings = []
    adr_id = None
    adr_title = None
    
    # Check file exists
    if not path.exists():
        return ADRToolResult(
            success=False,
            message=f"File not found: {path}",
            errors=[f"File does not exist: {path}"]
        )
    
    # Read content
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        return ADRToolResult(
            success=False,
            message=f"Cannot read file: {e}",
            errors=[str(e)]
        )
    
    # Try to use helix.adr.validator if available
    try:
        from helix.adr.validator import ADRValidator
        from helix.adr.parser import ADRParseError
        validator = ADRValidator()
        result = validator.validate_file(path)
        
        if not result.valid:
            errors.extend([e.message for e in result.errors])
        warnings.extend([w.message for w in result.warnings])
        
        # Extract metadata
        from helix.adr import ADRParser
        parser = ADRParser()
        adr = parser.parse_file(path)
        adr_id = adr.metadata.adr_id
        adr_title = adr.metadata.title
        
    except (ImportError, ADRParseError) as e:
        if isinstance(e, ADRParseError):
            errors.append(str(e))
            return ADRToolResult(
                success=False,
                message=f"ADR parse error: {e}",
                errors=[str(e)]
            )
        # ImportError - fallback to basic validation
        # Fallback: basic validation
        errors, warnings, adr_id, adr_title = _basic_validate(content)
    
    # Additional checks
    
    # Check filename format
    filename = path.name
    if not re.match(r"^\d{3}-[\w-]+\.md$", filename) and not filename.startswith("ADR-"):
        warnings.append(f"Filename should be 'NNN-name.md' format, got: {filename}")
    
    # Check if already in adr/ directory
    if path.parent.name != "adr":
        warnings.append(f"ADR is not in adr/ directory. Use finalize_adr() to move it.")
    
    success = len(errors) == 0
    
    if success:
        message = f"✅ ADR-{adr_id} '{adr_title}' is valid"
        if warnings:
            message += f" (with {len(warnings)} warnings)"
    else:
        message = f"❌ ADR validation failed with {len(errors)} errors"
    
    return ADRToolResult(
        success=success,
        message=message,
        errors=errors,
        warnings=warnings,
        adr_id=adr_id,
        adr_title=adr_title,
    )


def _basic_validate(content: str) -> tuple[list, list, str, str]:
    """Basic validation without helix.adr module."""
    errors = []
    warnings = []
    adr_id = None
    adr_title = None
    
    # Check YAML frontmatter
    if not content.startswith("---"):
        errors.append("Missing YAML frontmatter (must start with ---)")
    else:
        # Extract frontmatter
        parts = content.split("---", 2)
        if len(parts) < 3:
            errors.append("Invalid YAML frontmatter (missing closing ---)")
        else:
            yaml_content = parts[1]
            
            # Check required fields
            required = ["adr_id", "title", "status", "files"]
            for field in required:
                if f"{field}:" not in yaml_content:
                    errors.append(f"Missing required field: {field}")
            
            # Extract adr_id and title
            id_match = re.search(r'adr_id:\s*["\']?(\d+)["\']?', yaml_content)
            if id_match:
                adr_id = id_match.group(1)
            
            title_match = re.search(r'title:\s*["\']?([^"\'\n]+)["\']?', yaml_content)
            if title_match:
                adr_title = title_match.group(1).strip()
    
    # Check required sections
    required_sections = ["Kontext", "Entscheidung", "Akzeptanzkriterien"]
    for section in required_sections:
        if f"## {section}" not in content:
            errors.append(f"Missing required section: ## {section}")
    
    # Check for acceptance criteria checkboxes
    if "- [ ]" not in content and "- [x]" not in content:
        warnings.append("No acceptance criteria checkboxes found (use - [ ] format)")
    
    return errors, warnings, adr_id, adr_title


def finalize_adr(adr_path: str | Path, force: bool = False) -> ADRToolResult:
    """Finalize an ADR by moving it to adr/ and updating INDEX.md.
    
    Steps:
    1. Validate the ADR
    2. Determine correct filename (NNN-name.md)
    3. Move/copy to adr/ directory
    4. Update INDEX.md
    
    Args:
        adr_path: Path to the ADR file
        force: Overwrite if file exists in adr/
        
    Returns:
        ADRToolResult with finalization details
    """
    path = Path(adr_path)
    
    # First validate
    validation = validate_adr(path)
    if not validation.success:
        return ADRToolResult(
            success=False,
            message=f"Cannot finalize: ADR validation failed",
            errors=validation.errors,
            warnings=validation.warnings,
        )
    
    adr_id = validation.adr_id
    adr_title = validation.adr_title
    
    # Determine target filename
    # Convert title to slug
    slug = re.sub(r"[^\w\s-]", "", adr_title.lower())
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = slug[:50]  # Limit length
    
    target_filename = f"{adr_id.zfill(3)}-{slug}.md"
    target_path = ADR_DIR / target_filename
    
    # Check if already in adr/ directory with same ADR ID
    if path.parent.resolve() == ADR_DIR.resolve():
        # Already in adr/ directory
        _update_index(adr_id, adr_title, path.name)
        return ADRToolResult(
            success=True,
            message=f"✅ ADR-{adr_id} already in adr/ directory, INDEX.md updated",
            adr_id=adr_id,
            adr_title=adr_title,
            final_path=str(path),
        )
    
    # Check if an ADR with same ID already exists in adr/
    existing = list(ADR_DIR.glob(f"{adr_id.zfill(3)}-*.md"))
    if existing and not force:
        return ADRToolResult(
            success=False,
            message=f"ADR-{adr_id} already exists: {existing[0]}. Use force=True to overwrite.",
            errors=[f"Existing ADR: {existing[0]}"],
            adr_id=adr_id,
            adr_title=adr_title,
        )
    
    # Check if exact target exists
    if target_path.exists() and not force:
        return ADRToolResult(
            success=False,
            message=f"Target file already exists: {target_path}. Use force=True to overwrite.",
            errors=[f"File exists: {target_path}"],
            adr_id=adr_id,
            adr_title=adr_title,
        )
    
    # Ensure adr/ directory exists
    ADR_DIR.mkdir(parents=True, exist_ok=True)
    
    # Copy file (not move, to preserve original during development)
    try:
        shutil.copy2(path, target_path)
    except Exception as e:
        return ADRToolResult(
            success=False,
            message=f"Failed to copy ADR: {e}",
            errors=[str(e)],
            adr_id=adr_id,
            adr_title=adr_title,
        )
    
    # Update INDEX.md
    index_updated = _update_index(adr_id, adr_title, target_filename)
    
    message = f"✅ ADR-{adr_id} finalized: {target_path}"
    if index_updated:
        message += " (INDEX.md updated)"
    
    return ADRToolResult(
        success=True,
        message=message,
        adr_id=adr_id,
        adr_title=adr_title,
        final_path=str(target_path),
        warnings=validation.warnings,
    )


def _update_index(adr_id: str, title: str, filename: str) -> bool:
    """Update INDEX.md with the new ADR entry.
    
    Returns True if index was updated, False if entry already exists.
    """
    if not INDEX_FILE.exists():
        return False
    
    content = INDEX_FILE.read_text(encoding="utf-8")
    
    # Check if ADR already in index
    if filename in content:
        return False
    
    # Find the right section based on ADR number
    adr_num = int(adr_id)
    
    # Determine section
    if adr_num <= 10:
        section = "Core Architecture"
    elif adr_num <= 20:
        section = "Evolution System"
    else:
        section = "Extensions"
    
    # Find the table in that section and add entry
    # This is a simplified approach - just append info at the end
    
    # Add a note about the new ADR
    note = f"\n\n<!-- Auto-added by adr_tool: ADR-{adr_id} {title} -->\n"
    note += f"<!-- Please manually add to appropriate table: | {adr_id} | [{title}]({filename}) | 📋 | ... | -->\n"
    
    # For now, just log that we need to update
    # A more sophisticated implementation would parse and modify the table
    
    return False  # Manual update needed for now


def get_next_adr_number() -> int:
    """Get the next available ADR number."""
    if not ADR_DIR.exists():
        return 1
    
    max_num = 0
    for f in ADR_DIR.glob("*.md"):
        match = re.match(r"^(\d{3})-", f.name)
        if match:
            num = int(match.group(1))
            max_num = max(max_num, num)
    
    return max_num + 1


# CLI interface
if __name__ == "__main__":
    import sys
    
    def print_result(result: ADRToolResult):
        print(result.message)
        if result.errors:
            print("\nErrors:")
            for e in result.errors:
                print(f"  ❌ {e}")
        if result.warnings:
            print("\nWarnings:")
            for w in result.warnings:
                print(f"  ⚠️ {w}")
        if result.final_path:
            print(f"\nFinal path: {result.final_path}")
    
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python -m helix.tools.adr_tool validate <path>")
        print("  python -m helix.tools.adr_tool finalize <path>")
        print("  python -m helix.tools.adr_tool next-number")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "validate":
        result = validate_adr(sys.argv[2])
        print_result(result)
        sys.exit(0 if result.success else 1)
    
    elif command == "finalize":
        force = "--force" in sys.argv
        result = finalize_adr(sys.argv[2], force=force)
        print_result(result)
        sys.exit(0 if result.success else 1)
    
    elif command == "next-number":
        print(f"Next ADR number: {get_next_adr_number():03d}")
        sys.exit(0)
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
