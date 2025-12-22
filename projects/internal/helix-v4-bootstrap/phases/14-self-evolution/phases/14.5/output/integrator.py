"""
Integrator module for HELIX v4 Self-Evolution System.

This module handles the integration of evolution projects from the test environment
back into the production environment (helix-v4) after successful validation.

The integration workflow:
1. pre_integration_backup() - Create a git tag for rollback capability
2. integrate(project) - Copy validated files to production
3. post_integration_restart() - Restart the production API
4. rollback() - Revert to pre-integration state if needed
"""

from __future__ import annotations

import asyncio
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from helix.evolution.project import EvolutionProject


class IntegrationStatus(str, Enum):
    """Status of an integration operation."""

    PENDING = "pending"
    BACKING_UP = "backing_up"
    INTEGRATING = "integrating"
    RESTARTING = "restarting"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class IntegrationResult:
    """Result of an integration operation."""

    success: bool
    status: IntegrationStatus
    message: str
    backup_tag: str | None = None
    files_integrated: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "success": self.success,
            "status": self.status.value,
            "message": self.message,
            "backup_tag": self.backup_tag,
            "files_integrated": self.files_integrated,
            "errors": self.errors,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class Integrator:
    """
    Handles integration of validated evolution projects into production.

    The integrator manages the production system (helix-v4) and ensures that
    validated changes from evolution projects are safely integrated.

    Attributes:
        production_path: Path to the production HELIX installation.
        control_script: Path to the helix-control.sh script in production.
    """

    def __init__(
        self,
        production_path: Path | None = None,
    ) -> None:
        """
        Initialize the integrator.

        Args:
            production_path: Path to production HELIX. Defaults to /home/aiuser01/helix-v4.
        """
        self.production_path = production_path or Path("/home/aiuser01/helix-v4")
        self.control_script = self.production_path / "control" / "helix-control.sh"
        self._last_backup_tag: str | None = None

    def _check_production_exists(self) -> bool:
        """Check if the production directory exists."""
        return self.production_path.exists()

    def _check_is_git_repo(self) -> bool:
        """Check if production directory is a git repository."""
        return (self.production_path / ".git").exists()

    async def _run_command(
        self,
        command: list[str],
        cwd: Path | None = None,
        timeout: float = 120.0,
    ) -> tuple[int, str, str]:
        """
        Run a shell command asynchronously.

        Args:
            command: Command and arguments as list.
            cwd: Working directory for the command.
            timeout: Timeout in seconds.

        Returns:
            Tuple of (return_code, stdout, stderr).
        """
        process = None
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )

            return (
                process.returncode or 0,
                stdout.decode("utf-8", errors="replace"),
                stderr.decode("utf-8", errors="replace"),
            )

        except asyncio.TimeoutError:
            if process:
                process.kill()
                await process.wait()
            return (-1, "", f"Command timed out after {timeout} seconds")

        except Exception as e:
            return (-1, "", str(e))

    async def _get_current_commit(self) -> str | None:
        """Get the current git commit hash."""
        returncode, stdout, stderr = await self._run_command(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=self.production_path,
        )

        if returncode == 0:
            return stdout.strip()
        return None

    async def _has_uncommitted_changes(self) -> bool:
        """Check if there are uncommitted changes in the repository."""
        returncode, stdout, stderr = await self._run_command(
            ["git", "status", "--porcelain"],
            cwd=self.production_path,
        )

        if returncode == 0:
            # If output is not empty, there are uncommitted changes
            return bool(stdout.strip())
        return True  # Assume changes exist if we can't check

    async def pre_integration_backup(
        self,
        project_name: str | None = None,
    ) -> IntegrationResult:
        """
        Create a backup before integration.

        Creates a git tag that can be used to rollback if integration fails.
        Also stashes any uncommitted changes.

        Args:
            project_name: Optional project name to include in the tag.

        Returns:
            IntegrationResult with backup status.
        """
        result = IntegrationResult(
            success=False,
            status=IntegrationStatus.BACKING_UP,
            message="Starting pre-integration backup",
        )

        if not self._check_production_exists():
            result.status = IntegrationStatus.FAILED
            result.message = f"Production path not found at {self.production_path}"
            result.errors.append(result.message)
            result.completed_at = datetime.now()
            return result

        if not self._check_is_git_repo():
            result.status = IntegrationStatus.FAILED
            result.message = "Production is not a git repository"
            result.errors.append(result.message)
            result.completed_at = datetime.now()
            return result

        # Create backup tag name
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        tag_suffix = f"-{project_name}" if project_name else ""
        tag_name = f"pre-evolution{tag_suffix}-{timestamp}"

        # Check for uncommitted changes and stash them
        if await self._has_uncommitted_changes():
            returncode, stdout, stderr = await self._run_command(
                ["git", "stash", "push", "-m", f"Pre-evolution backup: {tag_name}"],
                cwd=self.production_path,
            )

            if returncode != 0:
                result.status = IntegrationStatus.FAILED
                result.message = f"Failed to stash changes: {stderr}"
                result.errors.append(stderr)
                result.completed_at = datetime.now()
                return result

        # Create the tag
        current_commit = await self._get_current_commit()
        returncode, stdout, stderr = await self._run_command(
            ["git", "tag", "-a", tag_name, "-m", f"Pre-evolution backup before integrating {project_name or 'unknown'}"],
            cwd=self.production_path,
        )

        if returncode != 0:
            result.status = IntegrationStatus.FAILED
            result.message = f"Failed to create backup tag: {stderr}"
            result.errors.append(stderr)
            result.completed_at = datetime.now()
            return result

        # Store the backup tag for potential rollback
        self._last_backup_tag = tag_name

        result.success = True
        result.status = IntegrationStatus.COMPLETED
        result.backup_tag = tag_name
        result.message = f"Backup created: {tag_name} (commit: {current_commit or 'unknown'})"
        result.completed_at = datetime.now()

        return result

    async def integrate(self, project: "EvolutionProject") -> IntegrationResult:
        """
        Integrate an evolution project into production.

        Copies all new and modified files from the project to the production system.

        Args:
            project: The EvolutionProject to integrate.

        Returns:
            IntegrationResult with integration status.
        """
        result = IntegrationResult(
            success=False,
            status=IntegrationStatus.INTEGRATING,
            message="Starting integration",
        )

        if not self._check_production_exists():
            result.status = IntegrationStatus.FAILED
            result.message = f"Production path not found at {self.production_path}"
            result.errors.append(result.message)
            result.completed_at = datetime.now()
            return result

        # Get files to integrate
        new_files = project.get_new_files()
        modified_files = project.get_modified_files()

        if not new_files and not modified_files:
            result.status = IntegrationStatus.FAILED
            result.message = "No files to integrate"
            result.errors.append("Project has no new or modified files")
            result.completed_at = datetime.now()
            return result

        # Copy new files
        new_dir = project.path / "new"
        for rel_path in new_files:
            src = new_dir / rel_path
            dst = self.production_path / rel_path

            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                result.files_integrated.append(f"new:{rel_path}")
            except Exception as e:
                result.errors.append(f"Failed to copy new file {rel_path}: {e}")

        # Copy modified files
        modified_dir = project.path / "modified"
        for rel_path in modified_files:
            src = modified_dir / rel_path
            dst = self.production_path / rel_path

            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                result.files_integrated.append(f"modified:{rel_path}")
            except Exception as e:
                result.errors.append(f"Failed to copy modified file {rel_path}: {e}")

        # Check if there were any errors
        if result.errors:
            result.status = IntegrationStatus.FAILED
            result.message = f"Integration completed with {len(result.errors)} errors"
            result.completed_at = datetime.now()
            return result

        result.success = True
        result.status = IntegrationStatus.COMPLETED
        result.message = f"Integrated {len(result.files_integrated)} files into production"
        result.completed_at = datetime.now()

        return result

    async def commit_integration(
        self,
        project_name: str,
        message: str | None = None,
    ) -> IntegrationResult:
        """
        Commit the integrated changes to git.

        Args:
            project_name: Name of the project being integrated.
            message: Optional custom commit message.

        Returns:
            IntegrationResult with commit status.
        """
        result = IntegrationResult(
            success=False,
            status=IntegrationStatus.INTEGRATING,
            message="Committing integration",
        )

        if not self._check_is_git_repo():
            result.status = IntegrationStatus.FAILED
            result.message = "Production is not a git repository"
            result.errors.append(result.message)
            result.completed_at = datetime.now()
            return result

        # Stage all changes
        returncode, stdout, stderr = await self._run_command(
            ["git", "add", "-A"],
            cwd=self.production_path,
        )

        if returncode != 0:
            result.status = IntegrationStatus.FAILED
            result.message = f"Failed to stage changes: {stderr}"
            result.errors.append(stderr)
            result.completed_at = datetime.now()
            return result

        # Create commit message
        commit_message = message or f"Evolution: Integrate {project_name}"

        # Commit
        returncode, stdout, stderr = await self._run_command(
            ["git", "commit", "-m", commit_message],
            cwd=self.production_path,
        )

        if returncode != 0:
            # Check if it's just "nothing to commit"
            if "nothing to commit" in stdout or "nothing to commit" in stderr:
                result.success = True
                result.status = IntegrationStatus.COMPLETED
                result.message = "No changes to commit"
                result.completed_at = datetime.now()
                return result

            result.status = IntegrationStatus.FAILED
            result.message = f"Failed to commit: {stderr}"
            result.errors.append(stderr)
            result.completed_at = datetime.now()
            return result

        result.success = True
        result.status = IntegrationStatus.COMPLETED
        result.message = f"Changes committed: {commit_message}"
        result.completed_at = datetime.now()

        return result

    async def post_integration_restart(self) -> IntegrationResult:
        """
        Restart the production API after integration.

        Uses helix-control.sh to restart the API.

        Returns:
            IntegrationResult with restart status.
        """
        result = IntegrationResult(
            success=False,
            status=IntegrationStatus.RESTARTING,
            message="Restarting production system",
        )

        if not self.control_script.exists():
            result.status = IntegrationStatus.FAILED
            result.message = f"Control script not found at {self.control_script}"
            result.errors.append(result.message)
            result.completed_at = datetime.now()
            return result

        # Make sure script is executable
        self.control_script.chmod(0o755)

        # Run restart command
        returncode, stdout, stderr = await self._run_command(
            [str(self.control_script), "restart"],
            cwd=self.production_path,
            timeout=60.0,
        )

        if returncode != 0:
            result.status = IntegrationStatus.FAILED
            result.message = f"Restart failed: {stderr or stdout}"
            result.errors.append(stderr or stdout)
            result.completed_at = datetime.now()
            return result

        # Wait for API to be ready
        await asyncio.sleep(3)

        # Health check
        returncode, stdout, stderr = await self._run_command(
            [str(self.control_script), "health"],
            cwd=self.production_path,
            timeout=30.0,
        )

        if returncode != 0:
            result.status = IntegrationStatus.FAILED
            result.message = "Health check failed after restart"
            result.errors.append(stderr or "Health check returned non-zero")
            result.completed_at = datetime.now()
            return result

        result.success = True
        result.status = IntegrationStatus.COMPLETED
        result.message = "Production system restarted successfully"
        result.completed_at = datetime.now()

        return result

    async def rollback(self, tag: str | None = None) -> IntegrationResult:
        """
        Rollback to a previous state.

        Reverts to the specified git tag or the last backup tag.

        Args:
            tag: Git tag to rollback to. If None, uses the last backup tag.

        Returns:
            IntegrationResult with rollback status.
        """
        result = IntegrationResult(
            success=False,
            status=IntegrationStatus.ROLLED_BACK,
            message="Starting rollback",
        )

        rollback_tag = tag or self._last_backup_tag

        if not rollback_tag:
            result.status = IntegrationStatus.FAILED
            result.message = "No rollback tag specified and no backup tag available"
            result.errors.append(result.message)
            result.completed_at = datetime.now()
            return result

        if not self._check_is_git_repo():
            result.status = IntegrationStatus.FAILED
            result.message = "Production is not a git repository"
            result.errors.append(result.message)
            result.completed_at = datetime.now()
            return result

        # Check if tag exists
        returncode, stdout, stderr = await self._run_command(
            ["git", "tag", "-l", rollback_tag],
            cwd=self.production_path,
        )

        if returncode != 0 or not stdout.strip():
            result.status = IntegrationStatus.FAILED
            result.message = f"Rollback tag not found: {rollback_tag}"
            result.errors.append(result.message)
            result.completed_at = datetime.now()
            return result

        # Reset to the tag
        returncode, stdout, stderr = await self._run_command(
            ["git", "reset", "--hard", rollback_tag],
            cwd=self.production_path,
        )

        if returncode != 0:
            result.status = IntegrationStatus.FAILED
            result.message = f"Git reset failed: {stderr}"
            result.errors.append(stderr)
            result.completed_at = datetime.now()
            return result

        # Clean untracked files
        returncode, stdout, stderr = await self._run_command(
            ["git", "clean", "-fd"],
            cwd=self.production_path,
        )

        if returncode != 0:
            result.errors.append(f"Git clean warning: {stderr}")

        # Restart production
        restart_result = await self.post_integration_restart()
        if not restart_result.success:
            result.status = IntegrationStatus.FAILED
            result.message = f"Rollback succeeded but restart failed: {restart_result.message}"
            result.errors.extend(restart_result.errors)
            result.completed_at = datetime.now()
            return result

        result.success = True
        result.backup_tag = rollback_tag
        result.message = f"Rolled back to {rollback_tag} successfully"
        result.completed_at = datetime.now()

        return result

    async def full_integration(
        self,
        project: "EvolutionProject",
        commit: bool = True,
        restart: bool = True,
    ) -> IntegrationResult:
        """
        Perform a full integration: backup, integrate, commit, and restart.

        This is a convenience method that runs all integration steps in sequence.

        Args:
            project: The EvolutionProject to integrate.
            commit: Whether to commit the changes (default: True).
            restart: Whether to restart production (default: True).

        Returns:
            IntegrationResult with final integration status.
        """
        # Step 1: Create backup
        backup_result = await self.pre_integration_backup(project.name)
        if not backup_result.success:
            return backup_result

        # Step 2: Integrate files
        integrate_result = await self.integrate(project)
        if not integrate_result.success:
            # Try to rollback on failure
            await self.rollback(backup_result.backup_tag)
            return integrate_result

        # Step 3: Commit changes
        if commit:
            commit_result = await self.commit_integration(project.name)
            if not commit_result.success:
                await self.rollback(backup_result.backup_tag)
                return commit_result

        # Step 4: Restart production
        if restart:
            restart_result = await self.post_integration_restart()
            if not restart_result.success:
                await self.rollback(backup_result.backup_tag)
                return restart_result

        # Return combined result
        final_result = IntegrationResult(
            success=True,
            status=IntegrationStatus.COMPLETED,
            message=f"Full integration completed: {integrate_result.message}",
            backup_tag=backup_result.backup_tag,
            files_integrated=integrate_result.files_integrated,
            started_at=backup_result.started_at,
            completed_at=datetime.now(),
        )

        return final_result

    async def get_integration_status(self) -> dict[str, Any]:
        """
        Get the current status of the production system.

        Returns:
            Dictionary with production system status information.
        """
        status: dict[str, Any] = {
            "exists": self._check_production_exists(),
            "path": str(self.production_path),
            "is_git_repo": self._check_is_git_repo(),
            "control_script_exists": self.control_script.exists(),
            "current_commit": None,
            "has_uncommitted_changes": None,
            "api_running": False,
            "last_backup_tag": self._last_backup_tag,
        }

        if not status["exists"]:
            return status

        # Get current commit
        status["current_commit"] = await self._get_current_commit()

        # Check for uncommitted changes
        status["has_uncommitted_changes"] = await self._has_uncommitted_changes()

        # Check API status
        if self.control_script.exists():
            returncode, stdout, stderr = await self._run_command(
                [str(self.control_script), "health"],
                cwd=self.production_path,
                timeout=10.0,
            )
            status["api_running"] = returncode == 0

        return status

    async def list_backup_tags(self) -> list[str]:
        """
        List all pre-evolution backup tags.

        Returns:
            List of backup tag names, newest first.
        """
        returncode, stdout, stderr = await self._run_command(
            ["git", "tag", "-l", "pre-evolution*", "--sort=-creatordate"],
            cwd=self.production_path,
        )

        if returncode != 0:
            return []

        tags = [tag.strip() for tag in stdout.strip().split("\n") if tag.strip()]
        return tags


def create_integrator(
    production_path: Path | None = None,
) -> Integrator:
    """
    Factory function to create an Integrator.

    Args:
        production_path: Optional production HELIX path.

    Returns:
        Configured Integrator instance.
    """
    return Integrator(production_path=production_path)
