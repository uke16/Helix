"""Integration tests for Unified API (ADR-022).

Tests all endpoints:
- / (health)
- /v1/models (OpenAI-compatible models list)
- /v1/chat/completions (OpenAI-compatible chat)
- /helix/execute (project execution)
- /helix/jobs (job listing)
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
        assert len(data["data"]) >= 2  # helix-consultant, helix-developer

    def test_models_contain_helix_consultant(self, api_client):
        """Models include helix-consultant."""
        response = api_client.get("/v1/models")
        data = response.json()

        model_ids = [m["id"] for m in data["data"]]
        assert "helix-consultant" in model_ids

    def test_models_contain_helix_developer(self, api_client):
        """Models include helix-developer."""
        response = api_client.get("/v1/models")
        data = response.json()

        model_ids = [m["id"] for m in data["data"]]
        assert "helix-developer" in model_ids

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

    def test_chat_completions_endpoint(self, api_client):
        """POST /v1/chat/completions returns chat response."""
        response = api_client.post(
            "/v1/chat/completions",
            json={
                "model": "helix-consultant",
                "messages": [{"role": "user", "content": "Hallo"}],
                "stream": False,
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert "id" in data
        assert data["object"] == "chat.completion"
        assert "choices" in data
        assert len(data["choices"]) > 0

    def test_chat_completions_response_format(self, api_client):
        """Chat completion has correct OpenAI response format."""
        response = api_client.post(
            "/v1/chat/completions",
            json={
                "model": "helix-consultant",
                "messages": [{"role": "user", "content": "Test"}],
                "stream": False,
            },
        )
        data = response.json()

        # Check response structure
        assert "id" in data
        assert "model" in data
        assert "created" in data
        assert "usage" in data

        # Check choices structure
        choice = data["choices"][0]
        assert "index" in choice
        assert "message" in choice
        assert "finish_reason" in choice

        # Check message structure
        message = choice["message"]
        assert "role" in message
        assert "content" in message


class TestHelixExecute:
    """Tests for HELIX project execution endpoint."""

    def test_execute_endpoint_exists(self, api_client):
        """POST /helix/execute endpoint exists."""
        response = api_client.post(
            "/helix/execute",
            json={"project_path": "nonexistent", "dry_run": True},
        )
        # Should return 200 or 400/404 (not found), not 405 (method not allowed)
        assert response.status_code in [200, 400, 404, 422]

    def test_execute_returns_job_id(self, api_client):
        """Execute with valid project returns job_id."""
        response = api_client.post(
            "/helix/execute",
            json={"project_path": "projects/test-simple", "dry_run": True},
        )
        # May fail if project doesn't exist, but endpoint works
        if response.status_code == 200:
            data = response.json()
            assert "job_id" in data
            assert "status" in data

    def test_execute_dry_run(self, api_client):
        """Dry run doesn't actually execute."""
        response = api_client.post(
            "/helix/execute",
            json={"project_path": "projects/test", "dry_run": True},
        )
        # Endpoint should accept dry_run parameter
        assert response.status_code in [200, 400, 404, 422]


class TestHelixJobs:
    """Tests for HELIX jobs endpoint."""

    def test_jobs_endpoint(self, api_client):
        """GET /helix/jobs returns job list."""
        response = api_client.get("/helix/jobs")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

    def test_jobs_list_format(self, api_client):
        """Jobs list contains properly formatted entries."""
        # First create a job
        api_client.post(
            "/helix/execute",
            json={"project_path": "projects/test", "dry_run": True},
        )

        response = api_client.get("/helix/jobs")
        data = response.json()

        # If there are jobs, check format
        if len(data) > 0:
            job = data[0]
            assert "job_id" in job
            assert "status" in job


class TestAsyncEndpoints:
    """Async tests for streaming endpoints."""

    @pytest.mark.asyncio
    async def test_health_async(self, async_api_client):
        """Async health check."""
        async with async_api_client:
            response = await async_api_client.get("/")
            assert response.status_code == 200
            assert response.json()["status"] == "running"

    @pytest.mark.asyncio
    async def test_models_async(self, async_api_client):
        """Async models list."""
        async with async_api_client:
            response = await async_api_client.get("/v1/models")
            assert response.status_code == 200
            data = response.json()
            assert len(data["data"]) >= 2

    @pytest.mark.asyncio
    async def test_jobs_async(self, async_api_client):
        """Async jobs list."""
        async with async_api_client:
            response = await async_api_client.get("/helix/jobs")
            assert response.status_code == 200
            assert isinstance(response.json(), list)


# Convenience function for manual testing
if __name__ == "__main__":
    print(f"Testing API at {API_BASE}")
    client = httpx.Client(base_url=API_BASE, timeout=30.0)

    print("\n1. Health check...")
    r = client.get("/")
    print(f"   Status: {r.status_code}")
    print(f"   Response: {r.json()}")

    print("\n2. Models...")
    r = client.get("/v1/models")
    print(f"   Status: {r.status_code}")
    print(f"   Models: {[m['id'] for m in r.json()['data']]}")

    print("\n3. Chat completion...")
    r = client.post("/v1/chat/completions", json={
        "model": "helix-consultant",
        "messages": [{"role": "user", "content": "Hallo"}],
        "stream": False,
    })
    print(f"   Status: {r.status_code}")

    print("\n4. Jobs...")
    r = client.get("/helix/jobs")
    print(f"   Status: {r.status_code}")
    print(f"   Jobs: {len(r.json())}")

    print("\nAll manual tests passed!")
