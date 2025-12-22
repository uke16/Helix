"""Evolution Deployer.

Handles deployment of evolution projects to the test system.
The test system is a separate HELIX instance at /home/aiuser01/helix-v4-test/
running on port 9001 with isolated databases.

Workflow:
1. pre_deploy_sync() - Git sync test system with production
2. deploy(project) - Copy new/ and modified/ files to test system
3. restart_test_system() - Restart test API
4. rollback() - Reset test system to clean state
"""

import asyncio
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from .project import EvolutionProject, EvolutionStatus


@dataclass
class DeployResult:
    """Result of a deploy operation."""
    success: bool
    message: str
    files_copied: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class Deployer:
    """Deploys evolution projects to the test system."""

    # Paths
    PRODUCTION_ROOT = Path("/home/aiuser01/helix-v4")
    TEST_ROOT = Path("/home/aiuser01/helix-v4-test")
    CONTROL_SCRIPT = "control/helix-control.sh"

    def __init__(
        self,
        production_root: Optional[Path] = None,
        test_root: Optional[Path] = None,
    ):
        """Initialize the deployer.

        Args:
            production_root: Path to production HELIX (default: /home/aiuser01/helix-v4)
            test_root: Path to test HELIX (default: /home/aiuser01/helix-v4-test)
        """
        self.production_root = Path(production_root or self.PRODUCTION_ROOT)
        self.test_root = Path(test_root or self.TEST_ROOT)

    async def pre_deploy_sync(self) -> DeployResult:
        """Sync test system with production via git.

        This ensures the test system starts from the same codebase
        as production before applying evolution changes.

        Returns:
            DeployResult with success status
        """
        started_at = datetime.now()

        try:
            # Check if test directory exists
            if not self.test_root.exists():
                return DeployResult(
                    success=False,
                    message="Test system directory does not exist",
                    error=f"Directory not found: {self.test_root}",
                    started_at=started_at,
                    completed_at=datetime.now(),
                )

            # Git fetch and reset
            commands = [
                ["git", "fetch", "origin"],
                ["git", "reset", "--hard", "origin/main"],
            ]

            for cmd in commands:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    cwd=self.test_root,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await process.communicate()

                if process.returncode != 0:
                    return DeployResult(
                        success=False,
                        message=f"Git command failed: {' '.join(cmd)}",
                        error=stderr.decode() if stderr else None,
                        started_at=started_at,
                        completed_at=datetime.now(),
                    )

            return DeployResult(
                success=True,
                message="Test system synced with production",
                started_at=started_at,
                completed_at=datetime.now(),
            )

        except Exception as e:
            return DeployResult(
                success=False,
                message="Pre-deploy sync failed",
                error=str(e),
                started_at=started_at,
                completed_at=datetime.now(),
            )

    async def deploy(self, project: EvolutionProject) -> DeployResult:
        """Deploy an evolution project to the test system.

        Copies files from project's new/ and modified/ directories
        to the test system.

        Args:
            project: The evolution project to deploy

        Returns:
            DeployResult with success status and file count
        """
        started_at = datetime.now()
        files_copied = 0

        try:
            # Check project status
            if project.get_status() not in [
                EvolutionStatus.READY,
                EvolutionStatus.DEVELOPING,
            ]:
                return DeployResult(
                    success=False,
                    message=f"Project not ready for deploy (status: {project.get_status().value})",
                    started_at=started_at,
                    completed_at=datetime.now(),
                )

            # Copy new files
            new_files = project.list_new_files()
            for rel_path in new_files:
                src = project.get_new_file_path(rel_path)
                dst = self.test_root / rel_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                files_copied += 1

            # Copy modified files
            modified_files = project.list_modified_files()
            for rel_path in modified_files:
                src = project.get_modified_file_path(rel_path)
                dst = self.test_root / rel_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                files_copied += 1

            # Update project status
            project.set_status(EvolutionStatus.DEPLOYED)

            return DeployResult(
                success=True,
                message=f"Deployed {files_copied} files to test system",
                files_copied=files_copied,
                started_at=started_at,
                completed_at=datetime.now(),
            )

        except Exception as e:
            return DeployResult(
                success=False,
                message="Deploy failed",
                error=str(e),
                files_copied=files_copied,
                started_at=started_at,
                completed_at=datetime.now(),
            )

    async def restart_test_system(self) -> DeployResult:
        """Restart the test system API.

        Uses the helix-control.sh script to restart.

        Returns:
            DeployResult with success status
        """
        started_at = datetime.now()

        try:
            control_script = self.test_root / self.CONTROL_SCRIPT

            if not control_script.exists():
                return DeployResult(
                    success=False,
                    message="Control script not found",
                    error=f"Script not found: {control_script}",
                    started_at=started_at,
                    completed_at=datetime.now(),
                )

            # Run restart command
            process = await asyncio.create_subprocess_exec(
                str(control_script),
                "restart",
                cwd=self.test_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                return DeployResult(
                    success=False,
                    message="Restart failed",
                    error=stderr.decode() if stderr else stdout.decode(),
                    started_at=started_at,
                    completed_at=datetime.now(),
                )

            # Wait for API to come up
            await asyncio.sleep(3)

            return DeployResult(
                success=True,
                message="Test system restarted",
                started_at=started_at,
                completed_at=datetime.now(),
            )

        except Exception as e:
            return DeployResult(
                success=False,
                message="Restart failed",
                error=str(e),
                started_at=started_at,
                completed_at=datetime.now(),
            )

    async def rollback(self) -> DeployResult:
        """Rollback test system to clean state.

        Resets test system to match production (git reset --hard).

        Returns:
            DeployResult with success status
        """
        started_at = datetime.now()

        try:
            # Git reset to clean state
            process = await asyncio.create_subprocess_exec(
                "git", "reset", "--hard", "origin/main",
                cwd=self.test_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                return DeployResult(
                    success=False,
                    message="Rollback failed",
                    error=stderr.decode() if stderr else None,
                    started_at=started_at,
                    completed_at=datetime.now(),
                )

            # Restart to apply clean state
            restart_result = await self.restart_test_system()

            if not restart_result.success:
                return DeployResult(
                    success=False,
                    message="Rollback succeeded but restart failed",
                    error=restart_result.error,
                    started_at=started_at,
                    completed_at=datetime.now(),
                )

            return DeployResult(
                success=True,
                message="Test system rolled back to clean state",
                started_at=started_at,
                completed_at=datetime.now(),
            )

        except Exception as e:
            return DeployResult(
                success=False,
                message="Rollback failed",
                error=str(e),
                started_at=started_at,
                completed_at=datetime.now(),
            )

    async def check_test_system_health(self) -> DeployResult:
        """Check if test system API is healthy.

        Returns:
            DeployResult with success if healthy
        """
        import aiohttp

        started_at = datetime.now()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "http://localhost:9001/health",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as response:
                    if response.status == 200:
                        return DeployResult(
                            success=True,
                            message="Test system is healthy",
                            started_at=started_at,
                            completed_at=datetime.now(),
                        )
                    else:
                        return DeployResult(
                            success=False,
                            message=f"Health check returned {response.status}",
                            started_at=started_at,
                            completed_at=datetime.now(),
                        )
        except Exception as e:
            return DeployResult(
                success=False,
                message="Health check failed",
                error=str(e),
                started_at=started_at,
                completed_at=datetime.now(),
            )

    async def full_deploy(self, project: EvolutionProject) -> DeployResult:
        """Perform a full deploy workflow.

        1. Pre-deploy sync
        2. Deploy project files
        3. Restart test system
        4. Health check

        Args:
            project: The evolution project to deploy

        Returns:
            DeployResult with final status
        """
        started_at = datetime.now()
        total_files = 0

        # Step 1: Pre-deploy sync
        sync_result = await self.pre_deploy_sync()
        if not sync_result.success:
            return sync_result

        # Step 2: Deploy files
        deploy_result = await self.deploy(project)
        if not deploy_result.success:
            return deploy_result
        total_files = deploy_result.files_copied

        # Step 3: Restart
        restart_result = await self.restart_test_system()
        if not restart_result.success:
            # Attempt rollback on failure
            await self.rollback()
            return restart_result

        # Step 4: Health check
        health_result = await self.check_test_system_health()
        if not health_result.success:
            # Attempt rollback on failure
            await self.rollback()
            return health_result

        return DeployResult(
            success=True,
            message=f"Full deploy complete: {total_files} files deployed",
            files_copied=total_files,
            started_at=started_at,
            completed_at=datetime.now(),
        )
