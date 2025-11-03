"""
Contract tests for session API endpoints
"""

import pytest
from httpx import AsyncClient
import uuid


@pytest.mark.contract
@pytest.mark.asyncio
async def test_create_session_contract(test_client: AsyncClient):
    """Test session creation API contract"""
    request_data = {
        "user_input": "I want to create a chatbot for customer service"
    }

    response = await test_client.post("/v1/sessions", json=request_data)

    # Test response structure
    assert response.status_code == 201

    data = response.json()
    required_fields = [
        "id", "user_input", "status", "iteration_count",
        "user_intervention_count", "created_at", "updated_at",
        "final_prompt"
    ]

    for field in required_fields:
        assert field in data, f"Missing required field: {field}"

    # Test field types
    assert isinstance(uuid.UUID(data["id"]), uuid.UUID)
    assert isinstance(data["user_input"], str)
    assert isinstance(data["status"], str)
    assert isinstance(data["iteration_count"], int)
    assert isinstance(data["user_intervention_count"], int)
    assert isinstance(data["created_at"], str)
    assert isinstance(data["updated_at"], str)
    assert data["final_prompt"] is None or isinstance(data["final_prompt"], str)

    # Test field values
    assert data["user_input"] == request_data["user_input"]
    assert data["status"] in ["active", "processing", "completed", "failed"]
    assert data["iteration_count"] == 0
    assert data["user_intervention_count"] == 0


@pytest.mark.contract
@pytest.mark.asyncio
async def test_get_session_contract(test_client: AsyncClient, sample_session_data):
    """Test get session API contract"""
    # First create a session
    create_response = await test_client.post("/v1/sessions", json={
        "user_input": "Test input for contract testing"
    })
    session_id = create_response.json()["id"]

    # Then retrieve it
    response = await test_client.get(f"/v1/sessions/{session_id}")

    assert response.status_code == 200

    data = response.json()
    required_fields = [
        "id", "user_input", "status", "iteration_count",
        "user_intervention_count", "created_at", "updated_at",
        "final_prompt"
    ]

    for field in required_fields:
        assert field in data, f"Missing required field: {field}"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_list_sessions_contract(test_client: AsyncClient):
    """Test list sessions API contract"""
    response = await test_client.get("/v1/sessions")

    assert response.status_code == 200

    data = response.json()
    required_fields = ["sessions", "total", "limit", "offset"]

    for field in required_fields:
        assert field in data, f"Missing required field: {field}"

    # Test field types
    assert isinstance(data["sessions"], list)
    assert isinstance(data["total"], int)
    assert isinstance(data["limit"], int)
    assert isinstance(data["offset"], int)

    # Test default pagination values
    assert data["limit"] == 20
    assert data["offset"] == 0


@pytest.mark.contract
@pytest.mark.asyncio
async def test_start_session_contract(test_client: AsyncClient):
    """Test start session API contract"""
    # Create a session first
    create_response = await test_client.post("/v1/sessions", json={
        "user_input": "Test input for starting session"
    })
    session_id = create_response.json()["id"]

    # Start the session
    response = await test_client.post(f"/v1/sessions/{session_id}/start")

    assert response.status_code == 200

    data = response.json()
    required_fields = [
        "session_id", "status", "current_iteration",
        "max_iterations", "estimated_completion_time"
    ]

    for field in required_fields:
        assert field in data, f"Missing required field: {field}"

    # Test field types
    assert isinstance(uuid.UUID(data["session_id"]), uuid.UUID)
    assert isinstance(data["status"], str)
    assert isinstance(data["current_iteration"], int)
    assert isinstance(data["max_iterations"], int)


@pytest.mark.contract
@pytest.mark.asyncio
async def test_error_response_contract(test_client: AsyncClient):
    """Test error response contract"""
    # Test invalid request data
    response = await test_client.post("/v1/sessions", json={
        "invalid_field": "This should fail validation"
    })

    assert response.status_code == 422

    data = response.json()
    error_fields = ["error", "message", "details"]

    for field in error_fields:
        assert field in data, f"Missing error field: {field}"

    assert data["error"] == "VALIDATION_ERROR"
    assert "validation_errors" in data["details"]
    assert isinstance(data["details"]["validation_errors"], list)


@pytest.mark.contract
@pytest.mark.asyncio
async def test_not_found_contract(test_client: AsyncClient):
    """Test 404 response contract"""
    fake_id = uuid.uuid4()
    response = await test_client.get(f"/v1/sessions/{fake_id}")

    assert response.status_code == 404

    data = response.json()
    error_fields = ["error", "message", "details"]

    for field in error_fields:
        assert field in data, f"Missing error field: {field}"

    assert data["error"] == "NOT_FOUND"