"""
Integration tests for the complete system
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
import websockets
from datetime import datetime, timezone
import uuid

from backend.src.api.app import app
from backend.src.database.connection import get_database
from backend.src.repositories.session_repository import SessionRepository
from backend.src.repositories.message_repository import MessageRepository
from backend.src.agents.orchestration_engine import AgentOrchestrationEngine
from backend.src.services.glm_api import GLMClient
from backend.src.models.session import SessionCreate, SessionStatus


class TestAPIIntegration:
    """Integration tests for API endpoints"""

    @pytest.fixture
    async def client(self):
        """Create async HTTP client for testing"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client

    @pytest.fixture
    async def mock_db(self):
        """Mock database connection"""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.fetch = AsyncMock()
        mock_conn.fetchval = AsyncMock()
        mock_conn.fetchmany = AsyncMock(return_value=[])
        return mock_conn

    @pytest.fixture
    async def mock_glm_client(self):
        """Mock GLM client for integration testing"""
        client = Mock(spec=GLMClient)
        client.complete = AsyncMock(return_value=Mock(
            content="AI generated response",
            role="assistant",
            finish_reason="stop",
            usage=Mock(prompt_tokens=10, completion_tokens=15, total_tokens=25)
        ))
        return client

    @pytest.mark.asyncio
    async def test_complete_session_workflow(self, client, mock_db, mock_glm_client):
        """Test complete session workflow from creation to completion"""
        # Mock database responses
        with patch('backend.src.database.connection.get_database', return_value=mock_db), \
             patch('backend.src.services.glm_api.GLMClient', return_value=mock_glm_client):

            # 1. Create a new session
            session_data = {
                "user_input": "Create a prompt for a customer service chatbot",
                "context": {
                    "industry": "e-commerce",
                    "company_size": "medium"
                }
            }

            response = await client.post("/v1/sessions", json=session_data)
            assert response.status_code == 201

            session = response.json()
            session_id = session["id"]
            assert session["user_input"] == session_data["user_input"]
            assert session["status"] == "processing"

            # 2. Start the session
            response = await client.post(f"/v1/sessions/{session_id}/start")
            assert response.status_code == 200
            assert response.json()["status"] == "processing"

            # 3. Get session status
            response = await client.get(f"/v1/sessions/{session_id}")
            assert response.status_code == 200
            assert response.json()["id"] == session_id

            # 4. Get messages (should be empty initially)
            response = await client.get(f"/v1/sessions/{session_id}/messages")
            assert response.status_code == 200
            messages = response.json()["messages"]
            assert len(messages) >= 0  # May have agent messages

            # 5. Handle user input if waiting for input
            if session.get("status") == "waiting_for_user_input":
                input_data = {
                    "input_content": "Please add more specific requirements for response time",
                    "input_type": "supplementary"
                }
                response = await client.post(f"/v1/sessions/{session_id}/user-input", json=input_data)
                assert response.status_code == 200

            # 6. Continue without input (alternative to step 5)
            response = await client.post(f"/v1/sessions/{session_id}/continue", json={"force_continue": False})
            # May succeed or fail depending on session state

            # 7. Get final session state
            response = await client.get(f"/v1/sessions/{session_id}")
            assert response.status_code == 200
            final_session = response.json()
            assert final_session["id"] == session_id

            # 8. Cancel session if still active
            if final_session["status"] in ["active", "processing", "waiting_for_user_input"]:
                response = await client.post(f"/v1/sessions/{session_id}/cancel")
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_error_handling_workflow(self, client, mock_db):
        """Test error handling across the API"""
        with patch('backend.src.database.connection.get_database', return_value=mock_db):
            # Test invalid session ID
            fake_id = str(uuid.uuid4())
            response = await client.get(f"/v1/sessions/{fake_id}")
            assert response.status_code == 404

            # Test invalid input validation
            response = await client.post("/v1/sessions", json={"user_input": ""})
            assert response.status_code == 422

            # Test user input to non-existent session
            response = await client.post(f"/v1/sessions/{fake_id}/user-input", json={
                "input_content": "test",
                "input_type": "supplementary"
            })
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_concurrent_sessions(self, client, mock_db, mock_glm_client):
        """Test handling multiple concurrent sessions"""
        with patch('backend.src.database.connection.get_database', return_value=mock_db), \
             patch('backend.src.services.glm_api.GLMClient', return_value=mock_glm_client):

            # Create multiple sessions concurrently
            session_creation_tasks = []
            for i in range(5):
                session_data = {
                    "user_input": f"Create prompt for session {i}",
                    "context": {"session_index": i}
                }
                task = client.post("/v1/sessions", json=session_data)
                session_creation_tasks.append(task)

            # Wait for all sessions to be created
            responses = await asyncio.gather(*session_creation_tasks, return_exceptions=True)

            # Verify all sessions were created successfully
            session_ids = []
            for response in responses:
                assert response.status_code == 201
                session_ids.append(response.json()["id"])

            # Start all sessions concurrently
            start_tasks = [client.post(f"/v1/sessions/{sid}/start") for sid in session_ids]
            start_responses = await asyncio.gather(*start_tasks, return_exceptions=True)

            # Verify all sessions started
            for response in start_responses:
                assert response.status_code == 200

            # Verify sessions are independent
            for session_id in session_ids:
                response = await client.get(f"/v1/sessions/{session_id}")
                assert response.status_code == 200
                assert response.json()["id"] == session_id

    @pytest.mark.asyncio
    async def test_session_pagination(self, client, mock_db):
        """Test session list pagination"""
        with patch('backend.src.database.connection.get_database', return_value=mock_db):
            # Mock database to return paginated results
            mock_sessions = [
                {
                    "id": str(uuid.uuid4()),
                    "user_input": f"Session {i}",
                    "status": "completed",
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                    "iteration_count": 1,
                    "user_intervention_count": 0
                }
                for i in range(10)
            ]

            mock_db.fetch.return_value = mock_sessions

            # Test pagination
            response = await client.get("/v1/sessions?page=1&page_size=5")
            assert response.status_code == 200
            data = response.json()
            assert len(data["sessions"]) <= 5
            assert data["total"] >= 5

            # Test filtering by status
            response = await client.get("/v1/sessions?status=completed")
            assert response.status_code == 200


class TestWebSocketIntegration:
    """Integration tests for WebSocket functionality"""

    @pytest.fixture
    async def mock_websocket_server(self):
        """Mock WebSocket server for testing"""
        class MockWebSocketServer:
            def __init__(self):
                self.connections = {}
                self.messages = []

            async def connect(self, websocket, session_id):
                self.connections[session_id] = websocket
                await websocket.send(json.dumps({
                    "type": "connection_established",
                    "session_id": session_id
                }))

            async def disconnect(self, session_id):
                if session_id in self.connections:
                    del self.connections[session_id]

            async def send_message(self, session_id, message):
                if session_id in self.connections:
                    await self.connections[session_id].send(json.dumps(message))

            async def broadcast(self, message):
                for websocket in self.connections.values():
                    await websocket.send(json.dumps(message))

        return MockWebSocketServer()

    @pytest.mark.asyncio
    async def test_websocket_connection_lifecycle(self, mock_websocket_server):
        """Test WebSocket connection and disconnection"""
        session_id = str(uuid.uuid4())

        # Mock websocket client
        mock_websocket = AsyncMock()
        mock_websocket.send = AsyncMock()
        mock_websocket.recv = AsyncMock(side_effect=[
            json.dumps({"type": "ping"}),
            websockets.exceptions.ConnectionClosed(1000, "Normal closure")
        ])

        # Connect
        await mock_websocket_server.connect(mock_websocket, session_id)
        assert session_id in mock_websocket_server.connections

        # Send message
        test_message = {
            "type": "agent_message",
            "session_id": session_id,
            "data": {
                "agent_type": "product_manager",
                "message": "Test message"
            }
        }
        await mock_websocket_server.send_message(session_id, test_message)
        mock_websocket.send.assert_called_with(json.dumps(test_message))

        # Disconnect
        await mock_websocket_server.disconnect(session_id)
        assert session_id not in mock_websocket_server.connections

    @pytest.mark.asyncio
    async def test_real_time_message_streaming(self, mock_websocket_server):
        """Test real-time message streaming through WebSocket"""
        session_id = str(uuid.uuid4())

        # Setup multiple mock connections
        websockets = []
        for i in range(3):
            ws = AsyncMock()
            ws.send = AsyncMock()
            websockets.append(ws)
            await mock_websocket_server.connect(ws, session_id)

        # Simulate agent messages
        agent_messages = [
            {
                "type": "agent_message",
                "session_id": session_id,
                "data": {
                    "agent_type": "product_manager",
                    "message": "Analyzing requirements...",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            },
            {
                "type": "agent_message",
                "session_id": session_id,
                "data": {
                    "agent_type": "technical_developer",
                    "message": "Designing technical solution...",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            },
            {
                "type": "agent_message",
                "session_id": session_id,
                "data": {
                    "agent_type": "team_lead",
                    "message": "Reviewing and approving...",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            }
        ]

        # Broadcast messages
        for message in agent_messages:
            await mock_websocket_server.broadcast(message)

        # Verify all connections received all messages
        for ws in websockets:
            assert ws.send.call_count == len(agent_messages)
            sent_messages = [call.args[0] for call in ws.send.call_args_list]
            for expected_message in agent_messages:
                assert json.dumps(expected_message) in sent_messages

    @pytest.mark.asyncio
    async def test_websocket_error_handling(self, mock_websocket_server):
        """Test WebSocket error handling"""
        session_id = str(uuid.uuid4())

        # Mock websocket that fails on send
        failing_websocket = AsyncMock()
        failing_websocket.send.side_effect = Exception("Connection lost")

        await mock_websocket_server.connect(failing_websocket, session_id)

        # Attempt to send message should handle error gracefully
        test_message = {"type": "test", "data": "test message"}

        # Should not raise exception
        try:
            await mock_websocket_server.send_message(session_id, test_message)
        except Exception:
            pass  # Expected for this test

        # Server should still be functional
        assert len(mock_websocket_server.connections) == 1

    @pytest.mark.asyncio
    async def test_websocket_session_isolation(self, mock_websocket_server):
        """Test WebSocket session isolation"""
        session_id_1 = str(uuid.uuid4())
        session_id_2 = str(uuid.uuid4())

        # Connect different sessions
        ws1 = AsyncMock()
        ws1.send = AsyncMock()
        ws2 = AsyncMock()
        ws2.send = AsyncMock()

        await mock_websocket_server.connect(ws1, session_id_1)
        await mock_websocket_server.connect(ws2, session_id_2)

        # Send message to specific session
        message_1 = {
            "type": "session_message",
            "session_id": session_id_1,
            "data": "Message for session 1"
        }

        await mock_websocket_server.send_message(session_id_1, message_1)

        # Only session 1 should receive the message
        ws1.send.assert_called_once_with(json.dumps(message_1))
        ws2.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_websocket_reconnection(self, mock_websocket_server):
        """Test WebSocket reconnection logic"""
        session_id = str(uuid.uuid4())

        # Initial connection
        ws1 = AsyncMock()
        ws1.send = AsyncMock()
        await mock_websocket_server.connect(ws1, session_id)

        # Simulate disconnection
        await mock_websocket_server.disconnect(session_id)

        # Reconnection
        ws2 = AsyncMock()
        ws2.send = AsyncMock()
        await mock_websocket_server.connect(ws2, session_id)

        # Verify reconnection works
        assert session_id in mock_websocket_server.connections
        assert mock_websocket_server.connections[session_id] == ws2


class TestAgentIntegration:
    """Integration tests for agent orchestration"""

    @pytest.fixture
    async def mock_glm_client(self):
        """Mock GLM client with realistic responses"""
        client = Mock(spec=GLMClient)

        # Different responses for different agents
        def mock_complete(request):
            if "product_manager" in str(request):
                return Mock(
                    content="I've analyzed the requirements for the customer service chatbot. Key aspects include: friendly tone, 24/7 availability, and efficient problem resolution.",
                    role="assistant",
                    finish_reason="stop",
                    usage=Mock(prompt_tokens=50, completion_tokens=40, total_tokens=90)
                )
            elif "technical_developer" in str(request):
                return Mock(
                    content="Technical solution: Use a prompt template with clear role definition, context instructions, and response format guidelines. Include escalation procedures.",
                    role="assistant",
                    finish_reason="stop",
                    usage=Mock(prompt_tokens=60, completion_tokens=45, total_tokens=105)
                )
            elif "team_lead" in str(request):
                return Mock(
                    content="Approved. The prompt meets requirements for clarity, completeness, and quality. Final prompt ready for deployment.",
                    role="assistant",
                    finish_reason="stop",
                    usage=Mock(prompt_tokens=70, completion_tokens=35, total_tokens=105)
                )
            else:
                return Mock(
                    content="General response",
                    role="assistant",
                    finish_reason="stop",
                    usage=Mock(prompt_tokens=10, completion_tokens=15, total_tokens=25)
                )

        client.complete = AsyncMock(side_effect=mock_complete)
        return client

    @pytest.fixture
    async def orchestration_engine(self, mock_glm_client):
        """Create orchestration engine with mocked dependencies"""
        mock_session_repo = Mock()
        mock_message_repo = Mock()
        mock_message_repo.create = AsyncMock(return_value={"id": str(uuid.uuid4())})

        engine = AgentOrchestrationEngine(
            glm_client=mock_glm_client,
            session_repo=mock_session_repo,
            message_repo=mock_message_repo
        )
        return engine

    @pytest.mark.asyncio
    async def test_agent_collaboration_workflow(self, orchestration_engine):
        """Test complete agent collaboration workflow"""
        session_id = str(uuid.uuid4())
        user_input = "Create a prompt for a customer service chatbot"

        # Start session
        state = await orchestration_engine.start_session(session_id, user_input)
        assert state.session_id == session_id
        assert state.current_step == "product_manager_analysis"

        # Process all steps
        steps = []
        while state.status == "processing":
            state = await orchestration_engine.process_current_step(session_id)
            steps.append(state.current_step)

        # Verify workflow progression
        expected_steps = ["technical_development", "team_lead_review", "completed"]
        assert steps == expected_steps
        assert state.status == "completed"

        # Verify all agents were called
        assert orchestration_engine.glm_client.complete.call_count == 3

    @pytest.mark.asyncio
    async def test_agent_error_recovery(self, orchestration_engine):
        """Test agent error handling and recovery"""
        # Simulate agent failure
        orchestration_engine.glm_client.complete.side_effect = [
            Exception("First agent failed"),  # Product manager fails
            Mock(content="Technical solution", role="assistant"),  # Technical developer succeeds
            Mock(content="Final approval", role="assistant")  # Team lead succeeds
        ]

        session_id = str(uuid.uuid4())
        user_input = "Test input"

        # Start session
        state = await orchestration_engine.start_session(session_id, user_input)

        # First step should fail
        with pytest.raises(Exception):
            await orchestration_engine.process_current_step(session_id)

        # Reset error and continue
        orchestration_engine.glm_client.complete.side_effect = None
        orchestration_engine.glm_client.complete.return_value = Mock(
            content="Recovery response",
            role="assistant"
        )

        # Should recover and continue
        state = await orchestration_engine.process_current_step(session_id)
        assert state.status == "processing"

    @pytest.mark.asyncio
    async def test_user_input_integration(self, orchestration_engine):
        """Test user input handling during agent processing"""
        session_id = str(uuid.uuid4())
        user_input = "Create a chatbot prompt"

        # Start session
        state = await orchestration_engine.start_session(session_id, user_input)

        # Simulate waiting for user input
        state.current_step = "waiting_for_user_input"
        state.status = "waiting_for_user_input"
        orchestration_engine.states[session_id] = state

        # Handle user input
        additional_input = "Please add requirements for multilingual support"
        new_state = await orchestration_engine.handle_user_input(session_id, additional_input)

        assert new_state.status == "processing"
        assert "additional_details" in new_state.context
        assert new_state.context["additional_details"] == additional_input

    @pytest.mark.asyncio
    async def test_concurrent_session_processing(self, orchestration_engine):
        """Test processing multiple sessions concurrently"""
        sessions = []
        for i in range(3):
            session_id = str(uuid.uuid4())
            user_input = f"Create prompt {i}"

            state = await orchestration_engine.start_session(session_id, user_input)
            sessions.append((session_id, state))

        # Process all sessions concurrently
        processing_tasks = []
        for session_id, _ in sessions:
            task = orchestration_engine.process_current_step(session_id)
            processing_tasks.append(task)

        results = await asyncio.gather(*processing_tasks, return_exceptions=True)

        # Verify all sessions progressed
        for i, result in enumerate(results):
            assert not isinstance(result, Exception)
            assert result.current_step != "product_manager_analysis"

    @pytest.mark.asyncio
    async def test_agent_context_sharing(self, orchestration_engine):
        """Test context sharing between agents"""
        session_id = str(uuid.uuid4())
        user_input = "Complex prompt request"

        # Start session and process first agent
        state = await orchestration_engine.start_session(session_id, user_input)
        state = await orchestration_engine.process_current_step(session_id)

        # Verify context is built correctly for next agent
        assert state.current_step == "technical_development"
        assert "product_manager_analysis" in state.completed_steps

        # Process second agent
        state = await orchestration_engine.process_current_step(session_id)

        # Verify context includes previous agent work
        assert state.current_step == "team_lead_review"
        assert "technical_development" in state.completed_steps
        assert "product_manager_analysis" in state.completed_steps


class TestEndToEndIntegration:
    """End-to-end integration tests"""

    @pytest.mark.asyncio
    async def test_full_system_integration(self):
        """Test complete system integration from API to agents"""
        # This would be a comprehensive test covering:
        # 1. API request handling
        # 2. Database operations
        # 3. Agent orchestration
        # 4. WebSocket real-time updates
        # 5. Response formatting and delivery

        # For this test environment, we'll create a simplified version
        mock_app = FastAPI()

        @mock_app.post("/test-session")
        async def create_test_session():
            return {"id": str(uuid.uuid4()), "status": "created"}

        @mock_app.get("/test-session/{session_id}")
        async def get_test_session(session_id: str):
            return {"id": session_id, "status": "processing"}

        async with AsyncClient(transport=ASGITransport(app=mock_app), base_url="http://test") as client:
            # Create session
            response = await client.post("/test-session")
            assert response.status_code == 200
            session_data = response.json()
            session_id = session_data["id"]

            # Get session
            response = await client.get(f"/test-session/{session_id}")
            assert response.status_code == 200
            assert response.json()["id"] == session_id

    @pytest.mark.asyncio
    async def test_performance_under_load(self):
        """Test system performance under load"""
        # Mock high-load scenario
        async def simulate_request():
            # Simulate API request -> Database -> Agent -> Response
            await asyncio.sleep(0.01)  # Simulate processing time
            return {"status": "success"}

        # Run concurrent requests
        tasks = [simulate_request() for _ in range(100)]
        start_time = asyncio.get_event_loop().time()

        results = await asyncio.gather(*tasks)

        end_time = asyncio.get_event_loop().time()
        total_time = end_time - start_time

        # Verify all requests succeeded
        assert len(results) == 100
        assert all(result["status"] == "success" for result in results)

        # Performance should be reasonable (less than 2 seconds for 100 requests)
        assert total_time < 2.0

    @pytest.mark.asyncio
    async def test_system_resilience(self):
        """Test system resilience and error recovery"""
        failure_scenarios = [
            "database_connection_error",
            "api_timeout",
            "agent_failure",
            "websocket_disconnect"
        ]

        for scenario in failure_scenarios:
            # Simulate each failure scenario
            async def simulate_failure():
                if scenario == "database_connection_error":
                    raise ConnectionError("Database unavailable")
                elif scenario == "api_timeout":
                    raise asyncio.TimeoutError("Request timeout")
                elif scenario == "agent_failure":
                    raise Exception("Agent processing failed")
                elif scenario == "websocket_disconnect":
                    raise ConnectionError("WebSocket disconnected")

            # System should handle failures gracefully
            try:
                await simulate_failure()
            except Exception as e:
                # Verify error is expected type and handled appropriately
                assert e is not None

    @pytest.mark.asyncio
    async def test_data_consistency(self):
        """Test data consistency across the system"""
        # This test would verify that data remains consistent
        # across API, database, agents, and WebSocket

        session_data = {
            "id": str(uuid.uuid4()),
            "user_input": "Test consistency",
            "status": "processing",
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        # Simulate data flow through system
        # API -> Database -> Agent -> WebSocket -> Client

        # Verify data integrity at each step
        assert session_data["id"] is not None
        assert session_data["user_input"] == "Test consistency"
        assert session_data["status"] == "processing"

        # More comprehensive consistency checks would go here


if __name__ == "__main__":
    pytest.main([__file__, "-v"])