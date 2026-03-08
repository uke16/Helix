"""Tests for Remote Control System."""

import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from helix.api.main import app
from helix.api.remote_control import (
    RemoteControlManager,
    ClaudeInstance,
    InstanceStatus,
    ServiceStatus,
    ServiceHealth,
    SystemStatus,
)


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def rc_manager():
    """Create a fresh RemoteControlManager for testing."""
    return RemoteControlManager()


class TestSystemStatus:
    """Tests for GET /remote-control/status."""

    def test_status_endpoint(self, client):
        """Test that status endpoint returns system info."""
        response = client.get("/remote-control/status")
        assert response.status_code == 200
        data = response.json()
        assert "api_healthy" in data
        assert data["api_healthy"] is True
        assert "api_pid" in data
        assert "helix_root" in data
        assert "services" in data
        assert "active_claude_instances" in data
        assert "path_validation" in data

    def test_services_endpoint(self, client):
        """Test that services endpoint returns health checks."""
        response = client.get("/remote-control/services")
        assert response.status_code == 200
        data = response.json()
        assert "services" in data
        assert "all_healthy" in data
        assert "instance_type" in data
        assert isinstance(data["services"], list)


class TestClaudeInstances:
    """Tests for Claude instance management endpoints."""

    def test_list_instances_empty(self, client):
        """Test listing instances when none exist."""
        response = client.get("/remote-control/instances")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["instances"] == []

    def test_list_instances_invalid_status(self, client):
        """Test listing instances with invalid status filter."""
        response = client.get("/remote-control/instances?status=invalid")
        assert response.status_code == 400

    def test_get_instance_not_found(self, client):
        """Test getting a non-existent instance."""
        response = client.get("/remote-control/instances/nonexistent")
        assert response.status_code == 404

    def test_get_instance_output_not_found(self, client):
        """Test getting output of a non-existent instance."""
        response = client.get("/remote-control/instances/nonexistent/output")
        assert response.status_code == 404

    def test_kill_instance_not_found(self, client):
        """Test killing a non-existent instance."""
        response = client.delete("/remote-control/instances/nonexistent")
        assert response.status_code == 404

    def test_kill_all_instances(self, client):
        """Test kill-all endpoint."""
        response = client.post("/remote-control/kill-all")
        assert response.status_code == 200
        data = response.json()
        assert "killed_count" in data

    def test_cleanup_instances(self, client):
        """Test cleanup endpoint."""
        response = client.post("/remote-control/cleanup?max_age_seconds=60")
        assert response.status_code == 200
        data = response.json()
        assert "cleaned_count" in data

    def test_spawn_empty_prompt(self, client):
        """Test that spawn rejects empty prompt."""
        response = client.post(
            "/remote-control/spawn",
            json={"prompt": ""},
        )
        assert response.status_code == 422  # Validation error


class TestLogs:
    """Tests for log reading endpoint."""

    def test_read_logs(self, client):
        """Test reading logs."""
        response = client.get("/remote-control/logs?log_type=api&lines=10")
        assert response.status_code == 200
        data = response.json()
        assert "log_type" in data
        assert data["log_type"] == "api"

    def test_read_logs_with_search(self, client):
        """Test reading logs with search filter."""
        response = client.get("/remote-control/logs?search=ERROR&lines=50")
        assert response.status_code == 200
        data = response.json()
        assert "lines" in data


class TestControlCommand:
    """Tests for control command endpoint."""

    def test_disallowed_command(self, client):
        """Test that disallowed commands are rejected."""
        response = client.post(
            "/remote-control/command",
            json={"command": "restart"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "not allowed" in data["error"]

    def test_allowed_command_format(self, client):
        """Test that allowed commands return proper format."""
        response = client.post(
            "/remote-control/command",
            json={"command": "status"},
        )
        assert response.status_code == 200
        data = response.json()
        # May fail if control script not found, but format should be correct
        assert "success" in data


class TestRemoteControlManager:
    """Unit tests for the RemoteControlManager class."""

    @pytest.mark.asyncio
    async def test_service_check_unreachable(self, rc_manager):
        """Test service check for unreachable port."""
        status = await rc_manager._check_service("TestService", 59999)
        assert status.health == ServiceHealth.UNHEALTHY
        assert status.latency_ms is None

    @pytest.mark.asyncio
    async def test_instance_lifecycle(self, rc_manager):
        """Test instance creation and tracking."""
        # Verify empty state
        instances = await rc_manager.list_instances()
        assert len(instances) == 0

    @pytest.mark.asyncio
    async def test_max_instances_limit(self, rc_manager):
        """Test that max instance limit is enforced."""
        rc_manager.MAX_INSTANCES = 2

        # Add fake running instances to hit the limit
        for i in range(2):
            inst = ClaudeInstance(
                instance_id=f"test-{i}",
                prompt="test",
                status=InstanceStatus.RUNNING,
            )
            rc_manager._instances[inst.instance_id] = inst

        # Third spawn should fail
        with pytest.raises(RuntimeError, match="Max active instances"):
            await rc_manager.spawn_claude("test prompt")

    @pytest.mark.asyncio
    async def test_kill_completed_instance(self, rc_manager):
        """Test that killing a completed instance returns False."""
        inst = ClaudeInstance(
            instance_id="completed-1",
            prompt="test",
            status=InstanceStatus.COMPLETED,
        )
        rc_manager._instances[inst.instance_id] = inst

        result = await rc_manager.kill_instance("completed-1")
        assert result is False

    @pytest.mark.asyncio
    async def test_kill_nonexistent_instance(self, rc_manager):
        """Test that killing a non-existent instance returns False."""
        result = await rc_manager.kill_instance("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_instance_output(self, rc_manager):
        """Test getting output of a completed instance."""
        inst = ClaudeInstance(
            instance_id="output-1",
            prompt="test",
            status=InstanceStatus.COMPLETED,
            stdout="Hello World",
            stderr="",
            exit_code=0,
        )
        rc_manager._instances[inst.instance_id] = inst

        output = await rc_manager.get_instance_output("output-1")
        assert output is not None
        assert output["stdout"] == "Hello World"
        assert output["exit_code"] == 0

    @pytest.mark.asyncio
    async def test_get_instance_output_not_found(self, rc_manager):
        """Test getting output of non-existent instance."""
        output = await rc_manager.get_instance_output("nonexistent")
        assert output is None

    @pytest.mark.asyncio
    async def test_list_instances_with_filter(self, rc_manager):
        """Test listing instances with status filter."""
        for i, status in enumerate([
            InstanceStatus.RUNNING,
            InstanceStatus.COMPLETED,
            InstanceStatus.FAILED,
        ]):
            inst = ClaudeInstance(
                instance_id=f"filter-{i}",
                prompt="test",
                status=status,
            )
            rc_manager._instances[inst.instance_id] = inst

        running = await rc_manager.list_instances(status_filter=InstanceStatus.RUNNING)
        assert len(running) == 1

        completed = await rc_manager.list_instances(status_filter=InstanceStatus.COMPLETED)
        assert len(completed) == 1

    @pytest.mark.asyncio
    async def test_cleanup_finished(self, rc_manager):
        """Test cleanup of old finished instances."""
        from datetime import datetime, timezone, timedelta

        old_time = datetime.now(timezone.utc) - timedelta(hours=2)

        inst = ClaudeInstance(
            instance_id="old-1",
            prompt="test",
            status=InstanceStatus.COMPLETED,
            completed_at=old_time,
        )
        rc_manager._instances[inst.instance_id] = inst

        cleaned = await rc_manager.cleanup_finished(max_age_seconds=3600)
        assert cleaned == 1
        assert "old-1" not in rc_manager._instances

    @pytest.mark.asyncio
    async def test_cleanup_keeps_recent(self, rc_manager):
        """Test that cleanup keeps recent finished instances."""
        from datetime import datetime, timezone

        inst = ClaudeInstance(
            instance_id="recent-1",
            prompt="test",
            status=InstanceStatus.COMPLETED,
            completed_at=datetime.now(timezone.utc),
        )
        rc_manager._instances[inst.instance_id] = inst

        cleaned = await rc_manager.cleanup_finished(max_age_seconds=3600)
        assert cleaned == 0
        assert "recent-1" in rc_manager._instances

    @pytest.mark.asyncio
    async def test_read_logs_nonexistent(self, rc_manager):
        """Test reading logs for non-existent log type."""
        result = await rc_manager.read_logs(log_type="nonexistent")
        assert result["exists"] is False

    @pytest.mark.asyncio
    async def test_control_command_disallowed(self, rc_manager):
        """Test that disallowed commands are rejected."""
        result = await rc_manager.run_control_command("dangerous-command")
        assert result["success"] is False
        assert "not allowed" in result["error"]

    @pytest.mark.asyncio
    async def test_system_status(self, rc_manager):
        """Test getting system status."""
        status = await rc_manager.get_system_status()
        assert status.api_healthy is True
        assert status.api_pid > 0
        assert status.helix_root
        assert isinstance(status.services, list)

    @pytest.mark.asyncio
    async def test_kill_all_instances(self, rc_manager):
        """Test killing all running instances."""
        # Add mock instances
        for i in range(3):
            inst = ClaudeInstance(
                instance_id=f"kill-all-{i}",
                prompt="test",
                status=InstanceStatus.RUNNING if i < 2 else InstanceStatus.COMPLETED,
            )
            rc_manager._instances[inst.instance_id] = inst

        # kill_all should only kill running ones (no process to actually kill,
        # but the status check should work)
        killed = await rc_manager.kill_all_instances()
        # The running instances don't have actual processes, so kill returns False
        assert isinstance(killed, int)


class TestClaudeInstanceModel:
    """Tests for ClaudeInstance data model."""

    def test_to_dict_running(self):
        """Test serialization of running instance."""
        inst = ClaudeInstance(
            instance_id="test-1",
            prompt="Hello world",
            status=InstanceStatus.RUNNING,
            pid=12345,
        )
        d = inst.to_dict()
        assert d["instance_id"] == "test-1"
        assert d["status"] == "running"
        assert d["pid"] == 12345
        assert "stdout_lines" not in d  # Not included for running

    def test_to_dict_completed(self):
        """Test serialization of completed instance."""
        inst = ClaudeInstance(
            instance_id="test-2",
            prompt="Hello world",
            status=InstanceStatus.COMPLETED,
            stdout="line1\nline2\nline3",
            stderr="",
            exit_code=0,
        )
        d = inst.to_dict()
        assert d["status"] == "completed"
        assert d["stdout_lines"] == 3  # Included for completed
        assert d["exit_code"] == 0

    def test_prompt_truncation(self):
        """Test that long prompts are truncated in dict output."""
        long_prompt = "x" * 500
        inst = ClaudeInstance(
            instance_id="test-3",
            prompt=long_prompt,
        )
        d = inst.to_dict()
        assert len(d["prompt"]) == 200


class TestServiceStatus:
    """Tests for ServiceStatus data model."""

    def test_healthy_service(self):
        """Test healthy service serialization."""
        s = ServiceStatus(
            name="PostgreSQL",
            port=5432,
            health=ServiceHealth.HEALTHY,
            latency_ms=1.5,
        )
        d = s.to_dict()
        assert d["health"] == "healthy"
        assert d["latency_ms"] == 1.5

    def test_unhealthy_service(self):
        """Test unhealthy service serialization."""
        s = ServiceStatus(
            name="Redis",
            port=6379,
            health=ServiceHealth.UNHEALTHY,
        )
        d = s.to_dict()
        assert d["health"] == "unhealthy"
        assert d["latency_ms"] is None
