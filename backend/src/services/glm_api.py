"""
GLM API service for LLM interactions
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Union
from enum import Enum
import json
import httpx
from pydantic import BaseModel, Field

from ..core.config import settings
from ..core.logging import get_logger
from ..core.exceptions import GLMAPIError, TimeoutError

logger = get_logger(__name__)


class GLMModel(str, Enum):
    """Available GLM models"""
    GLM_4 = "glm-4"
    GLM_4_TURBO = "glm-4-turbo"
    GLM_4_TURBO_VISION = "glm-4-turbo-vision"
    GLM_4_LONG = "glm-4-long"


class GLMMessage(BaseModel):
    """GLM API message format"""
    role: str = Field(..., description="Message role: system, user, or assistant")
    content: str = Field(..., description="Message content")
    name: Optional[str] = Field(None, description="Optional message name")


class GLMChatRequest(BaseModel):
    """GLM chat completion request"""
    model: GLMModel
    messages: List[GLMMessage]
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(2000, ge=1, le=8192, description="Maximum tokens in response")
    top_p: float = Field(0.9, ge=0.0, le=1.0, description="Nucleus sampling parameter")
    stream: bool = Field(False, description="Whether to stream response")
    stop: Optional[Union[str, List[str]]] = Field(None, description="Stop sequences")


class GLMChatResponse(BaseModel):
    """GLM chat completion response"""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]
    system_fingerprint: Optional[str] = None


class GLMApiClient:
    """GLM API client with authentication and error handling"""

    def __init__(self):
        self.base_url = settings.GLM_BASE_URL
        self.api_key = settings.GLM_API_KEY
        self.default_model = GLMModel(settings.GLM_MODEL)
        self.timeout = settings.GLM_TIMEOUT
        self.max_retries = settings.GLM_MAX_RETRIES

        # Rate limiting
        self.rate_limiter = RateLimiter()

        # Usage tracking
        self.usage_tracker = UsageTracker()

        # HTTP client
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers=self._get_headers()
        )

        logger.info("GLM API client initialized", model=self.default_model.value)

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for API requests"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "AI-Agent-Prompt-Generator/1.0.0"
        }

    async def chat_completion(
        self,
        messages: List[Union[GLMMessage, Dict[str, Any]]],
        model: Optional[GLMModel] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> GLMChatResponse:
        """
        Create a chat completion with GLM API

        Args:
            messages: List of messages in the conversation
            model: GLM model to use (defaults to configured model)
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens in response
            **kwargs: Additional parameters

        Returns:
            GLM chat completion response

        Raises:
            GLMAPIError: If API call fails
            TimeoutError: If request times out
        """
        # Rate limiting
        await self.rate_limiter.wait_if_needed()

        # Prepare request
        model = model or self.default_model
        temperature = temperature if temperature is not None else 0.7
        max_tokens = max_tokens if max_tokens is not None else 2000

        # Convert messages to proper format
        formatted_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                formatted_messages.append(GLMMessage(**msg))
            else:
                formatted_messages.append(msg)

        request_data = GLMChatRequest(
            model=model,
            messages=formatted_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )

        logger.info(
            "Making GLM API request",
            model=model.value,
            message_count=len(formatted_messages),
            temperature=temperature,
            max_tokens=max_tokens
        )

        # Implement retry logic with exponential backoff
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                response = await self._make_request(
                    endpoint="chat/completions",
                    data=request_data.dict(exclude_none=True)
                )

                # Parse response
                parsed_response = GLMChatResponse(**response)

                # Track usage
                self.usage_tracker.track_usage(
                    model=model,
                    usage=parsed_response.usage
                )

                logger.info(
                    "GLM API request successful",
                    response_id=parsed_response.id,
                    tokens_used=parsed_response.usage.get("total_tokens", 0)
                )

                return parsed_response

            except httpx.HTTPStatusError as e:
                last_exception = e
                error_data = e.response.json() if e.response.content else {}
                logger.warning(
                    "GLM API HTTP error",
                    status_code=e.response.status_code,
                    error_data=error_data,
                    attempt=attempt + 1,
                    max_retries=self.max_retries
                )

                if self._should_retry(e.response.status_code) and attempt < self.max_retries:
                    await asyncio.sleep(self._get_backoff_delay(attempt))
                    continue

                raise GLMAPIError(
                    message=f"GLM API HTTP error: {e.response.status_code}",
                    status_code=e.response.status_code,
                    response_data=error_data
                )

            except httpx.TimeoutException as e:
                last_exception = e
                logger.warning(
                    "GLM API timeout",
                    attempt=attempt + 1,
                    timeout=self.timeout
                )

                if attempt < self.max_retries:
                    await asyncio.sleep(self._get_backoff_delay(attempt))
                    continue

                raise TimeoutError(
                    message=f"GLM API timeout after {self.timeout}s",
                    timeout_seconds=self.timeout
                )

            except Exception as e:
                last_exception = e
                logger.error(
                    "GLM API unexpected error",
                    error=str(e),
                    attempt=attempt + 1
                )

                if attempt < self.max_retries:
                    await asyncio.sleep(self._get_backoff_delay(attempt))
                    continue

                raise GLMAPIError(
                    message=f"GLM API unexpected error: {str(e)}",
                    details={"error_type": type(e).__name__}
                )

        # If we get here, all retries failed
        if last_exception:
            raise last_exception

    async def _make_request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP request to GLM API"""
        response = await self.client.post(
            endpoint,
            json=data
        )
        response.raise_for_status()
        return response.json()

    def _should_retry(self, status_code: int) -> bool:
        """Determine if request should be retried based on status code"""
        retryable_codes = [
            429,  # Rate limited
            502,  # Bad gateway
            503,  # Service unavailable
            504,  # Gateway timeout
        ]
        return status_code in retryable_codes

    def _get_backoff_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay"""
        base_delay = 1.0
        max_delay = 60.0
        delay = min(base_delay * (2 ** attempt), max_delay)
        return delay

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
        logger.info("GLM API client closed")


class RateLimiter:
    """Simple rate limiter for API calls"""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests = []
        self.lock = asyncio.Lock()

    async def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        async with self.lock:
            now = time.time()
            # Remove requests older than 1 minute
            self.requests = [req_time for req_time in self.requests if now - req_time < 60]

            if len(self.requests) >= self.requests_per_minute:
                # Calculate wait time
                oldest_request = min(self.requests)
                wait_time = 60 - (now - oldest_request)
                if wait_time > 0:
                    logger.info(f"Rate limiting - waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)

            self.requests.append(now)


class UsageTracker:
    """Track API usage for monitoring and cost calculation"""

    def __init__(self):
        self.total_tokens = 0
        self.total_requests = 0
        self.model_usage = {}
        self.start_time = time.time()

    def track_usage(self, model: GLMModel, usage: Dict[str, int]):
        """Track API usage"""
        self.total_requests += 1
        self.total_tokens += usage.get("total_tokens", 0)

        model_name = model.value
        if model_name not in self.model_usage:
            self.model_usage[model_name] = {
                "requests": 0,
                "tokens": 0
            }

        self.model_usage[model_name]["requests"] += 1
        self.model_usage[model_name]["tokens"] += usage.get("total_tokens", 0)

    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        runtime = time.time() - self.start_time
        return {
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "runtime_seconds": runtime,
            "requests_per_minute": self.total_requests / max(runtime / 60, 1),
            "model_usage": self.model_usage
        }


# Global GLM API client instance
_glm_client: Optional[GLMApiClient] = None


async def get_glm_client() -> GLMApiClient:
    """Get or create GLM API client instance"""
    global _glm_client
    if _glm_client is None:
        _glm_client = GLMApiClient()
    return _glm_client


async def close_glm_client():
    """Close GLM API client"""
    global _glm_client
    if _glm_client:
        await _glm_client.close()
        _glm_client = None