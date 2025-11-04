"""
Agent response validation utilities
"""

import re
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from .interfaces import AgentType, MessageType, ParsedAgentResponse, AgentContext


class ValidationSeverity(str, Enum):
    """Validation issue severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    """Single validation issue"""
    severity: ValidationSeverity
    code: str
    message: str
    suggestion: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Result of response validation"""
    is_valid: bool
    confidence_score: float  # 0.0 to 1.0
    issues: List[ValidationIssue] = field(default_factory=list)
    corrected_content: Optional[str] = None
    validation_metadata: Dict[str, Any] = field(default_factory=dict)


class ResponseValidator:
    """Validates and corrects agent responses"""

    def __init__(self):
        self.validation_rules = self._load_validation_rules()
        self.correction_patterns = self._load_correction_patterns()

    def validate_response(
        self,
        response: ParsedAgentResponse,
        agent_type: AgentType,
        context: AgentContext
    ) -> ValidationResult:
        """
        Validate an agent response comprehensively

        Args:
            response: The parsed agent response to validate
            agent_type: Type of agent that generated the response
            context: Current conversation context

        Returns:
            ValidationResult with validation outcome and suggestions
        """
        issues = []
        content = response.content

        # Basic content validation
        issues.extend(self._validate_basic_content(content))

        # Agent-specific validation
        issues.extend(self._validate_agent_specific_content(
            content, response.message_type, agent_type, context
        ))

        # Context consistency validation
        issues.extend(self._validate_context_consistency(
            content, response.message_type, agent_type, context
        ))

        # Format and structure validation
        issues.extend(self._validate_format_and_structure(
            content, response.message_type, agent_type
        ))

        # Content quality validation
        issues.extend(self._validate_content_quality(
            content, response.message_type, agent_type
        ))

        # Determine overall validity
        critical_issues = [issue for issue in issues if issue.severity == ValidationSeverity.CRITICAL]
        error_issues = [issue for issue in issues if issue.severity == ValidationSeverity.ERROR]

        is_valid = len(critical_issues) == 0 and len(error_issues) == 0

        # Calculate confidence score
        confidence_score = self._calculate_confidence_score(issues, content)

        # Apply corrections if possible
        corrected_content = self._apply_corrections(content, issues, agent_type)

        return ValidationResult(
            is_valid=is_valid,
            confidence_score=confidence_score,
            issues=issues,
            corrected_content=corrected_content,
            validation_metadata={
                "agent_type": agent_type.value,
                "message_type": response.message_type,
                "validation_timestamp": datetime.utcnow().isoformat(),
                "original_length": len(content),
                "issue_counts": {
                    "critical": len(critical_issues),
                    "error": len(error_issues),
                    "warning": len([i for i in issues if i.severity == ValidationSeverity.WARNING]),
                    "info": len([i for i in issues if i.severity == ValidationSeverity.INFO])
                }
            }
        )

    def _validate_basic_content(self, content: str) -> List[ValidationIssue]:
        """Validate basic content properties"""
        issues = []

        # Check for empty content
        if not content or not content.strip():
            issues.append(ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                code="EMPTY_CONTENT",
                message="Response content is empty",
                suggestion="Please provide a meaningful response"
            ))
            return issues

        # Check minimum length
        if len(content.strip()) < 10:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="CONTENT_TOO_SHORT",
                message="Response content is too short",
                suggestion="Please provide more detailed content (at least 10 characters)"
            ))

        # Check for only whitespace
        if len(content.strip()) < len(content) * 0.5:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="EXCESSIVE_WHITESPACE",
                message="Response contains excessive whitespace",
                suggestion="Consider reducing whitespace and adding more substantive content"
            ))

        # Check for repeated content
        words = content.lower().split()
        if len(words) > 10:
            repeated_words = [word for word in set(words) if words.count(word) > 3]
            if repeated_words:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="REPEATED_CONTENT",
                    message=f"Response contains repeated words: {', '.join(repeated_words[:5])}",
                    suggestion="Try to vary your vocabulary and avoid repetition"
                ))

        return issues

    def _validate_agent_specific_content(
        self,
        content: str,
        message_type: MessageType,
        agent_type: AgentType,
        context: AgentContext
    ) -> List[ValidationIssue]:
        """Validate agent-specific content requirements"""
        issues = []

        if agent_type == AgentType.PRODUCT_MANAGER:
            issues.extend(self._validate_product_manager_response(content, message_type, context))
        elif agent_type == AgentType.TECHNICAL_DEVELOPER:
            issues.extend(self._validate_technical_developer_response(content, message_type, context))
        elif agent_type == AgentType.TEAM_LEAD:
            issues.extend(self._validate_team_lead_response(content, message_type, context))

        return issues

    def _validate_product_manager_response(
        self,
        content: str,
        message_type: MessageType,
        context: AgentContext
    ) -> List[ValidationIssue]:
        """Validate Product Manager agent responses"""
        issues = []
        content_lower = content.lower()

        if message_type == MessageType.REQUIREMENT:
            # Check for requirement indicators
            if not any(indicator in content_lower for indicator in [
                'requirement', 'specification', 'user need', 'functionality', 'feature'
            ]):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="MISSING_REQUIREMENT_INDICATORS",
                    message="Requirements response lacks clear requirement indicators",
                    suggestion="Include terms like 'requirement', 'specification', or 'user need'"
                ))

            # Check for user-centric language
            if not any(indicator in content_lower for indicator in [
                'user', 'customer', 'need', 'want', 'expect', 'experience'
            ]):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="MISSING_USER_FOCUS",
                    message="Requirements should focus on user needs",
                    suggestion="Include user-centric language and focus on user experience"
                ))

        elif message_type == MessageType.CLARIFICATION:
            # Check for question format
            if '?' not in content:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="CLARIFICATION_NOT_A_QUESTION",
                    message="Clarification response should contain questions",
                    suggestion="Rephrase as a clear question for the user"
                ))

        return issues

    def _validate_technical_developer_response(
        self,
        content: str,
        message_type: MessageType,
        context: AgentContext
    ) -> List[ValidationIssue]:
        """Validate Technical Developer agent responses"""
        issues = []
        content_lower = content.lower()

        if message_type == MessageType.SOLUTION:
            # Check for technical solution indicators
            if not any(indicator in content_lower for indicator in [
                'solution', 'approach', 'implementation', 'architecture', 'technical'
            ]):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="MISSING_SOLUTION_INDICATORS",
                    message="Technical solution response lacks solution indicators",
                    suggestion="Include terms like 'solution', 'approach', or 'implementation'"
                ))

            # Check for feasibility considerations
            if not any(indicator in content_lower for indicator in [
                'feasible', 'possible', 'practical', 'implementable', 'achievable'
            ]):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    code="MISSING_FEASIBILITY",
                    message="Technical solutions should address feasibility",
                    suggestion="Consider mentioning feasibility or implementation considerations"
                ))

        return issues

    def _validate_team_lead_response(
        self,
        content: str,
        message_type: MessageType,
        context: AgentContext
    ) -> List[ValidationIssue]:
        """Validate Team Lead agent responses"""
        issues = []
        content_lower = content.lower()

        if message_type == MessageType.APPROVAL:
            # Check for approval indicators
            if not any(indicator in content_lower for indicator in [
                'approve', 'accept', 'agree', 'endorse', 'confirm', 'good', 'excellent'
            ]):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="MISSING_APPROVAL_INDICATORS",
                    message="Approval response lacks clear approval indicators",
                    suggestion="Include explicit approval language"
                ))

        elif message_type == MessageType.REJECTION:
            # Check for constructive feedback
            if not any(indicator in content_lower for indicator in [
                'improve', 'suggest', 'recommend', 'modify', 'adjust', 'enhance'
            ]):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="MISSING_CONSTRUCTIVE_FEEDBACK",
                    message="Rejection should include constructive feedback",
                    suggestion="Provide specific suggestions for improvement"
                ))

        return issues

    def _validate_context_consistency(
        self,
        content: str,
        message_type: MessageType,
        agent_type: AgentType,
        context: AgentContext
    ) -> List[ValidationIssue]:
        """Validate consistency with conversation context"""
        issues = []

        if not context.user_requirements:
            return issues  # No context to validate against

        # Check if response addresses user requirements
        req_words = set(context.user_requirements.lower().split())
        content_words = set(content.lower().split())
        overlap = len(req_words.intersection(content_words))

        if len(req_words) > 0:
            overlap_percentage = overlap / len(req_words)
            if overlap_percentage < 0.1:  # Less than 10% overlap
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="LOW_CONTEXT_RELEVANCE",
                    message="Response has low relevance to user requirements",
                    suggestion="Try to address the user's original requirements more directly"
                ))

        # Check iteration consistency
        if context.current_iteration > 0:
            if 'iteration' not in content.lower() and 'refine' not in content.lower():
                if message_type in [MessageType.REQUIREMENT, MessageType.SOLUTION]:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.INFO,
                        code="MISSING_ITERATION_CONTEXT",
                        message="Response doesn't acknowledge this is a refined iteration",
                        suggestion="Consider mentioning this is an improved version based on feedback"
                    ))

        return issues

    def _validate_format_and_structure(
        self,
        content: str,
        message_type: MessageType,
        agent_type: AgentType
    ) -> List[ValidationIssue]:
        """Validate response format and structure"""
        issues = []

        # Check for basic structure
        has_headers = bool(re.search(r'^#{1,6}\s+', content, re.MULTILINE))
        has_lists = bool(re.search(r'^\s*[-*+]\s+', content, re.MULTILINE))
        has_numbered_lists = bool(re.search(r'^\s*\d+\.\s+', content, re.MULTILINE))

        content_length = len(content.strip())

        # Long responses should have structure
        if content_length > 200 and not (has_headers or has_lists or has_numbered_lists):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                code="MISSING_STRUCTURE",
                message="Long responses should be structured with headers or lists",
                suggestion="Consider using markdown formatting to improve readability"
            ))

        # Check for code blocks in technical responses
        if agent_type == AgentType.TECHNICAL_DEVELOPER and message_type == MessageType.SOLUTION:
            if '```' not in content and content_length > 100:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    code="MISSING_CODE_BLOCKS",
                    message="Technical solutions might benefit from code examples",
                    suggestion="Consider including code snippets in formatted code blocks"
                ))

        return issues

    def _validate_content_quality(
        self,
        content: str,
        message_type: MessageType,
        agent_type: AgentType
    ) -> List[ValidationIssue]:
        """Validate content quality metrics"""
        issues = []

        # Check sentence length
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]

        if sentences:
            avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
            if avg_sentence_length > 30:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    code="LONG_SENTENCES",
                    message="Average sentence length is quite long",
                    suggestion="Consider using shorter sentences for better readability"
                ))
            elif avg_sentence_length < 5:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    code="SHORT_SENTENCES",
                    message="Average sentence length is very short",
                    suggestion="Consider using more complex sentences to convey more detail"
                ))

        # Check paragraph structure
        paragraphs = content.split('\n\n')
        if len(paragraphs) > 1:
            long_paragraphs = [p for p in paragraphs if len(p.strip()) > 500]
            if long_paragraphs:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    code="LONG_PARAGRAPHS",
                    message="Response contains very long paragraphs",
                    suggestion="Consider breaking up long paragraphs for better readability"
                ))

        return issues

    def _calculate_confidence_score(self, issues: List[ValidationIssue], content: str) -> float:
        """Calculate confidence score based on validation issues"""
        base_score = 1.0

        # Deduct points based on issue severity
        severity_penalties = {
            ValidationSeverity.CRITICAL: 0.5,
            ValidationSeverity.ERROR: 0.2,
            ValidationSeverity.WARNING: 0.1,
            ValidationSeverity.INFO: 0.05
        }

        for issue in issues:
            base_score -= severity_penalties.get(issue.severity, 0)

        # Ensure score doesn't go below 0
        base_score = max(0.0, base_score)

        # Add points for content quality
        content_length = len(content.strip())
        if content_length > 100:
            base_score += 0.1
        if content_length > 500:
            base_score += 0.1

        # Add points for structure
        if any(indicator in content for indicator in ['##', '###', '1.', '-', '*']):
            base_score += 0.1

        # Cap at 1.0
        return min(1.0, base_score)

    def _apply_corrections(
        self,
        content: str,
        issues: List[ValidationIssue],
        agent_type: AgentType
    ) -> Optional[str]:
        """Apply automatic corrections to content if possible"""
        corrected = content

        # Apply whitespace corrections
        whitespace_issues = [i for i in issues if i.code == "EXCESSIVE_WHITESPACE"]
        if whitespace_issues:
            # Normalize whitespace
            corrected = re.sub(r'\s+', ' ', corrected).strip()
            corrected = re.sub(r'\n\s*\n\s*\n', '\n\n', corrected)

        # Apply formatting corrections
        if any(i.code == "MISSING_STRUCTURE" for i in issues) and len(corrected) > 200:
            # Add basic structure if completely missing
            if not any(indicator in corrected for indicator in ['#', '##', '###']):
                lines = corrected.split('\n')
                if len(lines) > 3:
                    # Make first line a header
                    lines[0] = f"# {lines[0]}"
                    corrected = '\n'.join(lines)

        # Return corrected content if changes were made
        return corrected if corrected != content else None

    def _load_validation_rules(self) -> Dict[str, Any]:
        """Load validation rules configuration"""
        return {
            "min_content_length": 10,
            "max_whitespace_ratio": 0.5,
            "min_context_overlap": 0.1,
            "max_sentence_length": 30,
            "min_sentence_length": 5,
            "max_paragraph_length": 500,
            "structure_threshold": 200
        }

    def _load_correction_patterns(self) -> Dict[str, str]:
        """Load correction patterns for automatic fixes"""
        return {
            "excessive_whitespace": r'\s+',
            "multiple_newlines": r'\n\s*\n\s*\n',
            "missing_period": r'([a-zA-Z0-9])\s*$',
            "repeated_spaces": r'  +'
        }


class ResponseQualityAssessor:
    """Assesses the quality of agent responses"""

    def __init__(self):
        pass

    def assess_quality(
        self,
        content: str,
        agent_type: AgentType,
        message_type: MessageType,
        context: Optional[AgentContext] = None
    ) -> Dict[str, Any]:
        """
        Assess response quality across multiple dimensions

        Returns:
            Dictionary with quality scores and assessments
        """
        return {
            "clarity_score": self._assess_clarity(content),
            "completeness_score": self._assess_completeness(content, message_type, agent_type),
            "relevance_score": self._assess_relevance(content, context) if context else 0.0,
            "structure_score": self._assess_structure(content),
            "readability_score": self._assess_readability(content),
            "overall_score": 0.0,  # Will be calculated
            "word_count": len(content.split()),
            "character_count": len(content),
            "assessment_metadata": {
                "agent_type": agent_type.value,
                "message_type": message_type,
                "assessment_timestamp": datetime.utcnow().isoformat()
            }
        }

    def _assess_clarity(self, content: str) -> float:
        """Assess content clarity"""
        score = 0.5  # Base score

        # Penalize very long sentences
        sentences = re.split(r'[.!?]+', content)
        long_sentences = [s for s in sentences if len(s.split()) > 25]
        if long_sentences:
            score -= min(0.3, len(long_sentences) * 0.1)

        # Reward clear structure
        if re.search(r'^#{1,6}\s+', content, re.MULTILINE):
            score += 0.2

        # Reward lists and bullet points
        if re.search(r'^\s*[-*+]\s+', content, re.MULTILINE):
            score += 0.2

        # Penalize jargon overload (simple heuristic)
        jargon_indicators = ['utilize', 'leverage', 'synergize', 'paradigm', 'holistic']
        jargon_count = sum(1 for word in jargon_indicators if word in content.lower())
        if jargon_count > 2:
            score -= min(0.2, jargon_count * 0.05)

        return max(0.0, min(1.0, score))

    def _assess_completeness(self, content: str, message_type: MessageType, agent_type: AgentType) -> float:
        """Assess content completeness for the given message type and agent"""
        score = 0.5  # Base score
        content_lower = content.lower()

        # Agent-specific completeness checks
        if agent_type == AgentType.PRODUCT_MANAGER and message_type == MessageType.REQUIREMENT:
            required_elements = ['user', 'need', 'requirement', 'feature']
            found_elements = sum(1 for element in required_elements if element in content_lower)
            score += (found_elements / len(required_elements)) * 0.3

        elif agent_type == AgentType.TECHNICAL_DEVELOPER and message_type == MessageType.SOLUTION:
            required_elements = ['solution', 'implement', 'approach', 'technical']
            found_elements = sum(1 for element in required_elements if element in content_lower)
            score += (found_elements / len(required_elements)) * 0.3

        elif agent_type == AgentType.TEAM_LEAD and message_type in [MessageType.APPROVAL, MessageType.REJECTION]:
            required_elements = ['approve', 'accept', 'good'] if message_type == MessageType.APPROVAL else ['improve', 'suggest', 'modify']
            found_elements = sum(1 for element in required_elements if element in content_lower)
            score += (found_elements / len(required_elements)) * 0.3

        # Length-based completeness (longer responses tend to be more complete)
        word_count = len(content.split())
        if word_count > 50:
            score += 0.2
        elif word_count > 100:
            score += 0.3

        return max(0.0, min(1.0, score))

    def _assess_relevance(self, content: str, context: AgentContext) -> float:
        """Assess relevance to conversation context"""
        if not context.user_requirements:
            return 0.5  # No context to assess against

        score = 0.0
        req_words = set(context.user_requirements.lower().split())
        content_words = set(content.lower().split())

        # Word overlap score
        if req_words:
            overlap = len(req_words.intersection(content_words))
            score = overlap / len(req_words)

        # Boost score if addresses iteration context
        if context.current_iteration > 0:
            iteration_words = ['iteration', 'refine', 'improve', 'feedback', 'revise']
            if any(word in content.lower() for word in iteration_words):
                score += 0.2

        return max(0.0, min(1.0, score))

    def _assess_structure(self, content: str) -> float:
        """Assess content structure"""
        score = 0.3  # Base score

        # Headers
        headers = len(re.findall(r'^#{1,6}\s+', content, re.MULTILINE))
        if headers > 0:
            score += min(0.3, headers * 0.1)

        # Lists
        lists = len(re.findall(r'^\s*[-*+]\s+', content, re.MULTILINE))
        if lists > 0:
            score += min(0.2, lists * 0.05)

        # Numbered lists
        numbered_lists = len(re.findall(r'^\s*\d+\.\s+', content, re.MULTILINE))
        if numbered_lists > 0:
            score += min(0.2, numbered_lists * 0.05)

        # Code blocks
        code_blocks = len(re.findall(r'```[^`]+```', content))
        if code_blocks > 0:
            score += min(0.2, code_blocks * 0.1)

        return max(0.0, min(1.0, score))

    def _assess_readability(self, content: str) -> float:
        """Assess content readability"""
        score = 0.5  # Base score

        # Sentence length analysis
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]

        if sentences:
            avg_length = sum(len(s.split()) for s in sentences) / len(sentences)
            # Optimal range is 10-20 words per sentence
            if 10 <= avg_length <= 20:
                score += 0.3
            elif 5 <= avg_length <= 25:
                score += 0.2
            else:
                score -= 0.1

        # Paragraph length
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        if paragraphs:
            avg_para_length = sum(len(p.split()) for p in paragraphs) / len(paragraphs)
            # Optimal range is 30-100 words per paragraph
            if 30 <= avg_para_length <= 100:
                score += 0.2
            elif avg_para_length > 150:
                score -= 0.1

        return max(0.0, min(1.0, score))


# Global validator instances
_response_validator = None
_quality_assessor = None


def get_response_validator() -> ResponseValidator:
    """Get or create response validator instance"""
    global _response_validator
    if _response_validator is None:
        _response_validator = ResponseValidator()
    return _response_validator


def get_quality_assessor() -> ResponseQualityAssessor:
    """Get or create quality assessor instance"""
    global _quality_assessor
    if _quality_assessor is None:
        _quality_assessor = ResponseQualityAssessor()
    return _quality_assessor