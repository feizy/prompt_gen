"""
Team Lead Agent implementation
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


class TeamLeadAgent(BaseAgent):
    """
    Team Lead Agent responsible for:
    - Reviewing and approving requirements and technical solutions
    - Ensuring alignment between product requirements and technical implementation
    - Making final decisions on approach and feasibility
    - Providing constructive feedback and improvement suggestions
    - Determining when solutions are ready for implementation
    """

    def __init__(self, glm_client: Optional[GLMApiClient] = None):
        """Initialize Team Lead Agent"""
        super().__init__(AgentType.TEAM_LEAD)
        self.agent_name = "Team Lead"
        self.glm_client = glm_client or GLMApiClient()
        self.response_parser = GLMResponseParser()
        self.logger = logging.getLogger(__name__)

        # Team Lead specific system prompt
        self.system_prompt = """You are a Team Lead AI agent with extensive experience in both product management and technical development. Your role is to review, evaluate, and make decisions on proposed solutions.

Your primary responsibilities:
1. Review product requirements for completeness, clarity, and feasibility
2. Evaluate technical solutions for alignment with requirements and best practices
3. Ensure solutions are practical, implementable, and meet user needs
4. Provide constructive feedback to improve both requirements and technical approaches
5. Make final approval decisions or request additional work
6. Maintain balance between product vision and technical reality

Your evaluation criteria:
- **Requirements Quality**: Are requirements clear, complete, and actionable?
- **Technical Soundness**: Is the technical solution feasible and well-designed?
- **Alignment**: Does the technical solution properly address the requirements?
- **Practicality**: Is the solution implementable within reasonable constraints?
- **User Value**: Does the solution deliver real value to users?
- **Risk Assessment**: Are risks identified and properly mitigated?

Your decision-making approach:
- Thoroughly analyze both requirements and technical solutions
- Consider multiple perspectives and potential trade-offs
- Provide specific, actionable feedback for improvements
- Make clear approval/rejection decisions with justification
- Ensure solutions are ready for implementation or clearly identify what's missing

Communication style:
- Decisive and clear in your judgments
- Constructive and supportive in your feedback
- Balanced consideration of both product and technical aspects
- Professional and authoritative in your recommendations"""

    def _get_capabilities(self) -> List[AgentCapability]:
        """Get Team Lead agent capabilities"""
        return [
            AgentCapability(
                name="Requirements Review",
                description="Review and evaluate product requirements for completeness and feasibility",
                enabled=True
            ),
            AgentCapability(
                name="Technical Solution Review",
                description="Evaluate technical solutions for soundness and alignment with requirements",
                enabled=True
            ),
            AgentCapability(
                name="Decision Making",
                description="Make approval/rejection decisions with clear justification",
                enabled=True
            ),
            AgentCapability(
                name="Feedback Generation",
                description="Provide constructive, actionable feedback for improvements",
                enabled=True
            ),
            AgentCapability(
                name="Risk Assessment",
                description="Identify and evaluate risks in proposed solutions",
                enabled=True
            ),
            AgentCapability(
                name="Final Approval",
                description="Grant final approval when solutions meet all criteria",
                enabled=True
            )
        ]

    async def process(self, context: AgentContext, input_message: Optional[str] = None) -> AgentResponse:
        """
        Process input and generate Team Lead response

        Args:
            context: Agent context containing conversation history and state
            input_message: Optional direct input message

        Returns:
            AgentResponse with review, decision, and feedback
        """
        try:
            logger.info(f"Team Lead processing request, iteration {context.current_iteration}")

            # Determine processing strategy based on context
            if context.current_iteration == 0:
                # First iteration - initial review of requirements and technical solution
                response = await self._handle_initial_review(context)
            elif context.current_iteration >= context.max_iterations - 1:
                # Final iteration - make final approval decision
                response = await self._handle_final_approval(context)
            else:
                # Intermediate iteration - review progress and provide feedback
                response = await self._handle_intermediate_review(context)

            # Add response metadata
            response.metadata.update({
                "agent_type": self.agent_type.value,
                "agent_name": self.agent_name,
                "processed_at": datetime.utcnow().isoformat(),
                "iteration": context.current_iteration,
                "max_iterations": context.max_iterations,
                "decision_made": response.message_type in [MessageType.APPROVAL, MessageType.REJECTION],
                "capabilities": [cap.name for cap in self._get_capabilities()]
            })

            logger.info(f"Team Lead completed processing, decision: {response.message_type.value}")
            return response

        except Exception as e:
            logger.error(f"Team Lead processing failed: {e}")
            return AgentResponse(
                content="I encountered an error while reviewing the proposal. Please try again.",
                message_type=MessageType.ERROR,
                confidence=0.1,
                requires_user_input=False,
                clarifying_questions=[]
            )

    async def _handle_initial_review(self, context: AgentContext) -> AgentResponse:
        """Handle initial review of requirements and technical solution"""
        logger.info("Performing initial review")

        # Get outputs from other agents
        pm_output = context.agent_outputs.get('product_manager', {})
        tech_output = context.agent_outputs.get('technical_developer', {})

        requirements = pm_output.get('content', 'No requirements available')
        technical_solution = tech_output.get('content', 'No technical solution available')

        # Format system prompt with context
        formatted_prompt = MessageFormatter.format_system_prompt(
            self.system_prompt,
            context,
            additional_instructions="This is the initial review. Thoroughly evaluate both the requirements and technical solution. Be constructively critical and provide specific feedback for improvements."
        )

        user_message = f"""Please review and evaluate the following product requirements and technical solution:

**Product Requirements:**
{requirements}

**Technical Solution:**
{technical_solution}

**Review Instructions:**
This is iteration {context.current_iteration + 1} of {context.max_iterations} maximum iterations.

Please provide a comprehensive review covering:

1. **Requirements Assessment**
   - Are requirements clear, complete, and actionable?
   - Do they address real user needs?
   - What's missing or unclear?

2. **Technical Solution Assessment**
   - Does the solution properly address the requirements?
   - Is the technical approach sound and feasible?
   - Are there better alternatives?

3. **Alignment Analysis**
   - How well does the technical solution align with requirements?
   - Are there gaps or mismatches?

4. **Risk Assessment**
   - What are the main risks (technical, product, timeline)?
   - How well are they addressed?

5. **Decision & Feedback**
   - Approval, rejection, or request for improvements
   - Specific, actionable feedback for each agent
   - Clear next steps

Structure your response with clear sections and provide specific, constructive feedback."""

        # Call GLM API
        glm_response = await self.glm_client.chat_completion(
            messages=[
                {"role": "system", "content": formatted_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.4,
            max_tokens=65535
        )

        # Parse GLM response
        parsed_response = self.response_parser.parse_response(
            glm_response,
            self.agent_type.value,
            None
        )

        # Determine decision based on content analysis
        decision_type = self._analyze_decision_type(parsed_response.content, context)

        # Format response for web display
        formatted_content = MessageFormatter.format_review(
            parsed_response.content,
            context
        )

        return AgentResponse(
            content=formatted_content,
            message_type=decision_type,
            confidence=parsed_response.confidence,
            requires_user_input=decision_type == MessageType.REJECTION,
            clarifying_questions=self._generate_feedback_questions(decision_type, parsed_response.content),
            metadata={
                # "raw_glm_response": parsed_response.raw_response, # Not available
                "review_type": "initial_review",
                "requirements_available": bool(pm_output.get('content')),
                "technical_solution_available": bool(tech_output.get('content'))
            }
        )

    async def _handle_intermediate_review(self, context: AgentContext) -> AgentResponse:
        """Handle intermediate review of progress"""
        logger.info(f"Performing intermediate review, iteration {context.current_iteration}")

        # Get current outputs from all agents
        pm_output = context.agent_outputs.get('product_manager', {})
        tech_output = context.agent_outputs.get('technical_developer', {})

        current_requirements = pm_output.get('content', 'No requirements available')
        current_technical_solution = tech_output.get('content', 'No technical solution available')

        formatted_prompt = MessageFormatter.format_system_prompt(
            self.system_prompt,
            context,
            additional_instructions=f"This is iteration {context.current_iteration + 1}. Evaluate progress and determine if the solution is approaching readiness for implementation."
        )

        user_message = f"""Please review the current progress and provide feedback:

**Iteration:** {context.current_iteration + 1} of {context.max_iterations}

**Current Product Requirements:**
{current_requirements}

**Current Technical Solution:**
{current_technical_solution}

**Review Focus:**
1. How much progress has been made since the last iteration?
2. Have previous feedback points been addressed?
3. What still needs improvement?
4. Are we moving toward an implementation-ready solution?
5. Should we continue refining or is this ready for approval?

Please provide:
- Assessment of progress made
- Remaining issues or concerns
- Specific feedback for further improvements
- Recommendation for next steps

Be constructive but decisive in your assessment."""

        glm_response = await self.glm_client.chat_completion(
            messages=[
                {"role": "system", "content": formatted_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.4,
            max_tokens=2000
        )

        parsed_response = self.response_parser.parse_response(
            glm_response,
            self.agent_type.value,
            None
        )

        decision_type = self._analyze_decision_type(parsed_response.content, context)

        formatted_content = MessageFormatter.format_review(
            parsed_response.content,
            context
        )

        return AgentResponse(
            content=formatted_content,
            message_type=decision_type,
            confidence=parsed_response.confidence,
            requires_user_input=decision_type == MessageType.REJECTION,
            clarifying_questions=self._generate_feedback_questions(decision_type, parsed_response.content),
            metadata={
                # "raw_glm_response": parsed_response.raw_response, # Not available
                "review_type": "intermediate_review",
                "iteration": context.current_iteration
            }
        )

    async def _handle_final_approval(self, context: AgentContext) -> AgentResponse:
        """Handle final approval decision"""
        logger.info("Making final approval decision")

        # Get final outputs from all agents
        pm_output = context.agent_outputs.get('product_manager', {})
        tech_output = context.agent_outputs.get('technical_developer', {})

        final_requirements = pm_output.get('content', 'No requirements available')
        final_technical_solution = tech_output.get('content', 'No technical solution available')

        formatted_prompt = MessageFormatter.format_system_prompt(
            self.system_prompt,
            context,
            additional_instructions="This is the final review. Make a definitive approval decision. If approving, generate the final comprehensive prompt that can be used for implementation."
        )

        user_message = f"""Please make the FINAL approval decision for this proposal:

**Final Iteration:** {context.current_iteration + 1} of {context.max_iterations}

**Final Product Requirements:**
{final_requirements}

**Final Technical Solution:**
{final_technical_solution}

**Final Review Instructions:**
This is your final decision. You must either:
1. **APPROVE** - If the solution is ready for implementation, OR
2. **REJECT** - If there are still critical issues that must be addressed

If APPROVING:
- Confirm that requirements are clear and complete
- Confirm that technical solution is sound and feasible
- Confirm alignment between requirements and solution
- Generate the FINAL COMPREHENSIVE PROMPT that incorporates all the work

If REJECTING:
- Clearly explain what critical issues remain
- Provide specific guidance for final improvements
- Be clear about what must be fixed before approval

This is your final decision - be decisive and provide clear justification."""

        glm_response = await self.glm_client.chat_completion(
            messages=[
                {"role": "system", "content": formatted_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3,
            max_tokens=2500
        )

        parsed_response = self.response_parser.parse_response(
            glm_response,
            self.agent_type.value,
            None
        )

        # Force a decision in final iteration
        decision_type = self._force_final_decision(parsed_response.content, context)

        if decision_type == MessageType.APPROVAL:
            formatted_content = MessageFormatter.format_approval(
                parsed_response.content,
                context
            )
        else:
            formatted_content = MessageFormatter.format_rejection(
                parsed_response.content,
                context
            )

        return AgentResponse(
            content=formatted_content,
            message_type=decision_type,
            confidence=parsed_response.confidence,
            requires_user_input=False,  # No more input in final iteration
            clarifying_questions=[],
            metadata={
                # "raw_glm_response": parsed_response.raw_response, # Not available
                "review_type": "final_approval",
                "final_decision": decision_type.value,
                "total_iterations": context.current_iteration + 1
            }
        )

    def _analyze_decision_type(self, content: str, context: AgentContext) -> MessageType:
        """Analyze content to determine the decision type"""
        content_lower = content.lower()

        # Look for approval indicators
        approval_indicators = [
            'approve', 'approved', 'approval', 'accept', 'accepted', 'good to go',
            'ready for implementation', 'implement', 'proceed', 'move forward',
            'excellent', 'perfect', 'well done', 'great job'
        ]

        # Look for rejection indicators
        rejection_indicators = [
            'reject', 'rejected', 'rejection', 'not ready', 'needs work',
            'inadequate', 'insufficient', 'missing', 'incomplete', 'unclear',
            'rethink', 'redo', 'start over', 'major issues'
        ]

        # Count indicators
        approval_count = sum(1 for indicator in approval_indicators if indicator in content_lower)
        rejection_count = sum(1 for indicator in rejection_indicators if indicator in content_lower)

        # Look for question/request indicators
        question_indicators = [
            'question', 'clarify', 'explain', 'elaborate', 'more detail',
            'unclear', 'confusing', 'what', 'how', 'why', 'when', 'where'
        ]
        question_count = sum(1 for indicator in question_indicators if indicator in content_lower)

        # Determine decision type
        if rejection_count > approval_count:
            return MessageType.REJECTION
        elif approval_count > rejection_count and approval_count > 0:
            return MessageType.APPROVAL
        elif question_count > 2 or context.current_iteration < context.max_iterations - 1:
            return MessageType.QUESTION
        else:
            return MessageType.REVIEW  # Default to review if unclear

    def _force_final_decision(self, content: str, context: AgentContext) -> MessageType:
        """Force a final decision in the last iteration"""
        content_lower = content.lower()

        # In final iteration, lean toward approval unless clearly rejected
        strong_rejection_indicators = [
            'cannot approve', 'strongly reject', 'major issues', 'fundamental problems',
            'completely inadequate', 'not acceptable', 'serious concerns'
        ]

        if any(indicator in content_lower for indicator in strong_rejection_indicators):
            return MessageType.REJECTION
        else:
            return MessageType.APPROVAL  # Default to approval in final iteration

    def _generate_feedback_questions(self, decision_type: MessageType, content: str) -> List[Dict[str, Any]]:
        """Generate clarifying questions based on feedback"""
        questions = []

        if decision_type == MessageType.REJECTION:
            # Extract questions from rejection content
            question_patterns = [
                r'what (.+?)\?',
                r'how (.+?)\?',
                r'why (.+?)\?',
                r'when (.+?)\?',
                r'where (.+?)\?',
                r'who (.+?)\?'
            ]

            for pattern in question_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    question_text = f"{match}?"
                    if len(question_text) > 10:
                        questions.append({
                            "question_text": question_text,
                            "question_type": "feedback_clarification",
                            "options": [],
                            "required": True
                        })

            # If no specific questions found, add a general one
            if not questions:
                questions.append({
                    "question_text": "Could you address the specific issues mentioned in the feedback?",
                    "question_type": "general_feedback",
                    "options": [],
                    "required": True
                })

        elif decision_type == MessageType.QUESTION:
            # Extract questions from review content
            explicit_questions = re.findall(r'([^.!?]*\?)', content)
            for question in explicit_questions[:3]:  # Limit to 3 questions
                question = question.strip()
                if len(question) > 10:
                    questions.append({
                        "question_text": question,
                        "question_type": "clarification",
                        "options": [],
                        "required": True
                    })

        return questions

    def _evaluate_readiness_score(self, context: AgentContext) -> float:
        """Evaluate how ready the solution is for implementation"""
        score = 0.0
        max_score = 1.0

        # Check if we have outputs from both agents
        if context.agent_outputs.get('product_manager', {}).get('content'):
            score += 0.3
        if context.agent_outputs.get('technical_developer', {}).get('content'):
            score += 0.3

        # Check iteration progress
        iteration_progress = context.current_iteration / max(context.max_iterations - 1, 1)
        score += iteration_progress * 0.4

        return min(score, max_score)

    def _build_system_prompt(self, context: AgentContext) -> str:
        """Build system prompt for the Team Lead agent"""
        prompt_parts = [
            self.system_prompt,
            "\n=== CURRENT CONTEXT ===",
            f"Session ID: {context.session_id}",
            f"Iteration: {context.current_iteration + 1} of {context.max_iterations}",
            f"User Requirements: {context.user_requirements}",
        ]

        # Add conversation context if available
        if context.conversation_history:
            recent_messages = context.conversation_history[-3:]  # Last 3 messages
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
            prompt_parts.append("Review the product requirements and technical solution. Provide constructive feedback and approve or request changes.")
        else:
            prompt_parts.append("\n=== YOUR TASK ===")
            prompt_parts.append("Review the updated solutions based on previous feedback. Determine if they're ready for implementation or need further refinement.")

        return "\n".join(prompt_parts)

    async def _agent_specific_validation(
        self,
        response: ParsedAgentResponse,
        context: AgentContext
    ) -> ParsedAgentResponse:
        """Perform Team Lead specific validation"""
        try:
            # Validate decision clarity
            content_lower = response.content.lower()

            # Check for clear decision (approve/reject)
            has_approval = any(word in content_lower for word in ['approve', 'approved', 'accept', 'accepted'])
            has_rejection = any(word in content_lower for word in ['reject', 'rejected', 'need', 'requires', 'revise', 'revision'])
            has_feedback = len(response.content) > 100  # Substantial feedback provided

            if not (has_approval or has_rejection):
                raise ValueError("Team Lead response must include clear approval or rejection decision")

            if not has_feedback and has_rejection:
                raise ValueError("Team Lead rejection must include constructive feedback")

            # Validate review completeness
            review_elements = [
                ('requirements_review', 'requirement' in content_lower),
                ('technical_review', 'technical' in content_lower or 'solution' in content_lower),
                ('feedback_quality', len(response.content) > 200)
            ]

            missing_elements = [elem for elem, present in review_elements if not present]
            if missing_elements:
                logger.warning(f"Team Lead response missing review elements: {missing_elements}")
                response.metadata['validation_warnings'] = missing_elements

            # Add team lead specific metadata
            response.metadata.update({
                'decision_type': 'approval' if has_approval else 'rejection',
                'has_feedback': has_feedback,
                'feedback_length': len(response.content),
                'review_completeness': len(review_elements) - len(missing_elements),
                'decision_authority': True,
                'validated_at': datetime.utcnow().isoformat()
            })

            return response

        except Exception as e:
            logger.error(f"Team Lead validation failed: {e}")
            raise ValueError(f"Team Lead validation failed: {str(e)}")

    async def get_status(self) -> Dict[str, Any]:
        """Get Team Lead agent status"""
        return {
            "agent_type": self.agent_type.value,
            "agent_name": self.agent_name,
            "status": "active",
            "capabilities": [cap.model_dump() for cap in self._get_capabilities()],
            "glm_client_connected": self.glm_client is not None,
            "response_parser_ready": self.response_parser is not None,
            "decision_authority": True
        }