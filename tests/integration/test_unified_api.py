"""Integration tests for Unified API (ADR-022).

Tests all endpoints:
- / (health)
- /v1/models (OpenAI-compatible models list)
- /helix/execute (project execution)
- /helix/jobs (job listing)

Note: Chat completion tests removed as they require real LLM calls.
"""

import pytest
import httpx
import os

API_BASE = os.getenv("HELIX_API_URL", "http://localhost:8001")


@pytest.fixture
def api_client():
    """Create HTTP client for API tests."""
    return httpx.Client(base_url=API_BASE, timeout=30.0)


@pytest.fixture
def async_api_client():
    """Create async HTTP client for API tests."""
    return httpx.AsyncClient(base_url=API_BASE, timeout=30.0)


class TestAPIHealth:
    """Tests for API health endpoint."""

    def test_health_endpoint(self, api_client):
        """GET / returns health status."""
        response = api_client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "running"
        assert "name" in data
        assert "version" in data
        assert "endpoints" in data

    def test_health_contains_endpoint_info(self, api_client):
        """Health response includes available endpoints."""
        response = api_client.get("/")
        data = response.json()

        endpoints = data["endpoints"]
        assert "openai" in endpoints
        assert "models" in endpoints
        assert "execute" in endpoints
        assert "jobs" in endpoints


class TestOpenAICompatibility:
    """Tests for OpenAI-compatible endpoints."""

    def test_models_endpoint(self, api_client):
        """GET /v1/models returns model list."""
        response = api_client.get("/v1/models")
        assert response.status_code == 200

        data = response.json()
        assert data["object"] == "list"
        assert "data" in data
        assert len(data["data"]) >= 1  # At least helix-consultant

    def test_models_contain_helix_consultant(self, api_client):
        """Models include helix-consultant."""
        response = api_client.get("/v1/models")
        data = response.json()

        model_ids = [m["id"] for m in data["data"]]
        assert "helix-consultant" in model_ids

    def test_models_have_required_fields(self, api_client):
        """Each model has required OpenAI fields."""
        response = api_client.get("/v1/models")
        data = response.json()

        for model in data["data"]:
            assert "id" in model
            assert "object" in model
            assert model["object"] == "model"
            assert "created" in model
            assert "owned_by" in model


class TestHelixExecute:
    """Tests for /helix/execute endpoint."""

    def test_execute_endpoint_exists(self, api_client):
        """POST /helix/execute is available."""
        response = api_client.post(
            "/helix/execute",
            json={"project": "nonexistent", "dry_run": True},
        )
        # 404 for nonexistent project is expected
        assert response.status_code in [200, 404]

    def test_execute_returns_job_id(self, api_client):
        """Execute returns job_id on success."""
        response = api_client.post(
            "/helix/execute",
            json={"project": "test-project", "dry_run": True},
        )
        if response.status_code == 200:
            data = response.json()
            assert "job_id" in data

    def test_execute_dry_run(self, api_client):
        """Dry run doesn't actually execute."""
        response = api_client.post(
            "/helix/execute",
            json={"project": "test-project", "dry_run": True},
        )
        if response.status_code == 200:
            data = response.json()
            assert data.get("dry_run") is True


class TestHelixJobs:
    """Tests for /helix/jobs endpoint."""

    def test_jobs_endpoint(self, api_client):
        """GET /helix/jobs returns job list."""
        response = api_client.get("/helix/jobs")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

    def test_jobs_list_format(self, api_client):
        """Jobs have expected fields."""
        response = api_client.get("/helix/jobs")
        data = response.json()

        # If there are jobs, check their format
        for job in data:
            assert "job_id" in job
            assert "status" in job
            assert "created_at" in job


class TestAsyncEndpoints:
    """Tests for async API access."""

    @pytest.mark.asyncio
    async def test_health_async(self, async_api_client):
        """Health endpoint works async."""
        async with async_api_client:
            response = await async_api_client.get("/")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_models_async(self, async_api_client):
        """Models endpoint works async."""
        async with async_api_client:
            response = await async_api_client.get("/v1/models")
            data = response.json()
            assert len(data["data"]) >= 1

    @pytest.mark.asyncio
    async def test_jobs_async(self, async_api_client):
        """Jobs endpoint works async."""
        async with async_api_client:
            response = await async_api_client.get("/helix/jobs")
            assert response.status_code == 200
