"""
AI Agent Prompt Generator - Main FastAPI Application
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import uvicorn

from src.api import sessions, agents, user_input, clarifying_questions, history
from src.websocket import websocket_handler
from src.core.config import settings
from src.core.logging import setup_logging
from src.core.exceptions import setup_exception_handlers
from src.database.connection import init_db
from src.database.redis_client import init_redis

# Setup logging
setup_logging()
logger = setup_logging().get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting AI Agent Prompt Generator...")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Initialize Redis
    init_redis()
    logger.info("Redis initialized")

    yield

    # Shutdown
    logger.info("Shutting down AI Agent Prompt Generator...")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI Agent Prompt Generator - Create detailed LLM prompts through collaborative AI agents",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup trusted hosts
if not settings.DEBUG:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "*.example.com"]
    )

# Setup exception handlers
setup_exception_handlers(app)

# Include API routers
app.include_router(sessions.router, prefix="/v1/sessions", tags=["sessions"])
app.include_router(agents.router, prefix="/v1/agents", tags=["agents"])
app.include_router(user_input.router, prefix="/v1", tags=["user-input"])
app.include_router(clarifying_questions.router, prefix="/v1", tags=["clarifying-questions"])
app.include_router(history.router, prefix="/v1/history", tags=["history"])

# Include WebSocket router
app.include_router(websocket_handler.router, prefix="/ws")

# Health check endpoint
@app.get("/v1/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "timestamp": "2025-11-03T10:00:00Z",
        "dependencies": {
            "database": "healthy",  # TODO: Add actual health check
            "llm_api": "healthy",   # TODO: Add actual health check
            "redis": "healthy"       # TODO: Add actual health check
        }
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI Agent Prompt Generator API",
        "version": settings.APP_VERSION,
        "docs": "/docs" if settings.DEBUG else "Documentation not available in production"
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )