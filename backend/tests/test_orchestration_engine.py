"""
Unit tests for Agent Orchestration Engine
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone
import uuid

from backend.src.agents.orchestration_engine import (
    AgentOrchestrationEngine,
    OrchestrationState,
    AgentTask,
    TaskStatus,
    AgentContext
)
from backend.src.agents.interfaces import (
    BaseAgent,
    AgentResponse,
    MessageType,
    AgentType
)
from backend.src.agents.exceptions import (
    OrchestrationError,
    AgentError,
    ValidationError
)
from backend.src.repositories.session_repository import SessionRepository
from backend.src.repositories.message_repository import MessageRepository
from backend.src.services.glm_api import GLMClient


class MockAgent(BaseAgent):
    """Mock agent for testing"""

    def __init__(self, agent_type: AgentType, response_content: str = None):
        self.agent_type = agent_type
        self.response_content = response_content or f"Response from {agent_type}"
        self.processed_requests = []

    async def process_request(self, request: str, context: AgentContext) -> AgentResponse:
        self.processed_requests.append((request, context))

        return AgentResponse(
            content=self.response_content,
            message_type=MessageType.REQUIREMENT if self.agent_type == AgentType.PRODUCT_MANAGER else MessageType.TECHNICAL_SOLUTION,
            confidence=0.9,
            metadata={"agent_type": self.agent_type.value}
        )

    async def validate_response(self, response: str) -> bool:
        return len(response) > 0

    @property
    def name(self) -> str:
        return f"Mock {self.agent_type.value}"

    @property
    def description(self) -> str:
        return f"Mock agent for testing {self.agent_type.value}"


class TestAgentOrchestrationEngine:
    """Test cases for Agent Orchestration Engine"""

    @pytest.fixture
    def mock_glm_client(self):
        """Mock GLM client"""
        client = Mock(spec=GLMClient)
        client.complete = AsyncMock()
        return client

    @pytest.fixture
    def mock_session_repo(self):
        """Mock session repository"""
        repo = Mock(spec=SessionRepository)
        repo.get_by_id = AsyncMock()
        repo.update = AsyncMock()
        return repo

    @pytest.fixture
    def mock_message_repo(self):
        """Mock message repository"""
        repo = Mock(spec=MessageRepository)
        repo.create = AsyncMock()
        repo.get_by_session_id = AsyncMock()
        return repo

    @pytest.fixture
    def mock_agents(self):
        """Mock agents for testing"""
        return {
            AgentType.PRODUCT_MANAGER: MockAgent(AgentType.PRODUCT_MANAGER, "Product requirements analysis"),
            AgentType.TECHNICAL_DEVELOPER: MockAgent(AgentType.TECHNICAL_DEVELOPER, "Technical solution design"),
            AgentType.TEAM_LEAD: MockAgent(AgentType.TEAM_LEAD, "Final review and approval")
        }

    @pytest.fixture
    def engine(self, mock_glm_client, mock_session_repo, mock_message_repo, mock_agents):
        """Create orchestration engine instance for testing"""
        return AgentOrchestrationEngine(
            glm_client=mock_glm_client,
            session_repo=mock_session_repo,
            message_repo=mock_message_repo,
            agents=mock_agents
        )

    @pytest.fixture
    def sample_session(self):
        """Sample session data"""
        return {
            "id": str(uuid.uuid4()),
            "user_input": "Create a prompt for a customer service chatbot",
            "status": "active",
            "iteration_count": 1,
            "user_intervention_count": 0
        }

    @pytest.mark.asyncio
    async def test_engine_initialization(self, engine):
        """Test engine initialization"""
        assert engine.glm_client is not None
        assert engine.session_repo is not None
        assert engine.message_repo is not None
        assert len(engine.agents) == 3
        assert AgentType.PRODUCT_MANAGER in engine.agents
        assert AgentType.TECHNICAL_DEVELOPER in engine.agents
        assert AgentType.TEAM_LEAD in engine.agents

    @pytest.mark.asyncio
    async def test_start_new_session_success(self, engine, sample_session, mock_session_repo):
        """Test successful session start"""
        mock_session_repo.get_by_id.return_value = sample_session
        mock_session_repo.update.return_value = {"status": "processing"}

        state = await engine.start_session(sample_session["id"], sample_session["user_input"])

        assert state.session_id == sample_session["id"]
        assert state.user_input == sample_session["user_input"]
        assert state.current_step == "product_manager_analysis"
        assert state.status == "processing"
        assert len(state.tasks) == 1
        assert state.tasks[0].agent_type == AgentType.PRODUCT_MANAGER

    @pytest.mark.asyncio
    async def test_start_session_not_found(self, engine, mock_session_repo):
        """Test session start with non-existent session"""
        mock_session_repo.get_by_id.return_value = None

        with pytest.raises(OrchestrationError) as exc_info:
            await engine.start_session("non-existent-id", "test input")

        assert "Session not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_process_current_step_success(self, engine, sample_session):
        """Test successful processing of current step"""
        # Setup state
        state = OrchestrationState(
            session_id=sample_session["id"],
            user_input=sample_session["user_input"],
            current_step="product_manager_analysis",
            status="processing",
            tasks=[
                AgentTask(
                    id=str(uuid.uuid4()),
                    agent_type=AgentType.PRODUCT_MANAGER,
                    status=TaskStatus.PENDING,
                    created_at=datetime.now(timezone.utc)
                )
            ]
        )

        engine.states[sample_session["id"]] = state

        # Mock repositories
        engine.message_repo.create = AsyncMock(return_value={"id": str(uuid.uuid4())})

        # Process step
        new_state = await engine.process_current_step(sample_session["id"])

        assert new_state.current_step == "technical_development"
        assert len(new_state.tasks) == 2
        assert new_state.tasks[0].status == TaskStatus.COMPLETED
        assert new_state.tasks[1].agent_type == AgentType.TECHNICAL_DEVELOPER

        # Verify agent was called
        product_manager = engine.agents[AgentType.PRODUCT_MANAGER]
        assert len(product_manager.processed_requests) == 1

    @pytest.mark.asyncio
    async def test_process_all_agent_collaboration(self, engine, sample_session):
        """Test full agent collaboration workflow"""
        # Mock repositories
        engine.message_repo.create = AsyncMock(return_value={"id": str(uuid.uuid4())})

        # Start session
        state = await engine.start_session(sample_session["id"], sample_session["user_input"])

        # Process all steps
        steps_processed = []
        while state.status == "processing":
            state = await engine.process_current_step(sample_session["id"])
            steps_processed.append(state.current_step)

        # Verify all agents were called in correct order
        expected_steps = [
            "technical_development",
            "team_lead_review",
            "completed"
        ]
        assert steps_processed == expected_steps

        # Verify all agents processed requests
        for agent in engine.agents.values():
            assert len(agent.processed_requests) == 1

        # Verify final state
        assert state.status == "completed"
        assert state.current_step == "completed"

    @pytest.mark.asyncio
    async def test_handle_user_input(self, engine, sample_session):
        """Test handling user input during processing"""
        # Setup state in waiting state
        state = OrchestrationState(
            session_id=sample_session["id"],
            user_input=sample_session["user_input"],
            current_step="waiting_for_user_input",
            status="waiting_for_user_input",
            context={"pending_question": "Need more details"}
        )

        engine.states[sample_session["id"]] = state

        # Handle user input
        new_state = await engine.handle_user_input(
            sample_session["id"],
            "Here are the additional details you requested"
        )

        assert new_state.status == "processing"
        assert "additional_details" in new_state.context
        assert new_state.context["additional_details"] == "Here are the additional details you requested"

    @pytest.mark.asyncio
    async def test_continue_without_input(self, engine, sample_session):
        """Test continuing without user input"""
        # Setup state in waiting state
        state = OrchestrationState(
            session_id=sample_session["id"],
            user_input=sample_session["user_input"],
            current_step="waiting_for_user_input",
            status="waiting_for_user_input"
        )

        engine.states[sample_session["id"]] = state

        # Continue without input
        new_state = await engine.continue_without_input(sample_session["id"])

        assert new_state.status == "processing"
        assert new_state.context.get("force_continue") is True

    @pytest.mark.asyncio
    async def test_agent_error_handling(self, engine, sample_session):
        """Test handling agent processing errors"""
        # Create agent that raises an error
        faulty_agent = Mock()
        faulty_agent.process_request = AsyncMock(side_effect=AgentError("Agent processing failed"))

        engine.agents[AgentType.PRODUCT_MANAGER] = faulty_agent

        # Start session
        state = await engine.start_session(sample_session["id"], sample_session["user_input"])

        # Process step - should handle agent error gracefully
        with pytest.raises(OrchestrationError) as exc_info:
            await engine.process_current_step(sample_session["id"])

        assert "Agent processing failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_task_creation(self, engine):
        """Test task creation functionality"""
        task = engine._create_task(AgentType.PRODUCT_MANAGER, "Analyze requirements")

        assert task.agent_type == AgentType.PRODUCT_MANAGER
        assert task.status == TaskStatus.PENDING
        assert task.description == "Analyze requirements"
        assert isinstance(task.id, str)
        assert isinstance(task.created_at, datetime)

    @pytest.mark.asyncio
    async def test_context_building(self, engine):
        """Test agent context building"""
        # Setup state with some history
        state = OrchestrationState(
            session_id="test-id",
            user_input="Create a chatbot prompt",
            current_step="technical_development",
            status="processing",
            completed_steps=["product_manager_analysis"],
            task_history=[{"agent": "product_manager", "result": "Requirements analyzed"}]
        )

        context = engine._build_agent_context(AgentType.TECHNICAL_DEVELOPER, state)

        assert context.session_id == "test-id"
        assert context.user_input == "Create a chatbot prompt"
        assert context.previous_step == "product_manager_analysis"
        assert len(context.completed_steps) == 1
        assert "Requirements analyzed" in str(context.task_history)

    def test_get_next_step(self, engine):
        """Test next step determination logic"""
        # Test product manager -> technical developer
        next_step = engine._get_next_step("product_manager_analysis")
        assert next_step == "technical_development"

        # Test technical developer -> team lead
        next_step = engine._get_next_step("technical_development")
        assert next_step == "team_lead_review"

        # Test team lead -> completed
        next_step = engine._get_next_step("team_lead_review")
        assert next_step == "completed"

        # Test unknown step
        with pytest.raises(OrchestrationError):
            engine._get_next_step("unknown_step")

    @pytest.mark.asyncio
    async def test_get_session_state(self, engine, sample_session):
        """Test retrieving session state"""
        # Test non-existent state
        state = await engine.get_session_state("non-existent")
        assert state is None

        # Create and retrieve state
        engine.states[sample_session["id"]] = OrchestrationState(
            session_id=sample_session["id"],
            user_input="test",
            current_step="processing",
            status="processing"
        )

        state = await engine.get_session_state(sample_session["id"])
        assert state is not None
        assert state.session_id == sample_session["id"]

    @pytest.mark.asyncio
    async def test_cancel_session(self, engine, sample_session):
        """Test session cancellation"""
        # Setup active session
        engine.states[sample_session["id"]] = OrchestrationState(
            session_id=sample_session["id"],
            user_input="test",
            current_step="processing",
            status="processing"
        )

        # Mock session repository update
        engine.session_repo.update = AsyncMock(return_value={"status": "cancelled"})

        # Cancel session
        state = await engine.cancel_session(sample_session["id"])

        assert state.status == "cancelled"
        assert sample_session["id"] not in engine.states

    @pytest.mark.asyncio
    async def test_validate_agent_response(self, engine):
        """Test agent response validation"""
        # Test valid response
        response = AgentResponse(
            content="Valid response content",
            message_type=MessageType.REQUIREMENT,
            confidence=0.8
        )
        assert engine._validate_agent_response(response) is True

        # Test invalid response (empty content)
        invalid_response = AgentResponse(
            content="",
            message_type=MessageType.REQUIREMENT,
            confidence=0.8
        )
        assert engine._validate_agent_response(invalid_response) is False

        # Test invalid response (low confidence)
        low_confidence_response = AgentResponse(
            content="Content",
            message_type=MessageType.REQUIREMENT,
            confidence=0.1
        )
        assert engine._validate_agent_response(low_confidence_response) is False

    def test_agent_task_status_transitions(self):
        """Test agent task status transitions"""
        task = AgentTask(
            id=str(uuid.uuid4()),
            agent_type=AgentType.PRODUCT_MANAGER,
            status=TaskStatus.PENDING,
            created_at=datetime.now(timezone.utc)
        )

        # Test transition to in_progress
        task.mark_in_progress()
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.started_at is not None

        # Test transition to completed
        task.mark_completed("Task completed successfully")
        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None
        assert task.result == "Task completed successfully"

        # Test transition to failed
        task.mark_failed("Task failed due to error")
        assert task.status == TaskStatus.FAILED
        assert task.failed_at is not None
        assert task.error == "Task failed due to error"

    @pytest.mark.asyncio
    async def test_concurrent_session_handling(self, engine, mock_session_repo):
        """Test handling multiple concurrent sessions"""
        sessions = [
            {"id": str(uuid.uuid4()), "user_input": f"Request {i}", "status": "active"}
            for i in range(3)
        ]

        mock_session_repo.get_by_id.side_effect = sessions

        # Start multiple sessions concurrently
        import asyncio
        tasks = [
            engine.start_session(session["id"], session["user_input"])
            for session in sessions
        ]

        states = await asyncio.gather(*tasks)

        # Verify all sessions were started
        assert len(states) == 3
        for i, state in enumerate(states):
            assert state.session_id == sessions[i]["id"]
            assert state.user_input == sessions[i]["user_input"]
            assert state.status == "processing"

        # Verify states are tracked separately
        assert len(engine.states) == 3
        for session in sessions:
            assert session["id"] in engine.states


if __name__ == "__main__":
    pytest.main([__file__])