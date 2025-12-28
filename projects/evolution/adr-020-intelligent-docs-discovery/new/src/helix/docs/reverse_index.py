"""
Reverse Index for CODE → ADR Mapping.

ADR-020: Builds a reverse index mapping source files to their originating ADRs.
Enables traceability from any file back to the ADR that specified its creation.

Usage:
    from helix.docs.reverse_index import ReverseIndex

    index = ReverseIndex()

    # Lookup a single file
    info = index.lookup("src/helix/debug/stream_parser.py")
    if info:
        print(f"Created by: {info.created_by}")

    # Get full index
    full_index = index.build()
    for path, info in full_index.items():
        print(f"{path}: {info.status}")
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


class FileStatus(str, Enum):
    """Tracking status of a file."""

    TRACKED = "tracked"  # File has ADR reference and exists
    UNTRACKED = "untracked"  # File exists but no ADR reference
    ORPHANED = "orphaned"  # ADR says "create" but file missing


@dataclass
class FileInfo:
    """Information about a file's ADR provenance."""

    path: str
    status: FileStatus
    created_by: str | None = None  # e.g., "ADR-013"
    adr_file: str | None = None  # e.g., "adr/013-debug-observability.md"
    modified_by: list[str] = field(default_factory=list)  # e.g., ["ADR-015", "ADR-017"]
    exists: bool = True
    history: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {
            "path": self.path,
            "status": self.status.value,
            "exists": self.exists,
        }
        if self.created_by:
            result["created_by"] = self.created_by
        if self.adr_file:
            result["adr_file"] = self.adr_file
        if self.modified_by:
            result["modified_by"] = self.modified_by
        if self.history:
            result["history"] = self.history
        return result


@dataclass
class ADRHeader:
    """Parsed ADR header information."""

    adr_id: str
    title: str
    status: str
    file_path: Path
    files_create: list[str] = field(default_factory=list)
    files_modify: list[str] = field(default_factory=list)
    files_docs: list[str] = field(default_factory=list)


class ReverseIndex:
    """Builds reverse index from files to ADRs.

    Parses all ADR files and builds a mapping:
    - file_path → ADR that created it
    - file_path → ADRs that modified it

    Categories:
    - tracked: File has ADR reference and exists
    - untracked: File exists but no ADR (legacy, tests)
    - orphaned: ADR says "create" but file doesn't exist

    Example:
        index = ReverseIndex()
        info = index.lookup("src/helix/debug/stream_parser.py")

        # Returns:
        # FileInfo(
        #     created_by="ADR-013",
        #     adr_file="adr/013-debug-observability.md",
        #     exists=True
        # )
    """

    def __init__(self, adr_dir: Path | None = None, project_root: Path | None = None):
        """Initialize the reverse index.

        Args:
            adr_dir: Directory containing ADR files. Defaults to "adr".
            project_root: Project root directory. Defaults to current directory.
        """
        self.project_root = project_root or Path.cwd()
        self.adr_dir = adr_dir or self.project_root / "adr"
        self._cache: dict[str, FileInfo] | None = None

    def _parse_adr_header(self, adr_file: Path) -> ADRHeader | None:
        """Parse the YAML frontmatter from an ADR file.

        Args:
            adr_file: Path to ADR markdown file

        Returns:
            ADRHeader if valid, None if parsing fails
        """
        try:
            content = adr_file.read_text(encoding="utf-8")

            # Extract YAML frontmatter between --- markers
            match = re.match(r"^---\n(.+?)\n---", content, re.DOTALL)
            if not match:
                return None

            frontmatter = yaml.safe_load(match.group(1))
            if not frontmatter:
                return None

            # Extract required fields
            adr_id = frontmatter.get("adr_id")
            if not adr_id:
                return None

            # Extract files section
            files = frontmatter.get("files", {})

            return ADRHeader(
                adr_id=str(adr_id),
                title=frontmatter.get("title", ""),
                status=frontmatter.get("status", ""),
                file_path=adr_file,
                files_create=files.get("create", []),
                files_modify=files.get("modify", []),
                files_docs=files.get("docs", []),
            )
        except Exception:
            return None

    def build(self) -> dict[str, FileInfo]:
        """Build the complete reverse index.

        Scans all ADR files and builds mappings for:
        - files.create → created_by
        - files.modify → modified_by

        Returns:
            Dictionary mapping file paths to FileInfo objects
        """
        if self._cache is not None:
            return self._cache

        index: dict[str, FileInfo] = {}

        # Find all ADR markdown files (exclude drafts)
        adr_files = sorted(self.adr_dir.glob("*.md"))

        for adr_file in adr_files:
            # Skip INDEX.md and other non-ADR files
            if adr_file.name in ("INDEX.md", "README.md"):
                continue

            header = self._parse_adr_header(adr_file)
            if not header:
                continue

            adr_ref = f"ADR-{header.adr_id}"
            adr_rel_path = str(adr_file.relative_to(self.project_root))

            # Process created files
            for file_path in header.files_create:
                full_path = self.project_root / file_path
                exists = full_path.exists()

                if file_path in index:
                    # File already tracked, add to history
                    existing = index[file_path]
                    existing.history.append(
                        {
                            "adr": adr_ref,
                            "action": "create",
                            "adr_file": adr_rel_path,
                        }
                    )
                else:
                    status = FileStatus.TRACKED if exists else FileStatus.ORPHANED
                    index[file_path] = FileInfo(
                        path=file_path,
                        status=status,
                        created_by=adr_ref,
                        adr_file=adr_rel_path,
                        exists=exists,
                        history=[
                            {
                                "adr": adr_ref,
                                "action": "create",
                                "adr_file": adr_rel_path,
                            }
                        ],
                    )

            # Process modified files
            for file_path in header.files_modify:
                full_path = self.project_root / file_path
                exists = full_path.exists()

                if file_path in index:
                    # Add modification record
                    existing = index[file_path]
                    if adr_ref not in existing.modified_by:
                        existing.modified_by.append(adr_ref)
                    existing.history.append(
                        {
                            "adr": adr_ref,
                            "action": "modify",
                            "adr_file": adr_rel_path,
                        }
                    )
                else:
                    # File only modified, not created by an ADR
                    status = FileStatus.TRACKED if exists else FileStatus.ORPHANED
                    index[file_path] = FileInfo(
                        path=file_path,
                        status=status,
                        modified_by=[adr_ref],
                        exists=exists,
                        history=[
                            {
                                "adr": adr_ref,
                                "action": "modify",
                                "adr_file": adr_rel_path,
                            }
                        ],
                    )

        self._cache = index
        return index

    def lookup(self, file_path: str) -> FileInfo | None:
        """Look up ADR information for a specific file.

        Args:
            file_path: Path to the file (relative to project root)

        Returns:
            FileInfo if file is tracked, None otherwise
        """
        index = self.build()
        return index.get(file_path)

    def get_orphaned(self) -> list[FileInfo]:
        """Get all orphaned files (ADR says create but file missing).

        Returns:
            List of orphaned file entries
        """
        index = self.build()
        return [f for f in index.values() if f.status == FileStatus.ORPHANED]

    def get_tracked(self) -> list[FileInfo]:
        """Get all tracked files (have ADR reference and exist).

        Returns:
            List of tracked file entries
        """
        index = self.build()
        return [f for f in index.values() if f.status == FileStatus.TRACKED]

    def get_by_adr(self, adr_id: str) -> list[FileInfo]:
        """Get all files associated with a specific ADR.

        Args:
            adr_id: ADR ID (e.g., "013" or "ADR-013")

        Returns:
            List of files created or modified by this ADR
        """
        # Normalize ADR ID
        adr_id = adr_id.replace("ADR-", "")
        adr_ref = f"ADR-{adr_id}"

        index = self.build()
        return [
            f
            for f in index.values()
            if f.created_by == adr_ref or adr_ref in f.modified_by
        ]

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about the reverse index.

        Returns:
            Dictionary with counts and percentages
        """
        index = self.build()

        tracked = sum(1 for f in index.values() if f.status == FileStatus.TRACKED)
        orphaned = sum(1 for f in index.values() if f.status == FileStatus.ORPHANED)
        total = len(index)

        return {
            "total_files": total,
            "tracked": tracked,
            "orphaned": orphaned,
            "coverage_percent": round(tracked / total * 100, 1) if total > 0 else 0,
        }

    def format_lookup(self, file_path: str) -> str:
        """Format lookup result for CLI output.

        Args:
            file_path: Path to look up

        Returns:
            Formatted string with file info
        """
        info = self.lookup(file_path)

        if not info:
            return f"{file_path}:\n  status: untracked (no ADR reference)"

        lines = [f"{file_path}:"]
        lines.append(f"  status: {info.status.value}")

        if info.created_by:
            lines.append(f"  created_by: {info.created_by}")
        if info.adr_file:
            lines.append(f"  adr_file: {info.adr_file}")
        if info.modified_by:
            lines.append(f"  modified_by: {', '.join(info.modified_by)}")
        if info.history:
            lines.append("  history:")
            for h in info.history:
                lines.append(f"    - {h['adr']}: {h['action']}")

        return "\n".join(lines)


def main():
    """CLI entry point for reverse index operations."""
    import argparse

    parser = argparse.ArgumentParser(description="CODE → ADR reverse index")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Lookup command
    lookup_parser = subparsers.add_parser("lookup", help="Look up a file")
    lookup_parser.add_argument("file_path", help="File path to look up")

    # Stats command
    subparsers.add_parser("stats", help="Show index statistics")

    # Orphaned command
    subparsers.add_parser("orphaned", help="List orphaned files")

    # By-ADR command
    by_adr_parser = subparsers.add_parser("by-adr", help="Files by ADR")
    by_adr_parser.add_argument("adr_id", help="ADR ID (e.g., 013)")

    args = parser.parse_args()

    index = ReverseIndex()

    if args.command == "lookup":
        print(index.format_lookup(args.file_path))
    elif args.command == "stats":
        stats = index.get_statistics()
        print(f"Reverse Index Statistics:")
        print(f"  Total files: {stats['total_files']}")
        print(f"  Tracked: {stats['tracked']}")
        print(f"  Orphaned: {stats['orphaned']}")
        print(f"  Coverage: {stats['coverage_percent']}%")
    elif args.command == "orphaned":
        orphaned = index.get_orphaned()
        if orphaned:
            print(f"Orphaned files ({len(orphaned)}):")
            for f in orphaned:
                print(f"  - {f.path} (from {f.created_by})")
        else:
            print("No orphaned files found.")
    elif args.command == "by-adr":
        files = index.get_by_adr(args.adr_id)
        if files:
            print(f"Files for ADR-{args.adr_id} ({len(files)}):")
            for f in files:
                action = "created" if f.created_by else "modified"
                print(f"  - {f.path} ({action})")
        else:
            print(f"No files found for ADR-{args.adr_id}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
