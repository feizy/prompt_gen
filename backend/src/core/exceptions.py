"""
Custom exception classes for the application
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .logging import get_logger

logger = get_logger(__name__)


class BaseApplicationError(Exception):
    """Base exception for all application errors"""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(BaseApplicationError):
    """Raised when input validation fails"""

    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if field:
            details["field"] = field
        super().__init__(message, error_code="VALIDATION_ERROR", details=details)


class DatabaseError(BaseApplicationError):
    """Raised when database operations fail"""

    def __init__(self, message: str, operation: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if operation:
            details["operation"] = operation
        super().__init__(message, error_code="DATABASE_ERROR", details=details)


class GLMAPIError(BaseApplicationError):
    """Raised when GLM API calls fail"""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if status_code:
            details["status_code"] = status_code
        if response_data:
            details["response_data"] = response_data
        super().__init__(message, error_code="GLM_API_ERROR", details=details)


class AgentError(BaseApplicationError):
    """Raised when agent operations fail"""

    def __init__(
        self,
        message: str,
        agent_type: Optional[str] = None,
        session_id: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if agent_type:
            details["agent_type"] = agent_type
        if session_id:
            details["session_id"] = session_id
        super().__init__(message, error_code="AGENT_ERROR", details=details)


class SessionError(BaseApplicationError):
    """Raised when session operations fail"""

    def __init__(
        self,
        message: str,
        session_id: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if session_id:
            details["session_id"] = session_id
        super().__init__(message, error_code="SESSION_ERROR", details=details)


class AuthenticationError(BaseApplicationError):
    """Raised when authentication fails"""

    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(message, error_code="AUTHENTICATION_ERROR", details=kwargs.get("details", {}))


class AuthorizationError(BaseApplicationError):
    """Raised when authorization fails"""

    def __init__(self, message: str = "Access denied", **kwargs):
        super().__init__(message, error_code="AUTHORIZATION_ERROR", details=kwargs.get("details", {}))


class RateLimitError(BaseApplicationError):
    """Raised when rate limits are exceeded"""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if retry_after:
            details["retry_after"] = retry_after
        super().__init__(message, error_code="RATE_LIMIT_ERROR", details=details)


class TimeoutError(BaseApplicationError):
    """Raised when operations timeout"""

    def __init__(
        self,
        message: str,
        timeout_seconds: Optional[int] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if timeout_seconds:
            details["timeout_seconds"] = timeout_seconds
        if operation:
            details["operation"] = operation
        super().__init__(message, error_code="TIMEOUT_ERROR", details=details)


# HTTP Exception helpers
def create_http_exception(
    status_code: int,
    message: str,
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> HTTPException:
    """Create an HTTP exception with standardized format"""
    return HTTPException(
        status_code=status_code,
        detail={
            "error": error_code or "HTTP_ERROR",
            "message": message,
            "details": details or {}
        }
    )


# Exception handlers
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle FastAPI validation errors"""
    logger.warning(
        "Validation error",
        path=request.url.path,
        method=request.method,
        errors=exc.errors()
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Invalid request data",
            "details": {
                "validation_errors": exc.errors()
            }
        }
    )


async def application_exception_handler(request: Request, exc: BaseApplicationError) -> JSONResponse:
    """Handle application-specific exceptions"""
    logger.error(
        "Application error",
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details,
        path=request.url.path,
        method=request.method
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "details": exc.details
        }
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle HTTP exceptions"""
    logger.warning(
        "HTTP error",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
        method=request.method
    )

    # Extract structured detail if it's already in our format
    if isinstance(exc.detail, dict):
        content = exc.detail
    else:
        content = {
            "error": "HTTP_ERROR",
            "message": str(exc.detail),
            "details": {}
        }

    return JSONResponse(
        status_code=exc.status_code,
        content=content
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions"""
    logger.error(
        "Unexpected error",
        error_type=type(exc).__name__,
        message=str(exc),
        path=request.url.path,
        method=request.method,
        exc_info=True
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
            "details": {
                "error_type": type(exc).__name__
            }
        }
    )


def setup_exception_handlers(app) -> None:
    """Setup all exception handlers for the FastAPI application"""
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(BaseApplicationError, application_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)