"""
GLM API response parsing utilities
"""

import json
import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, validator

from .glm_api import GLMChatResponse, GLMMessage


class ParsedAgentResponse(BaseModel):
    """Parsed response from an AI agent"""
    content: str = Field(..., description="Main response content")
    message_type: str = Field(..., description="Type of message: requirement, solution, review, approval, rejection")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence level in the response")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @validator('message_type')
    def validate_message_type(cls, v):
        allowed_types = ['requirement', 'solution', 'review', 'approval', 'rejection', 'clarification', 'question']
        if v not in allowed_types:
            # Try to infer message type from content
            v = cls.infer_message_type_from_content(v)
        return v

    @classmethod
    def infer_message_type_from_content(cls, content: str) -> str:
        """Infer message type from content"""
        content_lower = content.lower()

        # Look for keywords that indicate message type
        type_keywords = {
            'requirement': ['requirement', 'specification', 'user need', 'functionality'],
            'solution': ['solution', 'approach', 'implementation', 'technical', 'architecture'],
            'review': ['review', 'feedback', 'assessment', 'evaluation'],
            'approval': ['approve', 'accept', 'agreed', 'good', 'perfect', 'excellent'],
            'rejection': ['reject', 'disagree', 'problem', 'issue', 'concern', 'revision'],
            'clarification': ['clarify', 'unclear', 'ambiguous', 'question', 'explain'],
            'question': ['question', 'what', 'how', 'why', 'when', 'where']
        }

        scores = {}
        for msg_type, keywords in type_keywords.items():
            score = sum(1 for keyword in keywords if keyword in content_lower)
            if score > 0:
                scores[msg_type] = score

        if scores:
            return max(scores, key=scores.get)
        return 'review'  # Default to review if no clear indicator


class ConversationContext(BaseModel):
    """Conversation context for agents"""
    session_id: str
    agent_type: str
    conversation_history: List[Dict[str, Any]]
    key_points: List[str] = Field(default_factory=list)
    current_iteration: int = 0
    user_requirements: str = ""
    previous_feedback: Optional[str] = None
    waiting_for_user: bool = False


class GLMResponseParser:
    """Parser for GLM API responses"""

    def __init__(self):
        self.response_patterns = self._load_response_patterns()

    def _load_response_patterns(self) -> Dict[str, Dict[str, str]]:
        """Load response patterns for different agent types"""
        return {
            'product_manager': {
                'requirement_pattern': r'(?:I\s+)?(analyze|understand|create|design|define)\s+(?:the\s+)?(?:product\s+)?requirements?',
                'clarification_pattern': r'(?:I\s+)?(need|require)\s+(?:more\s+)?(?:information|clarification|details)',
                'approval_pattern': r'(?:This\s+)?(?:meets|satisfies|fulfills)\s+(?:all\s+)?(?:the\s+)?requirements'
            },
            'technical_developer': {
                'solution_pattern': r'(?:I\s+)?(propose|suggest|recommend|design)\s+(?:a\s+)?(?:technical\s+)?solution',
                'implementation_pattern': r'(?:I\s+)?(recommend|suggest)\s+(?:an\s+)?(?:implementation\s+)?approach',
                'feasibility_pattern': r'(?:This\s+)?(?:is\s+)?(?:feasible|possible|achievable|practical)'
            },
            'team_lead': {
                'approval_pattern': r'(?:I\s+)?(approve|accept|agree|endorse)\s+(?:this\s+)?(?:approach|solution)',
                'rejection_pattern': r'(?:I\s+)?(cannot|do\s+not|reject|disagree)\s+(?:accept|approve)',
                'modification_pattern': r'(?:I\s+)?(suggest|recommend)\s+(?:the\s+)?(?:following\s+)?(?:changes|modifications|improvements)',
                'final_prompt_pattern': r'(?:Here\s+)?(?:is\s+)?(?:the\s+)?(?:final\s+)?(?:prompt|template)'
            }
        }

    def parse_response(
        self,
        response: GLMChatResponse,
        agent_type: str,
        context: Optional[ConversationContext] = None
    ) -> ParsedAgentResponse:
        """
        Parse GLM API response into structured agent response

        Args:
            response: Raw GLM API response
            agent_type: Type of agent that generated the response
            context: Current conversation context

        Returns:
            Parsed agent response with structured data
        """
        content = self._extract_content(response)
        message_type = self._extract_message_type(content, agent_type, context)
        confidence = self._calculate_confidence(content, agent_type, context)
        metadata = self._extract_metadata(response, agent_type, context)

        return ParsedAgentResponse(
            content=content,
            message_type=message_type,
            confidence=confidence,
            metadata=metadata
        )

    def _extract_content(self, response: GLMChatResponse) -> str:
        """Extract content from GLM response"""
        if not response.choices or not response.choices[0]:
            return ""

        message = response.choices[0].get("message", {})
        return message.get("content", "").strip()

    def _extract_message_type(
        self,
        content: str,
        agent_type: str,
        context: Optional[ConversationContext] = None
    ) -> str:
        """Extract message type from content"""
        # Look for agent-specific patterns
        patterns = self.response_patterns.get(agent_type, {})

        for pattern_name, pattern in patterns.items():
            if re.search(pattern, content, re.IGNORECASE):
                return pattern_name.replace('_pattern', '')

        # Use ParsedAgentResponse's automatic inference
        parsed = ParsedAgentResponse(content=content)
        return parsed.message_type

    def _calculate_confidence(
        self,
        content: str,
        agent_type: str,
        context: Optional[ConversationContext] = None
    ) -> float:
        """Calculate confidence in the response"""
        confidence = 0.5  # Base confidence

        # Increase confidence based on content characteristics
        content_length = len(content)
        if content_length > 100:
            confidence += 0.2
        if content_length > 500:
            confidence += 0.1

        # Check for structured response
        if self._is_structured_response(content):
            confidence += 0.2

        # Check for agent-specific indicators
        if self._has_agent_indicators(content, agent_type):
            confidence += 0.1

        # Consider context consistency
        if context and self._is_context_consistent(content, context):
            confidence += 0.1

        return min(confidence, 1.0)

    def _is_structured_response(self, content: str) -> bool:
        """Check if response has structured format"""
        structured_indicators = [
            r'\n\d+\.',  # Numbered lists
            r'\* ',  # Bullet points
            r'---+',  # Markdown headers
            r'\*\*.*\*\*',  # Bold text
            r'```',  # Code blocks
        ]
        return any(re.search(pattern, content) for pattern in structured_indicators)

    def _has_agent_indicators(self, content: str, agent_type: str) -> bool:
        """Check if content has agent-specific indicators"""
        content_lower = content.lower()

        indicators = {
            'product_manager': ['requirement', 'specification', 'user need', 'functionality'],
            'technical_developer': ['solution', 'implementation', 'architecture', 'technical'],
            'team_lead': ['approve', 'review', 'assess', 'evaluate', 'final prompt']
        }

        agent_indicators = indicators.get(agent_type, [])
        return any(indicator in content_lower for indicator in agent_indicators)

    def _is_context_consistent(
        self,
        content: str,
        context: ConversationContext
    ) -> bool:
        """Check if response is consistent with conversation context"""
        if not context:
            return True

        content_lower = content.lower()

        # Check if response references previous messages
        if context.conversation_history:
            for message in context.conversation_history[-2:]:  # Check last 2 messages
                message_content = message.get('content', '').lower()
                if any(word in content_lower for word in message_content.split()[:5]):
                    return True

        # Check if response addresses user requirements
        if context.user_requirements:
            req_words = set(context.user_requirements.lower().split())
            content_words = set(content_lower.split())
            overlap = len(req_words.intersection(content_words))
            if overlap > len(req_words) * 0.3:  # 30% overlap
                return True

        return False

    def _extract_metadata(
        self,
        response: GLMChatResponse,
        agent_type: str,
        context: Optional[ConversationContext] = None
    ) -> Dict[str, Any]:
        """Extract metadata from response"""
        metadata = {
            "response_id": response.id,
            "model": response.model,
            "created_at": response.created,
            "agent_type": agent_type,
            "token_usage": response.usage,
            "system_fingerprint": response.system_fingerprint
        }

        if context:
            metadata.update({
                "session_id": context.session_id,
                "current_iteration": context.current_iteration,
                "conversation_length": len(context.conversation_history)
            })

        # Extract additional insights from content
        metadata.update(self._extract_content_insights(response.choices[0]["message"]["content"] if response.choices else ""))

        return metadata

    def _extract_content_insights(self, content: str) -> Dict[str, Any]:
        """Extract insights from content"""
        insights = {}

        # Word count
        insights["word_count"] = len(content.split())

        # Character count
        insights["char_count"] = len(content)

        # Contains code blocks
        insights["has_code"] = "```" in content

        # Contains lists or bullet points
        insights["has_lists"] = bool(re.search(r'[\n\r]*[-*•]\s+', content))

        # Contains questions
        insights["has_questions"] = "?" in content

        # Contains URLs
        insights["has_urls"] = bool(re.search(r'https?://[^\s]+', content))

        # Sentiment indicators (simple keyword-based)
        positive_words = ['excellent', 'perfect', 'great', 'good', 'optimal', 'ideal']
        negative_words = ['problem', 'issue', 'concern', 'difficulty', 'challenge', 'impossible']

        content_lower = content.lower()
        positive_count = sum(1 for word in positive_words if word in content_lower)
        negative_count = sum(1 for word in negative_words if word in content_lower)

        if positive_count > negative_count:
            insights["sentiment"] = "positive"
        elif negative_count > positive_count:
            insights["sentiment"] = "negative"
        else:
            insights["sentiment"] = "neutral"

        return insights


# Global parser instance
_response_parser = None


def get_response_parser() -> GLMResponseParser:
    """Get or create response parser instance"""
    global _response_parser
    if _response_parser is None:
        _response_parser = GLMResponseParser()
    return _response_parser