"""Remote Control System for HELIX v4.

Provides programmatic control over HELIX infrastructure, Claude instances,
and system operations via a centralized manager. This module is the backend
for the /remote-control API routes.

Capabilities:
- System status: Health checks, service port scanning, process info
- Claude instance management: Spawn, track, and stop Claude processes
- Log access: Read and tail API/system logs
- Infrastructure checks: Docker service health, path validation

Usage:
    from helix.api.remote_control import RemoteControlManager

    rc = RemoteControlManager()
    status = await rc.get_system_status()
    instance = await rc.spawn_claude("Analyze this codebase")
"""

import asyncio
import logging
import os
import signal
import socket
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from helix.config.paths import PathConfig

logger = logging.getLogger(__name__)


class InstanceStatus(str, Enum):
    """Status of a managed Claude instance."""
    STARTING = "starting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    KILLED = "killed"


class ServiceHealth(str, Enum):
    """Health status of an infrastructure service."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ServiceStatus:
    """Status of a single infrastructure service."""
    name: str
    port: int
    health: ServiceHealth
    latency_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "port": self.port,
            "health": self.health.value,
            "latency_ms": self.latency_ms,
        }


@dataclass
class ClaudeInstance:
    """A managed Claude CLI subprocess."""
    instance_id: str
    prompt: str
    status: InstanceStatus = InstanceStatus.STARTING
    pid: int | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    working_dir: str | None = None
    mode: str = "print"  # print, interactive
    _process: asyncio.subprocess.Process | None = field(default=None, repr=False)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "instance_id": self.instance_id,
            "prompt": self.prompt[:200],
            "status": self.status.value,
            "pid": self.pid,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "exit_code": self.exit_code,
            "working_dir": self.working_dir,
            "mode": self.mode,
        }
        # Include output only for completed instances
        if self.status in (InstanceStatus.COMPLETED, InstanceStatus.FAILED):
            result["stdout_lines"] = len(self.stdout.split("\n")) if self.stdout else 0
            result["stderr_lines"] = len(self.stderr.split("\n")) if self.stderr else 0
        return result


@dataclass
class SystemStatus:
    """Overall system status snapshot."""
    api_healthy: bool
    api_pid: int
    api_uptime_seconds: float
    helix_root: str
    instance_type: str  # production or test
    api_port: int
    services: list[ServiceStatus]
    active_claude_instances: int
    path_validation: dict[str, bool]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "api_healthy": self.api_healthy,
            "api_pid": self.api_pid,
            "api_uptime_seconds": round(self.api_uptime_seconds, 1),
            "helix_root": self.helix_root,
            "instance_type": self.instance_type,
            "api_port": self.api_port,
            "services": [s.to_dict() for s in self.services],
            "active_claude_instances": self.active_claude_instances,
            "path_validation": self.path_validation,
            "timestamp": self.timestamp.isoformat(),
        }


# Infrastructure service definitions by instance type
SERVICES = {
    "production": [
        ("PostgreSQL", 5432),
        ("Neo4j HTTP", 7474),
        ("Neo4j Bolt", 7687),
        ("Qdrant", 6333),
        ("Redis", 6379),
    ],
    "test": [
        ("PostgreSQL", 5433),
        ("Neo4j HTTP", 7475),
        ("Neo4j Bolt", 7688),
        ("Qdrant", 6335),
        ("Redis", 6380),
    ],
}


class RemoteControlManager:
    """Central manager for remote control operations.

    Manages Claude instances, checks infrastructure health,
    and provides system status information.

    Thread-safe via asyncio.Lock for instance management.
    """

    # Max instances to prevent runaway spawning
    MAX_INSTANCES = 10
    # Default timeout for spawned Claude instances
    DEFAULT_TIMEOUT = 600  # 10 minutes

    def __init__(self) -> None:
        self._instances: dict[str, ClaudeInstance] = {}
        self._lock = asyncio.Lock()
        self._start_time = time.monotonic()
        self._api_port = int(os.environ.get("PORT", 8001))

    @property
    def instance_type(self) -> str:
        """Detect if this is production or test instance."""
        if "helix-v4-test" in str(PathConfig.HELIX_ROOT):
            return "test"
        return "production"

    # ── System Status ──────────────────────────────────────────────

    async def get_system_status(self) -> SystemStatus:
        """Get comprehensive system status."""
        services = await self._check_all_services()
        active = sum(
            1 for inst in self._instances.values()
            if inst.status in (InstanceStatus.STARTING, InstanceStatus.RUNNING)
        )

        return SystemStatus(
            api_healthy=True,
            api_pid=os.getpid(),
            api_uptime_seconds=time.monotonic() - self._start_time,
            helix_root=str(PathConfig.HELIX_ROOT),
            instance_type=self.instance_type,
            api_port=self._api_port,
            services=services,
            active_claude_instances=active,
            path_validation=PathConfig.validate(),
        )

    async def _check_all_services(self) -> list[ServiceStatus]:
        """Check health of all infrastructure services."""
        service_defs = SERVICES.get(self.instance_type, SERVICES["production"])
        tasks = [self._check_service(name, port) for name, port in service_defs]
        return await asyncio.gather(*tasks)

    async def _check_service(self, name: str, port: int) -> ServiceStatus:
        """Check if a single service is reachable via TCP."""
        start = time.monotonic()
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection("localhost", port),
                timeout=2.0,
            )
            latency = (time.monotonic() - start) * 1000
            writer.close()
            await writer.wait_closed()
            return ServiceStatus(
                name=name, port=port,
                health=ServiceHealth.HEALTHY,
                latency_ms=round(latency, 1),
            )
        except (ConnectionRefusedError, asyncio.TimeoutError, OSError):
            return ServiceStatus(
                name=name, port=port,
                health=ServiceHealth.UNHEALTHY,
            )

    # ── Claude Instance Management ─────────────────────────────────

    async def spawn_claude(
        self,
        prompt: str,
        working_dir: str | None = None,
        timeout: int | None = None,
        system_prompt: str | None = None,
        output_format: str = "text",
    ) -> ClaudeInstance:
        """Spawn a new Claude CLI instance.

        Args:
            prompt: The prompt to send to Claude.
            working_dir: Working directory for the instance.
            timeout: Timeout in seconds (default 600).
            system_prompt: Optional system prompt override.
            output_format: Output format (text, json, stream-json).

        Returns:
            ClaudeInstance with tracking information.

        Raises:
            RuntimeError: If max instance limit reached.
        """
        async with self._lock:
            active = sum(
                1 for inst in self._instances.values()
                if inst.status in (InstanceStatus.STARTING, InstanceStatus.RUNNING)
            )
            if active >= self.MAX_INSTANCES:
                raise RuntimeError(
                    f"Max active instances ({self.MAX_INSTANCES}) reached. "
                    "Stop existing instances before spawning new ones."
                )

        instance_id = str(uuid.uuid4())[:12]
        cwd = working_dir or str(PathConfig.HELIX_ROOT)

        instance = ClaudeInstance(
            instance_id=instance_id,
            prompt=prompt,
            working_dir=cwd,
        )

        async with self._lock:
            self._instances[instance_id] = instance

        # Start the Claude process in background
        asyncio.create_task(
            self._run_claude_instance(
                instance,
                timeout=timeout or self.DEFAULT_TIMEOUT,
                system_prompt=system_prompt,
                output_format=output_format,
            )
        )

        logger.info(f"Spawned Claude instance {instance_id}: {prompt[:80]}")
        return instance

    async def _run_claude_instance(
        self,
        instance: ClaudeInstance,
        timeout: int,
        system_prompt: str | None,
        output_format: str,
    ) -> None:
        """Run a Claude CLI process and track its lifecycle."""
        PathConfig.ensure_claude_path()

        cmd = ["claude", "--print", "--dangerously-skip-permissions"]

        if system_prompt:
            cmd.extend(["--system-prompt", system_prompt])

        cmd.extend(["--output-format", output_format])

        env = {**os.environ, **PathConfig.get_env_dict()}

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=instance.working_dir,
                env=env,
            )

            instance._process = process
            instance.pid = process.pid
            instance.status = InstanceStatus.RUNNING

            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(input=instance.prompt.encode("utf-8")),
                timeout=timeout,
            )

            instance.stdout = stdout_bytes.decode("utf-8", errors="replace")
            instance.stderr = stderr_bytes.decode("utf-8", errors="replace")
            instance.exit_code = process.returncode or 0
            instance.status = (
                InstanceStatus.COMPLETED if instance.exit_code == 0
                else InstanceStatus.FAILED
            )

        except asyncio.TimeoutError:
            if instance._process and instance._process.returncode is None:
                instance._process.kill()
                await instance._process.wait()
            instance.status = InstanceStatus.FAILED
            instance.stderr = f"Timeout after {timeout} seconds"
            instance.exit_code = -1

        except Exception as e:
            instance.status = InstanceStatus.FAILED
            instance.stderr = str(e)
            instance.exit_code = -1
            logger.error(f"Claude instance {instance.instance_id} failed: {e}")

        finally:
            instance.completed_at = datetime.now(timezone.utc)
            instance._process = None
            logger.info(
                f"Claude instance {instance.instance_id} "
                f"finished: status={instance.status.value}"
            )

    async def get_instance(self, instance_id: str) -> ClaudeInstance | None:
        """Get a Claude instance by ID."""
        return self._instances.get(instance_id)

    async def get_instance_output(self, instance_id: str) -> dict[str, Any] | None:
        """Get full output of a Claude instance."""
        instance = self._instances.get(instance_id)
        if not instance:
            return None
        return {
            "instance_id": instance.instance_id,
            "status": instance.status.value,
            "stdout": instance.stdout,
            "stderr": instance.stderr,
            "exit_code": instance.exit_code,
        }

    async def list_instances(
        self,
        status_filter: InstanceStatus | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List Claude instances, optionally filtered by status."""
        instances = sorted(
            self._instances.values(),
            key=lambda i: i.started_at,
            reverse=True,
        )
        if status_filter:
            instances = [i for i in instances if i.status == status_filter]
        return [i.to_dict() for i in instances[:limit]]

    async def kill_instance(self, instance_id: str) -> bool:
        """Kill a running Claude instance.

        Returns True if the instance was killed, False if not found or already stopped.
        """
        instance = self._instances.get(instance_id)
        if not instance:
            return False

        if instance.status not in (InstanceStatus.STARTING, InstanceStatus.RUNNING):
            return False

        if instance._process and instance._process.returncode is None:
            try:
                instance._process.kill()
                await instance._process.wait()
            except ProcessLookupError:
                pass

        instance.status = InstanceStatus.KILLED
        instance.completed_at = datetime.now(timezone.utc)
        instance.exit_code = -9
        logger.info(f"Killed Claude instance {instance_id}")
        return True

    async def kill_all_instances(self) -> int:
        """Kill all running Claude instances. Returns count of killed instances."""
        killed = 0
        for instance_id, instance in self._instances.items():
            if instance.status in (InstanceStatus.STARTING, InstanceStatus.RUNNING):
                if await self.kill_instance(instance_id):
                    killed += 1
        return killed

    async def cleanup_finished(self, max_age_seconds: int = 3600) -> int:
        """Remove finished instances older than max_age_seconds.

        Returns count of cleaned up instances.
        """
        cutoff = datetime.now(timezone.utc)
        to_remove = []

        for instance_id, instance in self._instances.items():
            if instance.status in (
                InstanceStatus.COMPLETED,
                InstanceStatus.FAILED,
                InstanceStatus.KILLED,
            ):
                if instance.completed_at:
                    age = (cutoff - instance.completed_at).total_seconds()
                    if age > max_age_seconds:
                        to_remove.append(instance_id)

        async with self._lock:
            for instance_id in to_remove:
                del self._instances[instance_id]

        return len(to_remove)

    # ── Log Access ─────────────────────────────────────────────────

    async def read_logs(
        self,
        log_type: str = "api",
        lines: int = 100,
        search: str | None = None,
    ) -> dict[str, Any]:
        """Read log files.

        Args:
            log_type: Which log to read (api, helix).
            lines: Number of lines to return from the end.
            search: Optional search string to filter lines.

        Returns:
            Dict with log content and metadata.
        """
        log_dir = PathConfig.HELIX_ROOT / "logs"

        log_files = {
            "api": log_dir / "api.log",
            "helix": log_dir / "helix-v4.log",
            "helix-test": log_dir / "helix-v4-test.log",
        }

        log_file = log_files.get(log_type)
        if not log_file or not log_file.exists():
            return {
                "log_type": log_type,
                "exists": False,
                "lines": [],
                "total_lines": 0,
            }

        try:
            content = await asyncio.to_thread(log_file.read_text, encoding="utf-8")
            all_lines = content.strip().split("\n") if content.strip() else []

            if search:
                all_lines = [line for line in all_lines if search in line]

            result_lines = all_lines[-lines:]

            return {
                "log_type": log_type,
                "exists": True,
                "file": str(log_file),
                "lines": result_lines,
                "total_lines": len(all_lines),
                "returned_lines": len(result_lines),
            }
        except Exception as e:
            return {
                "log_type": log_type,
                "exists": True,
                "error": str(e),
                "lines": [],
                "total_lines": 0,
            }

    # ── Command Execution ──────────────────────────────────────────

    async def run_control_command(self, command: str) -> dict[str, Any]:
        """Run a HELIX control command.

        Only allows a whitelist of safe commands to prevent arbitrary execution.

        Args:
            command: The control command to run (e.g., "status", "health").

        Returns:
            Dict with command output.
        """
        allowed_commands = {
            "status", "health", "logs",
        }

        if command not in allowed_commands:
            return {
                "success": False,
                "error": f"Command '{command}' not allowed. Allowed: {sorted(allowed_commands)}",
            }

        control_script = PathConfig.CONTROL_PATH / "helix-control.sh"
        if not control_script.exists():
            return {
                "success": False,
                "error": f"Control script not found: {control_script}",
            }

        try:
            process = await asyncio.create_subprocess_exec(
                "bash", str(control_script), command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(PathConfig.HELIX_ROOT),
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=30.0,
            )

            return {
                "success": process.returncode == 0,
                "command": command,
                "stdout": stdout_bytes.decode("utf-8", errors="replace"),
                "stderr": stderr_bytes.decode("utf-8", errors="replace"),
                "exit_code": process.returncode,
            }
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": f"Command '{command}' timed out after 30 seconds",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }


# Global singleton instance
remote_control = RemoteControlManager()
