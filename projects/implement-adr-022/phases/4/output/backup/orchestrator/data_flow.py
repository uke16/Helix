"""Data Flow Manager for HELIX v4.

Handles the automatic copying of outputs from one phase
to inputs of the next phase, supporting glob patterns.
"""

import fnmatch
import shutil
from pathlib import Path
from typing import Any

from .status import ProjectStatus


class DataFlowManager:
    """Manages data flow between phases.

    Automatically copies outputs from completed phases to the input
    directories of dependent phases based on input_from configuration.

    The DataFlowManager supports:
    - Direct file copying
    - Glob pattern matching (*.yaml, src/**, etc.)
    - Project-level file copying (spec.yaml, ADR files)

    Example:
        manager = DataFlowManager()
        await manager.prepare_phase_inputs(
            project_dir=Path("projects/external/my-feature"),
            phase=phase_config,
            status=project_status,
        )
    """

    def __init__(self) -> None:
        """Initialize the DataFlowManager."""
        pass

    async def prepare_phase_inputs(
        self,
        project_dir: Path,
        phase: Any,
        status: ProjectStatus,
    ) -> list[Path]:
        """Prepare inputs for a phase from previous outputs.

        Copies files from source phases' output directories to the
        target phase's input directory.

        Args:
            project_dir: Project root directory.
            phase: Phase configuration with input_from.
            status: Current project status.

        Returns:
            List of paths that were copied.
        """
        copied_files: list[Path] = []

        # Get input_from configuration
        input_from = self._get_input_from(phase)
        if not input_from:
            # No explicit input_from, just copy project files
            phase_dir = project_dir / "phases" / phase.id
            input_dir = phase_dir / "input"
            input_dir.mkdir(parents=True, exist_ok=True)
            copied_files.extend(self._copy_project_files(project_dir, input_dir))
            return copied_files

        # Normalize input_from to list
        if isinstance(input_from, str):
            input_from = [input_from]

        # Get phase directory
        phase_dir = project_dir / "phases" / phase.id
        input_dir = phase_dir / "input"
        input_dir.mkdir(parents=True, exist_ok=True)

        # Copy from each source phase
        for source in input_from:
            if isinstance(source, dict):
                # Detailed specification: {phase_id: [patterns]}
                for source_phase_id, patterns in source.items():
                    copied = self._copy_from_phase(
                        project_dir, source_phase_id, input_dir, patterns
                    )
                    copied_files.extend(copied)
            else:
                # Simple phase ID - copy all outputs
                copied = self._copy_from_phase(
                    project_dir, source, input_dir, None
                )
                copied_files.extend(copied)

        # Also copy project-level files
        copied_files.extend(self._copy_project_files(project_dir, input_dir))

        return copied_files

    def _get_input_from(self, phase: Any) -> list[Any] | None:
        """Extract input_from configuration from phase.

        Args:
            phase: Phase configuration object.

        Returns:
            input_from configuration or None.
        """
        # Try config.input_from first (new style)
        if hasattr(phase, "config") and isinstance(phase.config, dict):
            input_from = phase.config.get("input_from")
            if input_from:
                return input_from

        # Try input.from (alternative style)
        if hasattr(phase, "input") and isinstance(phase.input, dict):
            input_from = phase.input.get("from")
            if input_from:
                return input_from

        # Try direct input_from attribute
        if hasattr(phase, "input_from"):
            return phase.input_from

        return None

    def _copy_from_phase(
        self,
        project_dir: Path,
        source_phase_id: str,
        dest_dir: Path,
        patterns: list[str] | None,
    ) -> list[Path]:
        """Copy outputs from a source phase.

        Args:
            project_dir: Project root directory.
            source_phase_id: ID of the source phase.
            dest_dir: Destination input directory.
            patterns: Optional glob patterns to filter files.

        Returns:
            List of copied file paths.
        """
        copied: list[Path] = []

        source_dir = project_dir / "phases" / source_phase_id / "output"
        if not source_dir.exists():
            return copied

        if patterns is None:
            # Copy all files from output
            copied.extend(self._copy_directory_contents(source_dir, dest_dir))
        else:
            # Copy only matching patterns
            for pattern in patterns:
                copied.extend(
                    self._copy_matching_files(source_dir, dest_dir, pattern)
                )

        return copied

    def _copy_directory_contents(
        self, source_dir: Path, dest_dir: Path
    ) -> list[Path]:
        """Copy all contents from source to destination.

        Args:
            source_dir: Source directory.
            dest_dir: Destination directory.

        Returns:
            List of copied paths.
        """
        copied: list[Path] = []

        for item in source_dir.iterdir():
            dest_path = dest_dir / item.name

            if item.is_file():
                shutil.copy2(item, dest_path)
                copied.append(dest_path)
            elif item.is_dir():
                if dest_path.exists():
                    shutil.rmtree(dest_path)
                shutil.copytree(item, dest_path)
                copied.append(dest_path)

        return copied

    def _copy_matching_files(
        self, source_dir: Path, dest_dir: Path, pattern: str
    ) -> list[Path]:
        """Copy files matching a glob pattern.

        Args:
            source_dir: Source directory.
            dest_dir: Destination directory.
            pattern: Glob pattern (e.g., "*.yaml", "src/**/*.py").

        Returns:
            List of copied paths.
        """
        copied: list[Path] = []

        # Use Path.glob for pattern matching
        for item in source_dir.glob(pattern):
            # Calculate relative path from source_dir
            rel_path = item.relative_to(source_dir)
            dest_path = dest_dir / rel_path

            # Ensure parent directory exists
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            if item.is_file():
                shutil.copy2(item, dest_path)
                copied.append(dest_path)
            elif item.is_dir():
                if dest_path.exists():
                    shutil.rmtree(dest_path)
                shutil.copytree(item, dest_path)
                copied.append(dest_path)

        return copied

    def _copy_project_files(
        self, project_dir: Path, input_dir: Path
    ) -> list[Path]:
        """Copy project-level files to phase input.

        Copies standard project files that all phases might need:
        - spec.yaml
        - ADR-*.md files
        - phases.yaml (for reference)

        Args:
            project_dir: Project root directory.
            input_dir: Phase input directory.

        Returns:
            List of copied paths.
        """
        copied: list[Path] = []

        # Copy spec.yaml if exists
        spec_path = project_dir / "spec.yaml"
        if spec_path.exists():
            dest = input_dir / "spec.yaml"
            if not dest.exists():  # Don't overwrite
                shutil.copy2(spec_path, dest)
                copied.append(dest)

        # Copy ADR files
        for adr in project_dir.glob("ADR-*.md"):
            dest = input_dir / adr.name
            if not dest.exists():
                shutil.copy2(adr, dest)
                copied.append(dest)

        # Also check for numbered ADR format
        for adr in project_dir.glob("[0-9][0-9][0-9]-*.md"):
            dest = input_dir / adr.name
            if not dest.exists():
                shutil.copy2(adr, dest)
                copied.append(dest)

        # Copy phases.yaml for reference
        phases_path = project_dir / "phases.yaml"
        if phases_path.exists():
            dest = input_dir / "phases.yaml"
            if not dest.exists():
                shutil.copy2(phases_path, dest)
                copied.append(dest)

        return copied

    def collect_outputs(
        self, project_dir: Path, dest_dir: Path, phases: list[str] | None = None
    ) -> list[Path]:
        """Collect all outputs from phases to a destination.

        Useful for integration phases that need to collect all
        outputs into the main project.

        Args:
            project_dir: Project root directory.
            dest_dir: Destination directory.
            phases: Optional list of phase IDs to collect from.
                   If None, collects from all phases.

        Returns:
            List of collected paths.
        """
        collected: list[Path] = []

        phases_dir = project_dir / "phases"
        if not phases_dir.exists():
            return collected

        # Get phase directories
        if phases:
            phase_dirs = [phases_dir / p for p in phases]
        else:
            phase_dirs = sorted(phases_dir.iterdir())

        for phase_dir in phase_dirs:
            if not phase_dir.is_dir():
                continue

            output_dir = phase_dir / "output"
            if not output_dir.exists():
                continue

            # Copy output contents
            for item in output_dir.iterdir():
                dest_path = dest_dir / item.name

                if item.is_file():
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest_path)
                    collected.append(dest_path)
                elif item.is_dir():
                    if dest_path.exists():
                        # Merge directories
                        self._merge_directories(item, dest_path)
                    else:
                        shutil.copytree(item, dest_path)
                    collected.append(dest_path)

        return collected

    def _merge_directories(self, source: Path, dest: Path) -> None:
        """Merge source directory into destination.

        Files in source will overwrite files in dest.

        Args:
            source: Source directory.
            dest: Destination directory.
        """
        for item in source.iterdir():
            dest_path = dest / item.name

            if item.is_file():
                shutil.copy2(item, dest_path)
            elif item.is_dir():
                if dest_path.exists():
                    self._merge_directories(item, dest_path)
                else:
                    shutil.copytree(item, dest_path)

    def cleanup_inputs(self, phase_dir: Path) -> None:
        """Clean up the input directory of a phase.

        Args:
            phase_dir: Phase directory.
        """
        input_dir = phase_dir / "input"
        if input_dir.exists():
            for item in input_dir.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
