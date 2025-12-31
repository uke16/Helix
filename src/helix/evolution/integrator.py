"""Evolution Integrator.

Handles integration of validated evolution projects from test system
back into production.

Workflow:
1. pre_integration_backup() - Create backup/tag in production
2. integrate(project) - Copy validated files to production
3. post_integration_restart() - Restart production API
4. rollback() - Revert to backup on failure
"""

import asyncio
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from helix.config.paths import PathConfig
from .project import EvolutionProject, EvolutionStatus


@dataclass
class IntegrationResult:
    """Result of an integration operation."""
    success: bool
    message: str
    backup_tag: Optional[str] = None
    files_integrated: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class Integrator:
    """Integrates evolution projects into production."""

    PRODUCTION_ROOT = PathConfig.HELIX_ROOT
    TEST_ROOT = Path(os.environ.get("HELIX_TEST_ROOT", str(PathConfig.HELIX_ROOT) + "-test"))
    CONTROL_SCRIPT = "control/helix-control.sh"

    def __init__(
        self,
        production_root: Optional[Path] = None,
        test_root: Optional[Path] = None,
    ):
        """Initialize the integrator.

        Args:
            production_root: Path to production HELIX (default: PathConfig.HELIX_ROOT)
            test_root: Path to test HELIX (default: HELIX_ROOT-test or HELIX_TEST_ROOT env)
        """
        self.production_root = Path(production_root or self.PRODUCTION_ROOT)
        self.test_root = Path(test_root or self.TEST_ROOT)
        self._backup_tag: Optional[str] = None

    async def pre_integration_backup(
        self,
        tag_prefix: str = "pre-integrate",
    ) -> IntegrationResult:
        """Create a backup before integration.

        Creates a git tag so we can rollback if needed.

        Args:
            tag_prefix: Prefix for the backup tag

        Returns:
            IntegrationResult with backup tag
        """
        started_at = datetime.now()

        try:
            # Generate tag name with timestamp
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            tag_name = f"{tag_prefix}-{timestamp}"

            # Stash any uncommitted changes
            stash_process = await asyncio.create_subprocess_exec(
                "git", "stash", "push", "-m", f"Auto-stash before {tag_name}",
                cwd=self.production_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await stash_process.communicate()

            # Create tag
            tag_process = await asyncio.create_subprocess_exec(
                "git", "tag", "-a", tag_name, "-m", f"Backup before integration",
                cwd=self.production_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await tag_process.communicate()

            if tag_process.returncode != 0:
                return IntegrationResult(
                    success=False,
                    message="Failed to create backup tag",
                    error=stderr.decode() if stderr else None,
                    started_at=started_at,
                    completed_at=datetime.now(),
                )

            self._backup_tag = tag_name

            return IntegrationResult(
                success=True,
                message=f"Backup created: {tag_name}",
                backup_tag=tag_name,
                started_at=started_at,
                completed_at=datetime.now(),
            )

        except Exception as e:
            return IntegrationResult(
                success=False,
                message="Backup failed",
                error=str(e),
                started_at=started_at,
                completed_at=datetime.now(),
            )

    async def integrate(
        self,
        project: EvolutionProject,
    ) -> IntegrationResult:
        """Integrate an evolution project into production.

        Copies files from test system (where they were validated)
        to production.

        Args:
            project: The evolution project to integrate

        Returns:
            IntegrationResult with status
        """
        started_at = datetime.now()
        files_integrated = 0

        try:
            # Check project status - must be DEPLOYED (validated in test)
            status = project.get_status()
            if status not in [EvolutionStatus.DEPLOYED, EvolutionStatus.READY]:
                return IntegrationResult(
                    success=False,
                    message=f"Project not ready for integration (status: {status.value})",
                    started_at=started_at,
                    completed_at=datetime.now(),
                )

            # Copy new files
            new_files = project.list_new_files()
            for rel_path in new_files:
                src = project.get_new_file_path(rel_path)
                dst = self.production_root / rel_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                files_integrated += 1

            # Copy modified files
            modified_files = project.list_modified_files()
            for rel_path in modified_files:
                src = project.get_modified_file_path(rel_path)
                dst = self.production_root / rel_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                files_integrated += 1

            # Git add and commit
            add_process = await asyncio.create_subprocess_exec(
                "git", "add", "-A",
                cwd=self.production_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await add_process.communicate()

            commit_msg = f"Integration: {project.name}"
            commit_process = await asyncio.create_subprocess_exec(
                "git", "commit", "-m", commit_msg,
                cwd=self.production_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await commit_process.communicate()

            # Update project status
            project.set_status(EvolutionStatus.INTEGRATED)

            return IntegrationResult(
                success=True,
                message=f"Integrated {files_integrated} files",
                files_integrated=files_integrated,
                backup_tag=self._backup_tag,
                started_at=started_at,
                completed_at=datetime.now(),
            )

        except Exception as e:
            return IntegrationResult(
                success=False,
                message="Integration failed",
                error=str(e),
                files_integrated=files_integrated,
                started_at=started_at,
                completed_at=datetime.now(),
            )

    async def post_integration_restart(self) -> IntegrationResult:
        """Restart production API after integration.

        Returns:
            IntegrationResult with status
        """
        started_at = datetime.now()

        try:
            control_script = self.production_root / self.CONTROL_SCRIPT

            if not control_script.exists():
                return IntegrationResult(
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
                cwd=self.production_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                return IntegrationResult(
                    success=False,
                    message="Restart failed",
                    error=stderr.decode() if stderr else stdout.decode(),
                    started_at=started_at,
                    completed_at=datetime.now(),
                )

            # Wait for API to come up
            await asyncio.sleep(3)

            return IntegrationResult(
                success=True,
                message="Production restarted",
                started_at=started_at,
                completed_at=datetime.now(),
            )

        except Exception as e:
            return IntegrationResult(
                success=False,
                message="Restart failed",
                error=str(e),
                started_at=started_at,
                completed_at=datetime.now(),
            )

    async def rollback(self) -> IntegrationResult:
        """Rollback production to backup state.

        Uses the backup tag created during pre_integration_backup.

        Returns:
            IntegrationResult with status
        """
        started_at = datetime.now()

        try:
            if not self._backup_tag:
                # Try to find latest backup tag
                process = await asyncio.create_subprocess_exec(
                    "git", "tag", "-l", "pre-integrate-*", "--sort=-creatordate",
                    cwd=self.production_root,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await process.communicate()

                if stdout:
                    tags = stdout.decode().strip().split("\n")
                    if tags and tags[0]:
                        self._backup_tag = tags[0]

            if not self._backup_tag:
                return IntegrationResult(
                    success=False,
                    message="No backup tag found",
                    started_at=started_at,
                    completed_at=datetime.now(),
                )

            # Reset to backup tag
            reset_process = await asyncio.create_subprocess_exec(
                "git", "reset", "--hard", self._backup_tag,
                cwd=self.production_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await reset_process.communicate()

            if reset_process.returncode != 0:
                return IntegrationResult(
                    success=False,
                    message="Rollback failed",
                    error=stderr.decode() if stderr else None,
                    backup_tag=self._backup_tag,
                    started_at=started_at,
                    completed_at=datetime.now(),
                )

            # Restart production
            restart_result = await self.post_integration_restart()

            if not restart_result.success:
                return IntegrationResult(
                    success=False,
                    message="Rollback succeeded but restart failed",
                    error=restart_result.error,
                    backup_tag=self._backup_tag,
                    started_at=started_at,
                    completed_at=datetime.now(),
                )

            return IntegrationResult(
                success=True,
                message=f"Rolled back to {self._backup_tag}",
                backup_tag=self._backup_tag,
                started_at=started_at,
                completed_at=datetime.now(),
            )

        except Exception as e:
            return IntegrationResult(
                success=False,
                message="Rollback failed",
                error=str(e),
                started_at=started_at,
                completed_at=datetime.now(),
            )

    async def full_integration(
        self,
        project: EvolutionProject,
    ) -> IntegrationResult:
        """Perform full integration workflow.

        1. Create backup
        2. Integrate files
        3. Restart production
        4. Rollback on failure

        Args:
            project: The evolution project to integrate

        Returns:
            IntegrationResult with final status
        """
        started_at = datetime.now()

        # Step 1: Backup
        backup_result = await self.pre_integration_backup()
        if not backup_result.success:
            return backup_result

        # Step 2: Integrate
        integrate_result = await self.integrate(project)
        if not integrate_result.success:
            # Attempt rollback
            await self.rollback()
            return integrate_result

        # Step 3: Restart
        restart_result = await self.post_integration_restart()
        if not restart_result.success:
            # Attempt rollback
            await self.rollback()
            return restart_result

        return IntegrationResult(
            success=True,
            message=f"Full integration complete: {integrate_result.files_integrated} files",
            files_integrated=integrate_result.files_integrated,
            backup_tag=backup_result.backup_tag,
            started_at=started_at,
            completed_at=datetime.now(),
        )

    async def check_production_health(self) -> IntegrationResult:
        """Check if production API is healthy.

        Returns:
            IntegrationResult with success if healthy
        """
        import aiohttp

        started_at = datetime.now()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "http://localhost:8001/health",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as response:
                    if response.status == 200:
                        return IntegrationResult(
                            success=True,
                            message="Production is healthy",
                            started_at=started_at,
                            completed_at=datetime.now(),
                        )
                    else:
                        return IntegrationResult(
                            success=False,
                            message=f"Health check returned {response.status}",
                            started_at=started_at,
                            completed_at=datetime.now(),
                        )
        except Exception as e:
            return IntegrationResult(
                success=False,
                message="Health check failed",
                error=str(e),
                started_at=started_at,
                completed_at=datetime.now(),
            )
