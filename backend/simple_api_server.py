"""
Simple FastAPI server for agent orchestration without database dependencies
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio
import logging

from src.agents.orchestration_engine import AgentOrchestrationEngine

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI Agent Orchestration API",
    version="1.0.0",
    description="Simple API for AI Agent Orchestration without database dependencies"
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize orchestration engine
orchestration_engine = AgentOrchestrationEngine()


class StartSessionRequest(BaseModel):
    user_requirements: str
    max_iterations: int = 5
    session_id: Optional[str] = None


class UserInputRequest(BaseModel):
    session_id: str
    user_input: str
    supplementary_inputs: Optional[List[str]] = None


class SessionResponse(BaseModel):
    session_id: str
    status: str
    current_iteration: int
    max_iterations: int
    agent_responses: Dict[str, Any]
    next_agent: Optional[str]
    requires_user_input: bool
    clarifying_questions: List[str]
    completed: bool
    final_prompt: Optional[str] = None


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI Agent Orchestration API",
        "version": "1.0.0",
        "status": "active",
        "docs": "/docs"
    }


@app.get("/test")
async def test_endpoint():
    """Simple test endpoint"""
    return {"message": "Agent Orchestration API is working!", "status": "active"}


@app.post("/api/v1/sessions/start", response_model=SessionResponse)
async def start_session(request: StartSessionRequest):
    """Start a new agent orchestration session"""
    try:
        logger.info(f"Starting new session for requirements: {request.user_requirements[:100]}...")

        response = await orchestration_engine.start_prompt_generation_session(
            user_requirements=request.user_requirements,
            session_id=request.session_id,
            max_iterations=request.max_iterations
        )

        logger.info(f"Session {response['session_id']} started successfully")
        return SessionResponse(**response)

    except Exception as e:
        logger.error(f"Failed to start session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/sessions/{session_id}/input")
async def process_user_input(session_id: str, request: UserInputRequest):
    """Process user input for a session"""
    try:
        logger.info(f"Processing user input for session: {session_id}")

        response = await orchestration_engine.process_user_input(
            session_id=session_id,
            user_input=request.user_input,
            supplementary_inputs=request.supplementary_inputs
        )

        logger.info(f"User input processed for session: {session_id}")
        return SessionResponse(**response)

    except Exception as e:
        logger.error(f"Failed to process user input for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/sessions/{session_id}/continue")
async def continue_session(session_id: str):
    """Continue session without additional user input"""
    try:
        logger.info(f"Continuing session without input: {session_id}")

        response = await orchestration_engine.continue_without_input(session_id)

        logger.info(f"Session continued: {session_id}")
        return SessionResponse(**response)

    except Exception as e:
        logger.error(f"Failed to continue session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/sessions/{session_id}/status")
async def get_session_status(session_id: str):
    """Get session status"""
    try:
        status = await orchestration_engine.get_session_status(session_id)
        return status
    except Exception as e:
        logger.error(f"Failed to get session status {session_id}: {e}")
        raise HTTPException(status_code=404, detail="Session not found")


@app.get("/api/v1/sessions/{session_id}/conversation")
async def get_conversation_history(session_id: str):
    """Get conversation history for a session"""
    try:
        conversation = await orchestration_engine.get_conversation_history(session_id)
        return {"session_id": session_id, "conversation": conversation}
    except Exception as e:
        logger.error(f"Failed to get conversation history {session_id}: {e}")
        raise HTTPException(status_code=404, detail="Session not found")


@app.get("/api/v1/engine/status")
async def get_engine_status():
    """Get orchestration engine status"""
    try:
        status = orchestration_engine.get_engine_status()
        return status
    except Exception as e:
        logger.error(f"Failed to get engine status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/sessions/{session_id}")
async def cleanup_session(session_id: str):
    """Clean up a completed session"""
    try:
        success = await orchestration_engine.cleanup_session(session_id)
        return {"success": success, "message": "Session cleaned up successfully" if success else "Session not found or not completed"}
    except Exception as e:
        logger.error(f"Failed to cleanup session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    try:
        engine_status = orchestration_engine.get_engine_status()
        return {
            "status": "healthy",
            "engine": engine_status,
            "version": "1.0.0"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "version": "1.0.0"
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "simple_api_server:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )