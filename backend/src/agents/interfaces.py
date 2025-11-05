"""
Agent interfaces and base classes
"""

from abc import ABC, abstractmethod
import json
import re
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

from ..services.glm_api import GLMMessage, get_glm_client
from ..services.glm_response_parser import ParsedAgentResponse, get_response_parser
from ..database.utils import SessionRepository, MessageRepository, SupplementaryInputRepository, ClarifyingQuestionRepository
from ..models.session import Session, AgentMessage, SupplementaryUserInput, ClarifyingQuestion
from ..core.logging import get_logger

logger = get_logger(__name__)


class AgentType(str, Enum):
    """Agent types"""
    PRODUCT_MANAGER = "product_manager"
    TECHNICAL_DEVELOPER = "technical_developer"
    TEAM_LEAD = "team_lead"


class MessageType(str, Enum):
    """Message types"""
    REQUIREMENT = "requirement"
    SOLUTION = "solution"
    TECHNICAL_SOLUTION = "technical_solution"
    REVIEW = "review"
    APPROVAL = "approval"
    REJECTION = "rejection"
    CLARIFICATION = "clarification"
    QUESTION = "question"
    ERROR = "error"


class AgentCapability(BaseModel):
    """Agent capability definition"""
    name: str
    description: str
    examples: List[str] = Field(default_factory=list)
    prompts: Dict[str, str] = Field(default_factory=dict)


class AgentContext(BaseModel):
    """Context provided to agents"""
    session_id: str
    user_requirements: str
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
    current_iteration: int = 0
    max_iterations: int = 5
    user_intervention_count: int = 0
    max_interventions: int = 3
    supplementary_inputs: List[str] = Field(default_factory=list)
    clarifying_questions: List[Dict[str, Any]] = Field(default_factory=list)
    agent_outputs: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Message(BaseModel):
    """Message in conversation history"""
    id: int
    agent_type: AgentType
    content: str
    message_type: MessageType
    timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    """Standardized agent response"""
    content: str
    message_type: MessageType
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    follow_up_questions: List[str] = Field(default_factory=list)
    requires_user_input: bool = False
    is_final_response: bool = False
    clarifying_questions: List[Dict[str, Any]] = Field(default_factory=list)


class BaseAgent(ABC):
    """Base class for all AI agents"""

    def __init__(self, agent_type: AgentType):
        self.agent_type = agent_type
        self.capabilities = self._get_capabilities()
        self.logger = get_logger(f"{self.__class__.__name__}")

        # Service instances
        self.glm_client = None
        self.response_parser = None

        # State
        self.is_initialized = False

    @abstractmethod
    def _get_capabilities(self) -> List[AgentCapability]:
        """Get agent capabilities"""
        pass

    async def initialize(self):
        """Initialize the agent"""
        if self.is_initialized:
            return

        self.glm_client = await get_glm_client()
        self.response_parser = get_response_parser()
        self.is_initialized = True

        self.logger.info(f"Agent {self.agent_type.value} initialized")

    async def cleanup(self):
        """Cleanup agent resources"""
        self.glm_client = None
        self.response_parser = None
        self.is_initialized = False

        self.logger.info(f"Agent {self.agent_type.value} cleaned up")

    async def process(
        self,
        context: AgentContext,
        input_message: Optional[str] = None,
        previous_messages: Optional[List[Dict[str, Any]]] = None
    ) -> AgentResponse:
        """
        Process input and generate response

        Args:
            context: Current conversation context
            input_message: Optional input message to process
            previous_messages: Previous messages in conversation

        Returns:
            Agent response with content and metadata
        """
        if not self.is_initialized:
            await self.initialize()

        # Build conversation context
        messages = self._build_conversation_messages(context, input_message, previous_messages)

        # Generate system prompt
        system_prompt = self._build_system_prompt(context)

        # Add system message to conversation
        full_messages = [GLMMessage(role="system", content=system_prompt)]
        full_messages.extend(messages)

        # Call GLM API
        self.logger.info(
            "Processing request",
            agent_type=self.agent_type.value,
            message_count=len(full_messages),
            context_session_id=context.session_id
        )

        try:
            response = await self.glm_client.chat_completion(
                messages=full_messages,
                model=None,  # Use default model
                temperature=self._get_temperature(context),
                max_tokens=self._get_max_tokens(context)
            )

            # Parse response
            parsed_response = self.response_parser.parse_response(
                response=response,
                agent_type=self.agent_type.value,
                context=None  # Pass None to avoid type mismatch issues
            )

            # Validate response
            validated_response = await self._validate_response(parsed_response, context)

            # Post-process response
            final_response = await self._post_process_response(validated_response, context)

            self.logger.info(
                "Response generated successfully",
                agent_type=self.agent_type.value,
                message_type=final_response.message_type,
                confidence=final_response.confidence,
                content_length=len(final_response.content)
            )

            return final_response

        except Exception as e:
            self.logger.error(
                "Failed to generate response",
                agent_type=self.agent_type.value,
                error=str(e),
                session_id=context.session_id
            )

            # Return error response
            return AgentResponse(
                content=f"I encountered an error while processing your request: {str(e)}",
                message_type=MessageType.REVIEW,
                confidence=0.0,
                metadata={"error": str(e)}
            )

    def _build_conversation_messages(
        self,
        context: AgentContext,
        input_message: Optional[str],
        previous_messages: Optional[List[Dict[str, Any]]]
    ) -> List[GLMMessage]:
        """Build conversation messages for GLM API"""
        messages = []

        # Add conversation history
        if context.conversation_history:
            for msg in context.conversation_history:
                if msg.get("agent_type") == self.agent_type.value:
                    # Skip own messages in history to maintain clarity
                    continue
                messages.append(GLMMessage(
                    role=msg.get("role", "user"),
                    content=msg.get("content", "")
                ))

        # Add previous messages from this method call
        if previous_messages:
            for msg in previous_messages:
                if msg.get("agent_type") == self.agent_type.value:
                    messages.append(GLMMessage(
                        role="assistant",
                        content=msg.get("content", "")
                    ))
                else:
                    messages.append(GLMMessage(
                        role="user",
                        content=msg.get("content", "")
                    ))

        # Add current input message
        if input_message:
            messages.append(GLMMessage(
                role="user",
                content=input_message
            ))

        # Add supplementary inputs if any
        for supplementary_input in context.supplementary_inputs:
            messages.append(GLMMessage(
                role="user",
                content=f"Supplementary input: {supplementary_input}"
            ))

        return messages

    @abstractmethod
    def _build_system_prompt(self, context: AgentContext) -> str:
        """Build system prompt for the agent"""
        pass

    def _get_temperature(self, context: AgentContext) -> float:
        """Get temperature for GLM API based on context"""
        # Higher temperature for creative tasks, lower for analytical tasks
        if self.agent_type == AgentType.PRODUCT_MANAGER:
            return 0.8  # More creative for requirements
        elif self.agent_type == AgentType.TECHNICAL_DEVELOPER:
            return 0.6  # Moderately creative for technical solutions
        else:  # Team Lead
            return 0.4  # More analytical for reviews

    def _get_max_tokens(self, context: AgentContext) -> int:
        """Get max tokens for response based on context"""
        # Set to maximum to ensure GLM-4.6 returns content
        return 65535  # Use near-maximum value to be safe

    async def _validate_response(
        self,
        response: ParsedAgentResponse,
        context: AgentContext
    ) -> ParsedAgentResponse:
        """Validate and potentially correct response"""
        # Basic validation - ensure response is not empty
        if not response.content or not response.content.strip():
            raise ValueError("Response content cannot be empty")

        # Agent-specific validation
        return await self._agent_specific_validation(response, context)

    @abstractmethod
    async def _agent_specific_validation(
        self,
        response: ParsedAgentResponse,
        context: AgentContext
    ) -> ParsedAgentResponse:
        """Agent-specific response validation"""
        pass

    async def _post_process_response(
        self,
        response: ParsedAgentResponse,
        context: AgentContext
    ) -> AgentResponse:
        """Post-process response to standardize format"""
        return AgentResponse(
            content=response.content,
            message_type=response.message_type,
            confidence=response.confidence,
            metadata=response.metadata,
            follow_up_questions=response.metadata.get("follow_up_questions", []),
            requires_user_input=response.metadata.get("requires_user_input", False),
            is_final_response=self._is_final_response(response, context)
        )

    def _is_final_response(
        self,
        response: ParsedAgentResponse,
        context: AgentContext
    ) -> bool:
        """Determine if this is a final response"""
        # Team Lead can give final responses
        if self.agent_type == AgentType.TEAM_LEAD:
            return response.message_type == MessageType.APPROVAL

        # Other agents rarely give final responses
        return False

    def get_agent_info(self) -> Dict[str, Any]:
        """Get agent information"""
        return {
            "type": self.agent_type.value,
            "capabilities": [
                {
                    "name": cap.name,
                    "description": cap.description,
                    "examples": cap.examples
                }
                for cap in self.capabilities
            ],
            "is_initialized": self.is_initialized
        }


class AgentFactory:
    """Factory for creating agent instances"""

    @staticmethod
    def create_agent(agent_type: AgentType) -> BaseAgent:
        """Create an agent instance of the specified type"""
        if agent_type == AgentType.PRODUCT_MANAGER:
            from .product_manager import ProductManagerAgent
            return ProductManagerAgent()
        elif agent_type == AgentType.TECHNICAL_DEVELOPER:
            from .technical_developer import TechnicalDeveloperAgent
            return TechnicalDeveloperAgent()
        elif agent_type == AgentType.TEAM_LEAD:
            from .team_lead import TeamLeadAgent
            return TeamLeadAgent()
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")

    @staticmethod
    def get_available_agents() -> List[AgentType]:
        """Get list of available agent types"""
        return list(AgentType)