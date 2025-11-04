"""
Agent Orchestration Engine implementation
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from enum import Enum

from .interfaces import (
    AgentContext,
    AgentResponse,
    MessageType,
    AgentType
)
from .product_manager import ProductManagerAgent
from .technical_developer import TechnicalDeveloperAgent
from .team_lead import TeamLeadAgent
from .conversation_manager import ConversationManager
from .state_tracker import AgentStateTracker
from ..services.glm_api import GLMApiClient

logger = logging.getLogger(__name__)


class OrchestrationState(Enum):
    """Orchestration states"""
    INITIALIZING = "initializing"
    REQUIREMENTS_ANALYSIS = "requirements_analysis"
    TECHNICAL_DESIGN = "technical_design"
    TEAM_LEAD_REVIEW = "team_lead_review"
    FEEDBACK_PROCESSING = "feedback_processing"
    FINAL_APPROVAL = "final_approval"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentOrchestrationEngine:
    """
    Main orchestration engine that coordinates the three AI agents
    in their collaborative process of generating LLM prompts.
    """

    def __init__(self, glm_client: Optional[GLMApiClient] = None):
        """Initialize the orchestration engine"""
        self.glm_client = glm_client or GLMApiClient()

        # Initialize agents
        self.product_manager = ProductManagerAgent()
        self.technical_developer = TechnicalDeveloperAgent(self.glm_client)
        self.team_lead = TeamLeadAgent(self.glm_client)

        # Initialize support components
        self.conversation_manager = None  # TODO: Initialize when session_id is available
        self.state_tracker = None  # TODO: Initialize when session_id is available

        # Orchestration state
        self.current_state = OrchestrationState.INITIALIZING
        self.current_iteration = 0
        self.max_iterations = 5  # Maximum iterations before forcing completion

        # Session tracking
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

    async def start_prompt_generation_session(
        self,
        user_requirements: str,
        session_id: Optional[str] = None,
        max_iterations: int = 5
    ) -> Dict[str, Any]:
        """
        Start a new prompt generation session

        Args:
            user_requirements: Initial user requirements
            session_id: Optional session ID (will generate if not provided)
            max_iterations: Maximum iterations for the collaborative process

        Returns:
            Session information and initial response
        """
        try:
            # Generate session ID if not provided
            if not session_id:
                session_id = f"session_{datetime.utcnow().timestamp()}"

            logger.info(f"Starting prompt generation session: {session_id}")

            # Initialize session
            session_data = {
                "session_id": session_id,
                "user_requirements": user_requirements,
                "max_iterations": max_iterations,
                "current_iteration": 0,
                "state": OrchestrationState.INITIALIZING.value,
                "created_at": datetime.utcnow().isoformat(),
                "agent_outputs": {},
                "conversation_history": [],
                "final_prompt": None,
                "status": "active"
            }

            self.active_sessions[session_id] = session_data

            # Create initial agent context
            context = AgentContext(
                session_id=session_id,
                user_requirements=user_requirements,
                current_iteration=0,
                max_iterations=max_iterations,
                conversation_history=[]
            )

            # Start with Product Manager
            self.current_state = OrchestrationState.REQUIREMENTS_ANALYSIS
            session_data["state"] = self.current_state.value

            # Get initial response from Product Manager
            pm_response = await self.product_manager.process(context)

            # Store response and update context
            session_data["agent_outputs"]["product_manager"] = {
                "content": pm_response.content,
                "message_type": pm_response.message_type.value,
                "confidence": pm_response.confidence,
                "clarifying_questions": pm_response.clarifying_questions,
                "timestamp": datetime.utcnow().isoformat()
            }

            # Add to conversation history
            self._add_to_conversation_history(
                session_id,
                AgentType.PRODUCT_MANAGER,
                pm_response
            )

            # Update session state
            if pm_response.requires_user_input:
                session_data["status"] = "waiting_for_user_input"
                next_state = OrchestrationState.REQUIREMENTS_ANALYSIS
            else:
                next_state = OrchestrationState.TECHNICAL_DESIGN

            session_data["state"] = next_state.value

            logger.info(f"Session {session_id} initialized successfully")

            return {
                "session_id": session_id,
                "status": session_data["status"],
                "current_iteration": 0,
                "max_iterations": max_iterations,
                "agent_responses": {
                    "product_manager": self._format_agent_response(pm_response)
                },
                "next_agent": self._get_next_agent_name(next_state),
                "requires_user_input": pm_response.requires_user_input,
                "clarifying_questions": pm_response.clarifying_questions
            }

        except Exception as e:
            logger.error(f"Failed to start session: {e}")
            raise Exception(f"Session initialization failed: {str(e)}")

    async def process_user_input(
        self,
        session_id: str,
        user_input: str,
        supplementary_inputs: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Process user input and continue the collaborative process

        Args:
            session_id: Session identifier
            user_input: User's response to clarifying questions
            supplementary_inputs: Additional user inputs

        Returns:
            Updated session information and agent responses
        """
        try:
            if session_id not in self.active_sessions:
                raise Exception(f"Session {session_id} not found")

            session_data = self.active_sessions[session_id]
            logger.info(f"Processing user input for session: {session_id}")

            # Update session with user input
            if supplementary_inputs:
                session_data.setdefault("supplementary_inputs", []).extend(supplementary_inputs)
            else:
                session_data.setdefault("supplementary_inputs", []).append(user_input)

            # Create updated context
            context = self._create_agent_context(session_data)

            # Determine which agent should process based on current state
            next_agent = self._determine_next_agent(session_data)

            if not next_agent:
                return await self._finalize_session(session_id)

            # Process with the appropriate agent
            agent_response = await next_agent.process(context)

            # Store response
            agent_name = self._get_agent_name(next_agent)
            session_data["agent_outputs"][agent_name] = {
                "content": agent_response.content,
                "message_type": agent_response.message_type.value,
                "confidence": agent_response.confidence,
                "clarifying_questions": agent_response.clarifying_questions,
                "timestamp": datetime.utcnow().isoformat()
            }

            # Add to conversation history
            self._add_to_conversation_history(
                session_id,
                next_agent.agent_type,
                agent_response
            )

            # Determine next state
            next_state = self._determine_next_state(session_data, agent_response)
            session_data["state"] = next_state.value

            # Update iteration count if needed
            if agent_response.message_type in [MessageType.APPROVAL]:
                session_data["current_iteration"] += 1

            # Check if we need more user input
            if agent_response.requires_user_input:
                session_data["status"] = "waiting_for_user_input"
            else:
                session_data["status"] = "processing"

            # Prepare response
            response_data = {
                "session_id": session_id,
                "status": session_data["status"],
                "current_iteration": session_data["current_iteration"],
                "max_iterations": session_data["max_iterations"],
                "agent_responses": {
                    agent_name: self._format_agent_response(agent_response)
                },
                "next_agent": self._get_next_agent_name(next_state) if next_state != OrchestrationState.COMPLETED else None,
                "requires_user_input": agent_response.requires_user_input,
                "clarifying_questions": agent_response.clarifying_questions,
                "final_prompt": session_data.get("final_prompt"),
                "completed": next_state == OrchestrationState.COMPLETED
            }

            # Check if session is completed
            if next_state == OrchestrationState.COMPLETED:
                response_data.update(await self._finalize_session(session_id))

            return response_data

        except Exception as e:
            logger.error(f"Failed to process user input for session {session_id}: {e}")
            session_data = self.active_sessions.get(session_id, {})
            session_data["status"] = "failed"
            session_data["error"] = str(e)
            raise Exception(f"Failed to process user input: {str(e)}")

    async def continue_without_input(self, session_id: str) -> Dict[str, Any]:
        """
        Continue the process without additional user input
        (when agents have enough information to proceed)

        Args:
            session_id: Session identifier

        Returns:
            Updated session information and agent responses
        """
        try:
            if session_id not in self.active_sessions:
                raise Exception(f"Session {session_id} not found")

            session_data = self.active_sessions[session_id]
            logger.info(f"Continuing session without user input: {session_id}")

            # Create context
            context = self._create_agent_context(session_data)

            # Determine next agent
            next_agent = self._determine_next_agent(session_data)

            if not next_agent:
                return await self._finalize_session(session_id)

            # Process with the agent
            agent_response = await next_agent.process(context)

            # Store response
            agent_name = self._get_agent_name(next_agent)
            session_data["agent_outputs"][agent_name] = {
                "content": agent_response.content,
                "message_type": agent_response.message_type.value,
                "confidence": agent_response.confidence,
                "clarifying_questions": agent_response.clarifying_questions,
                "timestamp": datetime.utcnow().isoformat()
            }

            # Add to conversation history
            self._add_to_conversation_history(
                session_id,
                next_agent.agent_type,
                agent_response
            )

            # Determine next state
            next_state = self._determine_next_state(session_data, agent_response)
            session_data["state"] = next_state.value

            # Update status
            if agent_response.requires_user_input:
                session_data["status"] = "waiting_for_user_input"
            elif next_state == OrchestrationState.COMPLETED:
                session_data["status"] = "completed"
            else:
                session_data["status"] = "processing"

            # Prepare response
            response_data = {
                "session_id": session_id,
                "status": session_data["status"],
                "current_iteration": session_data["current_iteration"],
                "max_iterations": session_data["max_iterations"],
                "agent_responses": {
                    agent_name: self._format_agent_response(agent_response)
                },
                "next_agent": self._get_next_agent_name(next_state) if next_state != OrchestrationState.COMPLETED else None,
                "requires_user_input": agent_response.requires_user_input,
                "clarifying_questions": agent_response.clarifying_questions,
                "completed": next_state == OrchestrationState.COMPLETED
            }

            # Finalize if completed
            if next_state == OrchestrationState.COMPLETED:
                response_data.update(await self._finalize_session(session_id))

            return response_data

        except Exception as e:
            logger.error(f"Failed to continue session {session_id}: {e}")
            raise Exception(f"Failed to continue session: {str(e)}")

    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get current status of a session"""
        if session_id not in self.active_sessions:
            raise Exception(f"Session {session_id} not found")

        session_data = self.active_sessions[session_id]

        return {
            "session_id": session_id,
            "status": session_data["status"],
            "state": session_data["state"],
            "current_iteration": session_data["current_iteration"],
            "max_iterations": session_data["max_iterations"],
            "created_at": session_data["created_at"],
            "agent_outputs_count": len(session_data["agent_outputs"]),
            "conversation_history_length": len(session_data["conversation_history"]),
            "final_prompt_available": session_data.get("final_prompt") is not None,
            "last_activity": self._get_last_activity_time(session_data)
        }

    async def get_conversation_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get conversation history for a session"""
        if session_id not in self.active_sessions:
            raise Exception(f"Session {session_id} not found")

        session_data = self.active_sessions[session_id]
        return session_data.get("conversation_history", [])

    def _create_agent_context(self, session_data: Dict[str, Any]) -> AgentContext:
        """Create AgentContext from session data"""
        return AgentContext(
            session_id=session_data["session_id"],
            user_requirements=session_data["user_requirements"],
            current_iteration=session_data["current_iteration"],
            max_iterations=session_data["max_iterations"],
            supplementary_inputs=session_data.get("supplementary_inputs", []),
            clarifying_questions=session_data.get("pending_questions", []),
            agent_outputs=session_data.get("agent_outputs", {}),
            conversation_history=session_data.get("conversation_history", [])
        )

    def _determine_next_agent(self, session_data: Dict[str, Any]) -> Optional[object]:
        """Determine which agent should process next"""
        state = session_data["state"]

        if state == OrchestrationState.REQUIREMENTS_ANALYSIS.value:
            return self.product_manager
        elif state == OrchestrationState.TECHNICAL_DESIGN.value:
            return self.technical_developer
        elif state == OrchestrationState.TEAM_LEAD_REVIEW.value:
            return self.team_lead
        elif state == OrchestrationState.FEEDBACK_PROCESSING.value:
            # Determine which agent needs to address feedback
            last_feedback = self._get_last_team_lead_feedback(session_data)
            if last_feedback and "requirements" in last_feedback.lower():
                return self.product_manager
            else:
                return self.technical_developer
        else:
            return None

    def _determine_next_state(
        self,
        session_data: Dict[str, Any],
        agent_response: AgentResponse
    ) -> OrchestrationState:
        """Determine the next orchestration state"""
        current_state = OrchestrationState(session_data["state"])
        current_iteration = session_data["current_iteration"]

        # Handle approval
        if agent_response.message_type == MessageType.APPROVAL:
            if current_state == OrchestrationState.TEAM_LEAD_REVIEW:
                return OrchestrationState.COMPLETED
            else:
                return OrchestrationState.TEAM_LEAD_REVIEW

        # Handle rejection/feedback
        elif agent_response.message_type == MessageType.REJECTION:
            return OrchestrationState.FEEDBACK_PROCESSING

        # Handle questions
        elif agent_response.message_type == MessageType.QUESTION:
            return current_state  # Stay in current state

        # Handle normal progression
        else:
            if current_state == OrchestrationState.REQUIREMENTS_ANALYSIS:
                return OrchestrationState.TECHNICAL_DESIGN
            elif current_state == OrchestrationState.TECHNICAL_DESIGN:
                return OrchestrationState.TEAM_LEAD_REVIEW
            elif current_state == OrchestrationState.FEEDBACK_PROCESSING:
                # Check if we've reached max iterations
                if current_iteration >= session_data["max_iterations"] - 1:
                    return OrchestrationState.FINAL_APPROVAL
                else:
                    return OrchestrationState.TEAM_LEAD_REVIEW
            else:
                return current_state

    def _add_to_conversation_history(
        self,
        session_id: str,
        agent_type: AgentType,
        response: AgentResponse
    ):
        """Add message to conversation history"""
        if session_id not in self.active_sessions:
            return

        session_data = self.active_sessions[session_id]

        message = Message(
            id=len(session_data["conversation_history"]) + 1,
            agent_type=agent_type,
            content=response.content,
            message_type=response.message_type,
            timestamp=datetime.utcnow(),
            metadata=response.metadata
        )

        session_data["conversation_history"].append(message.model_dump())

    def _format_agent_response(self, response: AgentResponse) -> Dict[str, Any]:
        """Format agent response for API response"""
        return {
            "content": response.content,
            "message_type": response.message_type.value,
            "confidence": response.confidence,
            "requires_user_input": response.requires_user_input,
            "clarifying_questions": response.clarifying_questions,
            "metadata": response.metadata
        }

    def _get_agent_name(self, agent: object) -> str:
        """Get string name of agent"""
        if isinstance(agent, ProductManagerAgent):
            return "product_manager"
        elif isinstance(agent, TechnicalDeveloperAgent):
            return "technical_developer"
        elif isinstance(agent, TeamLeadAgent):
            return "team_lead"
        else:
            return "unknown"

    def _get_next_agent_name(self, state: OrchestrationState) -> Optional[str]:
        """Get the name of the next agent to process"""
        state_to_agent = {
            OrchestrationState.REQUIREMENTS_ANALYSIS: "product_manager",
            OrchestrationState.TECHNICAL_DESIGN: "technical_developer",
            OrchestrationState.TEAM_LEAD_REVIEW: "team_lead",
            OrchestrationState.FEEDBACK_PROCESSING: "depends_on_feedback",
            OrchestrationState.FINAL_APPROVAL: "team_lead"
        }
        return state_to_agent.get(state)

    def _get_last_team_lead_feedback(self, session_data: Dict[str, Any]) -> Optional[str]:
        """Get the last feedback from team lead"""
        team_lead_output = session_data.get("agent_outputs", {}).get("team_lead")
        if team_lead_output:
            return team_lead_output.get("content")
        return None

    def _get_last_activity_time(self, session_data: Dict[str, Any]) -> str:
        """Get the last activity time for the session"""
        # Check agent outputs for timestamps
        latest_time = session_data.get("created_at")

        for agent_output in session_data.get("agent_outputs", {}).values():
            output_time = agent_output.get("timestamp")
            if output_time and output_time > latest_time:
                latest_time = output_time

        return latest_time

    async def _finalize_session(self, session_id: str) -> Dict[str, Any]:
        """Finalize a session and extract the final prompt"""
        session_data = self.active_sessions[session_id]
        logger.info(f"Finalizing session: {session_id}")

        # Extract final prompt from team lead approval
        team_lead_output = session_data.get("agent_outputs", {}).get("team_lead", {})

        # Try to extract the final prompt from the approval message
        final_prompt = self._extract_final_prompt(team_lead_output.get("content", ""))

        # Update session
        session_data["status"] = "completed"
        session_data["state"] = OrchestrationState.COMPLETED.value
        session_data["final_prompt"] = final_prompt
        session_data["completed_at"] = datetime.utcnow().isoformat()

        return {
            "final_prompt": final_prompt,
            "completed_at": session_data["completed_at"],
            "total_iterations": session_data["current_iteration"] + 1
        }

    def _extract_final_prompt(self, approval_content: str) -> str:
        """Extract the final prompt from team lead approval content"""
        # Look for "Final Prompt" section
        final_prompt_match = re.search(
            r'#?\s*Final Prompt\s*:?\s*\n?(.*?)(?=\n#|\n\n|$)',
            approval_content,
            re.IGNORECASE | re.DOTALL
        )

        if final_prompt_match:
            return final_prompt_match.group(1).strip()

        # If no explicit final prompt section, look for the main approval content
        # Remove approval headers and extract the core content
        content_lines = approval_content.split('\n')
        core_content_lines = []

        skip_headers = ['#', 'approval', 'approved', '✅', 'summary']

        for line in content_lines:
            line = line.strip()
            if line and not any(header in line.lower() for header in skip_headers):
                core_content_lines.append(line)

        return '\n'.join(core_content_lines) if core_content_lines else approval_content

    async def cleanup_session(self, session_id: str) -> bool:
        """Clean up a completed session"""
        if session_id in self.active_sessions:
            session_data = self.active_sessions[session_id]
            if session_data["status"] in ["completed", "failed"]:
                del self.active_sessions[session_id]
                logger.info(f"Cleaned up session: {session_id}")
                return True
        return False

    def get_active_sessions_count(self) -> int:
        """Get the number of active sessions"""
        return len(self.active_sessions)

    def get_engine_status(self) -> Dict[str, Any]:
        """Get the orchestration engine status"""
        return {
            "status": "active",
            "active_sessions": len(self.active_sessions),
            "agents_initialized": True,
            "glm_client_connected": self.glm_client is not None,
            "supported_states": [state.value for state in OrchestrationState],
            "max_iterations_per_session": self.max_iterations
        }