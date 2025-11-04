"""
User input API endpoints
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc, func

from ..database.connection import get_async_session
from ..models.session import Session as SessionModel, SupplementaryUserInput
from ..agents.orchestration_engine import AgentOrchestrationEngine
from ..core.exceptions import SessionNotFoundError, InvalidUserInputError
from ..core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Global orchestration engine instance (shared with sessions)
orchestration_engine = AgentOrchestrationEngine()

# Pydantic models for request/response
class UserInputRequest(BaseModel):
    """Request model for user input"""
    input_content: str = Field(..., min_length=5, description="User's input content")
    input_type: str = Field(default="supplementary", description="Type of input (supplementary, clarification_response, general)")

class UserInputResponse(BaseModel):
    """Response model for user input submission"""
    id: str
    session_id: str
    input_content: str
    input_type: str
    processing_status: str
    provided_at: str
    incorporated_into_requirements: bool
    sequence_number: int
    metadata: Dict[str, Any]

class SessionContinueRequest(BaseModel):
    """Request model for continuing session without additional input"""
    force_continue: bool = Field(default=False, description="Force continuation even if input might be helpful")

class SessionContinueResponse(BaseModel):
    """Response model for session continuation"""
    session_id: str
    status: str
    message: str
    agent_responses: Dict[str, Any]
    next_agent: Optional[str]
    requires_user_input: bool
    clarifying_questions: List[Dict[str, Any]]
    completed: bool
    final_prompt: Optional[str]

@router.post("/sessions/{session_id}/user-input", response_model=UserInputResponse, status_code=201)
async def add_user_input(
    session_id: str,
    request: UserInputRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Add user input to an active session

    This endpoint allows users to provide additional input, clarification responses,
    or supplementary information during the agent collaboration process.
    """
    try:
        logger.info(f"Adding user input to session {session_id}: {request.input_content[:100]}...")

        # Check if session exists and is active
        session_result = await db.execute(
            select(SessionModel).where(SessionModel.id == session_id)
        )
        session = session_result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        if session.status not in ["active", "processing", "waiting_for_user_input"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot add input to session with status: {session.status}"
            )

        # Get next sequence number
        seq_result = await db.execute(
            select(func.coalesce(func.max(SupplementaryUserInput.sequence_number), 0) + 1)
            .where(SupplementaryUserInput.session_id == session_id)
        )
        next_sequence = seq_result.scalar() or 1

        # Create user input record
        user_input = SupplementaryUserInput(
            session_id=session_id,
            input_content=request.input_content,
            input_type=request.input_type,
            sequence_number=next_sequence,
            processing_status="pending",
            metadata={
                "provided_via_api": True,
                "user_agent": "api_client"
            }
        )

        db.add(user_input)
        await db.commit()
        await db.refresh(user_input)

        # Update session intervention count
        session.user_intervention_count += 1

        # Clear waiting state if session was waiting for input
        if session.waiting_for_user_since:
            session.waiting_for_user_since = None
            session.current_question_id = None

        session.status = "processing"
        await db.commit()

        # Process input in background
        background_tasks.add_task(
            _process_user_input_background,
            session_id,
            str(user_input.id),
            request.input_content,
            request.input_type
        )

        logger.info(f"User input {user_input.id} added to session {session_id}")

        return UserInputResponse(
            id=str(user_input.id),
            session_id=session_id,
            input_content=user_input.input_content,
            input_type=user_input.input_type,
            processing_status=user_input.processing_status,
            provided_at=user_input.provided_at.isoformat(),
            incorporated_into_requirements=user_input.incorporated_into_requirements,
            sequence_number=user_input.sequence_number,
            metadata=user_input.metadata or {}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add user input to session {session_id}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to add user input: {str(e)}")

@router.post("/sessions/{session_id}/continue", response_model=SessionContinueResponse)
async def continue_session(
    session_id: str,
    request: SessionContinueRequest,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Continue session processing without additional user input

    This endpoint allows the session to continue when agents have sufficient information
    to proceed without requiring more user input.
    """
    try:
        logger.info(f"Continuing session {session_id} without additional user input")

        # Check if session exists
        session_result = await db.execute(
            select(SessionModel).where(SessionModel.id == session_id)
        )
        session = session_result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        if session.status not in ["waiting_for_user_input", "processing"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot continue session with status: {session.status}"
            )

        # Update session status
        session.status = "processing"
        session.waiting_for_user_since = None
        session.current_question_id = None
        await db.commit()

        # Continue orchestration without input
        response = await orchestration_engine.continue_without_input(session_id)

        # Update session based on response
        if response.get("completed"):
            session.status = "completed"
            session.completed_at = func.now()
            session.final_prompt = response.get("final_prompt")
            session.iteration_count = response.get("total_iterations", session.iteration_count)
        elif response.get("requires_user_input"):
            session.status = "waiting_for_user_input"
            session.waiting_for_user_since = func.now()

        await db.commit()

        return SessionContinueResponse(
            session_id=session_id,
            status=response.get("status", "processing"),
            message=response.get("message", "Session continued successfully"),
            agent_responses=response.get("agent_responses", {}),
            next_agent=response.get("next_agent"),
            requires_user_input=response.get("requires_user_input", False),
            clarifying_questions=response.get("clarifying_questions", []),
            completed=response.get("completed", False),
            final_prompt=response.get("final_prompt")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to continue session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to continue session: {str(e)}")

@router.get("/sessions/{session_id}/user-inputs", response_model=List[UserInputResponse])
async def get_session_user_inputs(
    session_id: str,
    input_type: Optional[str] = None,
    processing_status: Optional[str] = None,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get all user inputs for a specific session
    """
    try:
        # Check if session exists
        session_result = await db.execute(
            select(SessionModel).where(SessionModel.id == session_id)
        )
        session = session_result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Build query
        query = select(SupplementaryUserInput).where(SupplementaryUserInput.session_id == session_id)

        if input_type:
            query = query.where(SupplementaryUserInput.input_type == input_type)

        if processing_status:
            query = query.where(SupplementaryUserInput.processing_status == processing_status)

        # Order by sequence number
        query = query.order_by(SupplementaryUserInput.sequence_number)

        # Execute query
        result = await db.execute(query)
        user_inputs = result.scalars().all()

        # Convert to response format
        input_responses = []
        for user_input in user_inputs:
            input_responses.append(UserInputResponse(
                id=str(user_input.id),
                session_id=str(user_input.session_id),
                input_content=user_input.input_content,
                input_type=user_input.input_type,
                processing_status=user_input.processing_status,
                provided_at=user_input.provided_at.isoformat(),
                incorporated_into_requirements=user_input.incorporated_into_requirements,
                sequence_number=user_input.sequence_number,
                metadata=user_input.metadata or {}
            ))

        return input_responses

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user inputs for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get user inputs: {str(e)}")

@router.get("/user-inputs/{input_id}", response_model=UserInputResponse)
async def get_user_input(
    input_id: str,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get details of a specific user input
    """
    try:
        # Query user input
        result = await db.execute(
            select(SupplementaryUserInput).where(SupplementaryUserInput.id == input_id)
        )
        user_input = result.scalar_one_or_none()

        if not user_input:
            raise HTTPException(status_code=404, detail="User input not found")

        return UserInputResponse(
            id=str(user_input.id),
            session_id=str(user_input.session_id),
            input_content=user_input.input_content,
            input_type=user_input.input_type,
            processing_status=user_input.processing_status,
            provided_at=user_input.provided_at.isoformat(),
            incorporated_into_requirements=user_input.incorporated_into_requirements,
            sequence_number=user_input.sequence_number,
            metadata=user_input.metadata or {}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user input {input_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get user input: {str(e)}")

@router.put("/user-inputs/{input_id}/status")
async def update_user_input_status(
    input_id: str,
    processing_status: str,
    incorporated_into_requirements: bool = False,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Update the processing status of a user input
    (Internal endpoint used by orchestration engine)
    """
    try:
        # Query user input
        result = await db.execute(
            select(SupplementaryUserInput).where(SupplementaryUserInput.id == input_id)
        )
        user_input = result.scalar_one_or_none()

        if not user_input:
            raise HTTPException(status_code=404, detail="User input not found")

        # Update status
        user_input.processing_status = processing_status
        user_input.incorporated_into_requirements = incorporated_into_requirements

        # Update metadata
        user_input.metadata = user_input.metadata or {}
        user_input.metadata["status_updated_at"] = func.now()
        user_input.metadata["status_updated_via"] = "api"

        await db.commit()

        logger.info(f"Updated user input {input_id} status to {processing_status}")

        return {
            "input_id": input_id,
            "processing_status": processing_status,
            "incorporated_into_requirements": incorporated_into_requirements,
            "updated_at": user_input.metadata.get("status_updated_at")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update user input {input_id} status: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update user input status: {str(e)}")

# Background task helper
async def _process_user_input_background(
    session_id: str,
    input_id: str,
    input_content: str,
    input_type: str
):
    """Background task to process user input through orchestration engine"""
    try:
        logger.info(f"Processing user input {input_id} for session {session_id}")

        # Process the input through orchestration engine
        response = await orchestration_engine.process_user_input(
            session_id=session_id,
            user_input=input_content,
            supplementary_inputs=[input_content] if input_type == "supplementary" else None
        )

        # Update user input status based on response
        async with get_async_session() as db:
            result = await db.execute(
                select(SupplementaryUserInput).where(SupplementaryUserInput.id == input_id)
            )
            user_input = result.scalar_one_or_none()

            if user_input:
                user_input.processing_status = "processed"
                if response.get("agent_responses"):
                    user_input.incorporated_into_requirements = True

                user_input.metadata = user_input.metadata or {}
                user_input.metadata["processing_response"] = response
                user_input.metadata["processed_at"] = func.now()

                await db.commit()

        logger.info(f"Successfully processed user input {input_id}")

    except Exception as e:
        logger.error(f"Failed to process user input {input_id} for session {session_id}: {e}")

        # Update user input status to failed
        async with get_async_session() as db:
            result = await db.execute(
                select(SupplementaryUserInput).where(SupplementaryUserInput.id == input_id)
            )
            user_input = result.scalar_one_or_none()

            if user_input:
                user_input.processing_status = "failed"
                user_input.metadata = user_input.metadata or {}
                user_input.metadata["processing_error"] = str(e)
                user_input.metadata["failed_at"] = func.now()

                await db.commit()