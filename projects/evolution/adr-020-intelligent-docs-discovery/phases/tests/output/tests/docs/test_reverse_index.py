"""
Tests for ReverseIndex.

ADR-020: Tests the CODE -> ADR reverse index that maps source files
back to their originating ADRs.
"""

import tempfile
from pathlib import Path
from textwrap import dedent

import pytest

from helix.docs.reverse_index import FileInfo, FileStatus, ReverseIndex


@pytest.fixture
def sample_adr_content():
    """Sample ADR file content for testing."""
    return dedent("""
        ---
        adr_id: "013"
        title: "Debug Observability Engine"
        status: Implemented

        files:
          create:
            - src/helix/debug/stream_parser.py
            - src/helix/debug/event_handler.py
          modify:
            - src/helix/tools/main.py
        ---

        # ADR-013: Debug Observability Engine

        ## Status
        Implemented
    """).strip()


@pytest.fixture
def sample_adr_content_proposed():
    """Sample ADR with Proposed status."""
    return dedent("""
        ---
        adr_id: "015"
        title: "New Feature"
        status: Proposed

        files:
          create:
            - src/helix/new/feature.py
        ---

        # ADR-015: New Feature
    """).strip()


@pytest.fixture
def sample_adr_modifies_only():
    """Sample ADR that only modifies files."""
    return dedent("""
        ---
        adr_id: "017"
        title: "Enhancement"
        status: Implemented

        files:
          modify:
            - src/helix/debug/stream_parser.py
            - src/helix/tools/main.py
        ---

        # ADR-017: Enhancement
    """).strip()


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project structure with ADRs and source files."""
    # Create adr directory
    adr_dir = tmp_path / "adr"
    adr_dir.mkdir()

    # Create source directories
    (tmp_path / "src" / "helix" / "debug").mkdir(parents=True)
    (tmp_path / "src" / "helix" / "tools").mkdir(parents=True)

    return tmp_path


@pytest.fixture
def project_with_adrs(temp_project, sample_adr_content, sample_adr_modifies_only):
    """Create project with ADR files and some source files."""
    adr_dir = temp_project / "adr"

    # Create ADR-013
    (adr_dir / "013-debug-observability.md").write_text(sample_adr_content)

    # Create ADR-017
    (adr_dir / "017-enhancement.md").write_text(sample_adr_modifies_only)

    # Create some source files that exist
    (temp_project / "src" / "helix" / "debug" / "stream_parser.py").write_text(
        "# Stream parser"
    )
    (temp_project / "src" / "helix" / "tools" / "main.py").write_text("# Main tools")

    # Note: event_handler.py is NOT created (orphaned file)

    return temp_project


@pytest.fixture
def reverse_index(project_with_adrs):
    """Create ReverseIndex for test project."""
    return ReverseIndex(
        adr_dir=project_with_adrs / "adr", project_root=project_with_adrs
    )


class TestReverseIndexInit:
    """Tests for ReverseIndex initialization."""

    def test_init_with_default_paths(self, tmp_path):
        """Test initialization with default paths."""
        index = ReverseIndex(project_root=tmp_path)
        assert index.adr_dir == tmp_path / "adr"
        assert index.project_root == tmp_path

    def test_init_with_custom_paths(self, tmp_path):
        """Test initialization with custom paths."""
        custom_adr = tmp_path / "custom_adr"
        index = ReverseIndex(adr_dir=custom_adr, project_root=tmp_path)
        assert index.adr_dir == custom_adr


class TestReverseIndexBuild:
    """Tests for ReverseIndex.build() method."""

    def test_build_creates_file_entries(self, reverse_index):
        """Test that build creates entries for files."""
        index = reverse_index.build()

        assert "src/helix/debug/stream_parser.py" in index
        assert "src/helix/tools/main.py" in index

    def test_build_tracks_created_by(self, reverse_index):
        """Test that created_by is tracked correctly."""
        index = reverse_index.build()

        file_info = index["src/helix/debug/stream_parser.py"]
        assert file_info.created_by == "ADR-013"

    def test_build_tracks_adr_file(self, reverse_index):
        """Test that adr_file path is tracked."""
        index = reverse_index.build()

        file_info = index["src/helix/debug/stream_parser.py"]
        assert file_info.adr_file == "adr/013-debug-observability.md"

    def test_build_tracks_modified_by(self, reverse_index):
        """Test that modified_by is tracked correctly."""
        index = reverse_index.build()

        file_info = index["src/helix/debug/stream_parser.py"]
        assert "ADR-017" in file_info.modified_by

    def test_build_detects_orphaned_files(self, reverse_index):
        """Test that orphaned files are detected."""
        index = reverse_index.build()

        # event_handler.py was not created but is in ADR
        file_info = index["src/helix/debug/event_handler.py"]
        assert file_info.status == FileStatus.ORPHANED
        assert file_info.exists is False

    def test_build_detects_tracked_files(self, reverse_index):
        """Test that existing tracked files are marked correctly."""
        index = reverse_index.build()

        file_info = index["src/helix/debug/stream_parser.py"]
        assert file_info.status == FileStatus.TRACKED
        assert file_info.exists is True

    def test_build_creates_history(self, reverse_index):
        """Test that history is tracked."""
        index = reverse_index.build()

        file_info = index["src/helix/debug/stream_parser.py"]
        assert len(file_info.history) >= 2  # create + modify
        actions = [h["action"] for h in file_info.history]
        assert "create" in actions
        assert "modify" in actions

    def test_build_caches_result(self, reverse_index):
        """Test that build result is cached."""
        index1 = reverse_index.build()
        index2 = reverse_index.build()

        assert index1 is index2

    def test_build_skips_index_md(self, project_with_adrs):
        """Test that INDEX.md is skipped."""
        # Create INDEX.md in adr directory
        (project_with_adrs / "adr" / "INDEX.md").write_text("# ADR Index")

        index = ReverseIndex(
            adr_dir=project_with_adrs / "adr", project_root=project_with_adrs
        )
        result = index.build()

        # Should not cause errors
        assert isinstance(result, dict)


class TestReverseIndexLookup:
    """Tests for ReverseIndex.lookup() method."""

    def test_lookup_existing_file(self, reverse_index):
        """Test lookup of tracked file."""
        info = reverse_index.lookup("src/helix/debug/stream_parser.py")

        assert info is not None
        assert info.created_by == "ADR-013"
        assert info.status == FileStatus.TRACKED

    def test_lookup_orphaned_file(self, reverse_index):
        """Test lookup of orphaned file."""
        info = reverse_index.lookup("src/helix/debug/event_handler.py")

        assert info is not None
        assert info.status == FileStatus.ORPHANED

    def test_lookup_untracked_file(self, reverse_index):
        """Test lookup of file not in any ADR."""
        info = reverse_index.lookup("src/helix/unknown/file.py")

        assert info is None


class TestReverseIndexFilters:
    """Tests for filter methods."""

    def test_get_orphaned(self, reverse_index):
        """Test getting orphaned files."""
        orphaned = reverse_index.get_orphaned()

        assert len(orphaned) == 1
        assert orphaned[0].path == "src/helix/debug/event_handler.py"

    def test_get_tracked(self, reverse_index):
        """Test getting tracked files."""
        tracked = reverse_index.get_tracked()

        paths = [f.path for f in tracked]
        assert "src/helix/debug/stream_parser.py" in paths
        assert "src/helix/tools/main.py" in paths

    def test_get_by_adr_with_prefix(self, reverse_index):
        """Test getting files by ADR ID with prefix."""
        files = reverse_index.get_by_adr("ADR-013")

        assert len(files) >= 2
        paths = [f.path for f in files]
        assert "src/helix/debug/stream_parser.py" in paths

    def test_get_by_adr_without_prefix(self, reverse_index):
        """Test getting files by ADR ID without prefix."""
        files = reverse_index.get_by_adr("013")

        assert len(files) >= 2
        paths = [f.path for f in files]
        assert "src/helix/debug/stream_parser.py" in paths

    def test_get_by_adr_no_match(self, reverse_index):
        """Test getting files for non-existent ADR."""
        files = reverse_index.get_by_adr("999")

        assert len(files) == 0


class TestReverseIndexStatistics:
    """Tests for get_statistics() method."""

    def test_statistics_counts(self, reverse_index):
        """Test statistics counts."""
        stats = reverse_index.get_statistics()

        assert stats["total_files"] >= 3
        assert stats["tracked"] >= 2
        assert stats["orphaned"] >= 1

    def test_statistics_coverage(self, reverse_index):
        """Test coverage percentage calculation."""
        stats = reverse_index.get_statistics()

        # Coverage should be between 0 and 100
        assert 0 <= stats["coverage_percent"] <= 100

    def test_statistics_empty_index(self, tmp_path):
        """Test statistics with empty ADR directory."""
        adr_dir = tmp_path / "adr"
        adr_dir.mkdir()

        index = ReverseIndex(adr_dir=adr_dir, project_root=tmp_path)
        stats = index.get_statistics()

        assert stats["total_files"] == 0
        assert stats["coverage_percent"] == 0


class TestFileInfo:
    """Tests for FileInfo dataclass."""

    def test_file_info_to_dict(self):
        """Test FileInfo serialization."""
        info = FileInfo(
            path="src/test.py",
            status=FileStatus.TRACKED,
            created_by="ADR-001",
            adr_file="adr/001-test.md",
            modified_by=["ADR-002"],
            exists=True,
            history=[{"adr": "ADR-001", "action": "create", "adr_file": "adr/001.md"}],
        )

        result = info.to_dict()

        assert result["path"] == "src/test.py"
        assert result["status"] == "tracked"
        assert result["created_by"] == "ADR-001"
        assert result["adr_file"] == "adr/001-test.md"
        assert result["modified_by"] == ["ADR-002"]
        assert result["exists"] is True
        assert len(result["history"]) == 1

    def test_file_info_to_dict_minimal(self):
        """Test FileInfo serialization with minimal fields."""
        info = FileInfo(
            path="src/test.py",
            status=FileStatus.UNTRACKED,
            exists=True,
        )

        result = info.to_dict()

        assert result["path"] == "src/test.py"
        assert result["status"] == "untracked"
        assert "created_by" not in result
        assert "modified_by" not in result


class TestFormatLookup:
    """Tests for format_lookup() method."""

    def test_format_lookup_tracked(self, reverse_index):
        """Test formatting tracked file lookup."""
        result = reverse_index.format_lookup("src/helix/debug/stream_parser.py")

        assert "src/helix/debug/stream_parser.py:" in result
        assert "status: tracked" in result
        assert "created_by: ADR-013" in result

    def test_format_lookup_untracked(self, reverse_index):
        """Test formatting untracked file lookup."""
        result = reverse_index.format_lookup("src/unknown/file.py")

        assert "untracked" in result
        assert "no ADR reference" in result

    def test_format_lookup_with_history(self, reverse_index):
        """Test formatting lookup with history."""
        result = reverse_index.format_lookup("src/helix/debug/stream_parser.py")

        assert "history:" in result
        assert "ADR-013: create" in result


class TestADRParsing:
    """Tests for ADR file parsing edge cases."""

    def test_parse_adr_without_frontmatter(self, temp_project):
        """Test handling ADR without frontmatter."""
        adr_dir = temp_project / "adr"
        (adr_dir / "invalid.md").write_text("# Just a header\n\nNo frontmatter here.")

        index = ReverseIndex(adr_dir=adr_dir, project_root=temp_project)
        result = index.build()

        # Should not cause errors
        assert isinstance(result, dict)

    def test_parse_adr_without_adr_id(self, temp_project):
        """Test handling ADR without adr_id field."""
        adr_dir = temp_project / "adr"
        content = dedent("""
            ---
            title: "No ID"
            status: Draft
            ---
            # No ID ADR
        """).strip()
        (adr_dir / "no-id.md").write_text(content)

        index = ReverseIndex(adr_dir=adr_dir, project_root=temp_project)
        result = index.build()

        # Should not cause errors
        assert isinstance(result, dict)

    def test_parse_adr_without_files_section(self, temp_project):
        """Test handling ADR without files section."""
        adr_dir = temp_project / "adr"
        content = dedent("""
            ---
            adr_id: "100"
            title: "No Files"
            status: Draft
            ---
            # No Files ADR
        """).strip()
        (adr_dir / "100-no-files.md").write_text(content)

        index = ReverseIndex(adr_dir=adr_dir, project_root=temp_project)
        result = index.build()

        # Should not cause errors
        assert isinstance(result, dict)


class TestFileStatus:
    """Tests for FileStatus enum."""

    def test_file_status_values(self):
        """Test FileStatus enum values."""
        assert FileStatus.TRACKED.value == "tracked"
        assert FileStatus.UNTRACKED.value == "untracked"
        assert FileStatus.ORPHANED.value == "orphaned"

    def test_file_status_string_enum(self):
        """Test FileStatus is a string enum."""
        assert isinstance(FileStatus.TRACKED, str)
        assert str(FileStatus.TRACKED) == "tracked"
