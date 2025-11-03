"""
Integration tests for health check endpoints
"""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_check_endpoint(test_client: AsyncClient):
    """Test the health check endpoint"""
    response = await test_client.get("/v1/health")

    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "timestamp" in data
    assert "dependencies" in data

    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"

    dependencies = data["dependencies"]
    assert "database" in dependencies
    assert "llm_api" in dependencies
    assert "redis" in dependencies


@pytest.mark.integration
@pytest.mark.asyncio
async def test_root_endpoint(test_client: AsyncClient):
    """Test the root endpoint"""
    response = await test_client.get("/")

    assert response.status_code == 200

    data = response.json()
    assert "message" in data
    assert "version" in data
    assert "docs" in data

    assert "AI Agent Prompt Generator API" in data["message"]
    assert data["version"] == "1.0.0"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cors_headers(test_client: AsyncClient):
    """Test that CORS headers are properly set"""
    response = await test_client.options("/v1/health")

    # Check for CORS headers
    assert "access-control-allow-origin" in response.headers
    assert "access-control-allow-methods" in response.headers
    assert "access-control-allow-headers" in response.headers


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_handling(test_client: AsyncClient):
    """Test error handling for non-existent endpoints"""
    response = await test_client.get("/v1/non-existent")

    assert response.status_code == 404

    data = response.json()
    assert "error" in data
    assert "message" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_invalid_json_request(test_client: AsyncClient):
    """Test handling of invalid JSON requests"""
    response = await test_client.post(
        "/v1/sessions",
        data="invalid json",
        headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 422

    data = response.json()
    assert "error" in data
    assert "details" in data
    assert "validation_errors" in data["details"]