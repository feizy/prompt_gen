"""
Unit tests for GLM API client
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import json
from datetime import datetime

from backend.src.services.glm_api import GLMClient, GLMRequest, GLMResponse, GLMMessage
from backend.src.services.exceptions import GLMError, RateLimitError, AuthenticationError


class TestGLMClient:
    """Test cases for GLM API client"""

    @pytest.fixture
    def client(self):
        """Create GLM client instance for testing"""
        return GLMClient(
            api_key="test_key",
            base_url="https://api.test.com",
            model="glm-4",
            max_retries=2
        )

    @pytest.fixture
    def mock_response(self):
        """Create mock HTTP response"""
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.headers = {"content-type": "application/json"}
        return mock_resp

    def test_initialization(self):
        """Test GLM client initialization"""
        client = GLMClient(
            api_key="test_key",
            model="glm-4",
            timeout=30,
            max_retries=3
        )

        assert client.api_key == "test_key"
        assert client.model == "glm-4"
        assert client.timeout == 30
        assert client.max_retries == 3
        assert client.base_url == "https://open.bigmodel.cn/api/paas/v4"

    def test_initialization_with_custom_base_url(self):
        """Test GLM client initialization with custom base URL"""
        client = GLMClient(
            api_key="test_key",
            base_url="https://custom.api.com",
            model="glm-4"
        )

        assert client.base_url == "https://custom.api.com"

    def test_prepare_request(self, client):
        """Test request preparation"""
        messages = [
            GLMMessage(role="user", content="Hello"),
            GLMMessage(role="assistant", content="Hi there!")
        ]

        request = GLMRequest(
            model="glm-4",
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )

        result = client._prepare_request(request)

        assert result["model"] == "glm-4"
        assert len(result["messages"]) == 2
        assert result["temperature"] == 0.7
        assert result["max_tokens"] == 1000
        assert result["stream"] is False

    def test_prepare_request_with_system_message(self, client):
        """Test request preparation with system message"""
        messages = [
            GLMMessage(role="system", content="You are a helpful assistant"),
            GLMMessage(role="user", content="Hello")
        ]

        request = GLMRequest(model="glm-4", messages=messages)
        result = client._prepare_request(request)

        assert len(result["messages"]) == 2
        assert result["messages"][0]["role"] == "system"
        assert result["messages"][1]["role"] == "user"

    @pytest.mark.asyncio
    async def test_successful_completion(self, client, mock_response):
        """Test successful API completion"""
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "Hello! How can I help you?",
                    "role": "assistant"
                },
                "finish_reason": "stop",
                "index": 0
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 15,
                "total_tokens": 25
            },
            "model": "glm-4",
            "id": "test-id",
            "created": int(datetime.now().timestamp())
        }

        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response

            messages = [GLMMessage(role="user", content="Hello")]
            request = GLMRequest(model="glm-4", messages=messages)

            response = await client.complete(request)

            assert response.content == "Hello! How can I help you?"
            assert response.role == "assistant"
            assert response.finish_reason == "stop"
            assert response.usage.prompt_tokens == 10
            assert response.usage.completion_tokens == 15
            assert response.usage.total_tokens == 25

    @pytest.mark.asyncio
    async def test_authentication_error(self, client, mock_response):
        """Test authentication error handling"""
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": {"message": "Invalid API key"}}

        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response

            messages = [GLMMessage(role="user", content="Hello")]
            request = GLMRequest(model="glm-4", messages=messages)

            with pytest.raises(AuthenticationError) as exc_info:
                await client.complete(request)

            assert "Invalid API key" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_rate_limit_error(self, client, mock_response):
        """Test rate limit error handling"""
        mock_response.status_code = 429
        mock_response.headers = {"retry-after": "60"}
        mock_response.json.return_value = {
            "error": {"message": "Rate limit exceeded"}
        }

        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response

            messages = [GLMMessage(role="user", content="Hello")]
            request = GLMRequest(model="glm-4", messages=messages)

            with pytest.raises(RateLimitError) as exc_info:
                await client.complete(request)

            assert "Rate limit exceeded" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_server_error_with_retry(self, client, mock_response):
        """Test server error with retry mechanism"""
        # First call fails
        mock_response_fail = Mock()
        mock_response_fail.status_code = 500

        # Second call succeeds
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            "choices": [{
                "message": {
                    "content": "Success after retry",
                    "role": "assistant"
                },
                "finish_reason": "stop",
                "index": 0
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "model": "glm-4"
        }

        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.side_effect = [
                mock_response_fail,
                mock_response_success
            ]

            messages = [GLMMessage(role="user", content="Hello")]
            request = GLMRequest(model="glm-4", messages=messages)

            response = await client.complete(request)

            assert response.content == "Success after retry"
            assert mock_post.call_count == 2

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, client, mock_response):
        """Test max retries exceeded"""
        mock_response.status_code = 500

        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response

            messages = [GLMMessage(role="user", content="Hello")]
            request = GLMRequest(model="glm-4", messages=messages)

            with pytest.raises(GLMError) as exc_info:
                await client.complete(request)

            assert "Max retries exceeded" in str(exc_info.value)
            assert mock_post.call_count == client.max_retries + 1  # Initial attempt + retries

    def test_validate_response_success(self, client):
        """Test successful response validation"""
        response_data = {
            "choices": [{
                "message": {
                    "content": "Hello",
                    "role": "assistant"
                },
                "finish_reason": "stop",
                "index": 0
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "model": "glm-4"
        }

        # Should not raise an exception
        client._validate_response(response_data)

    def test_validate_response_missing_choices(self, client):
        """Test response validation with missing choices"""
        response_data = {
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "model": "glm-4"
        }

        with pytest.raises(GLMError) as exc_info:
            client._validate_response(response_data)

        assert "Invalid response format" in str(exc_info.value)

    def test_validate_response_empty_choices(self, client):
        """Test response validation with empty choices"""
        response_data = {
            "choices": [],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "model": "glm-4"
        }

        with pytest.raises(GLMError) as exc_info:
            client._validate_response(response_data)

        assert "No choices in response" in str(exc_info.value)

    def test_parse_response_success(self, client):
        """Test successful response parsing"""
        response_data = {
            "choices": [{
                "message": {
                    "content": "Hello world",
                    "role": "assistant"
                },
                "finish_reason": "stop",
                "index": 0
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "model": "glm-4",
            "id": "test-id",
            "created": 1234567890
        }

        response = client._parse_response(response_data)

        assert response.content == "Hello world"
        assert response.role == "assistant"
        assert response.finish_reason == "stop"
        assert response.usage.prompt_tokens == 10
        assert response.usage.completion_tokens == 5
        assert response.usage.total_tokens == 15
        assert response.model == "glm-4"
        assert response.id == "test-id"
        assert response.created == 1234567890

    @pytest.mark.asyncio
    async def test_streaming_completion(self, client):
        """Test streaming completion (placeholder for future implementation)"""
        # This would test streaming functionality when implemented
        messages = [GLMMessage(role="user", content="Hello")]
        request = GLMRequest(model="glm-4", messages=messages, stream=True)

        # For now, streaming should raise NotImplementedError
        with pytest.raises(NotImplementedError):
            async for chunk in client.stream_complete(request):
                pass

    def test_rate_limiter_initialization(self, client):
        """Test rate limiter initialization"""
        assert client.rate_limiter is not None
        assert client.rate_limiter.max_requests_per_minute == 200
        assert client.rate_limiter.max_tokens_per_minute == 30000

    @pytest.mark.asyncio
    async def test_rate_limiter_acquire(self, client):
        """Test rate limiter acquire functionality"""
        # Should not raise an exception under normal circumstances
        await client.rate_limiter.acquire(tokens=100)

    def test_message_model_validation(self):
        """Test GLM message model validation"""
        # Valid message
        message = GLMMessage(role="user", content="Hello")
        assert message.role == "user"
        assert message.content == "Hello"

        # Message with optional fields
        message_with_name = GLMMessage(
            role="system",
            content="You are helpful",
            name="system_prompt"
        )
        assert message_with_name.name == "system_prompt"

    def test_request_model_validation(self):
        """Test GLM request model validation"""
        messages = [GLMMessage(role="user", content="Hello")]

        request = GLMRequest(
            model="glm-4",
            messages=messages,
            temperature=0.7,
            max_tokens=1000,
            top_p=0.9,
            stream=False
        )

        assert request.model == "glm-4"
        assert len(request.messages) == 1
        assert request.temperature == 0.7
        assert request.max_tokens == 1000
        assert request.top_p == 0.9
        assert request.stream is False

    def test_response_model_validation(self):
        """Test GLM response model validation"""
        from backend.src.services.glm_api import GLMUsage

        usage = GLMUsage(
            prompt_tokens=10,
            completion_tokens=15,
            total_tokens=25
        )

        response = GLMResponse(
            content="Hello world",
            role="assistant",
            finish_reason="stop",
            usage=usage,
            model="glm-4"
        )

        assert response.content == "Hello world"
        assert response.role == "assistant"
        assert response.finish_reason == "stop"
        assert response.usage.prompt_tokens == 10
        assert response.usage.completion_tokens == 15
        assert response.usage.total_tokens == 25
        assert response.model == "glm-4"


if __name__ == "__main__":
    pytest.main([__file__])