"""
Mock GLM API for testing
"""

from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock
import json


class MockGLMResponse:
    """Mock GLM API response"""

    def __init__(self, content: str, model: str = "glm-4", usage: Optional[Dict[str, int]] = None):
        self.choices = [{
            "message": {
                "content": content,
                "role": "assistant"
            }
        }]
        self.model = model
        self.usage = usage or {
            "prompt_tokens": 100,
            "completion_tokens": 200,
            "total_tokens": 300
        }
        self.created = 1699000000


class MockGLMAPI:
    """Mock GLM API client for testing"""

    def __init__(self):
        self.chat = AsyncMock()
        self.responses: Dict[str, MockGLMResponse] = {}
        self.call_history: List[Dict[str, Any]] = []

        # Setup default responses
        self._setup_default_responses()

    def _setup_default_responses(self):
        """Setup default mock responses"""
        self.responses["product_manager_requirement"] = MockGLMResponse(
            "Based on your requirement, I'll create a detailed product specification that includes user stories, acceptance criteria, and technical requirements for a customer service chatbot."
        )

        self.responses["technical_developer_solution"] = MockGLMResponse(
            "I'll design a technical solution using modern web technologies with natural language processing capabilities, real-time messaging, and scalable architecture for the customer service chatbot."
        )

        self.responses["team_lead_approval"] = MockGLMResponse(
            "The proposed solution meets all requirements. I approve this approach and recommend proceeding with implementation. The technical architecture is sound and aligns with the product specifications."
        )

        self.responses["team_lead_rejection"] = MockGLMResponse(
            "The current approach needs refinement. Please address the following concerns: scalability limitations, missing error handling, and insufficient user experience considerations."
        )

    async def create_chat_completion(self, messages: List[Dict[str, str]], model: str = "glm-4", **kwargs) -> MockGLMResponse:
        """Mock chat completion method"""
        # Record the call for testing verification
        self.call_history.append({
            "messages": messages,
            "model": model,
            "kwargs": kwargs
        })

        # Determine appropriate response based on the last message content
        if not messages:
            return self.responses["product_manager_requirement"]

        last_message = messages[-1]["content"].lower()

        # Simple content-based response selection
        if "product manager" in last_message or "requirement" in last_message:
            return self.responses["product_manager_requirement"]
        elif "technical" in last_message or "solution" in last_message:
            return self.responses["technical_developer_solution"]
        elif "approve" in last_message or "good" in last_message:
            return self.responses["team_lead_approval"]
        elif "reject" in last_message or "problem" in last_message:
            return self.responses["team_lead_rejection"]
        else:
            # Default response
            return MockGLMResponse("I understand your request and will provide a detailed response.")

    def get_call_history(self) -> List[Dict[str, Any]]:
        """Get the history of API calls"""
        return self.call_history.copy()

    def clear_call_history(self):
        """Clear the call history"""
        self.call_history.clear()

    def set_custom_response(self, key: str, response: MockGLMResponse):
        """Set a custom response for testing"""
        self.responses[key] = response

    def simulate_api_error(self, error_type: str = "rate_limit"):
        """Simulate an API error"""
        if error_type == "rate_limit":
            raise Exception("Rate limit exceeded")
        elif error_type == "auth_error":
            raise Exception("Authentication failed")
        elif error_type == "server_error":
            raise Exception("Internal server error")
        else:
            raise Exception(f"Simulated API error: {error_type}")


# Global mock instance
mock_glm_api = MockGLMAPI()


def get_mock_glm_api() -> MockGLMAPI:
    """Get the global mock GLM API instance"""
    return mock_glm_api


def reset_mock_glm_api():
    """Reset the global mock GLM API instance"""
    global mock_glm_api
    mock_glm_api = MockGLMAPI()