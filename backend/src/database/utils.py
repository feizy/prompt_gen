"""
Database utility functions
"""

import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, desc, asc
from sqlalchemy.orm import selectinload

from .connection import get_db_session
from ..models.session import Session, AgentMessage, SupplementaryUserInput, ClarifyingQuestion, SessionWaitingState
from ..core.logging import get_logger

logger = get_logger(__name__)


class SessionRepository:
    """Repository for session operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_session(self, user_input: str) -> Session:
        """Create a new session"""
        session = Session(user_input=user_input)
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        logger.info(f"Created new session: {session.id}")
        return session

    async def get_session(self, session_id: uuid.UUID) -> Optional[Session]:
        """Get a session by ID"""
        result = await self.db.execute(
            select(Session).where(Session.id == session_id)
        )
        return result.scalar_one_or_none()

    async def update_session_status(self, session_id: uuid.UUID, status: str) -> bool:
        """Update session status"""
        stmt = (
            update(Session)
            .where(Session.id == session_id)
            .values(status=status, updated_at=datetime.utcnow())
        )
        result = await self.db.execute(stmt)
        await self.db.commit()

        if result.rowcount > 0:
            logger.info(f"Updated session {session_id} status to {status}")
            return True
        return False

    async def get_sessions_list(
        self,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        created_after: Optional[datetime] = None
    ) -> List[Session]:
        """Get list of sessions with filtering"""
        query = select(Session).order_by(desc(Session.created_at))

        conditions = []
        if status:
            conditions.append(Session.status == status)
        if created_after:
            conditions.append(Session.created_at >= created_after)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.limit(limit).offset(offset)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def delete_session(self, session_id: uuid.UUID) -> bool:
        """Delete a session"""
        stmt = delete(Session).where(Session.id == session_id)
        result = await self.db.execute(stmt)
        await self.db.commit()

        if result.rowcount > 0:
            logger.info(f"Deleted session: {session_id}")
            return True
        return False


class MessageRepository:
    """Repository for agent message operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_message(
        self,
        session_id: uuid.UUID,
        agent_type: str,
        message_content: str,
        message_type: str,
        sequence_number: int,
        parent_message_id: Optional[uuid.UUID] = None,
        processing_time_ms: Optional[int] = None
    ) -> AgentMessage:
        """Create a new agent message"""
        message = AgentMessage(
            session_id=session_id,
            agent_type=agent_type,
            message_content=message_content,
            message_type=message_type,
            sequence_number=sequence_number,
            parent_message_id=parent_message_id,
            processing_time_ms=processing_time_ms
        )
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        logger.info(f"Created new message: {message.id} for session: {session_id}")
        return message

    async def get_session_messages(
        self,
        session_id: uuid.UUID,
        agent_type: Optional[str] = None,
        limit: int = 50
    ) -> List[AgentMessage]:
        """Get messages for a session"""
        query = select(AgentMessage).where(AgentMessage.session_id == session_id)

        if agent_type:
            query = query.where(AgentMessage.agent_type == agent_type)

        query = query.order_by(asc(AgentMessage.sequence_number)).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_next_sequence_number(self, session_id: uuid.UUID) -> int:
        """Get the next sequence number for a session"""
        result = await self.db.execute(
            select(func.coalesce(func.max(AgentMessage.sequence_number), 0))
            .where(AgentMessage.session_id == session_id)
        )
        max_sequence = result.scalar() or 0
        return max_sequence + 1


class SupplementaryInputRepository:
    """Repository for supplementary user input operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_supplementary_input(
        self,
        session_id: uuid.UUID,
        input_content: str,
        input_type: str = "supplementary"
    ) -> SupplementaryUserInput:
        """Create a new supplementary user input"""
        # Get next sequence number
        result = await self.db.execute(
            select(func.coalesce(func.max(SupplementaryUserInput.sequence_number), 0))
            .where(SupplementaryUserInput.session_id == session_id)
        )
        sequence_number = (result.scalar() or 0) + 1

        input_obj = SupplementaryUserInput(
            session_id=session_id,
            input_content=input_content,
            input_type=input_type,
            sequence_number=sequence_number
        )
        self.db.add(input_obj)
        await self.db.commit()
        await self.db.refresh(input_obj)
        logger.info(f"Created supplementary input: {input_obj.id} for session: {session_id}")
        return input_obj

    async def get_session_inputs(self, session_id: uuid.UUID) -> List[SupplementaryUserInput]:
        """Get all supplementary inputs for a session"""
        result = await self.db.execute(
            select(SupplementaryUserInput)
            .where(SupplementaryUserInput.session_id == session_id)
            .order_by(asc(SupplementaryUserInput.sequence_number))
        )
        return result.scalars().all()


class ClarifyingQuestionRepository:
    """Repository for clarifying question operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_clarifying_question(
        self,
        session_id: uuid.UUID,
        question_text: str,
        question_type: str = "clarification",
        priority: int = 1
    ) -> ClarifyingQuestion:
        """Create a new clarifying question"""
        # Get next sequence number
        result = await self.db.execute(
            select(func.coalesce(func.max(ClarifyingQuestion.sequence_number), 0))
            .where(ClarifyingQuestion.session_id == session_id)
        )
        sequence_number = (result.scalar() or 0) + 1

        question = ClarifyingQuestion(
            session_id=session_id,
            question_text=question_text,
            question_type=question_type,
            priority=priority,
            sequence_number=sequence_number
        )
        self.db.add(question)
        await self.db.commit()
        await self.db.refresh(question)
        logger.info(f"Created clarifying question: {question.id} for session: {session_id}")
        return question

    async def get_pending_questions(self, session_id: uuid.UUID) -> List[ClarifyingQuestion]:
        """Get pending clarifying questions for a session"""
        result = await self.db.execute(
            select(ClarifyingQuestion)
            .where(and_(
                ClarifyingQuestion.session_id == session_id,
                ClarifyingQuestion.status == "pending"
            ))
            .order_by(asc(ClarifyingQuestion.priority), asc(ClarifyingQuestion.asked_at))
        )
        return result.scalars().all()

    async def respond_to_question(
        self,
        question_id: uuid.UUID,
        response_text: str
    ) -> bool:
        """Respond to a clarifying question"""
        stmt = (
            update(ClarifyingQuestion)
            .where(ClarifyingQuestion.id == question_id)
            .where(ClarifyingQuestion.status == "pending")
            .values(
                response_text=response_text,
                responded_at=datetime.utcnow(),
                status="answered"
            )
        )
        result = await self.db.execute(stmt)
        await self.db.commit()

        if result.rowcount > 0:
            logger.info(f"Responded to question: {question_id}")
            return True
        return False


async def get_db_repository():
    """Get database session and repositories"""
    async for session in get_db_session():
        yield {
            'session': session,
            'sessions': SessionRepository(session),
            'messages': MessageRepository(session),
            'inputs': SupplementaryInputRepository(session),
            'questions': ClarifyingQuestionRepository(session)
        }