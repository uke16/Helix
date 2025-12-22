"""Evolution Project Manager.

Manages the lifecycle of HELIX self-evolution projects.
Projects are stored in projects/evolution/ with the structure:

    projects/evolution/{project_name}/
    ├── spec.yaml           # Project specification
    ├── phases.yaml         # Development phases
    ├── status.json         # Current status and metadata
    ├── new/                # New files (mirrored structure)
    │   └── src/helix/...
    └── modified/           # Modified files (copies)
        └── src/helix/...
"""

import json
import os
import shutil
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml


class EvolutionStatus(str, Enum):
    """Status of an evolution project."""
    PENDING = "pending"         # Waiting for development
    DEVELOPING = "developing"   # In development phases
    READY = "ready"             # Ready for deploy
    DEPLOYED = "deployed"       # Deployed to test system
    VALIDATING = "validating"   # Running validation
    INTEGRATED = "integrated"   # Successfully integrated
    FAILED = "failed"           # Validation failed


class EvolutionError(Exception):
    """Base exception for evolution errors."""
    pass


class EvolutionProject:
    """Represents a single evolution project."""

    def __init__(self, path: Path):
        """Initialize project from path.
        
        Args:
            path: Path to the project directory
        """
        self.path = Path(path)
        self.name = self.path.name
        self._status_file = self.path / "status.json"
        self._spec_file = self.path / "spec.yaml"
        self._phases_file = self.path / "phases.yaml"
        self._new_dir = self.path / "new"
        self._modified_dir = self.path / "modified"

    @classmethod
    def create(
        cls,
        base_path: Path,
        name: str,
        spec: dict,
        phases: Optional[dict] = None,
    ) -> "EvolutionProject":
        """Create a new evolution project.
        
        Args:
            base_path: Base path for evolution projects
            name: Project name (will be directory name)
            spec: Project specification dict
            phases: Optional phases definition
            
        Returns:
            New EvolutionProject instance
        """
        # Sanitize name
        safe_name = "".join(c for c in name if c.isalnum() or c in "-_").lower()
        if not safe_name:
            raise EvolutionError(f"Invalid project name: {name}")
        
        project_path = Path(base_path) / safe_name
        
        if project_path.exists():
            raise EvolutionError(f"Project already exists: {safe_name}")
        
        # Create directory structure
        project_path.mkdir(parents=True)
        (project_path / "new").mkdir()
        (project_path / "modified").mkdir()
        
        # Write spec.yaml
        with open(project_path / "spec.yaml", "w") as f:
            yaml.safe_dump(spec, f, default_flow_style=False, allow_unicode=True)
        
        # Write phases.yaml if provided
        if phases:
            with open(project_path / "phases.yaml", "w") as f:
                yaml.safe_dump(phases, f, default_flow_style=False, allow_unicode=True)
        
        # Write initial status
        status = {
            "status": EvolutionStatus.PENDING.value,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "current_phase": None,
            "error": None,
        }
        with open(project_path / "status.json", "w") as f:
            json.dump(status, f, indent=2)
        
        return cls(project_path)

    def get_status(self) -> EvolutionStatus:
        """Get current project status."""
        if not self._status_file.exists():
            return EvolutionStatus.PENDING
        
        with open(self._status_file) as f:
            data = json.load(f)
        
        return EvolutionStatus(data.get("status", "pending"))

    def set_status(
        self,
        status: EvolutionStatus,
        current_phase: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """Update project status.
        
        Args:
            status: New status
            current_phase: Optional current phase ID
            error: Optional error message (for failed status)
        """
        data = self.get_status_data()
        data["status"] = status.value
        data["updated_at"] = datetime.now().isoformat()
        
        if current_phase is not None:
            data["current_phase"] = current_phase
        
        if error is not None:
            data["error"] = error
        elif status != EvolutionStatus.FAILED:
            data["error"] = None
        
        with open(self._status_file, "w") as f:
            json.dump(data, f, indent=2)

    def get_status_data(self) -> dict:
        """Get full status data dict."""
        if not self._status_file.exists():
            return {
                "status": EvolutionStatus.PENDING.value,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "current_phase": None,
                "error": None,
            }
        
        with open(self._status_file) as f:
            return json.load(f)

    def get_spec(self) -> Optional[dict]:
        """Get project specification."""
        if not self._spec_file.exists():
            return None
        
        with open(self._spec_file) as f:
            return yaml.safe_load(f)

    def get_phases(self) -> Optional[dict]:
        """Get project phases definition."""
        if not self._phases_file.exists():
            return None
        
        with open(self._phases_file) as f:
            return yaml.safe_load(f)

    def list_new_files(self) -> list[Path]:
        """List all new files to be added.
        
        Returns:
            List of paths relative to new/ directory
        """
        if not self._new_dir.exists():
            return []
        
        return [
            p.relative_to(self._new_dir)
            for p in self._new_dir.rglob("*")
            if p.is_file()
        ]

    def list_modified_files(self) -> list[Path]:
        """List all modified files.
        
        Returns:
            List of paths relative to modified/ directory
        """
        if not self._modified_dir.exists():
            return []
        
        return [
            p.relative_to(self._modified_dir)
            for p in self._modified_dir.rglob("*")
            if p.is_file()
        ]

    def get_new_file_path(self, relative_path: Path) -> Path:
        """Get full path to a new file.
        
        Args:
            relative_path: Path relative to new/
            
        Returns:
            Full path to the file
        """
        return self._new_dir / relative_path

    def get_modified_file_path(self, relative_path: Path) -> Path:
        """Get full path to a modified file.
        
        Args:
            relative_path: Path relative to modified/
            
        Returns:
            Full path to the file
        """
        return self._modified_dir / relative_path

    def add_new_file(self, relative_path: Path, content: str) -> Path:
        """Add a new file to the project.
        
        Args:
            relative_path: Target path relative to new/
            content: File content
            
        Returns:
            Full path to the created file
        """
        full_path = self._new_dir / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
        return full_path

    def add_modified_file(self, relative_path: Path, content: str) -> Path:
        """Add a modified file to the project.
        
        Args:
            relative_path: Target path relative to modified/
            content: File content
            
        Returns:
            Full path to the created file
        """
        full_path = self._modified_dir / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
        return full_path

    def get_file_count(self) -> dict:
        """Get count of new and modified files."""
        return {
            "new": len(self.list_new_files()),
            "modified": len(self.list_modified_files()),
        }

    def to_dict(self) -> dict:
        """Convert project to dictionary for API responses."""
        status_data = self.get_status_data()
        file_count = self.get_file_count()
        
        return {
            "name": self.name,
            "path": str(self.path),
            "status": status_data["status"],
            "created_at": status_data.get("created_at"),
            "updated_at": status_data.get("updated_at"),
            "current_phase": status_data.get("current_phase"),
            "error": status_data.get("error"),
            "files": file_count,
        }

    def delete(self) -> None:
        """Delete the project directory."""
        if self.path.exists():
            shutil.rmtree(self.path)


class EvolutionProjectManager:
    """Manager for evolution projects."""

    def __init__(self, helix_root: Optional[Path] = None):
        """Initialize project manager.
        
        Args:
            helix_root: Root path of HELIX (default: auto-detect)
        """
        if helix_root is None:
            # Auto-detect from environment or default
            helix_root = Path(
                os.environ.get("HELIX_ROOT", "/home/aiuser01/helix-v4")
            )
        
        self.helix_root = Path(helix_root)
        self.evolution_path = self.helix_root / "projects" / "evolution"
        
        # Ensure evolution directory exists
        self.evolution_path.mkdir(parents=True, exist_ok=True)

    def list_projects(self) -> list[EvolutionProject]:
        """List all evolution projects.
        
        Returns:
            List of EvolutionProject instances
        """
        projects = []
        
        if not self.evolution_path.exists():
            return projects
        
        for item in self.evolution_path.iterdir():
            if item.is_dir() and (item / "status.json").exists():
                projects.append(EvolutionProject(item))
        
        # Sort by updated_at descending
        projects.sort(
            key=lambda p: p.get_status_data().get("updated_at", ""),
            reverse=True,
        )
        
        return projects

    def get_project(self, name: str) -> Optional[EvolutionProject]:
        """Get a project by name.
        
        Args:
            name: Project name
            
        Returns:
            EvolutionProject or None if not found
        """
        project_path = self.evolution_path / name
        
        if not project_path.exists():
            return None
        
        if not (project_path / "status.json").exists():
            return None
        
        return EvolutionProject(project_path)

    def create_project(
        self,
        name: str,
        spec: dict,
        phases: Optional[dict] = None,
    ) -> EvolutionProject:
        """Create a new evolution project.
        
        Args:
            name: Project name
            spec: Project specification
            phases: Optional phases definition
            
        Returns:
            New EvolutionProject
        """
        return EvolutionProject.create(
            base_path=self.evolution_path,
            name=name,
            spec=spec,
            phases=phases,
        )

    def delete_project(self, name: str) -> bool:
        """Delete a project.
        
        Args:
            name: Project name
            
        Returns:
            True if deleted, False if not found
        """
        project = self.get_project(name)
        if project is None:
            return False
        
        project.delete()
        return True

    def get_projects_by_status(
        self,
        status: EvolutionStatus,
    ) -> list[EvolutionProject]:
        """Get projects with a specific status.
        
        Args:
            status: Status to filter by
            
        Returns:
            List of matching projects
        """
        return [
            p for p in self.list_projects()
            if p.get_status() == status
        ]

    def get_ready_projects(self) -> list[EvolutionProject]:
        """Get projects ready for deployment."""
        return self.get_projects_by_status(EvolutionStatus.READY)

    def get_deployed_project(self) -> Optional[EvolutionProject]:
        """Get the currently deployed project (if any).
        
        Only one project can be deployed at a time.
        """
        deployed = self.get_projects_by_status(EvolutionStatus.DEPLOYED)
        return deployed[0] if deployed else None
