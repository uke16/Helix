"""
Deployer module for HELIX v4 Self-Evolution System.

This module handles deploying evolution projects from the development environment
(helix-v4) to the test environment (helix-v4-test) for validation before integration.

The deployment workflow:
1. pre_deploy_sync() - Sync test system with production (git fetch + reset)
2. deploy(project) - Copy new and modified files to test system
3. restart_test_system() - Restart the test API
4. rollback() - Reset test system to clean state
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from helix.evolution.project import EvolutionProject


class DeploymentStatus(str, Enum):
    """Status of a deployment operation."""

    PENDING = "pending"
    SYNCING = "syncing"
    DEPLOYING = "deploying"
    RESTARTING = "restarting"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class DeploymentResult:
    """Result of a deployment operation."""

    success: bool
    status: DeploymentStatus
    message: str
    files_copied: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "success": self.success,
            "status": self.status.value,
            "message": self.message,
            "files_copied": self.files_copied,
            "errors": self.errors,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class Deployer:
    """
    Handles deployment of evolution projects to the test system.

    The deployer manages the test system (helix-v4-test) and ensures that
    evolution projects can be safely tested before integration into production.

    Attributes:
        production_path: Path to the production HELIX installation.
        test_system_path: Path to the test HELIX installation.
        control_script: Path to the helix-control.sh script in test system.
    """

    def __init__(
        self,
        production_path: Path | None = None,
        test_system_path: Path | None = None,
    ) -> None:
        """
        Initialize the deployer.

        Args:
            production_path: Path to production HELIX. Defaults to /home/aiuser01/helix-v4.
            test_system_path: Path to test HELIX. Defaults to /home/aiuser01/helix-v4-test.
        """
        self.production_path = production_path or Path("/home/aiuser01/helix-v4")
        self.test_system_path = test_system_path or Path("/home/aiuser01/helix-v4-test")
        self.control_script = self.test_system_path / "control" / "helix-control.sh"

    def _check_test_system_exists(self) -> bool:
        """Check if the test system directory exists."""
        return self.test_system_path.exists()

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

    async def pre_deploy_sync(self) -> DeploymentResult:
        """
        Synchronize the test system with production.

        This ensures the test system has the same base as production
        before applying evolution changes.

        Steps:
        1. git fetch origin
        2. git reset --hard origin/main (or current branch)

        Returns:
            DeploymentResult with sync status.
        """
        result = DeploymentResult(
            success=False,
            status=DeploymentStatus.SYNCING,
            message="Starting pre-deploy sync",
        )

        if not self._check_test_system_exists():
            result.status = DeploymentStatus.FAILED
            result.message = f"Test system not found at {self.test_system_path}"
            result.errors.append(result.message)
            result.completed_at = datetime.now()
            return result

        # Check if test system is a git repository
        git_dir = self.test_system_path / ".git"
        if not git_dir.exists():
            result.status = DeploymentStatus.FAILED
            result.message = "Test system is not a git repository"
            result.errors.append(result.message)
            result.completed_at = datetime.now()
            return result

        # Git fetch
        returncode, stdout, stderr = await self._run_command(
            ["git", "fetch", "origin"],
            cwd=self.test_system_path,
        )

        if returncode != 0:
            result.status = DeploymentStatus.FAILED
            result.message = f"Git fetch failed: {stderr}"
            result.errors.append(stderr)
            result.completed_at = datetime.now()
            return result

        # Get current branch name from production
        returncode, stdout, stderr = await self._run_command(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=self.production_path,
        )

        branch = stdout.strip() if returncode == 0 else "main"

        # Git reset --hard
        returncode, stdout, stderr = await self._run_command(
            ["git", "reset", "--hard", f"origin/{branch}"],
            cwd=self.test_system_path,
        )

        if returncode != 0:
            result.status = DeploymentStatus.FAILED
            result.message = f"Git reset failed: {stderr}"
            result.errors.append(stderr)
            result.completed_at = datetime.now()
            return result

        # Clean untracked files
        returncode, stdout, stderr = await self._run_command(
            ["git", "clean", "-fd"],
            cwd=self.test_system_path,
        )

        result.success = True
        result.status = DeploymentStatus.COMPLETED
        result.message = f"Test system synced with origin/{branch}"
        result.completed_at = datetime.now()

        return result

    async def deploy(self, project: "EvolutionProject") -> DeploymentResult:
        """
        Deploy an evolution project to the test system.

        Copies all new and modified files from the project to the test system.

        Args:
            project: The EvolutionProject to deploy.

        Returns:
            DeploymentResult with deployment status.
        """
        result = DeploymentResult(
            success=False,
            status=DeploymentStatus.DEPLOYING,
            message="Starting deployment",
        )

        if not self._check_test_system_exists():
            result.status = DeploymentStatus.FAILED
            result.message = f"Test system not found at {self.test_system_path}"
            result.errors.append(result.message)
            result.completed_at = datetime.now()
            return result

        # Get files to deploy
        new_files = project.get_new_files()
        modified_files = project.get_modified_files()

        if not new_files and not modified_files:
            result.status = DeploymentStatus.FAILED
            result.message = "No files to deploy"
            result.errors.append("Project has no new or modified files")
            result.completed_at = datetime.now()
            return result

        # Copy new files
        new_dir = project.path / "new"
        for rel_path in new_files:
            src = new_dir / rel_path
            dst = self.test_system_path / rel_path

            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                result.files_copied.append(f"new:{rel_path}")
            except Exception as e:
                result.errors.append(f"Failed to copy {rel_path}: {e}")

        # Copy modified files
        modified_dir = project.path / "modified"
        for rel_path in modified_files:
            src = modified_dir / rel_path
            dst = self.test_system_path / rel_path

            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                result.files_copied.append(f"modified:{rel_path}")
            except Exception as e:
                result.errors.append(f"Failed to copy {rel_path}: {e}")

        # Check if there were any errors
        if result.errors:
            result.status = DeploymentStatus.FAILED
            result.message = f"Deployment completed with {len(result.errors)} errors"
            result.completed_at = datetime.now()
            return result

        result.success = True
        result.status = DeploymentStatus.COMPLETED
        result.message = f"Deployed {len(result.files_copied)} files to test system"
        result.completed_at = datetime.now()

        return result

    async def restart_test_system(self) -> DeploymentResult:
        """
        Restart the test system API.

        Uses helix-control.sh to restart the API after deployment.

        Returns:
            DeploymentResult with restart status.
        """
        result = DeploymentResult(
            success=False,
            status=DeploymentStatus.RESTARTING,
            message="Restarting test system",
        )

        if not self.control_script.exists():
            result.status = DeploymentStatus.FAILED
            result.message = f"Control script not found at {self.control_script}"
            result.errors.append(result.message)
            result.completed_at = datetime.now()
            return result

        # Make sure script is executable
        self.control_script.chmod(0o755)

        # Run restart command
        returncode, stdout, stderr = await self._run_command(
            [str(self.control_script), "restart"],
            cwd=self.test_system_path,
            timeout=60.0,
        )

        if returncode != 0:
            result.status = DeploymentStatus.FAILED
            result.message = f"Restart failed: {stderr}"
            result.errors.append(stderr)
            result.completed_at = datetime.now()
            return result

        # Wait for API to be ready
        await asyncio.sleep(3)

        # Health check
        returncode, stdout, stderr = await self._run_command(
            [str(self.control_script), "health"],
            cwd=self.test_system_path,
            timeout=30.0,
        )

        if returncode != 0:
            result.status = DeploymentStatus.FAILED
            result.message = "Health check failed after restart"
            result.errors.append(stderr or "Health check returned non-zero")
            result.completed_at = datetime.now()
            return result

        result.success = True
        result.status = DeploymentStatus.COMPLETED
        result.message = "Test system restarted successfully"
        result.completed_at = datetime.now()

        return result

    async def rollback(self) -> DeploymentResult:
        """
        Rollback the test system to a clean state.

        Performs git reset --hard to discard all changes.

        Returns:
            DeploymentResult with rollback status.
        """
        result = DeploymentResult(
            success=False,
            status=DeploymentStatus.SYNCING,
            message="Starting rollback",
        )

        if not self._check_test_system_exists():
            result.status = DeploymentStatus.FAILED
            result.message = f"Test system not found at {self.test_system_path}"
            result.errors.append(result.message)
            result.completed_at = datetime.now()
            return result

        # Git reset --hard
        returncode, stdout, stderr = await self._run_command(
            ["git", "reset", "--hard", "HEAD"],
            cwd=self.test_system_path,
        )

        if returncode != 0:
            result.status = DeploymentStatus.FAILED
            result.message = f"Git reset failed: {stderr}"
            result.errors.append(stderr)
            result.completed_at = datetime.now()
            return result

        # Clean untracked files
        returncode, stdout, stderr = await self._run_command(
            ["git", "clean", "-fd"],
            cwd=self.test_system_path,
        )

        if returncode != 0:
            result.status = DeploymentStatus.FAILED
            result.message = f"Git clean failed: {stderr}"
            result.errors.append(stderr)
            result.completed_at = datetime.now()
            return result

        # Restart the test system
        restart_result = await self.restart_test_system()
        if not restart_result.success:
            result.status = DeploymentStatus.FAILED
            result.message = f"Rollback succeeded but restart failed: {restart_result.message}"
            result.errors.extend(restart_result.errors)
            result.completed_at = datetime.now()
            return result

        result.success = True
        result.status = DeploymentStatus.ROLLED_BACK
        result.message = "Test system rolled back successfully"
        result.completed_at = datetime.now()

        return result

    async def get_test_system_status(self) -> dict:
        """
        Get the current status of the test system.

        Returns:
            Dictionary with test system status information.
        """
        status = {
            "exists": self._check_test_system_exists(),
            "path": str(self.test_system_path),
            "control_script_exists": self.control_script.exists(),
            "git_status": None,
            "api_running": False,
        }

        if not status["exists"]:
            return status

        # Get git status
        returncode, stdout, stderr = await self._run_command(
            ["git", "status", "--porcelain"],
            cwd=self.test_system_path,
        )

        if returncode == 0:
            modified_files = [line for line in stdout.strip().split("\n") if line]
            status["git_status"] = {
                "clean": len(modified_files) == 0,
                "modified_count": len(modified_files),
            }

        # Check API status
        if self.control_script.exists():
            returncode, stdout, stderr = await self._run_command(
                [str(self.control_script), "health"],
                cwd=self.test_system_path,
                timeout=10.0,
            )
            status["api_running"] = returncode == 0

        return status

    async def full_deploy(self, project: "EvolutionProject") -> DeploymentResult:
        """
        Perform a full deployment: sync, deploy, and restart.

        This is a convenience method that runs all deployment steps in sequence.

        Args:
            project: The EvolutionProject to deploy.

        Returns:
            DeploymentResult with final deployment status.
        """
        # Step 1: Pre-deploy sync
        sync_result = await self.pre_deploy_sync()
        if not sync_result.success:
            return sync_result

        # Step 2: Deploy files
        deploy_result = await self.deploy(project)
        if not deploy_result.success:
            # Try to rollback on failure
            await self.rollback()
            return deploy_result

        # Step 3: Restart test system
        restart_result = await self.restart_test_system()
        if not restart_result.success:
            # Try to rollback on failure
            await self.rollback()
            return restart_result

        # Return combined result
        final_result = DeploymentResult(
            success=True,
            status=DeploymentStatus.COMPLETED,
            message=f"Full deployment completed: {deploy_result.message}",
            files_copied=deploy_result.files_copied,
            started_at=sync_result.started_at,
            completed_at=datetime.now(),
        )

        return final_result


def create_deployer(
    production_path: Path | None = None,
    test_system_path: Path | None = None,
) -> Deployer:
    """
    Factory function to create a Deployer.

    Args:
        production_path: Optional production HELIX path.
        test_system_path: Optional test HELIX path.

    Returns:
        Configured Deployer instance.
    """
    return Deployer(
        production_path=production_path,
        test_system_path=test_system_path,
    )
