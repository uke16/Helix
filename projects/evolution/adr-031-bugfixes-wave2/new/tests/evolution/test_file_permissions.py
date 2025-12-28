"""Tests for file_permissions module.

ADR-031: Fix 2 - File Permission Normalization Tests

These tests verify that the file permission normalization module correctly:
1. Normalizes file permissions to 0644 (rw-r--r--)
2. Normalizes script permissions to 0755 (rwxr-xr-x)
3. Detects shebangs and sets appropriate permissions
4. Normalizes directory permissions to 0755 (rwxr-xr-x)
5. Provides copy functions with automatic permission normalization
"""

import stat
import tempfile
from pathlib import Path

import pytest

from helix.evolution.file_permissions import (
    PERMISSION_DIR,
    PERMISSION_FILE,
    PERMISSION_SCRIPT,
    check_permissions,
    copy_with_permissions,
    copytree_with_permissions,
    find_permission_issues,
    get_permission_string,
    is_executable_script,
    normalize_directory_recursive,
    normalize_permissions,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_file(temp_dir):
    """Create a sample file with restrictive permissions."""
    file_path = temp_dir / "sample.txt"
    file_path.write_text("Hello, World!")
    file_path.chmod(0o600)  # Restrictive permissions (rw-------)
    return file_path


@pytest.fixture
def sample_script(temp_dir):
    """Create a sample shell script with restrictive permissions."""
    script_path = temp_dir / "script.sh"
    script_path.write_text("#!/bin/bash\necho 'Hello'")
    script_path.chmod(0o600)
    return script_path


@pytest.fixture
def sample_python_with_shebang(temp_dir):
    """Create a Python file with shebang."""
    py_path = temp_dir / "cli.py"
    py_path.write_text("#!/usr/bin/env python3\nprint('CLI')")
    py_path.chmod(0o600)
    return py_path


@pytest.fixture
def sample_python_without_shebang(temp_dir):
    """Create a regular Python file without shebang."""
    py_path = temp_dir / "module.py"
    py_path.write_text("def hello():\n    return 'Hello'")
    py_path.chmod(0o600)
    return py_path


class TestIsExecutableScript:
    """Tests for is_executable_script function."""

    def test_shell_script(self, sample_script):
        """Test that .sh files are considered executable."""
        assert is_executable_script(sample_script) is True

    def test_bash_script(self, temp_dir):
        """Test that .bash files are considered executable."""
        bash_path = temp_dir / "script.bash"
        bash_path.write_text("echo 'test'")
        assert is_executable_script(bash_path) is True

    def test_python_with_shebang(self, sample_python_with_shebang):
        """Test that Python files with shebang are executable."""
        assert is_executable_script(sample_python_with_shebang) is True

    def test_python_without_shebang(self, sample_python_without_shebang):
        """Test that Python files without shebang are not executable."""
        assert is_executable_script(sample_python_without_shebang) is False

    def test_regular_text_file(self, sample_file):
        """Test that regular files are not executable."""
        assert is_executable_script(sample_file) is False

    def test_file_without_extension_with_shebang(self, temp_dir):
        """Test that files without extension but with shebang are executable."""
        script = temp_dir / "my_command"
        script.write_text("#!/bin/sh\necho 'test'")
        assert is_executable_script(script) is True

    def test_file_without_extension_no_shebang(self, temp_dir):
        """Test that files without extension and no shebang are not executable."""
        file_path = temp_dir / "data"
        file_path.write_text("some data")
        assert is_executable_script(file_path) is False

    def test_nonexistent_file(self, temp_dir):
        """Test that nonexistent files return False."""
        assert is_executable_script(temp_dir / "nonexistent.sh") is False

    def test_directory(self, temp_dir):
        """Test that directories return False."""
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        assert is_executable_script(subdir) is False

    def test_perl_with_shebang(self, temp_dir):
        """Test that Perl files with shebang are executable."""
        pl_path = temp_dir / "script.pl"
        pl_path.write_text("#!/usr/bin/perl\nprint 'Hello';")
        assert is_executable_script(pl_path) is True

    def test_ruby_with_shebang(self, temp_dir):
        """Test that Ruby files with shebang are executable."""
        rb_path = temp_dir / "script.rb"
        rb_path.write_text("#!/usr/bin/env ruby\nputs 'Hello'")
        assert is_executable_script(rb_path) is True


class TestNormalizePermissions:
    """Tests for normalize_permissions function."""

    def test_normalize_regular_file(self, sample_file):
        """Test normalizing a regular file to 0644."""
        assert (sample_file.stat().st_mode & 0o777) == 0o600  # Pre-condition

        normalize_permissions(sample_file)

        assert (sample_file.stat().st_mode & 0o777) == PERMISSION_FILE

    def test_normalize_shell_script(self, sample_script):
        """Test normalizing a shell script to 0755."""
        normalize_permissions(sample_script)

        assert (sample_script.stat().st_mode & 0o777) == PERMISSION_SCRIPT

    def test_normalize_python_with_shebang(self, sample_python_with_shebang):
        """Test normalizing a Python script with shebang to 0755."""
        normalize_permissions(sample_python_with_shebang)

        assert (sample_python_with_shebang.stat().st_mode & 0o777) == PERMISSION_SCRIPT

    def test_normalize_python_without_shebang(self, sample_python_without_shebang):
        """Test normalizing a Python module without shebang to 0644."""
        normalize_permissions(sample_python_without_shebang)

        assert (sample_python_without_shebang.stat().st_mode & 0o777) == PERMISSION_FILE

    def test_normalize_directory(self, temp_dir):
        """Test normalizing a directory to 0755."""
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        subdir.chmod(0o700)  # Restrictive permissions

        normalize_permissions(subdir)

        assert (subdir.stat().st_mode & 0o777) == PERMISSION_DIR

    def test_normalize_nonexistent_file(self, temp_dir):
        """Test normalizing nonexistent file does not raise."""
        nonexistent = temp_dir / "nonexistent.txt"
        # Should not raise, just log warning
        normalize_permissions(nonexistent)

    def test_idempotent(self, sample_file):
        """Test that normalize_permissions is idempotent."""
        normalize_permissions(sample_file)
        mode1 = sample_file.stat().st_mode & 0o777

        normalize_permissions(sample_file)
        mode2 = sample_file.stat().st_mode & 0o777

        assert mode1 == mode2 == PERMISSION_FILE


class TestNormalizeDirectoryRecursive:
    """Tests for normalize_directory_recursive function."""

    def test_empty_directory(self, temp_dir):
        """Test normalizing an empty directory."""
        subdir = temp_dir / "empty"
        subdir.mkdir()
        subdir.chmod(0o700)

        count = normalize_directory_recursive(subdir)

        assert count == 1  # Just the directory itself
        assert (subdir.stat().st_mode & 0o777) == PERMISSION_DIR

    def test_directory_with_files(self, temp_dir):
        """Test normalizing a directory with files."""
        subdir = temp_dir / "project"
        subdir.mkdir()

        # Create files with restrictive permissions
        (subdir / "readme.txt").write_text("README")
        (subdir / "readme.txt").chmod(0o600)

        (subdir / "script.sh").write_text("#!/bin/bash")
        (subdir / "script.sh").chmod(0o600)

        count = normalize_directory_recursive(subdir)

        assert count == 3  # 2 files + 1 directory
        assert (subdir.stat().st_mode & 0o777) == PERMISSION_DIR
        assert ((subdir / "readme.txt").stat().st_mode & 0o777) == PERMISSION_FILE
        assert ((subdir / "script.sh").stat().st_mode & 0o777) == PERMISSION_SCRIPT

    def test_nested_directories(self, temp_dir):
        """Test normalizing nested directory structure."""
        # Create nested structure
        (temp_dir / "a" / "b" / "c").mkdir(parents=True)
        (temp_dir / "a" / "b" / "c").chmod(0o700)
        (temp_dir / "a" / "b").chmod(0o700)
        (temp_dir / "a").chmod(0o700)

        (temp_dir / "a" / "file1.txt").write_text("1")
        (temp_dir / "a" / "file1.txt").chmod(0o600)

        (temp_dir / "a" / "b" / "file2.py").write_text("def foo(): pass")
        (temp_dir / "a" / "b" / "file2.py").chmod(0o600)

        (temp_dir / "a" / "b" / "c" / "script.sh").write_text("#!/bin/bash")
        (temp_dir / "a" / "b" / "c" / "script.sh").chmod(0o600)

        root = temp_dir / "a"
        count = normalize_directory_recursive(root)

        # 4 directories (a, a/b, a/b/c, root) + 3 files
        # Actually just counts: a (root) + b + c + file1 + file2 + script = 6
        # Plus the root "a" = 6 total items counted
        assert count == 6

        # Verify all permissions
        assert ((temp_dir / "a").stat().st_mode & 0o777) == PERMISSION_DIR
        assert ((temp_dir / "a" / "b").stat().st_mode & 0o777) == PERMISSION_DIR
        assert ((temp_dir / "a" / "b" / "c").stat().st_mode & 0o777) == PERMISSION_DIR
        assert ((temp_dir / "a" / "file1.txt").stat().st_mode & 0o777) == PERMISSION_FILE
        assert ((temp_dir / "a" / "b" / "file2.py").stat().st_mode & 0o777) == PERMISSION_FILE
        assert ((temp_dir / "a" / "b" / "c" / "script.sh").stat().st_mode & 0o777) == PERMISSION_SCRIPT

    def test_nonexistent_directory_raises(self, temp_dir):
        """Test that nonexistent directory raises ValueError."""
        with pytest.raises(ValueError, match="does not exist"):
            normalize_directory_recursive(temp_dir / "nonexistent")

    def test_file_instead_of_directory_raises(self, sample_file):
        """Test that passing a file raises ValueError."""
        with pytest.raises(ValueError, match="not a directory"):
            normalize_directory_recursive(sample_file)


class TestCopyWithPermissions:
    """Tests for copy_with_permissions function."""

    def test_copy_regular_file(self, sample_file, temp_dir):
        """Test copying a regular file normalizes permissions."""
        dst = temp_dir / "copy" / "copied.txt"

        copy_with_permissions(sample_file, dst)

        assert dst.exists()
        assert dst.read_text() == "Hello, World!"
        assert (dst.stat().st_mode & 0o777) == PERMISSION_FILE
        # Parent directory should also be normalized
        assert (dst.parent.stat().st_mode & 0o777) == PERMISSION_DIR

    def test_copy_script(self, sample_script, temp_dir):
        """Test copying a script normalizes to executable."""
        dst = temp_dir / "bin" / "copied.sh"

        copy_with_permissions(sample_script, dst)

        assert dst.exists()
        assert (dst.stat().st_mode & 0o777) == PERMISSION_SCRIPT

    def test_copy_python_with_shebang(self, sample_python_with_shebang, temp_dir):
        """Test copying Python script with shebang becomes executable."""
        dst = temp_dir / "bin" / "cli.py"

        copy_with_permissions(sample_python_with_shebang, dst)

        assert (dst.stat().st_mode & 0o777) == PERMISSION_SCRIPT

    def test_copy_creates_parent_dirs(self, sample_file, temp_dir):
        """Test that copy creates parent directories."""
        dst = temp_dir / "a" / "b" / "c" / "d" / "file.txt"

        copy_with_permissions(sample_file, dst)

        assert dst.exists()
        assert dst.parent.exists()

    def test_copy_nonexistent_source_raises(self, temp_dir):
        """Test copying nonexistent file raises FileNotFoundError."""
        src = temp_dir / "nonexistent.txt"
        dst = temp_dir / "copy.txt"

        with pytest.raises(FileNotFoundError):
            copy_with_permissions(src, dst)

    def test_copy_directory_raises(self, temp_dir):
        """Test copying a directory raises IsADirectoryError."""
        src = temp_dir / "subdir"
        src.mkdir()
        dst = temp_dir / "copy"

        with pytest.raises(IsADirectoryError):
            copy_with_permissions(src, dst)

    def test_copy_preserves_content(self, temp_dir):
        """Test that file content is preserved after copy."""
        src = temp_dir / "source.txt"
        content = "Line 1\nLine 2\nLine 3"
        src.write_text(content)
        src.chmod(0o600)

        dst = temp_dir / "dest.txt"
        copy_with_permissions(src, dst)

        assert dst.read_text() == content

    def test_copy_overwrite(self, sample_file, temp_dir):
        """Test copying overwrites existing file."""
        dst = temp_dir / "existing.txt"
        dst.write_text("Old content")
        dst.chmod(0o600)

        copy_with_permissions(sample_file, dst)

        assert dst.read_text() == "Hello, World!"
        assert (dst.stat().st_mode & 0o777) == PERMISSION_FILE


class TestCopytreeWithPermissions:
    """Tests for copytree_with_permissions function."""

    def test_copy_directory_tree(self, temp_dir):
        """Test copying a directory tree with normalized permissions."""
        # Create source structure
        src = temp_dir / "source"
        src.mkdir()
        (src / "subdir").mkdir()
        (src / "file.txt").write_text("content")
        (src / "file.txt").chmod(0o600)
        (src / "script.sh").write_text("#!/bin/bash")
        (src / "script.sh").chmod(0o600)
        (src / "subdir" / "nested.py").write_text("pass")
        (src / "subdir" / "nested.py").chmod(0o600)

        dst = temp_dir / "dest"

        count = copytree_with_permissions(src, dst)

        assert count > 0
        assert dst.exists()
        assert (dst / "file.txt").exists()
        assert (dst / "script.sh").exists()
        assert (dst / "subdir" / "nested.py").exists()

        # All permissions should be normalized
        assert ((dst / "file.txt").stat().st_mode & 0o777) == PERMISSION_FILE
        assert ((dst / "script.sh").stat().st_mode & 0o777) == PERMISSION_SCRIPT
        assert ((dst / "subdir").stat().st_mode & 0o777) == PERMISSION_DIR
        assert ((dst / "subdir" / "nested.py").stat().st_mode & 0o777) == PERMISSION_FILE

    def test_copytree_nonexistent_source_raises(self, temp_dir):
        """Test copying nonexistent directory raises FileNotFoundError."""
        src = temp_dir / "nonexistent"
        dst = temp_dir / "dest"

        with pytest.raises(FileNotFoundError):
            copytree_with_permissions(src, dst)

    def test_copytree_file_as_source_raises(self, sample_file, temp_dir):
        """Test copying a file (not dir) raises NotADirectoryError."""
        dst = temp_dir / "dest"

        with pytest.raises(NotADirectoryError):
            copytree_with_permissions(sample_file, dst)


class TestGetPermissionString:
    """Tests for get_permission_string function."""

    def test_regular_file(self, sample_file):
        """Test permission string for regular file."""
        sample_file.chmod(0o644)
        result = get_permission_string(sample_file)
        assert "0o644" in result
        assert "rw-r--r--" in result

    def test_executable_file(self, sample_script):
        """Test permission string for executable file."""
        sample_script.chmod(0o755)
        result = get_permission_string(sample_script)
        assert "0o755" in result
        assert "rwxr-xr-x" in result

    def test_nonexistent_file(self, temp_dir):
        """Test permission string for nonexistent file."""
        result = get_permission_string(temp_dir / "nonexistent")
        assert result == "N/A"


class TestCheckPermissions:
    """Tests for check_permissions function."""

    def test_correct_file_permissions(self, sample_file):
        """Test checking correct file permissions."""
        sample_file.chmod(0o644)

        result = check_permissions(sample_file)

        assert result["is_correct"] is True
        assert result["current"] == "0o644"
        assert result["expected"] == "0o644"

    def test_incorrect_file_permissions(self, sample_file):
        """Test checking incorrect file permissions."""
        sample_file.chmod(0o600)

        result = check_permissions(sample_file)

        assert result["is_correct"] is False
        assert result["current"] == "0o600"
        assert result["expected"] == "0o644"

    def test_correct_script_permissions(self, sample_script):
        """Test checking correct script permissions."""
        sample_script.chmod(0o755)

        result = check_permissions(sample_script)

        assert result["is_correct"] is True
        assert result["expected"] == "0o755"

    def test_incorrect_script_permissions(self, sample_script):
        """Test checking incorrect script permissions."""
        sample_script.chmod(0o644)

        result = check_permissions(sample_script)

        assert result["is_correct"] is False
        assert result["current"] == "0o644"
        assert result["expected"] == "0o755"

    def test_correct_directory_permissions(self, temp_dir):
        """Test checking correct directory permissions."""
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        subdir.chmod(0o755)

        result = check_permissions(subdir)

        assert result["is_correct"] is True
        assert result["expected"] == "0o755"

    def test_nonexistent_path(self, temp_dir):
        """Test checking nonexistent path."""
        result = check_permissions(temp_dir / "nonexistent")

        assert result["is_correct"] is False
        assert result["current"] is None
        assert "does not exist" in result["message"]


class TestFindPermissionIssues:
    """Tests for find_permission_issues function."""

    def test_no_issues(self, temp_dir):
        """Test finding no issues when all permissions are correct."""
        subdir = temp_dir / "project"
        subdir.mkdir()
        subdir.chmod(0o755)

        (subdir / "file.txt").write_text("content")
        (subdir / "file.txt").chmod(0o644)

        (subdir / "script.sh").write_text("#!/bin/bash")
        (subdir / "script.sh").chmod(0o755)

        issues = find_permission_issues(subdir)

        assert len(issues) == 0

    def test_finds_issues(self, temp_dir):
        """Test finding permission issues."""
        subdir = temp_dir / "project"
        subdir.mkdir()
        subdir.chmod(0o755)

        # Create files with wrong permissions
        (subdir / "file.txt").write_text("content")
        (subdir / "file.txt").chmod(0o600)  # Wrong: should be 0644

        (subdir / "script.sh").write_text("#!/bin/bash")
        (subdir / "script.sh").chmod(0o644)  # Wrong: should be 0755

        issues = find_permission_issues(subdir)

        assert len(issues) == 2
        assert any("file.txt" in issue["path"] for issue in issues)
        assert any("script.sh" in issue["path"] for issue in issues)

    def test_nonexistent_directory_returns_empty(self, temp_dir):
        """Test that nonexistent directory returns empty list."""
        issues = find_permission_issues(temp_dir / "nonexistent")
        assert issues == []

    def test_file_instead_of_directory_returns_empty(self, sample_file):
        """Test that passing a file returns empty list."""
        issues = find_permission_issues(sample_file)
        assert issues == []


class TestIntegration:
    """Integration tests for file permissions module."""

    def test_restrictive_umask_scenario(self, temp_dir):
        """Test the scenario that caused the original bug.

        Simulates files created with a restrictive umask (0077).
        """
        # Create files with restrictive permissions (as would happen with umask 0077)
        project_dir = temp_dir / "evolution_project"
        project_dir.mkdir()
        project_dir.chmod(0o700)

        new_dir = project_dir / "new" / "src" / "helix"
        new_dir.mkdir(parents=True)

        # Simulate files created by Claude Code with restrictive umask
        module_py = new_dir / "module.py"
        module_py.write_text("def hello(): pass")
        module_py.chmod(0o600)

        cli_py = new_dir / "cli.py"
        cli_py.write_text("#!/usr/bin/env python3\nprint('CLI')")
        cli_py.chmod(0o600)

        # Find issues before normalization
        issues_before = find_permission_issues(project_dir)
        assert len(issues_before) > 0

        # Normalize everything
        count = normalize_directory_recursive(project_dir)
        assert count > 0

        # All issues should be resolved
        issues_after = find_permission_issues(project_dir)
        assert len(issues_after) == 0

        # Verify specific files
        assert (module_py.stat().st_mode & 0o777) == PERMISSION_FILE
        assert (cli_py.stat().st_mode & 0o777) == PERMISSION_SCRIPT

    def test_deployer_copy_scenario(self, temp_dir):
        """Test copying files as the deployer would."""
        # Create source files with wrong permissions
        src_dir = temp_dir / "source"
        src_dir.mkdir()

        (src_dir / "new_feature.py").write_text("class Feature: pass")
        (src_dir / "new_feature.py").chmod(0o600)

        (src_dir / "deploy.sh").write_text("#!/bin/bash\necho 'deploy'")
        (src_dir / "deploy.sh").chmod(0o600)

        # Copy using copy_with_permissions
        dst_dir = temp_dir / "dest"
        dst_dir.mkdir()

        for src_file in src_dir.iterdir():
            dst_file = dst_dir / src_file.name
            copy_with_permissions(src_file, dst_file)

        # Verify all copied files have correct permissions
        assert ((dst_dir / "new_feature.py").stat().st_mode & 0o777) == PERMISSION_FILE
        assert ((dst_dir / "deploy.sh").stat().st_mode & 0o777) == PERMISSION_SCRIPT


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
