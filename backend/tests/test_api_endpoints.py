"""
Unit tests for API endpoints
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import status
import uuid
import json
from datetime import datetime, timezone

from backend.src.api.sessions import router as sessions_router
from backend.src.api.user_input import router as user_input_router
from backend.src.models.session import SessionCreate, SessionResponse, SessionStatus
from backend.src.models.message import MessageResponse, MessageType
from backend.src.repositories.session_repository import SessionRepository
from backend.src.repositories.message_repository import MessageRepository
from backend.src.agents.orchestration_engine import AgentOrchestrationEngine, OrchestrationState


class TestSessionAPI:
    """Test cases for session API endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(sessions_router, prefix="/v1/sessions")
        return TestClient(app)

    @pytest.fixture
    def mock_session_repo(self):
        """Mock session repository"""
        repo = Mock(spec=SessionRepository)
        repo.create = AsyncMock()
        repo.get_by_id = AsyncMock()
        repo.get_all = AsyncMock()
        repo.update = AsyncMock()
        repo.delete = AsyncMock()
        return repo

    @pytest.fixture
    def mock_orchestration_engine(self):
        """Mock orchestration engine"""
        engine = Mock(spec=AgentOrchestrationEngine)
        engine.start_session = AsyncMock()
        engine.get_session_state = AsyncMock()
        engine.cancel_session = AsyncMock()
        return engine

    @pytest.fixture
    def sample_session_data(self):
        """Sample session data"""
        return {
            "user_input": "Create a prompt for a customer service chatbot",
            "context": {
                "industry": "e-commerce",
                "target_audience": "customers"
            }
        }

    @pytest.fixture
    def sample_session_response(self):
        """Sample session response from database"""
        return {
            "id": str(uuid.uuid4()),
            "user_input": "Create a prompt for a customer service chatbot",
            "status": "active",
            "final_prompt": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "iteration_count": 1,
            "user_intervention_count": 0,
            "waiting_for_user_since": None
        }

    def test_create_session_success(self, client, sample_session_data, sample_session_response):
        """Test successful session creation"""
        with patch('backend.src.api.sessions.get_session_repository') as mock_get_repo, \
             patch('backend.src.api.sessions.get_orchestration_engine') as mock_get_engine:

            # Setup mocks
            mock_repo = Mock(spec=SessionRepository)
            mock_repo.create = AsyncMock(return_value=sample_session_response)
            mock_get_repo.return_value = mock_repo

            mock_engine = Mock(spec=AgentOrchestrationEngine)
            mock_engine.start_session = AsyncMock(return_value=OrchestrationState(
                session_id=sample_session_response["id"],
                user_input=sample_session_data["user_input"],
                current_step="product_manager_analysis",
                status="processing"
            ))
            mock_get_engine.return_value = mock_engine

            # Make request
            response = client.post("/v1/sessions", json=sample_session_data)

            # Assertions
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["id"] == sample_session_response["id"]
            assert data["user_input"] == sample_session_data["user_input"]
            assert data["status"] == "processing"

    def test_create_session_validation_error(self, client):
        """Test session creation with invalid data"""
        invalid_data = {
            "user_input": "",  # Empty input should fail validation
            "context": {}
        }

        response = client.post("/v1/sessions", json=invalid_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        errors = response.json()["detail"]
        assert any(error["field"] == "user_input" for error in errors)

    def test_get_session_by_id_success(self, client, sample_session_response):
        """Test successful session retrieval by ID"""
        with patch('backend.src.api.sessions.get_session_repository') as mock_get_repo:
            mock_repo = Mock(spec=SessionRepository)
            mock_repo.get_by_id = AsyncMock(return_value=sample_session_response)
            mock_get_repo.return_value = mock_repo

            response = client.get(f"/v1/sessions/{sample_session_response['id']}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == sample_session_response["id"]
            assert data["user_input"] == sample_session_response["user_input"]

    def test_get_session_not_found(self, client):
        """Test session retrieval with non-existent ID"""
        with patch('backend.src.api.sessions.get_session_repository') as mock_get_repo:
            mock_repo = Mock(spec=SessionRepository)
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_get_repo.return_value = mock_repo

            session_id = str(uuid.uuid4())
            response = client.get(f"/v1/sessions/{session_id}")

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "not found" in response.json()["detail"].lower()

    def test_get_sessions_list_success(self, client):
        """Test successful sessions list retrieval"""
        with patch('backend.src.api.sessions.get_session_repository') as mock_get_repo:
            sample_sessions = [
                {
                    "id": str(uuid.uuid4()),
                    "user_input": f"Request {i}",
                    "status": "active",
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                    "iteration_count": 1,
                    "user_intervention_count": 0
                }
                for i in range(3)
            ]

            mock_repo = Mock(spec=SessionRepository)
            mock_repo.get_all = AsyncMock(return_value=sample_sessions)
            mock_get_repo.return_value = mock_repo

            response = client.get("/v1/sessions")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data["sessions"]) == 3
            assert data["total"] == 3

    def test_get_sessions_with_filters(self, client):
        """Test sessions list retrieval with filters"""
        with patch('backend.src.api.sessions.get_session_repository') as mock_get_repo:
            mock_repo = Mock(spec=SessionRepository)
            mock_repo.get_all = AsyncMock(return_value=[])
            mock_get_repo.return_value = mock_repo

            response = client.get("/v1/sessions?status=active&page=1&page_size=10")

            assert response.status_code == status.HTTP_200_OK
            mock_repo.get_all.assert_called_once_with(
                status="active",
                page=1,
                page_size=10
            )

    def test_start_session_success(self, client, sample_session_response):
        """Test successful session start"""
        with patch('backend.src.api.sessions.get_session_repository') as mock_get_repo, \
             patch('backend.src.api.sessions.get_orchestration_engine') as mock_get_engine:

            # Setup mocks
            mock_repo = Mock(spec=SessionRepository)
            mock_repo.get_by_id = AsyncMock(return_value=sample_session_response)
            mock_repo.update = AsyncMock(return_value={**sample_session_response, "status": "processing"})
            mock_get_repo.return_value = mock_repo

            mock_engine = Mock(spec=AgentOrchestrationEngine)
            mock_engine.start_session = AsyncMock(return_value=OrchestrationState(
                session_id=sample_session_response["id"],
                user_input=sample_session_response["user_input"],
                current_step="product_manager_analysis",
                status="processing"
            ))
            mock_get_engine.return_value = mock_engine

            session_id = sample_session_response["id"]
            response = client.post(f"/v1/sessions/{session_id}/start")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "processing"

    def test_start_session_not_found(self, client):
        """Test starting non-existent session"""
        with patch('backend.src.api.sessions.get_session_repository') as mock_get_repo:
            mock_repo = Mock(spec=SessionRepository)
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_get_repo.return_value = mock_repo

            session_id = str(uuid.uuid4())
            response = client.post(f"/v1/sessions/{session_id}/start")

            assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_cancel_session_success(self, client, sample_session_response):
        """Test successful session cancellation"""
        with patch('backend.src.api.sessions.get_session_repository') as mock_get_repo, \
             patch('backend.src.api.sessions.get_orchestration_engine') as mock_get_engine:

            # Setup mocks
            mock_repo = Mock(spec=SessionRepository)
            mock_repo.get_by_id = AsyncMock(return_value=sample_session_response)
            mock_repo.update = AsyncMock(return_value={**sample_session_response, "status": "cancelled"})
            mock_get_repo.return_value = mock_repo

            mock_engine = Mock(spec=AgentOrchestrationEngine)
            mock_engine.cancel_session = AsyncMock(return_value=OrchestrationState(
                session_id=sample_session_response["id"],
                user_input=sample_session_response["user_input"],
                current_step="cancelled",
                status="cancelled"
            ))
            mock_get_engine.return_value = mock_engine

            session_id = sample_session_response["id"]
            response = client.post(f"/v1/sessions/{session_id}/cancel")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "cancelled"

    def test_delete_session_success(self, client, sample_session_response):
        """Test successful session deletion"""
        with patch('backend.src.api.sessions.get_session_repository') as mock_get_repo:
            mock_repo = Mock(spec=SessionRepository)
            mock_repo.get_by_id = AsyncMock(return_value=sample_session_response)
            mock_repo.delete = AsyncMock(return_value=True)
            mock_get_repo.return_value = mock_repo

            session_id = sample_session_response["id"]
            response = client.delete(f"/v1/sessions/{session_id}")

            assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_session_not_found(self, client):
        """Test deleting non-existent session"""
        with patch('backend.src.api.sessions.get_session_repository') as mock_get_repo:
            mock_repo = Mock(spec=SessionRepository)
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_get_repo.return_value = mock_repo

            session_id = str(uuid.uuid4())
            response = client.delete(f"/v1/sessions/{session_id}")

            assert response.status_code == status.HTTP_404_NOT_FOUND


class TestUserInputAPI:
    """Test cases for user input API endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(user_input_router, prefix="/v1/sessions")
        return TestClient(app)

    @pytest.fixture
    def sample_session(self):
        """Sample session"""
        return {
            "id": str(uuid.uuid4()),
            "user_input": "Original request",
            "status": "waiting_for_user_input"
        }

    @pytest.fixture
    def sample_input_data(self):
        """Sample user input data"""
        return {
            "input_content": "Here are additional details for the prompt",
            "input_type": "supplementary"
        }

    def test_submit_user_input_success(self, client, sample_session, sample_input_data):
        """Test successful user input submission"""
        with patch('backend.src.api.user_input.get_session_repository') as mock_get_repo, \
             patch('backend.src.api.user_input.get_orchestration_engine') as mock_get_engine:

            # Setup mocks
            mock_repo = Mock(spec=SessionRepository)
            mock_repo.get_by_id = AsyncMock(return_value=sample_session)
            mock_get_repo.return_value = mock_repo

            mock_engine = Mock(spec=AgentOrchestrationEngine)
            mock_engine.handle_user_input = AsyncMock(return_value=OrchestrationState(
                session_id=sample_session["id"],
                user_input=sample_session["user_input"],
                current_step="processing",
                status="processing"
            ))
            mock_get_engine.return_value = mock_engine

            session_id = sample_session["id"]
            response = client.post(f"/v1/sessions/{session_id}/user-input", json=sample_input_data)

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "processing"

    def test_submit_user_input_session_not_found(self, client, sample_input_data):
        """Test user input submission for non-existent session"""
        with patch('backend.src.api.user_input.get_session_repository') as mock_get_repo:
            mock_repo = Mock(spec=SessionRepository)
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_get_repo.return_value = mock_repo

            session_id = str(uuid.uuid4())
            response = client.post(f"/v1/sessions/{session_id}/user-input", json=sample_input_data)

            assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_submit_user_input_wrong_session_status(self, client, sample_session, sample_input_data):
        """Test user input submission for session not waiting for input"""
        sample_session["status"] = "processing"  # Not waiting for user input

        with patch('backend.src.api.user_input.get_session_repository') as mock_get_repo:
            mock_repo = Mock(spec=SessionRepository)
            mock_repo.get_by_id = AsyncMock(return_value=sample_session)
            mock_get_repo.return_value = mock_repo

            session_id = sample_session["id"]
            response = client.post(f"/v1/sessions/{session_id}/user-input", json=sample_input_data)

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "not waiting for user input" in response.json()["detail"].lower()

    def test_continue_without_input_success(self, client, sample_session):
        """Test successful continue without input"""
        with patch('backend.src.api.user_input.get_session_repository') as mock_get_repo, \
             patch('backend.src.api.user_input.get_orchestration_engine') as mock_get_engine:

            # Setup mocks
            mock_repo = Mock(spec=SessionRepository)
            mock_repo.get_by_id = AsyncMock(return_value=sample_session)
            mock_get_repo.return_value = mock_repo

            mock_engine = Mock(spec=AgentOrchestrationEngine)
            mock_engine.continue_without_input = AsyncMock(return_value=OrchestrationState(
                session_id=sample_session["id"],
                user_input=sample_session["user_input"],
                current_step="processing",
                status="processing"
            ))
            mock_get_engine.return_value = mock_engine

            session_id = sample_session["id"]
            response = client.post(f"/v1/sessions/{session_id}/continue", json={
                "force_continue": False
            })

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "processing"

    def test_get_session_messages_success(self, client, sample_session):
        """Test successful session messages retrieval"""
        with patch('backend.src.api.user_input.get_session_repository') as mock_get_repo, \
             patch('backend.src.api.user_input.get_message_repository') as mock_get_message_repo:

            # Setup mocks
            mock_repo = Mock(spec=SessionRepository)
            mock_repo.get_by_id = AsyncMock(return_value=sample_session)
            mock_get_repo.return_value = mock_repo

            sample_messages = [
                {
                    "id": str(uuid.uuid4()),
                    "session_id": sample_session["id"],
                    "agent_type": "product_manager",
                    "message_content": "Requirements analyzed",
                    "message_type": "requirement",
                    "sequence_number": 1,
                    "created_at": datetime.now(timezone.utc),
                    "processing_time_ms": 1500
                }
            ]

            mock_message_repo = Mock(spec=MessageRepository)
            mock_message_repo.get_by_session_id = AsyncMock(return_value=sample_messages)
            mock_get_message_repo.return_value = mock_message_repo

            session_id = sample_session["id"]
            response = client.get(f"/v1/sessions/{session_id}/messages")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data["messages"]) == 1
            assert data["messages"][0]["agent_type"] == "product_manager"

    def test_get_session_messages_with_pagination(self, client, sample_session):
        """Test session messages retrieval with pagination"""
        with patch('backend.src.api.user_input.get_session_repository') as mock_get_repo, \
             patch('backend.src.api.user_input.get_message_repository') as mock_get_message_repo:

            # Setup mocks
            mock_repo = Mock(spec=SessionRepository)
            mock_repo.get_by_id = AsyncMock(return_value=sample_session)
            mock_get_repo.return_value = mock_repo

            mock_message_repo = Mock(spec=MessageRepository)
            mock_message_repo.get_by_session_id = AsyncMock(return_value=[])
            mock_get_message_repo.return_value = mock_message_repo

            session_id = sample_session["id"]
            response = client.get(f"/v1/sessions/{session_id}/messages?limit=10&offset=20")

            assert response.status_code == status.HTTP_200_OK
            mock_message_repo.get_by_session_id.assert_called_once_with(
                session_id,
                limit=10,
                offset=20
            )


class TestAPIIntegration:
    """Integration tests for API endpoints"""

    @pytest.fixture
    def app(self):
        """Create FastAPI app with all routers"""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(sessions_router, prefix="/v1/sessions")
        app.include_router(user_input_router, prefix="/v1/sessions")
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return TestClient(app)

    def test_cors_headers(self, client):
        """Test CORS headers are present"""
        response = client.options("/v1/sessions")
        # Check if CORS headers are present (if CORS middleware is configured)
        # This would depend on your actual CORS configuration

    def test_api_health_check(self, client):
        """Test API health endpoint (if implemented)"""
        # This would test a health check endpoint if you implement one
        pass

    def test_api_response_format(self, client):
        """Test API response format consistency"""
        # Test that all responses follow consistent format
        # This would involve checking that error responses have the expected structure
        pass

    def test_api_error_handling(self, client):
        """Test consistent error handling across endpoints"""
        # Test various error scenarios and ensure consistent error responses
        invalid_uuid = "invalid-uuid"

        # Test that invalid UUID format returns 422
        response = client.get(f"/v1/sessions/{invalid_uuid}")
        assert response.status_code in [status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_404_NOT_FOUND]

    def test_request_validation(self, client):
        """Test request validation for various endpoints"""
        # Test create session with missing required fields
        response = client.post("/v1/sessions", json={})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test user input with missing required fields
        session_id = str(uuid.uuid4())
        response = client.post(f"/v1/sessions/{session_id}/user-input", json={})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


if __name__ == "__main__":
    pytest.main([__file__])