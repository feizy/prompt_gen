"""
Technical Developer Agent implementation
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

from .interfaces import (
    BaseAgent,
    AgentContext,
    AgentResponse,
    MessageType,
    AgentType,
    AgentCapability
)
from ..services.glm_response_parser import ParsedAgentResponse
from .message_formatter import MessageFormatter
from ..services.glm_api import GLMApiClient
from ..services.glm_response_parser import GLMResponseParser

logger = logging.getLogger(__name__)


class TechnicalDeveloperAgent(BaseAgent):
    """
    Technical Developer Agent responsible for:
    - Analyzing product requirements from technical perspective
    - Designing technical solutions and architecture
    - Identifying technical constraints and considerations
    - Creating implementation approaches and technical specifications
    """

    def __init__(self, glm_client: Optional[GLMApiClient] = None):
        """Initialize Technical Developer Agent"""
        super().__init__(AgentType.TECHNICAL_DEVELOPER)
        self.agent_name = "Technical Developer"
        self.glm_client = glm_client or GLMApiClient()
        self.response_parser = GLMResponseParser()

        # Technical Developer specific system prompt
        self.system_prompt = """You are a Senior Technical Developer AI agent with expertise in software architecture, system design, and technical implementation.

Your primary responsibilities:
1. Analyze product requirements from a technical perspective
2. Design robust, scalable, and maintainable technical solutions
3. Identify technical constraints, risks, and considerations
4. Create detailed implementation approaches and architecture specifications
5. Ensure solutions follow best practices and industry standards

Your technical expertise includes:
- System architecture and design patterns
- Database design and data modeling
- API design and integration
- Security best practices and implementation
- Performance optimization and scalability
- DevOps and deployment strategies
- Technology stack selection and evaluation

Your approach:
- Always consider scalability, maintainability, and security
- Provide clear, actionable technical specifications
- Identify potential technical risks and mitigation strategies
- Suggest appropriate technology stacks and frameworks
- Consider both immediate and long-term technical needs

Communication style:
- Technical but clear and accessible
- Data-driven and analytical
- Practical and implementation-focused
- Always considering trade-offs and alternatives"""

    def _get_capabilities(self) -> List[AgentCapability]:
        """Get Technical Developer agent capabilities"""
        return [
            AgentCapability(
                name="Technical Analysis",
                description="Analyze requirements for technical feasibility and constraints",
                enabled=True
            ),
            AgentCapability(
                name="Architecture Design",
                description="Design system architecture and technical solutions",
                enabled=True
            ),
            AgentCapability(
                name="Technology Selection",
                description="Recommend appropriate technology stacks and frameworks",
                enabled=True
            ),
            AgentCapability(
                name="Implementation Planning",
                description="Create detailed implementation approaches and technical specifications",
                enabled=True
            ),
            AgentCapability(
                name="Risk Assessment",
                description="Identify technical risks and mitigation strategies",
                enabled=True
            ),
            AgentCapability(
                name="Performance Optimization",
                description="Design solutions with performance and scalability considerations",
                enabled=True
            )
        ]

    async def process(self, context: AgentContext, input_message: Optional[str] = None) -> AgentResponse:
        """
        Process input and generate Technical Developer response

        Args:
            context: Agent context containing conversation history and state
            input_message: Optional direct input message

        Returns:
            AgentResponse with structured technical content and metadata
        """
        try:
            logger.info(f"Technical Developer processing request, iteration {context.current_iteration}")

            # Determine processing strategy based on context
            if context.current_iteration == 0:
                # First iteration - analyze requirements and propose initial technical solution
                response = await self._handle_initial_technical_analysis(context)
            elif context.current_iteration > 0 and context.agent_outputs.get('team_lead'):
                # Subsequent iteration with team lead feedback
                response = await self._handle_feedback_incorporation(context)
            else:
                # Subsequent iteration - refine technical solution
                response = await self._handle_solution_refinement(context)

            # Add response metadata
            response.metadata.update({
                "agent_type": self.agent_type.value,
                "agent_name": self.agent_name,
                "processed_at": datetime.utcnow().isoformat(),
                "iteration": context.current_iteration,
                "capabilities": [cap.name for cap in self._get_capabilities()]
            })

            logger.info(f"Technical Developer completed processing, message type: {response.message_type.value}")
            return response

        except Exception as e:
            logger.error(f"Technical Developer processing failed: {e}")
            return AgentResponse(
                content="I encountered an error while analyzing the technical requirements. Please try again or provide more specific technical details.",
                message_type=MessageType.ERROR,
                confidence=0.1,
                requires_user_input=False,
                clarifying_questions=[{
                    "question_text": "Could you clarify the technical aspects or constraints I should consider?",
                    "question_type": "error_recovery",
                    "options": [],
                    "required": False
                }]
            )

    async def _handle_initial_technical_analysis(self, context: AgentContext) -> AgentResponse:
        """Handle initial technical analysis of requirements"""
        logger.info("Performing initial technical analysis")

        # Format system prompt with context
        formatted_prompt = MessageFormatter.format_system_prompt(
            self.system_prompt,
            context,
            additional_instructions="Focus on analyzing requirements from a technical perspective and proposing initial technical solutions. Consider architecture, technology stack, implementation approach, and potential technical challenges."
        )

        # Get product manager requirements if available
        pm_output = context.agent_outputs.get('product_manager', {})
        requirements_text = pm_output.get('content', context.user_requirements)

        # Create user message for GLM
        user_message = f"""Please analyze the following requirements from a technical perspective and design a comprehensive technical solution:

Product Requirements:
{requirements_text}

Your technical analysis should include:

1. **Technical Requirements Analysis**
   - Identify key technical requirements and constraints
   - Analyze feasibility and complexity
   - Identify technical dependencies and integration points

2. **System Architecture Design**
   - High-level system architecture
   - Key components and their interactions
   - Data flow and system boundaries

3. **Technology Stack Recommendations**
   - Recommended technologies, frameworks, and tools
   - Rationale for technology choices
   - Consideration of scalability and maintenance

4. **Implementation Approach**
   - Development methodology and phases
   - Key implementation steps and milestones
   - Testing and quality assurance strategy

5. **Technical Risks and Mitigation**
   - Identify potential technical risks and challenges
   - Propose mitigation strategies
   - Consider security, performance, and scalability

6. **Database and API Design**
   - Data model recommendations
   - API design principles
   - Integration strategies

Please provide a structured, detailed technical specification that a development team can use to implement this solution."""

        # Call GLM API
        glm_response = await self.glm_client.chat_completion(
            messages=[
                {"role": "system", "content": formatted_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.5,
            max_tokens=2500
        )

        # Parse GLM response
        parsed_response = self.response_parser.parse_response(
            glm_response,
            self.agent_type.value,
            context.conversation_context
        )

        # Format response for web display
        formatted_content = MessageFormatter.format_technical_solution(
            parsed_response.content,
            context
        )

        return AgentResponse(
            content=formatted_content,
            message_type=MessageType.TECHNICAL_SOLUTION,
            confidence=parsed_response.confidence,
            requires_user_input=False,
            clarifying_questions=[],
            metadata={
                "raw_glm_response": parsed_response.raw_response,
                "analysis_type": "initial_technical_analysis",
                "requirements_analyzed": len(requirements_text) if requirements_text else 0
            }
        )

    async def _handle_feedback_incorporation(self, context: AgentContext) -> AgentResponse:
        """Handle incorporation of team lead feedback"""
        logger.info("Incorporating team lead feedback")

        formatted_prompt = MessageFormatter.format_system_prompt(
            self.system_prompt,
            context,
            additional_instructions="Incorporate feedback from the Team Lead to refine and improve the technical solution. Address all concerns and suggestions while maintaining technical integrity."
        )

        # Get previous technical solution and team lead feedback
        previous_tech_output = context.agent_outputs.get('technical_developer', {})
        team_lead_output = context.agent_outputs.get('team_lead', {})

        previous_solution = previous_tech_output.get('content', 'No previous solution available')
        team_lead_feedback = team_lead_output.get('content', 'No team lead feedback available')

        user_message = f"""Please refine your technical solution based on the Team Lead's feedback:

**Previous Technical Solution:**
{previous_solution}

**Team Lead Feedback:**
{team_lead_feedback}

**Current Iteration:** {context.current_iteration}

Your task:
1. Carefully analyze all feedback and suggestions from the Team Lead
2. Address each concern and incorporate valid suggestions
3. Refine the technical solution while maintaining technical integrity
4. Explain any trade-offs or design decisions made
5. Provide an updated, improved technical specification

Focus on:
- Addressing specific concerns raised by the Team Lead
- Improving the overall technical approach
- Maintaining feasibility and best practices
- Clear explanation of changes made and why

Structure your response to clearly show:
1. Summary of Feedback Addressed
2. Changes Made to Technical Solution
3. Updated Technical Specification
4. Rationale for Key Decisions"""

        glm_response = await self.glm_client.chat_completion(
            messages=[
                {"role": "system", "content": formatted_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.4,
            max_tokens=2500
        )

        parsed_response = self.response_parser.parse_response(
            glm_response,
            self.agent_type.value,
            context.conversation_context
        )

        formatted_content = MessageFormatter.format_technical_solution(
            parsed_response.content,
            context
        )

        return AgentResponse(
            content=formatted_content,
            message_type=MessageType.TECHNICAL_SOLUTION,
            confidence=parsed_response.confidence,
            requires_user_input=False,
            clarifying_questions=[],
            metadata={
                "raw_glm_response": parsed_response.raw_response,
                "analysis_type": "feedback_incorporation",
                "iteration": context.current_iteration,
                "feedback_processed": len(team_lead_feedback) if team_lead_feedback else 0
            }
        )

    async def _handle_solution_refinement(self, context: AgentContext) -> AgentResponse:
        """Handle solution refinement in subsequent iterations"""
        logger.info(f"Refining technical solution, iteration {context.current_iteration}")

        formatted_prompt = MessageFormatter.format_system_prompt(
            self.system_prompt,
            context,
            additional_instructions=f"This is iteration {context.current_iteration}. Continuously refine and improve the technical solution based on all available feedback and context."
        )

        # Get previous solution and any new context
        previous_tech_output = context.agent_outputs.get('technical_developer', {})
        previous_solution = previous_tech_output.get('content', 'No previous solution available')

        user_message = f"""Please refine and improve your technical solution:

**Current Iteration:** {context.current_iteration}
**Previous Technical Solution:** {previous_solution[:500]}...

**Additional Context:**
{self._get_refinement_context(context)}

Your refinement should focus on:
1. Technical improvements and optimizations
2. Addressing any unresolved issues or concerns
3. Enhancing scalability, security, or maintainability
4. Incorporating any new technical considerations
5. Moving toward a final, implementation-ready technical specification

Consider:
- Have new requirements or constraints emerged?
- Can the architecture be improved or simplified?
- Are there better technology choices or approaches?
- What technical debt or risks need to be addressed?
- How can the solution be made more robust or efficient?

Provide a refined technical solution that shows clear improvements over previous versions."""

        glm_response = await self.glm_client.chat_completion(
            messages=[
                {"role": "system", "content": formatted_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.4,
            max_tokens=2500
        )

        parsed_response = self.response_parser.parse_response(
            glm_response,
            self.agent_type.value,
            context.conversation_context
        )

        formatted_content = MessageFormatter.format_technical_solution(
            parsed_response.content,
            context
        )

        return AgentResponse(
            content=formatted_content,
            message_type=MessageType.TECHNICAL_SOLUTION,
            confidence=parsed_response.confidence,
            requires_user_input=False,
            clarifying_questions=[],
            metadata={
                "raw_glm_response": parsed_response.raw_response,
                "analysis_type": "solution_refinement",
                "iteration": context.current_iteration
            }
        )

    def _get_refinement_context(self, context: AgentContext) -> str:
        """Get context for solution refinement"""
        context_parts = []

        # Add any supplementary user inputs
        if context.supplementary_inputs:
            context_parts.append("Recent User Inputs:")
            context_parts.extend(f"- {inp}" for inp in context.supplementary_inputs[-2:])

        # Add any clarifying questions that were asked
        if context.clarifying_questions:
            context_parts.append("Recent Technical Questions:")
            context_parts.extend(f"- {q.get('question_text', 'No question text')}"
                               for q in context.clarifying_questions[-2:])

        # Add other agent outputs if available
        if context.agent_outputs:
            if 'product_manager' in context.agent_outputs:
                pm_output = context.agent_outputs['product_manager']
                if pm_output.get('content'):
                    context_parts.append(f"Product Manager Update: {pm_output['content'][:200]}...")

            if 'team_lead' in context.agent_outputs:
                tl_output = context.agent_outputs['team_lead']
                if tl_output.get('content'):
                    context_parts.append(f"Team Lead Feedback: {tl_output['content'][:200]}...")

        return "\n".join(context_parts) if context_parts else "No additional context available."

    def _extract_technical_components(self, content: str) -> List[Dict[str, Any]]:
        """Extract technical components from solution content"""
        components = []

        # Look for component patterns
        component_patterns = [
            r"component:\s*(.+?)(?=\n|$)",
            r"module:\s*(.+?)(?=\n|$)",
            r"service:\s*(.+?)(?=\n|$)",
            r"api:\s*(.+?)(?=\n|$)",
            r"database:\s*(.+?)(?=\n|$)",
        ]

        for pattern in component_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                component_text = match.strip()
                if len(component_text) > 10:
                    components.append({
                        "name": component_text,
                        "type": self._classify_component_type(component_text),
                        "description": self._extract_component_description(component_text, content)
                    })

        return components

    def _classify_component_type(self, component_text: str) -> str:
        """Classify component type based on content"""
        text_lower = component_text.lower()

        if any(word in text_lower for word in ["api", "rest", "graphql", "endpoint"]):
            return "api"
        elif any(word in text_lower for word in ["database", "db", "storage", "data"]):
            return "database"
        elif any(word in text_lower for word in ["service", "microservice", "business logic"]):
            return "service"
        elif any(word in text_lower for word in ["ui", "interface", "frontend", "client"]):
            return "frontend"
        elif any(word in text_lower for word in ["auth", "security", "authentication"]):
            return "security"
        else:
            return "component"

    def _extract_component_description(self, component_text: str, full_content: str) -> str:
        """Extract description for a component"""
        # Look for description patterns near the component mention
        lines = full_content.split('\n')
        description_lines = []

        for i, line in enumerate(lines):
            if component_text.lower() in line.lower():
                # Look at the next few lines for description
                for j in range(i + 1, min(i + 4, len(lines))):
                    next_line = lines[j].strip()
                    if next_line and not next_line.startswith('#') and not next_line.startswith('*'):
                        description_lines.append(next_line)
                    elif next_line.startswith('#') or next_line.startswith('*'):
                        break
                break

        return ' '.join(description_lines) if description_lines else "No description available"

    def _assess_technical_complexity(self, content: str) -> Dict[str, Any]:
        """Assess technical complexity of the solution"""
        complexity_indicators = {
            "architecture_patterns": len(re.findall(r"(microservice|monolith|serverless|event-driven|pub/sub)", content, re.IGNORECASE)),
            "technologies_mentioned": len(re.findall(r"(react|vue|angular|node|python|java|docker|kubernetes)", content, re.IGNORECASE)),
            "security_considerations": len(re.findall(r"(security|auth|encryption|ssl|tls|oauth)", content, re.IGNORECASE)),
            "performance_considerations": len(re.findall(r"(performance|scalability|cache|optimize|load balance)", content, re.IGNORECASE)),
            "integration_points": len(re.findall(r"(api|integration|connect|interface)", content, re.IGNORECASE))
        }

        # Calculate overall complexity score
        total_indicators = sum(complexity_indicators.values())
        complexity_score = min(1.0, total_indicators / 20.0)  # Normalize to 0-1

        return {
            "complexity_score": complexity_score,
            "complexity_level": "high" if complexity_score > 0.7 else "medium" if complexity_score > 0.3 else "low",
            "indicators": complexity_indicators,
            "total_indicators": total_indicators
        }

    def _build_system_prompt(self, context: AgentContext) -> str:
        """Build system prompt for the Technical Developer agent"""
        prompt_parts = [
            self.system_prompt,
            "\n=== CURRENT CONTEXT ===",
            f"Session ID: {context.session_id}",
            f"Iteration: {context.current_iteration + 1} of {context.max_iterations}",
            f"User Requirements: {context.user_requirements}",
        ]

        # Add conversation context if available
        if context.conversation_context and context.conversation_context.message_history:
            recent_messages = context.conversation_context.message_history[-3:]  # Last 3 messages
            prompt_parts.append("\n=== RECENT CONVERSATION ===")
            for msg in recent_messages:
                prompt_parts.append(f"{msg.agent_type}: {msg.content}")

        # Add supplementary inputs if any
        if context.supplementary_inputs:
            prompt_parts.append("\n=== SUPPLEMENTARY USER INPUTS ===")
            for i, input_data in enumerate(context.supplementary_inputs):
                prompt_parts.append(f"Input {i+1}: {input_data.get('content', 'No content')}")

        # Add previous agent outputs if available
        if context.agent_outputs:
            prompt_parts.append("\n=== PREVIOUS AGENT OUTPUTS ===")
            for agent, output in context.agent_outputs.items():
                prompt_parts.append(f"{agent.upper()}: {output.get('content', 'No content')}")

        # Add current task instruction based on iteration
        if context.current_iteration == 0:
            prompt_parts.append("\n=== YOUR TASK ===")
            prompt_parts.append("Analyze the user requirements and provide a comprehensive technical solution design.")
        else:
            prompt_parts.append("\n=== YOUR TASK ===")
            prompt_parts.append("Review the feedback and refine your technical solution accordingly.")

        return "\n".join(prompt_parts)

    async def _agent_specific_validation(
        self,
        response: ParsedAgentResponse,
        context: AgentContext
    ) -> ParsedAgentResponse:
        """Perform Technical Developer specific validation"""
        try:
            # Validate technical completeness
            content_lower = response.content.lower()

            # Check for essential technical components
            required_sections = [
                ('architecture', 'architecture or system design'),
                ('technology', 'technology stack or technologies'),
                ('implementation', 'implementation or development approach'),
                ('data', 'data model or database design')
            ]

            missing_sections = []
            for section, keywords in required_sections:
                if not any(keyword in content_lower for keyword in keywords.split(' or ')):
                    missing_sections.append(section)

            if missing_sections:
                logger.warning(f"Technical Developer response missing sections: {missing_sections}")
                response.metadata['validation_warnings'] = missing_sections

            # Validate technical feasibility
            if len(response.content) < 200:
                raise ValueError("Technical Developer response too brief - provide detailed technical analysis")

            # Add technical-specific metadata
            response.metadata.update({
                'has_architecture': 'architecture' in content_lower or 'system design' in content_lower,
                'has_technology_stack': 'technology' in content_lower or 'stack' in content_lower,
                'has_implementation': 'implementation' in content_lower or 'development' in content_lower,
                'complexity_score': self._assess_technical_complexity(response.content),
                'validated_at': datetime.utcnow().isoformat()
            })

            return response

        except Exception as e:
            logger.error(f"Technical Developer validation failed: {e}")
            raise ValueError(f"Technical Developer validation failed: {str(e)}")

    async def get_status(self) -> Dict[str, Any]:
        """Get Technical Developer agent status"""
        return {
            "agent_type": self.agent_type.value,
            "agent_name": self.agent_name,
            "status": "active",
            "capabilities": [cap.model_dump() for cap in self._get_capabilities()],
            "glm_client_connected": self.glm_client is not None,
            "response_parser_ready": self.response_parser is not None
        }