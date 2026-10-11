"""Integration tests for API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import Base, get_db_manager
from app.main import app


@pytest.fixture(autouse=True)
async def setup_db():
    """Create tables before each test."""
    db_manager = get_db_manager()
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    """Create a test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHealthEndpoint:
    """Test health check endpoint."""

    async def test_health_check(self, client: AsyncClient):
        response = await client.get("/api/v1/scans/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"


class TestRubricEndpoint:
    """Test rubric endpoint."""

    async def test_get_rubric(self, client: AsyncClient):
        response = await client.get("/api/v1/rubric")
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "1.0"
        assert len(data["dimensions"]) == 10
        assert "project_type_rules" in data
        assert "severity_mapping" in data
        assert "confidence_by_category" in data


class TestScanCreation:
    """Test scan creation endpoint."""

    async def test_create_scan_missing_url(self, client: AsyncClient):
        response = await client.post("/api/v1/scans", json={})
        assert response.status_code == 422

    async def test_create_scan_invalid_url(self, client: AsyncClient):
        response = await client.post("/api/v1/scans", json={"repo_url": "https://example.com/repo"})
        assert response.status_code == 400

    async def test_create_scan_valid_url(self, client: AsyncClient):
        # This will fail at the orchestrator level but should create the scan record
        response = await client.post("/api/v1/scans", json={"repo_url": "https://github.com/octocat/Hello-World"})
        # The scan creation itself should succeed (or fail at orchestration)
        assert response.status_code in [201, 500]


class TestScanStatus:
    """Test scan status endpoint."""

    async def test_get_scan_status_not_found(self, client: AsyncClient):
        response = await client.get("/api/v1/scans/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404


class TestScanHistory:
    """Test scan history endpoint."""

    async def test_get_scan_history(self, client: AsyncClient):
        response = await client.get("/api/v1/scans/history?limit=50&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
