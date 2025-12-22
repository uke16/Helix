"""
Evolution Project Manager for HELIX v4 Self-Evolution System.

This module provides classes for managing evolution projects - projects where
HELIX develops new features or modifications to itself.

The evolution workflow:
1. Consultant creates an evolution project (spec.yaml, phases.yaml)
2. Developer phases run and produce code in new/ and modified/ directories
3. Project status progresses through: pending -> developing -> ready -> deployed -> integrated
4. After validation, changes are integrated into the main codebase
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


class EvolutionStatus(str, Enum):
    """Status of an evolution project."""

    PENDING = "pending"           # Created, waiting for development
    DEVELOPING = "developing"     # Development phases running
    READY = "ready"               # Development complete, ready for deploy
    DEPLOYED = "deployed"         # Deployed to test system
    INTEGRATED = "integrated"     # Integrated into production
    FAILED = "failed"             # Validation or integration failed


@dataclass
class EvolutionProject:
    """
    Represents a single evolution project.

    An evolution project contains new code or modifications to HELIX itself.
    The project structure:

        projects/evolution/{name}/
        ├── spec.yaml           # Project specification
        ├── phases.yaml         # Development phases
        ├── status.json         # Current status and metadata
        ├── new/                # New files (mirrored structure)
        │   └── src/helix/...
        └── modified/           # Modified files (copies)
            └── src/helix/...

    Attributes:
        name: Unique name of the evolution project.
        session_id: ID of the consultant session that created this project.
        status: Current status of the project.
        path: Path to the project directory.
        created_at: When the project was created.
        updated_at: When the project was last updated.
        error: Error message if status is FAILED.
    """

    name: str
    session_id: str
    status: EvolutionStatus
    path: Path
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    error: str | None = None

    def get_new_files(self) -> list[Path]:
        """
        Get all new files in this evolution project.

        Returns:
            List of paths to new files (relative to new/ directory).
        """
        new_dir = self.path / "new"
        if not new_dir.exists():
            return []

        return [
            p.relative_to(new_dir)
            for p in new_dir.rglob("*")
            if p.is_file()
        ]

    def get_modified_files(self) -> list[Path]:
        """
        Get all modified files in this evolution project.

        Returns:
            List of paths to modified files (relative to modified/ directory).
        """
        modified_dir = self.path / "modified"
        if not modified_dir.exists():
            return []

        return [
            p.relative_to(modified_dir)
            for p in modified_dir.rglob("*")
            if p.is_file()
        ]

    def get_all_files(self) -> dict[str, list[Path]]:
        """
        Get all files (new and modified) in this project.

        Returns:
            Dictionary with 'new' and 'modified' keys containing file lists.
        """
        return {
            "new": self.get_new_files(),
            "modified": self.get_modified_files()
        }

    def update_status(self, status: EvolutionStatus, error: str | None = None) -> None:
        """
        Update the project status and persist to status.json.

        Args:
            status: The new status to set.
            error: Optional error message (for FAILED status).
        """
        self.status = status
        self.updated_at = datetime.now()
        self.error = error
        self._save_status()

    def _save_status(self) -> None:
        """Persist the current status to status.json."""
        status_file = self.path / "status.json"
        status_data = {
            "status": self.status.value,
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "error": self.error
        }
        status_file.write_text(
            json.dumps(status_data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def get_spec(self) -> dict[str, Any]:
        """
        Load and return the project specification.

        Returns:
            Dictionary containing the spec.yaml content.

        Raises:
            FileNotFoundError: If spec.yaml doesn't exist.
        """
        spec_file = self.path / "spec.yaml"
        if not spec_file.exists():
            raise FileNotFoundError(f"spec.yaml not found in {self.path}")

        with open(spec_file, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def get_phases(self) -> dict[str, Any]:
        """
        Load and return the project phases.

        Returns:
            Dictionary containing the phases.yaml content.

        Raises:
            FileNotFoundError: If phases.yaml doesn't exist.
        """
        phases_file = self.path / "phases.yaml"
        if not phases_file.exists():
            raise FileNotFoundError(f"phases.yaml not found in {self.path}")

        with open(phases_file, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert project to dictionary representation.

        Returns:
            Dictionary with all project information.
        """
        return {
            "name": self.name,
            "session_id": self.session_id,
            "status": self.status.value,
            "path": str(self.path),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "error": self.error,
            "files": {
                "new": [str(p) for p in self.get_new_files()],
                "modified": [str(p) for p in self.get_modified_files()]
            }
        }

    @classmethod
    def from_path(cls, project_path: Path) -> EvolutionProject:
        """
        Load an evolution project from its directory.

        Args:
            project_path: Path to the project directory.

        Returns:
            EvolutionProject instance loaded from the directory.

        Raises:
            FileNotFoundError: If status.json doesn't exist.
        """
        status_file = project_path / "status.json"
        if not status_file.exists():
            raise FileNotFoundError(f"status.json not found in {project_path}")

        with open(status_file, encoding="utf-8") as f:
            status_data = json.load(f)

        return cls(
            name=project_path.name,
            session_id=status_data.get("session_id", "unknown"),
            status=EvolutionStatus(status_data.get("status", "pending")),
            path=project_path,
            created_at=datetime.fromisoformat(status_data.get(
                "created_at", datetime.now().isoformat()
            )),
            updated_at=datetime.fromisoformat(status_data.get(
                "updated_at", datetime.now().isoformat()
            )),
            error=status_data.get("error")
        )


class EvolutionProjectManager:
    """
    Manages evolution projects for HELIX self-evolution.

    This manager handles creating, listing, and retrieving evolution projects.
    Projects are stored in the projects/evolution/ directory.

    Attributes:
        base_path: Base path for evolution projects (projects/evolution/).
        helix_root: Root path of the HELIX installation.
    """

    def __init__(self, helix_root: Path | None = None) -> None:
        """
        Initialize the evolution project manager.

        Args:
            helix_root: Root path of HELIX installation.
                       Defaults to /home/aiuser01/helix-v4.
        """
        if helix_root is None:
            helix_root = Path("/home/aiuser01/helix-v4")

        self.helix_root = helix_root
        self.base_path = helix_root / "projects" / "evolution"

        # Ensure base directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)

    def list_projects(self) -> list[EvolutionProject]:
        """
        List all evolution projects.

        Returns:
            List of EvolutionProject instances.
        """
        projects = []

        if not self.base_path.exists():
            return projects

        for project_dir in self.base_path.iterdir():
            if not project_dir.is_dir():
                continue

            status_file = project_dir / "status.json"
            if not status_file.exists():
                continue

            try:
                project = EvolutionProject.from_path(project_dir)
                projects.append(project)
            except (FileNotFoundError, json.JSONDecodeError, ValueError):
                # Skip invalid projects
                continue

        # Sort by creation date (newest first)
        projects.sort(key=lambda p: p.created_at, reverse=True)
        return projects

    def get_project(self, name: str) -> EvolutionProject | None:
        """
        Get a specific evolution project by name.

        Args:
            name: Name of the project.

        Returns:
            EvolutionProject if found, None otherwise.
        """
        project_path = self.base_path / name

        if not project_path.exists():
            return None

        try:
            return EvolutionProject.from_path(project_path)
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            return None

    def create_project(
        self,
        name: str,
        spec: dict[str, Any],
        phases: dict[str, Any],
        session_id: str = "manual"
    ) -> EvolutionProject:
        """
        Create a new evolution project.

        Args:
            name: Unique name for the project.
            spec: Project specification dictionary.
            phases: Project phases dictionary.
            session_id: ID of the consultant session (default: "manual").

        Returns:
            The created EvolutionProject instance.

        Raises:
            ValueError: If a project with this name already exists.
        """
        project_path = self.base_path / name

        if project_path.exists():
            raise ValueError(f"Project '{name}' already exists")

        # Create project directory structure
        project_path.mkdir(parents=True)
        (project_path / "new").mkdir()
        (project_path / "modified").mkdir()
        (project_path / "phases").mkdir()

        # Write spec.yaml
        spec_file = project_path / "spec.yaml"
        spec_file.write_text(
            yaml.dump(spec, allow_unicode=True, default_flow_style=False, sort_keys=False),
            encoding="utf-8"
        )

        # Write phases.yaml
        phases_file = project_path / "phases.yaml"
        phases_file.write_text(
            yaml.dump(phases, allow_unicode=True, default_flow_style=False, sort_keys=False),
            encoding="utf-8"
        )

        # Create project instance
        now = datetime.now()
        project = EvolutionProject(
            name=name,
            session_id=session_id,
            status=EvolutionStatus.PENDING,
            path=project_path,
            created_at=now,
            updated_at=now
        )

        # Save status
        project._save_status()

        return project

    def delete_project(self, name: str, force: bool = False) -> bool:
        """
        Delete an evolution project.

        Args:
            name: Name of the project to delete.
            force: If True, delete even if project is in active state.

        Returns:
            True if deleted, False if project not found.

        Raises:
            ValueError: If project is in active state and force=False.
        """
        project = self.get_project(name)

        if project is None:
            return False

        # Check if project can be deleted
        active_states = {
            EvolutionStatus.DEVELOPING,
            EvolutionStatus.DEPLOYED
        }

        if project.status in active_states and not force:
            raise ValueError(
                f"Cannot delete project '{name}' in {project.status.value} state. "
                "Use force=True to delete anyway."
            )

        # Delete the project directory
        shutil.rmtree(project.path)
        return True

    def get_projects_by_status(
        self, status: EvolutionStatus
    ) -> list[EvolutionProject]:
        """
        Get all projects with a specific status.

        Args:
            status: The status to filter by.

        Returns:
            List of projects with the specified status.
        """
        return [p for p in self.list_projects() if p.status == status]

    def get_ready_projects(self) -> list[EvolutionProject]:
        """
        Get all projects that are ready for deployment.

        Returns:
            List of projects with READY status.
        """
        return self.get_projects_by_status(EvolutionStatus.READY)

    def get_active_deployment(self) -> EvolutionProject | None:
        """
        Get the currently deployed project (if any).

        Only one project can be deployed at a time.

        Returns:
            The deployed project, or None if no project is deployed.
        """
        deployed = self.get_projects_by_status(EvolutionStatus.DEPLOYED)
        return deployed[0] if deployed else None

    def check_conflicts(
        self, project: EvolutionProject
    ) -> dict[str, list[str]]:
        """
        Check for file conflicts with other evolution projects.

        Args:
            project: The project to check for conflicts.

        Returns:
            Dictionary mapping conflicting project names to conflicting files.
        """
        conflicts: dict[str, list[str]] = {}

        project_files = set()
        for f in project.get_new_files():
            project_files.add(str(f))
        for f in project.get_modified_files():
            project_files.add(str(f))

        if not project_files:
            return conflicts

        # Check against other active projects
        for other in self.list_projects():
            if other.name == project.name:
                continue

            if other.status in {EvolutionStatus.INTEGRATED, EvolutionStatus.FAILED}:
                continue

            other_files = set()
            for f in other.get_new_files():
                other_files.add(str(f))
            for f in other.get_modified_files():
                other_files.add(str(f))

            common = project_files & other_files
            if common:
                conflicts[other.name] = list(common)

        return conflicts


def create_project_manager(helix_root: Path | None = None) -> EvolutionProjectManager:
    """
    Factory function to create an EvolutionProjectManager.

    Args:
        helix_root: Optional HELIX root path.

    Returns:
        Configured EvolutionProjectManager instance.
    """
    return EvolutionProjectManager(helix_root=helix_root)
