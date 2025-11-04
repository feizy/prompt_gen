"""
Session repository for database operations
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc, func, and_, or_
from sqlalchemy.orm import selectinload

from ..models.session import (
    Session as SessionModel,
    AgentMessage,
    SupplementaryUserInput,
    ClarifyingQuestion,
    SessionWaitingState
)
from ..core.logging import get_logger

logger = get_logger(__name__)


class SessionRepository:
    """Repository for session database operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_session(
        self,
        user_input: str,
        max_interventions: int = 3,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SessionModel:
        """Create a new session"""
        try:
            session = SessionModel(
                user_input=user_input,
                max_interventions=max_interventions,
                metadata=metadata or {}
            )

            self.db.add(session)
            await self.db.commit()
            await self.db.refresh(session)

            logger.info(f"Created session {session.id}")
            return session

        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            await self.db.rollback()
            raise

    async def get_session(self, session_id: str) -> Optional[SessionModel]:
        """Get a session by ID"""
        try:
            result = await self.db.execute(
                select(SessionModel).where(SessionModel.id == session_id)
            )
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            raise

    async def get_session_with_messages(self, session_id: str) -> Optional[SessionModel]:
        """Get a session with all related messages"""
        try:
            result = await self.db.execute(
                select(SessionModel)
                .options(
                    selectinload(SessionModel.agent_messages),
                    selectinload(SessionModel.supplementary_inputs),
                    selectinload(SessionModel.clarifying_questions)
                )
                .where(SessionModel.id == session_id)
            )
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Failed to get session {session_id} with messages: {e}")
            raise

    async def list_sessions(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        limit: Optional[int] = None
    ) -> tuple[List[SessionModel], int]:
        """List sessions with pagination and filtering"""
        try:
            # Build query
            query = select(SessionModel)

            if status:
                query = query.where(SessionModel.status == status)

            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            total_count_result = await self.db.execute(count_query)
            total_count = total_count_result.scalar()

            # Apply pagination and ordering
            query = query.order_by(desc(SessionModel.created_at))

            if limit:
                query = query.limit(limit)
            else:
                query = query.offset((page - 1) * page_size).limit(page_size)

            # Execute query
            result = await self.db.execute(query)
            sessions = result.scalars().all()

            return sessions, total_count

        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            raise

    async def update_session_status(
        self,
        session_id: str,
        status: str,
        final_prompt: Optional[str] = None,
        completed_at: Optional[datetime] = None,
        metadata_updates: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update session status and related fields"""
        try:
            result = await self.db.execute(
                select(SessionModel).where(SessionModel.id == session_id)
            )
            session = result.scalar_one_or_none()

            if not session:
                return False

            session.status = status

            if final_prompt:
                session.final_prompt = final_prompt

            if completed_at:
                session.completed_at = completed_at
            elif status in ["completed", "cancelled"] and not session.completed_at:
                session.completed_at = func.now()

            if metadata_updates:
                session.metadata = session.metadata or {}
                session.metadata.update(metadata_updates)

            await self.db.commit()
            logger.info(f"Updated session {session_id} status to {status}")
            return True

        except Exception as e:
            logger.error(f"Failed to update session {session_id} status: {e}")
            await self.db.rollback()
            raise

    async def increment_session_iteration(self, session_id: str) -> bool:
        """Increment session iteration count"""
        try:
            result = await self.db.execute(
                select(SessionModel).where(SessionModel.id == session_id)
            )
            session = result.scalar_one_or_none()

            if not session:
                return False

            session.iteration_count += 1
            await self.db.commit()
            return True

        except Exception as e:
            logger.error(f"Failed to increment session {session_id} iteration: {e}")
            await self.db.rollback()
            raise

    async def set_waiting_state(
        self,
        session_id: str,
        waiting_type: str,
        related_entity_id: Optional[str] = None,
        timeout_duration: int = 1800  # 30 minutes default
    ) -> bool:
        """Set session to waiting state"""
        try:
            result = await self.db.execute(
                select(SessionModel).where(SessionModel.id == session_id)
            )
            session = result.scalar_one_or_none()

            if not session:
                return False

            # Update session
            session.waiting_for_user_since = func.now()
            session.status = "waiting_for_user_input"

            if related_entity_id:
                session.current_question_id = related_entity_id

            # Create waiting state record
            waiting_state = SessionWaitingState(
                session_id=session_id,
                waiting_type=waiting_type,
                related_entity_id=related_entity_id,
                timeout_duration_seconds=timeout_duration
            )

            self.db.add(waiting_state)
            await self.db.commit()

            logger.info(f"Set session {session_id} to waiting state: {waiting_type}")
            return True

        except Exception as e:
            logger.error(f"Failed to set waiting state for session {session_id}: {e}")
            await self.db.rollback()
            raise

    async def clear_waiting_state(self, session_id: str) -> bool:
        """Clear session waiting state"""
        try:
            result = await self.db.execute(
                select(SessionModel).where(SessionModel.id == session_id)
            )
            session = result.scalar_one_or_none()

            if not session:
                return False

            # Update session
            session.waiting_for_user_since = None
            session.current_question_id = None
            session.status = "processing"

            # End active waiting states
            waiting_result = await self.db.execute(
                select(SessionWaitingState)
                .where(
                    and_(
                        SessionWaitingState.session_id == session_id,
                        SessionWaitingState.status == "active"
                    )
                )
            )

            for waiting_state in waiting_result.scalars().all():
                waiting_state.status = "resolved"
                waiting_state.ended_at = func.now()

            await self.db.commit()

            logger.info(f"Cleared waiting state for session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to clear waiting state for session {session_id}: {e}")
            await self.db.rollback()
            raise

    async def cancel_session(self, session_id: str) -> bool:
        """Cancel a session"""
        try:
            result = await self.db.execute(
                select(SessionModel).where(SessionModel.id == session_id)
            )
            session = result.scalar_one_or_none()

            if not session:
                return False

            session.status = "cancelled"
            session.completed_at = func.now()

            # End any active waiting states
            await self.clear_waiting_state(session_id)

            await self.db.commit()
            logger.info(f"Cancelled session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to cancel session {session_id}: {e}")
            await self.db.rollback()
            raise

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and all related data"""
        try:
            result = await self.db.execute(
                select(SessionModel).where(SessionModel.id == session_id)
            )
            session = result.scalar_one_or_none()

            if not session:
                return False

            await self.db.delete(session)
            await self.db.commit()

            logger.info(f"Deleted session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            await self.db.rollback()
            raise

    async def get_active_sessions_count(self) -> int:
        """Get count of active sessions"""
        try:
            result = await self.db.execute(
                select(func.count())
                .select_from(
                    select(SessionModel)
                    .where(SessionModel.status.in_(["active", "processing", "waiting_for_user_input"]))
                    .subquery()
                )
            )
            return result.scalar()

        except Exception as e:
            logger.error(f"Failed to get active sessions count: {e}")
            raise

    async def get_session_statistics(self) -> Dict[str, Any]:
        """Get session statistics"""
        try:
            # Get counts by status
            status_counts = {}
            for status in ["active", "processing", "waiting_for_user_input", "completed", "cancelled", "failed"]:
                result = await self.db.execute(
                    select(func.count())
                    .select_from(
                        select(SessionModel)
                        .where(SessionModel.status == status)
                        .subquery()
                    )
                )
                status_counts[status] = result.scalar()

            # Get average processing time
            avg_iterations_result = await self.db.execute(
                select(func.avg(SessionModel.iteration_count))
                .where(SessionModel.status == "completed")
            )
            avg_iterations = avg_iterations_result.scalar() or 0

            return {
                "status_counts": status_counts,
                "average_iterations_per_completion": float(avg_iterations),
                "total_sessions": sum(status_counts.values())
            }

        except Exception as e:
            logger.error(f"Failed to get session statistics: {e}")
            raise