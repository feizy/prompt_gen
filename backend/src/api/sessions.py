"""
Session management API endpoints
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, desc, func

from ..database.connection import get_async_session, async_session_maker
from ..models.session import Session as SessionModel, AgentMessage
from ..agents.orchestration_engine import AgentOrchestrationEngine
from ..services.glm_api import GLMApiClient
from ..core.exceptions import SessionError
from ..core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Global orchestration engine instance
orchestration_engine = AgentOrchestrationEngine()

# Pydantic models for request/response
class SessionCreateRequest(BaseModel):
    """Request model for creating a new session"""
    user_input: str = Field(..., min_length=10, description="User's initial requirements")
    max_iterations: int = Field(default=5, ge=1, le=10, description="Maximum collaboration iterations")
    max_interventions: int = Field(default=3, ge=1, le=10, description="Maximum user interventions")

class SessionResponse(BaseModel):
    """Response model for session data"""
    id: str
    user_input: str
    status: str
    final_prompt: Optional[str]
    created_at: str
    updated_at: str
    completed_at: Optional[str]
    iteration_count: int
    user_intervention_count: int
    max_interventions: int
    waiting_for_user_since: Optional[str]
    current_question_id: Optional[str]
    metadata: Dict[str, Any]

class SessionListResponse(BaseModel):
    """Response model for session list"""
    sessions: List[SessionResponse]
    total_count: int
    page: int
    page_size: int

class SessionStartRequest(BaseModel):
    """Request model for starting session collaboration"""
    session_id: str

class AgentMessageResponse(BaseModel):
    """Response model for agent messages"""
    id: str
    session_id: str
    agent_type: str
    message_content: str
    message_type: str
    sequence_number: int
    parent_message_id: Optional[str]
    created_at: str
    processing_time_ms: Optional[int]
    metadata: Dict[str, Any]

class SessionMessagesResponse(BaseModel):
    """Response model for session messages"""
    session_id: str
    messages: List[AgentMessageResponse]
    total_count: int

@router.post("/", response_model=Dict[str, Any], status_code=201)
async def create_session(
    request: SessionCreateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Create a new prompt generation session

    This endpoint initializes a new collaboration session with the AI agents.
    The session will immediately start processing the user's requirements.
    """
    try:
        logger.info(f"Creating new session with input: {request.user_input[:100]}...")

        # Create session in database
        db_session = SessionModel(
            user_input=request.user_input,
            max_interventions=request.max_interventions,
            metadata={
                "max_iterations": request.max_iterations,
                "created_via_api": True
            }
        )

        db.add(db_session)
        await db.commit()
        await db.refresh(db_session)

        # Start orchestration in background
        background_tasks.add_task(
            _start_session_background,
            str(db_session.id),
            request.user_input,
            request.max_iterations
        )

        logger.info(f"Session {db_session.id} created successfully")

        return {
            "session_id": str(db_session.id),
            "status": "initializing",
            "message": "Session created successfully. Agent collaboration starting...",
            "created_at": db_session.created_at.isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")

@router.get("/", response_model=SessionListResponse)
async def list_sessions(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_async_session)
):
    """
    List all sessions with pagination and filtering
    """
    try:
        # Build query
        query = select(SessionModel)

        if status:
            query = query.where(SessionModel.status == status)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_count_result = await db.execute(count_query)
        total_count = total_count_result.scalar()

        # Apply pagination and ordering
        query = query.order_by(desc(SessionModel.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)

        # Execute query
        result = await db.execute(query)
        sessions = result.scalars().all()

        # Convert to response format
        session_responses = []
        for session in sessions:
            session_responses.append(SessionResponse(
                id=str(session.id),
                user_input=session.user_input,
                status=session.status,
                final_prompt=session.final_prompt,
                created_at=session.created_at.isoformat(),
                updated_at=session.updated_at.isoformat(),
                completed_at=session.completed_at.isoformat() if session.completed_at else None,
                iteration_count=session.iteration_count,
                user_intervention_count=session.user_intervention_count,
                max_interventions=session.max_interventions,
                waiting_for_user_since=session.waiting_for_user_since.isoformat() if session.waiting_for_user_since else None,
                current_question_id=str(session.current_question_id) if session.current_question_id else None,
                metadata=session.metadata or {}
            ))

        return SessionListResponse(
            sessions=session_responses,
            total_count=total_count,
            page=page,
            page_size=page_size
        )

    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")

@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get detailed information about a specific session
    """
    try:
        # Query session
        result = await db.execute(
            select(SessionModel).where(SessionModel.id == session_id)
        )
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        return SessionResponse(
            id=str(session.id),
            user_input=session.user_input,
            status=session.status,
            final_prompt=session.final_prompt,
            created_at=session.created_at.isoformat(),
            updated_at=session.updated_at.isoformat(),
            completed_at=session.completed_at.isoformat() if session.completed_at else None,
            iteration_count=session.iteration_count,
            user_intervention_count=session.user_intervention_count,
            max_interventions=session.max_interventions,
            waiting_for_user_since=session.waiting_for_user_since.isoformat() if session.waiting_for_user_since else None,
            current_question_id=str(session.current_question_id) if session.current_question_id else None,
            metadata=session.metadata or {}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get session: {str(e)}")

@router.post("/{session_id}/start", response_model=Dict[str, Any])
async def start_session_collaboration(
    session_id: str,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Start the agent collaboration for a session
    """
    try:
        # Check if session exists
        result = await db.execute(
            select(SessionModel).where(SessionModel.id == session_id)
        )
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        if session.status != "active":
            raise HTTPException(status_code=400, detail=f"Session cannot be started. Current status: {session.status}")

        logger.info(f"Starting collaboration for session {session_id}")

        # Start orchestration
        response = await orchestration_engine.start_prompt_generation_session(
            user_requirements=session.user_input,
            session_id=session_id,
            max_iterations=session.metadata.get("max_iterations", 5)
        )

        # Update session status
        session.status = "processing"
        await db.commit()

        return {
            "session_id": session_id,
            "status": "processing",
            "message": "Agent collaboration started",
            "agent_responses": response.get("agent_responses", {}),
            "next_agent": response.get("next_agent"),
            "requires_user_input": response.get("requires_user_input", False),
            "clarifying_questions": response.get("clarifying_questions", [])
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start session: {str(e)}")

@router.get("/{session_id}/messages", response_model=SessionMessagesResponse)
async def get_session_messages(
    session_id: str,
    page: int = 1,
    page_size: int = 50,
    agent_type: Optional[str] = None,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get all messages for a specific session
    """
    try:
        # Check if session exists
        session_result = await db.execute(
            select(SessionModel).where(SessionModel.id == session_id)
        )
        session = session_result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Build message query
        query = select(AgentMessage).where(AgentMessage.session_id == session_id)

        if agent_type:
            query = query.where(AgentMessage.agent_type == agent_type)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_count_result = await db.execute(count_query)
        total_count = total_count_result.scalar()

        # Apply pagination and ordering
        query = query.order_by(AgentMessage.sequence_number)
        query = query.offset((page - 1) * page_size).limit(page_size)

        # Execute query
        result = await db.execute(query)
        messages = result.scalars().all()

        # Convert to response format
        message_responses = []
        for message in messages:
            message_responses.append(AgentMessageResponse(
                id=str(message.id),
                session_id=str(message.session_id),
                agent_type=message.agent_type,
                message_content=message.message_content,
                message_type=message.message_type,
                sequence_number=message.sequence_number,
                parent_message_id=str(message.parent_message_id) if message.parent_message_id else None,
                created_at=message.created_at.isoformat(),
                processing_time_ms=message.processing_time_ms,
                metadata=message.metadata or {}
            ))

        return SessionMessagesResponse(
            session_id=session_id,
            messages=message_responses,
            total_count=total_count
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get messages for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get session messages: {str(e)}")

@router.delete("/{session_id}", response_model=Dict[str, Any])
async def cancel_session(
    session_id: str,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Cancel a session and mark it as cancelled
    """
    try:
        # Get session
        result = await db.execute(
            select(SessionModel).where(SessionModel.id == session_id)
        )
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        if session.status in ["completed", "cancelled"]:
            raise HTTPException(status_code=400, detail=f"Session cannot be cancelled. Current status: {session.status}")

        # Update session status
        session.status = "cancelled"
        session.completed_at = func.now()
        await db.commit()

        # Clean up orchestration engine if needed
        try:
            await orchestration_engine.cleanup_session(session_id)
        except Exception as e:
            logger.warning(f"Failed to cleanup orchestration engine for session {session_id}: {e}")

        logger.info(f"Session {session_id} cancelled successfully")

        return {
            "session_id": session_id,
            "status": "cancelled",
            "message": "Session cancelled successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel session: {str(e)}")

@router.get("/{session_id}/status", response_model=Dict[str, Any])
async def get_session_status(
    session_id: str,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get current status and progress of a session
    """
    try:
        # Get session from database
        session_result = await db.execute(
            select(SessionModel).where(SessionModel.id == session_id)
        )
        session = session_result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Get status from orchestration engine if active
        orchestration_status = {}
        try:
            orchestration_status = await orchestration_engine.get_session_status(session_id)
        except Exception as e:
            logger.warning(f"Failed to get orchestration status for session {session_id}: {e}")

        return {
            "session_id": session_id,
            "database_status": session.status,
            "orchestration_status": orchestration_status,
            "iteration_count": session.iteration_count,
            "user_intervention_count": session.user_intervention_count,
            "max_interventions": session.max_interventions,
            "waiting_for_user_since": session.waiting_for_user_since.isoformat() if session.waiting_for_user_since else None,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "completed_at": session.completed_at.isoformat() if session.completed_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get status for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get session status: {str(e)}")

# Background task helper
async def _start_session_background(session_id: str, user_input: str, max_iterations: int):
    """Background task to start session orchestration"""
    try:
        await orchestration_engine.start_prompt_generation_session(
            user_requirements=user_input,
            session_id=session_id,
            max_iterations=max_iterations
        )
        logger.info(f"Background orchestration started for session {session_id}")
    except Exception as e:
        logger.error(f"Failed to start background orchestration for session {session_id}: {e}")
        # Update session status to failed
        async with get_async_session() as db:
            result = await db.execute(
                select(SessionModel).where(SessionModel.id == session_id)
            )
            session = result.scalar_one_or_none()
            if session:
                session.status = "failed"
                session.metadata = session.metadata or {}
                session.metadata["error"] = str(e)
                await db.commit()