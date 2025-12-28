"""File permission normalization for Evolution Pipeline.

ADR-031: Fix 2 - File Permission Normalization

This module ensures consistent file permissions regardless of umask or source file permissions.
It addresses the bug where files created by Claude Code's str_replace_editor inherit the
user's umask (often 0077), resulting in restrictive 0600 permissions.

Root Cause (from ADR-031):
    Claude Code's str_replace_editor creates files with the user's umask.
    shutil.copy2() preserves source file permissions.
    When umask is 0077, new files get 0600 (rw-------) permissions.

Solution:
    Normalize all file permissions to standard values:
    - Directories: 0755 (rwxr-xr-x)
    - Scripts (.sh, .bash): 0755 (rwxr-xr-x)
    - Files with shebang: 0755 (rwxr-xr-x)
    - All other files: 0644 (rw-r--r--)

Usage:
    from helix.evolution.file_permissions import (
        normalize_permissions,
        normalize_directory_recursive,
        copy_with_permissions
    )

    # Single file
    normalize_permissions(Path("src/module.py"))

    # Entire directory tree
    count = normalize_directory_recursive(Path("output/"))

    # Copy with normalized permissions
    copy_with_permissions(src, dst)
"""

from pathlib import Path
import logging
import shutil
import stat
from typing import Set

logger = logging.getLogger(__name__)

# Standard permissions
PERMISSION_FILE = 0o644      # rw-r--r--
PERMISSION_SCRIPT = 0o755    # rwxr-xr-x
PERMISSION_DIR = 0o755       # rwxr-xr-x

# File extensions that always need execute permission
EXECUTABLE_EXTENSIONS: Set[str] = {".sh", ".bash"}

# File extensions that may need execute permission if they have a shebang
SHEBANG_EXTENSIONS: Set[str] = {".py", ".pl", ".rb", ".php"}


def is_executable_script(path: Path) -> bool:
    """Check if a file should have executable permissions.

    A file is considered executable if:
    1. It has an always-executable extension (.sh, .bash), OR
    2. It has a shebang (#!) as the first line

    Args:
        path: Path to the file to check

    Returns:
        True if file should be executable, False otherwise
    """
    if not path.is_file():
        return False

    suffix = path.suffix.lower()

    # Always executable extensions
    if suffix in EXECUTABLE_EXTENSIONS:
        return True

    # Check for shebang in potential script files
    if suffix in SHEBANG_EXTENSIONS:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                first_line = f.readline()
                if first_line.startswith("#!"):
                    return True
        except (IOError, OSError) as e:
            logger.debug(f"Could not read file for shebang check: {path} - {e}")
            return False

    # For files without extension, also check for shebang
    if not suffix:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                first_line = f.readline()
                if first_line.startswith("#!"):
                    return True
        except (IOError, OSError):
            return False

    return False


def normalize_permissions(path: Path) -> None:
    """Normalize file/directory permissions to standard values.

    - Directories: 0755 (rwxr-xr-x)
    - Scripts (.sh, .bash): 0755 (rwxr-xr-x)
    - Files with shebang: 0755 (rwxr-xr-x)
    - All other files: 0644 (rw-r--r--)

    Args:
        path: File or directory to normalize

    Raises:
        OSError: If permission change fails (e.g., permission denied)
    """
    if not path.exists():
        logger.warning(f"Path does not exist: {path}")
        return

    try:
        if path.is_dir():
            path.chmod(PERMISSION_DIR)
            logger.debug(f"Dir permissions: {path} -> 0755")
        elif is_executable_script(path):
            path.chmod(PERMISSION_SCRIPT)
            logger.debug(f"Script permissions: {path} -> 0755")
        else:
            path.chmod(PERMISSION_FILE)
            logger.debug(f"File permissions: {path} -> 0644")
    except OSError as e:
        logger.error(f"Failed to set permissions on {path}: {e}")
        raise


def normalize_directory_recursive(directory: Path) -> int:
    """Normalize permissions for all files in a directory tree.

    Traverses the directory tree and normalizes permissions for all files
    and directories. The root directory is normalized last.

    Args:
        directory: Root directory to normalize

    Returns:
        Number of files/directories normalized

    Raises:
        ValueError: If directory does not exist
        OSError: If permission change fails on any file
    """
    if not directory.exists():
        raise ValueError(f"Directory does not exist: {directory}")

    if not directory.is_dir():
        raise ValueError(f"Path is not a directory: {directory}")

    count = 0

    # First, normalize all children (depth-first)
    for path in directory.rglob("*"):
        normalize_permissions(path)
        count += 1

    # Then normalize the root directory itself
    normalize_permissions(directory)
    count += 1

    logger.info(f"Normalized permissions for {count} items in {directory}")
    return count


def copy_with_permissions(src: Path, dst: Path) -> None:
    """Copy a file and normalize its permissions.

    Use this instead of shutil.copy2() to ensure consistent permissions
    regardless of source file permissions or umask settings.

    The function:
    1. Creates parent directories if needed (with 0755 permissions)
    2. Copies the file (preserving metadata with copy2)
    3. Normalizes file permissions based on file type
    4. Normalizes parent directory permissions

    Args:
        src: Source file path
        dst: Destination file path

    Raises:
        FileNotFoundError: If source file does not exist
        IsADirectoryError: If source is a directory (use shutil.copytree)
        OSError: If copy or permission change fails
    """
    if not src.exists():
        raise FileNotFoundError(f"Source file not found: {src}")

    if src.is_dir():
        raise IsADirectoryError(
            f"Cannot copy directory with copy_with_permissions. "
            f"Use shutil.copytree + normalize_directory_recursive: {src}"
        )

    # Create parent directories with correct permissions
    dst.parent.mkdir(parents=True, exist_ok=True)
    normalize_permissions(dst.parent)

    # Copy the file (preserves metadata)
    shutil.copy2(src, dst)

    # Normalize the copied file's permissions
    normalize_permissions(dst)

    logger.debug(f"Copied with permissions: {src} -> {dst}")


def copytree_with_permissions(src: Path, dst: Path) -> int:
    """Copy a directory tree with normalized permissions.

    Use this instead of shutil.copytree() to ensure consistent permissions
    for all copied files and directories.

    Args:
        src: Source directory path
        dst: Destination directory path

    Returns:
        Number of items copied and normalized

    Raises:
        FileNotFoundError: If source directory does not exist
        NotADirectoryError: If source is not a directory
        OSError: If copy or permission change fails
    """
    if not src.exists():
        raise FileNotFoundError(f"Source directory not found: {src}")

    if not src.is_dir():
        raise NotADirectoryError(f"Source is not a directory: {src}")

    # Copy the entire tree
    shutil.copytree(src, dst, dirs_exist_ok=True)

    # Normalize all permissions in the destination
    count = normalize_directory_recursive(dst)

    logger.info(f"Copied tree with permissions: {src} -> {dst} ({count} items)")
    return count


def get_permission_string(path: Path) -> str:
    """Get a human-readable permission string for a file.

    Args:
        path: Path to check

    Returns:
        Permission string like 'rw-r--r-- (0644)' or 'N/A' if file doesn't exist
    """
    if not path.exists():
        return "N/A"

    mode = path.stat().st_mode
    perms = stat.filemode(mode)
    octal = oct(mode & 0o777)

    return f"{perms[1:]} ({octal})"


def check_permissions(path: Path) -> dict:
    """Check if a file/directory has the expected permissions.

    Args:
        path: Path to check

    Returns:
        Dictionary with:
            - path: The path checked
            - current: Current permission octal (e.g., '0o644')
            - expected: Expected permission octal
            - is_correct: Whether permissions match expected
            - message: Human-readable status message
    """
    if not path.exists():
        return {
            "path": str(path),
            "current": None,
            "expected": None,
            "is_correct": False,
            "message": "Path does not exist"
        }

    current_mode = path.stat().st_mode & 0o777

    if path.is_dir():
        expected = PERMISSION_DIR
        file_type = "directory"
    elif is_executable_script(path):
        expected = PERMISSION_SCRIPT
        file_type = "script"
    else:
        expected = PERMISSION_FILE
        file_type = "file"

    is_correct = current_mode == expected

    return {
        "path": str(path),
        "current": oct(current_mode),
        "expected": oct(expected),
        "is_correct": is_correct,
        "message": (
            f"{file_type.capitalize()} has correct permissions"
            if is_correct
            else f"{file_type.capitalize()} has {oct(current_mode)}, expected {oct(expected)}"
        )
    }


def find_permission_issues(directory: Path) -> list:
    """Find all files with incorrect permissions in a directory tree.

    Args:
        directory: Root directory to check

    Returns:
        List of dictionaries from check_permissions() for files with issues
    """
    issues = []

    if not directory.exists() or not directory.is_dir():
        return issues

    # Check root directory
    check = check_permissions(directory)
    if not check["is_correct"]:
        issues.append(check)

    # Check all children
    for path in directory.rglob("*"):
        check = check_permissions(path)
        if not check["is_correct"]:
            issues.append(check)

    return issues
