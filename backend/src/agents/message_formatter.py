"""
Agent message formatting utilities
"""

import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

from .interfaces import MessageType, AgentContext


class MessageFormatter:
    """Utility class for formatting agent messages"""

    @staticmethod
    def format_system_prompt(
        base_prompt: str,
        context: AgentContext,
        additional_instructions: Optional[str] = None
    ) -> str:
        """Format system prompt with context information"""
        prompt_parts = [base_prompt]

        # Add context information
        if context.user_requirements:
            prompt_parts.append(f"\nUser Requirements: {context.user_requirements}")

        if context.current_iteration > 0:
            prompt_parts.append(f"\nCurrent Iteration: {context.current_iteration}")

        if context.max_iterations:
            prompt_parts.append(f"\nMaximum Iterations: {context.max_iterations}")

        # Add supplementary inputs
        if context.supplementary_inputs:
            prompt_parts.append("\nSupplementary User Inputs:")
            for i, input_text in enumerate(context.supplementary_inputs, 1):
                prompt_parts.append(f"{i}. {input_text}")

        # Add clarifying questions
        if context.clarifying_questions:
            prompt_parts.append("\nClarifying Questions:")
            for question in context.clarifying_questions:
                prompt_parts.append(f"- {question.get('question_text', 'No question text')}")

        # Add additional instructions
        if additional_instructions:
            prompt_parts.append(f"\nAdditional Instructions: {additional_instructions}")

        # Add session metadata
        if context.metadata:
            prompt_parts.append(f"\nSession Metadata: {json.dumps(context.metadata, indent=2)}")

        return "\n".join(prompt_parts)

    @staticmethod
    def format_requirement_response(requirement: str, context: AgentContext) -> str:
        """Format requirement response with structure"""
        response_parts = []

        response_parts.append("# Product Requirements")
        response_parts.append("")
        response_parts.append(requirement)
        response_parts.append("")

        # Add structure indicators
        if "##" not in requirement:
            response_parts.append("## Acceptance Criteria")
            response_parts.append("")
            response_parts.append("- [ ] Requirements are clearly defined")
            response_parts.append("- [ ] User needs are addressed")
            response_parts.append("- [ ] Implementation approach is feasible")

        # Add iteration info
        if context.current_iteration > 0:
            response_parts.append("")
            response_parts.append(f"## Iteration {context.current_iteration}")
            response_parts.append("")
            response_parts.append("This is a refined requirement based on feedback from previous iterations.")

        return "\n".join(response_parts)

    @staticmethod
    def format_technical_solution(solution: str, context: AgentContext) -> str:
        """Format technical solution with structure"""
        response_parts = []

        response_parts.append("# Technical Solution")
        response_parts.append("")
        response_parts.append(solution)
        response_parts.append("")

        # Add structure indicators
        if "##" not in solution:
            response_parts.append("## Implementation Approach")
            response_parts.append("")
            response_parts.append("- [ ] Technical feasibility confirmed")
            response_parts.append("- [ ] Architecture is scalable")
            response_parts.append("- [ ] Security considerations addressed")

        # Add iteration info
        if context.current_iteration > 0:
            response_parts.append("")
            response_parts.append(f"## Iteration {context.current_iteration}")
            response_parts.append("")
            response_parts.append("This solution addresses feedback from previous iterations.")

        return "\n".join(response_parts)

    @staticmethod
    def format_review(review: str, context: AgentContext) -> str:
        """Format review with structure"""
        response_parts = []

        response_parts.append("# Review")
        response_parts.append("")
        response_parts.append(review)
        response_parts.append("")

        # Add review summary
        if "##" not in review:
            response_parts.append("## Summary")
            response_parts.append("")
            response_parts.append("This is my review of the current proposal.")

        return "\n".join(response_parts)

    @staticmethod
    def format_approval(approval: str, context: AgentContext) -> str:
        """Format approval message"""
        response_parts = []

        response_parts.append("# Approval")
        response_parts.append("")
        response_parts.append("✅ " + approval)
        response_parts.append("")
        response_parts.append("This proposal meets all requirements and is approved for implementation.")

        # Add final prompt generation if this is the final approval
        if context.current_iteration >= context.max_iterations - 1:
            response_parts.append("")
            response_parts.append("# Final Prompt")
            response_parts.append("")
            response_parts.append("Based on all the collaboration, here is the final prompt:")

        return "\n".join(response_parts)

    @staticmethod
    def format_rejection(rejection: str, context: AgentContext) -> str:
        """Format rejection message with structured feedback"""
        response_parts = []

        response_parts.append("# Rejection with Feedback")
        response_parts.append("")
        response_parts.append("❌ " + rejection)
        response_parts.append("")
        response_parts.append("I cannot approve this approach for the following reasons:")
        response_parts.append("")
        response_parts.append(rejection)
        response_parts.append("")
        response_parts.append("## Required Changes")
        response_parts.append("")
        response_parts.append("Please address these concerns and resubmit for review.")

        return "\n".join(response_parts)

    @staticmethod
    def format_clarifying_question(question: str, context: AgentContext) -> str:
        """Format clarifying question"""
        response_parts = []

        response_parts.append("# Clarifying Question")
        response_parts.append("")
        response_parts.append(question)
        response_parts.append("")
        response_parts.append("Please provide additional information to help me create better requirements.")

        return "\n".join(response_parts)

    @staticmethod
    def extract_action_items(content: str) -> List[str]:
        """Extract action items from content"""
        action_items = []

        # Look for action item patterns
        patterns = [
            r'- \[ \] (.+)',  # Markdown checkboxes
            r'\* (.+)',  # Bullet points
            r'\d+\.\s+(.+)',  # Numbered lists
        ]

        for pattern in patterns:
            matches = [match.strip() for match in re.findall(pattern, content, re.MULTILINE)]
            action_items.extend(matches)

        # Filter out non-action items
        filtered_items = [
            item for item in action_items
            if len(item) > 10  # Filter out very short items
            and not item.startswith('- [ ]')  # Filter out incomplete items
        ]

        return filtered_items

    @staticmethod
    def extract_key_points(content: str) -> List[str]:
        """Extract key points from content"""
        key_points = []

        # Look for bold text, headers, or important statements
        patterns = [
            r'\*\*(.+?)\*\*',  # Bold text
            r'^#{1,3}\s+(.+)$',  # Headers
            r'IMPORTANT:\s*(.+)',  # Important statements
            r'NOTE:\s*(.+)',  # Notes
        ]

        for pattern in patterns:
            matches = [match.strip() for match in re.findall(pattern, content, re.MULTILINE)]
            key_points.extend(matches)

        # Add sentences that indicate importance
        sentences = content.split('.')
        for sentence in sentences:
            sentence = sentence.strip()
            if any(indicator in sentence.lower() for indicator in ['must', 'should', 'critical', 'important', 'essential']):
                key_points.append(sentence)

        # Remove duplicates and empty items
        return list(set(filter(None, [kp.strip() for kp in key_points if kp.strip()])))

    @staticmethod
    def calculate_response_quality(content: str) -> Dict[str, Any]:
        """Calculate quality metrics for response"""
        quality_metrics = {
            "length": len(content),
            "word_count": len(content.split()),
            "has_structure": any(marker in content for marker in ['##', '###', '####']),
            "has_lists": any(marker in content for marker in ['\n* ', '\n- ', '\n1. ']),
            "has_code_blocks": '```' in content,
            "readability_score": 0.0
        }

        # Calculate readability score (simplified)
        sentences = content.split('.')
        if len(sentences) > 0:
            avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
            # Optimal sentence length is around 15-20 words
            if 10 <= avg_sentence_length <= 25:
                quality_metrics["readability_score"] = 1.0
            elif 5 <= avg_sentence_length <= 30:
                quality_metrics["readability_score"] = 0.8
            else:
                quality_metrics["readability_score"] = 0.6

        return quality_metrics

    @staticmethod
    def format_for_web_display(content: str) -> Dict[str, Any]:
        """Format content for web display"""
        return {
            "raw_content": content,
            "html_content": MessageFormatter._convert_markdown_to_html(content),
            "action_items": MessageFormatter.extract_action_items(content),
            "key_points": MessageFormatter.extract_key_points(content),
            "quality_metrics": MessageFormatter.calculate_response_quality(content),
            "formatted_at": datetime.utcnow().isoformat()
        }

    @staticmethod
    def _convert_markdown_to_html(content: str) -> str:
        """Convert basic markdown to HTML (simplified)"""
        # This is a very basic markdown to HTML converter
        # In production, you might want to use a proper markdown library
        html = content

        # Convert headers
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

        # Convert bold text
        html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)

        # Convert italic text
        html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)

        # Convert code blocks
        html = re.sub(r'```([^`]+)```', r'<pre><code>\1</code></pre>', html)

        # Convert code spans
        html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)

        # Convert links
        html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)

        # Convert line breaks
        html = html.replace('\n', '<br>')

        return html