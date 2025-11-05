"""
Product Manager Agent implementation
"""

import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

from .interfaces import (
    BaseAgent, AgentType, AgentCapability, AgentContext, AgentResponse,
    MessageType, ParsedAgentResponse
)
from ..services.glm_response_parser import GLMResponseParser
from ..services.glm_api import GLMApiClient
from .message_formatter import MessageFormatter
from .context_manager import AgentContextManager
from .state_tracker import AgentState, SessionState
from .response_validator import get_response_validator, get_quality_assessor
from ..core.logging import get_logger

logger = get_logger(__name__)


class ProductManagerAgent(BaseAgent):
    """Product Manager agent responsible for requirements analysis and generation"""

    def __init__(self):
        super().__init__(AgentType.PRODUCT_MANAGER)
        self.validator = get_response_validator()
        self.quality_assessor = get_quality_assessor()
        self.requirement_templates = self._load_requirement_templates()
        self.logger = get_logger(__name__)

    def _get_capabilities(self) -> List[AgentCapability]:
        """Get Product Manager agent capabilities"""
        return [
            AgentCapability(
                name="Requirement Analysis",
                description="Analyze user inputs to extract and structure requirements",
                examples=[
                    "Extract user needs from natural language descriptions",
                    "Identify key features and functionalities",
                    "Structure requirements in clear format"
                ],
                prompts={
                    "analyze": "Analyze the following user input and extract clear requirements: {input}",
                    "structure": "Structure these requirements into a comprehensive specification: {requirements}"
                }
            ),
            AgentCapability(
                name="Clarifying Questions",
                description="Generate clarifying questions when requirements are ambiguous",
                examples=[
                    "Ask for specific details about unclear requirements",
                    "Request examples or use cases",
                    "Seek clarification on technical constraints"
                ],
                prompts={
                    "clarify": "What additional information do you need to clarify these requirements: {requirements}",
                    "examples": "Can you provide examples of how this should work: {feature}"
                }
            ),
            AgentCapability(
                name="Requirement Refinement",
                description="Refine and improve requirements based on feedback",
                examples=[
                    "Incorporate user feedback into requirements",
                    "Resolve conflicts between requirements",
                    "Improve clarity and specificity"
                ],
                prompts={
                    "refine": "Refine these requirements based on the following feedback: {requirements} Feedback: {feedback}",
                    "improve": "How can these requirements be made more specific and actionable: {requirements}"
                }
            ),
            AgentCapability(
                name="User Input Integration",
                description="Integrate supplementary user inputs into existing requirements",
                examples=[
                    "Merge additional requirements with existing ones",
                    "Handle conflicting user inputs",
                    "Update requirements based on new information"
                ],
                prompts={
                    "integrate": "Integrate this new user input into the existing requirements: {existing} New input: {new_input}",
                    "resolve_conflicts": "Resolve conflicts between these requirements: {conflicting_requirements}"
                }
            )
        ]

    def _build_system_prompt(self, context: AgentContext) -> str:
        """Build system prompt for Product Manager agent"""
        base_prompt = self._get_base_system_prompt()

        # Add context-specific instructions
        context_instructions = self._get_context_instructions(context)

        # Add iteration-specific guidance
        iteration_guidance = self._get_iteration_guidance(context)

        # Add capability-specific prompts
        capability_prompts = self._get_capability_prompts(context)

        return MessageFormatter.format_system_prompt(
            base_prompt + "\n\n" + context_instructions + "\n\n" + iteration_guidance + "\n\n" + capability_prompts,
            context
        )

    def _get_base_system_prompt(self) -> str:
        """Get base system prompt for Product Manager"""
        return """You are a Product Manager AI agent specializing in requirements analysis and specification.

Your primary responsibilities:
1. Analyze user inputs to extract clear, actionable requirements
2. Ask clarifying questions when requirements are ambiguous or incomplete
3. Structure requirements in a comprehensive, user-centric format
4. Refine requirements based on feedback from other agents and users
5. Ensure requirements address real user needs and are technically feasible

Your approach should be:
- User-centric: Always focus on user needs and experiences
- Clear and specific: Avoid ambiguity, provide concrete details
- Comprehensive: Cover all aspects of the user's requirements
- Collaborative: Work with other agents to refine and improve requirements
- Iterative: Continuously improve requirements based on feedback

When analyzing requirements, consider:
- Who are the users?
- What problems are they trying to solve?
- What are the key features and functionalities?
- What are the success criteria?
- What constraints or limitations exist?
- What are the edge cases and error conditions?"""

    def _get_context_instructions(self, context: AgentContext) -> str:
        """Get context-specific instructions"""
        instructions = []

        if context.user_requirements:
            instructions.append(f"Current User Requirements: {context.user_requirements}")

        if context.supplementary_inputs:
            instructions.append("Supplementary User Inputs:")
            for i, input_text in enumerate(context.supplementary_inputs, 1):
                instructions.append(f"{i}. {input_text}")

        if context.clarifying_questions:
            instructions.append("Previously Asked Clarifying Questions:")
            for question in context.clarifying_questions:
                instructions.append(f"- {question.get('question_text', 'No question text')}")

        if context.agent_outputs:
            if 'technical_developer' in context.agent_outputs:
                instructions.append("Technical Developer Feedback Available")
            if 'team_lead' in context.agent_outputs:
                instructions.append("Team Lead Feedback Available")

        return "\n".join(instructions) if instructions else "No additional context available."

    def _get_iteration_guidance(self, context: AgentContext) -> str:
        """Get iteration-specific guidance"""
        if context.current_iteration == 0:
            return """This is the initial requirements analysis. Focus on:
1. Understanding the core user needs
2. Identifying key features and functionalities
3. Asking clarifying questions if needed
4. Providing a comprehensive initial requirements document"""
        elif context.current_iteration < 3:
            return f"""This is iteration {context.current_iteration + 1}. Focus on:
1. Incorporating feedback from previous iterations
2. Refining and improving the requirements
3. Resolving any ambiguities or conflicts
4. Making requirements more specific and actionable"""
        else:
            return f"""This is iteration {context.current_iteration + 1}. Focus on:
1. Finalizing the requirements
2. Ensuring all aspects are covered comprehensively
3. Making sure requirements are ready for implementation
4. Providing clear acceptance criteria"""

    def _get_capability_prompts(self, context: AgentContext) -> str:
        """Get capability-specific prompts based on context"""
        prompts = []

        # Determine which capabilities to emphasize
        if not context.user_requirements or len(context.user_requirements.strip()) < 20:
            prompts.append("CAPABILITY: Requirement Analysis - Analyze user input thoroughly")
            prompts.append("If requirements are unclear, use your Clarifying Questions capability")

        if context.current_iteration > 0:
            prompts.append("CAPABILITY: Requirement Refinement - Improve based on feedback")

        if context.supplementary_inputs:
            prompts.append("CAPABILITY: User Input Integration - Incorporate new inputs")

        if context.clarifying_questions:
            prompts.append("Review and incorporate answers to previous clarifying questions")

        # Add decision guidance
        prompts.append("\nDECISION GUIDANCE:")
        prompts.append("- If user input is clear and comprehensive → Generate detailed requirements")
        prompts.append("- If user input is ambiguous or incomplete → Ask clarifying questions")
        prompts.append("- If feedback indicates issues → Refine requirements accordingly")
        prompts.append("- If new information provided → Integrate into existing requirements")

        return "\n".join(prompts)

    async def _agent_specific_validation(
        self,
        response: ParsedAgentResponse,
        context: AgentContext
    ) -> ParsedAgentResponse:
        """Product Manager specific response validation"""

        # Use the response validator
        validation_result = self.validator.validate_response(response, self.agent_type, context)

        if not validation_result.is_valid:
            # Log validation issues
            self.logger.warning(
                "Product Manager response validation failed",
                issues=[issue.message for issue in validation_result.issues],
                session_id=context.session_id
            )

            # Try to use corrected content if available
            if validation_result.corrected_content:
                response.content = validation_result.corrected_content
                self.logger.info("Applied automatic corrections to Product Manager response")

        # Assess response quality
        quality_result = self.quality_assessor.assess_quality(
            response.content, self.agent_type, response.message_type, context
        )

        # Update response metadata with validation results
        response.metadata.update({
            "validation_score": validation_result.confidence_score,
            "quality_scores": quality_result,
            "validation_issues": len(validation_result.issues)
        })

        return response

    def _analyze_ambiguity(self, content: str, context: AgentContext) -> List[str]:
        """Analyze content for ambiguity and generate clarifying questions"""
        questions = []
        content_lower = content.lower()

        # Common ambiguity patterns
        ambiguity_patterns = {
            "missing_details": [
                r"(\w+)\s+system", r"(\w+)\s+platform", r"(\w+)\s+application",
                r"(\w+)\s+feature", r"(\w+)\s+functionality"
            ],
            "missing_metrics": [
                r"fast", r"quick", r"slow", r"responsive", r"scalable",
                r"user-friendly", r"intuitive", r"efficient"
            ],
            "missing_users": [
                r"users", r"customers", r"clients", r"people"
            ],
            "missing_goals": [
                r"need", r"want", r"require", r"should"
            ]
        }

        # Check for missing specific details
        for pattern_list in ambiguity_patterns["missing_details"]:
            matches = re.findall(pattern_list, content_lower)
            for match in matches:
                questions.append(f"Can you provide more specific details about the '{match}' you mentioned?")

        # Check for undefined metrics
        for word in ambiguity_patterns["missing_metrics"]:
            if word in content_lower:
                questions.append(f"What specific metrics or standards should be used to measure '{word}' performance?")

        # Check if users are not well defined
        if any(word in content_lower for word in ambiguity_patterns["missing_users"]):
            if "who" not in content_lower and "user" not in content_lower[:100]:
                questions.append("Who are the primary users or target audience for this system?")

        # Check if goals are vague
        vague_goal_patterns = [
            r"need to", r"should be able to", r"want to", r"looking for"
        ]
        if any(re.search(pattern, content_lower) for pattern in vague_goal_patterns):
            questions.append("What specific problems or pain points are you trying to solve?")

        # Limit questions to most important ones
        return questions[:3]  # Max 3 questions per response

    def _extract_requirements(self, content: str) -> List[Dict[str, Any]]:
        """Extract structured requirements from content"""
        requirements = []

        # Look for requirement patterns
        requirement_patterns = [
            r"requirement:\s*(.+?)(?=\n|$)",
            r"feature:\s*(.+?)(?=\n|$)",
            r"functionality:\s*(.+?)(?=\n|$)",
            r"(\d+\.\s*.+)",  # Numbered lists
            r"[-*]\s*(.+)",   # Bullet points
        ]

        for pattern in requirement_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if match[0] else match[1]

                requirement_text = match.strip()
                if len(requirement_text) > 10:  # Filter out very short matches
                    requirements.append({
                        "text": requirement_text,
                        "type": self._classify_requirement_type(requirement_text),
                        "priority": self._estimate_priority(requirement_text),
                        "source": "extracted"
                    })

        # Remove duplicates
        unique_requirements = []
        seen_texts = set()
        for req in requirements:
            if req["text"] not in seen_texts:
                unique_requirements.append(req)
                seen_texts.add(req["text"])

        return unique_requirements

    def _classify_requirement_type(self, requirement_text: str) -> str:
        """Classify requirement type based on content"""
        text_lower = requirement_text.lower()

        if any(word in text_lower for word in ["user", "interface", "ui", "ux", "display", "show"]):
            return "ui_requirement"
        elif any(word in text_lower for word in ["data", "store", "save", "database", "persist"]):
            return "data_requirement"
        elif any(word in text_lower for word in ["api", "service", "integration", "connect"]):
            return "integration_requirement"
        elif any(word in text_lower for word in ["security", "auth", "login", "permission", "access"]):
            return "security_requirement"
        elif any(word in text_lower for word in ["performance", "speed", "fast", "load", "scale"]):
            return "performance_requirement"
        else:
            return "functional_requirement"

    def _estimate_priority(self, requirement_text: str) -> str:
        """Estimate requirement priority based on language"""
        text_lower = requirement_text.lower()

        high_priority_words = ["critical", "essential", "must", "required", "necessary", "key"]
        medium_priority_words = ["should", "important", "valuable", "useful"]
        low_priority_words = ["could", "nice", "optional", "would be", "if possible"]

        if any(word in text_lower for word in high_priority_words):
            return "high"
        elif any(word in text_lower for word in medium_priority_words):
            return "medium"
        elif any(word in text_lower for word in low_priority_words):
            return "low"
        else:
            return "medium"  # Default to medium

    def _load_requirement_templates(self) -> Dict[str, str]:
        """Load requirement templates for different types of inputs"""
        return {
            "simple_feature": """
# Feature Requirements: {feature_name}

## User Story
As a {user_type}, I want to {action} so that {benefit}.

## Functional Requirements
- {requirement_1}
- {requirement_2}
- {requirement_3}

## Acceptance Criteria
- [ ] {criteria_1}
- [ ] {criteria_2}
- [ ] {criteria_3}

## Success Metrics
- {metric_1}
- {metric_2}
            """,

            "system_requirements": """
# System Requirements

## Overview
{overview}

## Core Features
### {feature_1}
{description_1}

### {feature_2}
{description_2}

### {feature_3}
{description_3}

## User Requirements
- {user_req_1}
- {user_req_2}
- {user_req_3}

## Technical Considerations
- {tech_consideration_1}
- {tech_consideration_2}

## Success Criteria
- {success_criteria_1}
- {success_criteria_2}
            """,

            "clarifying_questions": """
# Clarifying Questions

I need some additional information to better understand your requirements:

## User Context
1. {question_1}

## Functional Details
2. {question_2}

## Technical Constraints
3. {question_3}

Please provide more details about these aspects so I can create comprehensive requirements.
            """
        }

    def _generate_requirements_from_template(
        self,
        user_input: str,
        context: AgentContext
    ) -> str:
        """Generate requirements using appropriate template"""
        # Determine which template to use
        if len(user_input.strip()) < 100 or "?" in user_input:
            return self._generate_simple_requirements(user_input, context)
        else:
            return self._generate_comprehensive_requirements(user_input, context)

    def _generate_simple_requirements(self, user_input: str, context: AgentContext) -> str:
        """Generate simple requirements for brief user input"""
        # Extract key information
        requirements = self._extract_requirements(user_input)

        # Check for ambiguity
        questions = self._analyze_ambiguity(user_input, context)

        if questions:
            # Ask clarifying questions
            return MessageFormatter.format_clarifying_question(
                "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions)),
                context
            )
        else:
            # Generate basic requirements
            template = self.requirement_templates["simple_feature"]
            return template.format(
                feature_name=user_input[:50] + "..." if len(user_input) > 50 else user_input,
                user_type="user",
                action="accomplish the described task",
                benefit="their needs are met",
                requirement_1="Core functionality as described",
                requirement_2="User-friendly interface",
                requirement_3="Reliable performance",
                criteria_1="Feature works as expected",
                criteria_2="Interface is intuitive",
                criteria_3="Performance meets requirements",
                metric_1="User satisfaction",
                metric_2="Task completion rate"
            )

    def _generate_comprehensive_requirements(self, user_input: str, context: AgentContext) -> str:
        """Generate comprehensive requirements for detailed user input"""
        requirements = self._extract_requirements(user_input)

        # Structure requirements
        structured_requirements = []
        for req in requirements:
            structured_requirements.append(f"- {req['text']}")

        # Create comprehensive requirements document
        template = self.requirement_templates["system_requirements"]

        return template.format(
            overview=user_input[:200] + "..." if len(user_input) > 200 else user_input,
            feature_1="Primary Feature",
            description_1=requirements[0]['text'] if requirements else "Main functionality as described",
            feature_2="Supporting Features",
            description_2="\n".join(f"- {req['text']}" for req in requirements[1:4]) if len(requirements) > 1 else "Additional functionality",
            feature_3="Quality Attributes",
            description_3="Performance, reliability, and usability requirements",
            user_req_1="Clear and intuitive user interface",
            user_req_2="Responsive and performant system",
            user_req_3="Reliable and consistent behavior",
            tech_consideration_1="Scalability for future growth",
            tech_consideration_2="Integration with existing systems",
            success_criteria_1="All functional requirements are implemented",
            success_criteria_2="User acceptance criteria are met"
        )

    def get_requirement_analysis_summary(self, content: str) -> Dict[str, Any]:
        """Get analysis summary of requirements content"""
        requirements = self._extract_requirements(content)

        # Analyze requirements
        analysis = {
            "total_requirements": len(requirements),
            "requirement_types": {},
            "priority_distribution": {},
            "ambiguity_score": 0.0,
            "completeness_score": 0.0,
            "key_topics": [],
            "suggested_improvements": []
        }

        # Count requirement types
        for req in requirements:
            req_type = req["type"]
            analysis["requirement_types"][req_type] = analysis["requirement_types"].get(req_type, 0) + 1

        # Count priorities
        for req in requirements:
            priority = req["priority"]
            analysis["priority_distribution"][priority] = analysis["priority_distribution"].get(priority, 0) + 1

        # Calculate scores
        if requirements:
            analysis["completeness_score"] = min(1.0, len(requirements) / 10.0)  # 10 requirements = full score

            # Ambiguity score based on vague language
            vague_words = ["system", "platform", "feature", "functionality", "etc."]
            vague_count = sum(1 for word in vague_words if word in content.lower())
            analysis["ambiguity_score"] = min(1.0, vague_count / 5.0)

        # Extract key topics
        words = content.lower().split()
        word_freq = {}
        for word in words:
            if len(word) > 4:  # Only consider words longer than 4 characters
                word_freq[word] = word_freq.get(word, 0) + 1

        # Get top 5 most frequent words
        analysis["key_topics"] = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]

        return analysis

    async def _agent_specific_validation(
        self,
        response: ParsedAgentResponse,
        context: AgentContext
    ) -> ParsedAgentResponse:
        """Product Manager specific response validation"""

        # Use the response validator
        validation_result = self.validator.validate_response(response, self.agent_type, context)

        if not validation_result.is_valid:
            # Log validation issues
            self.logger.warning(
                "Product Manager response validation failed",
                issues=[issue.message for issue in validation_result.issues],
                session_id=context.session_id
            )

            # Try to use corrected content if available
            if validation_result.corrected_content:
                response.content = validation_result.corrected_content
                self.logger.info("Applied automatic corrections to Product Manager response")

        # Assess response quality
        quality_result = self.quality_assessor.assess_quality(
            response.content, self.agent_type, response.message_type, context
        )

        # Update response metadata with validation results
        response.metadata.update({
            "validation_score": validation_result.confidence_score,
            "quality_scores": quality_result,
            "validation_issues": len(validation_result.issues)
        })

        return response