"""
Clarifying question repository for database operations
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc, func, and_, or_
from sqlalchemy.orm import selectinload

from ..models.session import ClarifyingQuestion, Session as SessionModel
from ..core.logging import get_logger

logger = get_logger(__name__)


class QuestionRepository:
    """Repository for clarifying question database operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_question(
        self,
        session_id: str,
        question_text: str,
        question_type: str = "clarification",
        priority: int = 1,
        agent_type: str = "product_manager",
        response_deadline: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ClarifyingQuestion:
        """Create a new clarifying question"""
        try:
            # Get next sequence number
            seq_result = await self.db.execute(
                select(func.coalesce(func.max(ClarifyingQuestion.sequence_number), 0) + 1)
                .where(ClarifyingQuestion.session_id == session_id)
            )
            next_sequence = seq_result.scalar() or 1

            question = ClarifyingQuestion(
                session_id=session_id,
                question_text=question_text,
                question_type=question_type,
                priority=priority,
                agent_type=agent_type,
                sequence_number=next_sequence,
                response_deadline=response_deadline,
                metadata=metadata or {}
            )

            self.db.add(question)
            await self.db.commit()
            await self.db.refresh(question)

            logger.info(f"Created clarifying question {question.id} for session {session_id}")
            return question

        except Exception as e:
            logger.error(f"Failed to create clarifying question: {e}")
            await self.db.rollback()
            raise

    async def get_question(self, question_id: str) -> Optional[ClarifyingQuestion]:
        """Get a clarifying question by ID"""
        try:
            result = await self.db.execute(
                select(ClarifyingQuestion).where(ClarifyingQuestion.id == question_id)
            )
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Failed to get clarifying question {question_id}: {e}")
            raise

    async def get_session_questions(
        self,
        session_id: str,
        status: Optional[str] = None,
        question_type: Optional[str] = None,
        priority: Optional[int] = None,
        include_answered: bool = True
    ) -> List[ClarifyingQuestion]:
        """Get clarifying questions for a session"""
        try:
            query = select(ClarifyingQuestion).where(ClarifyingQuestion.session_id == session_id)

            if status:
                query = query.where(ClarifyingQuestion.status == status)
            elif not include_answered:
                query = query.where(ClarifyingQuestion.status.in_(["pending", "expired"]))

            if question_type:
                query = query.where(ClarifyingQuestion.question_type == question_type)

            if priority:
                query = query.where(ClarifyingQuestion.priority == priority)

            query = query.order_by(ClarifyingQuestion.sequence_number)

            result = await self.db.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Failed to get clarifying questions for session {session_id}: {e}")
            raise

    async def get_pending_questions(self, session_id: str) -> List[ClarifyingQuestion]:
        """Get pending clarifying questions for a session"""
        try:
            result = await self.db.execute(
                select(ClarifyingQuestion)
                .where(
                    and_(
                        ClarifyingQuestion.session_id == session_id,
                        ClarifyingQuestion.status == "pending"
                    )
                )
                .order_by(ClarifyingQuestion.priority.asc(), ClarifyingQuestion.sequence_number.asc())
            )
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Failed to get pending questions for session {session_id}: {e}")
            raise

    async def answer_question(
        self,
        question_id: str,
        response_text: str,
        responded_at: Optional[datetime] = None
    ) -> bool:
        """Answer a clarifying question"""
        try:
            result = await self.db.execute(
                select(ClarifyingQuestion).where(ClarifyingQuestion.id == question_id)
            )
            question = result.scalar_one_or_none()

            if not question:
                return False

            question.response_text = response_text
            question.status = "answered"
            question.responded_at = responded_at or datetime.utcnow()

            await self.db.commit()
            logger.info(f"Answered clarifying question {question_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to answer clarifying question {question_id}: {e}")
            await self.db.rollback()
            raise

    async def cancel_question(self, question_id: str) -> bool:
        """Cancel a clarifying question"""
        try:
            result = await self.db.execute(
                select(ClarifyingQuestion).where(ClarifyingQuestion.id == question_id)
            )
            question = result.scalar_one_or_none()

            if not question:
                return False

            question.status = "cancelled"

            await self.db.commit()
            logger.info(f"Cancelled clarifying question {question_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to cancel clarifying question {question_id}: {e}")
            await self.db.rollback()
            raise

    async def update_question_metadata(
        self,
        question_id: str,
        metadata_updates: Dict[str, Any]
    ) -> bool:
        """Update question metadata"""
        try:
            result = await self.db.execute(
                select(ClarifyingQuestion).where(ClarifyingQuestion.id == question_id)
            )
            question = result.scalar_one_or_none()

            if not question:
                return False

            question.metadata = question.metadata or {}
            question.metadata.update(metadata_updates)

            await self.db.commit()
            return True

        except Exception as e:
            logger.error(f"Failed to update question {question_id} metadata: {e}")
            await self.db.rollback()
            raise

    async def mark_questions_expired(self, session_id: str) -> int:
        """Mark overdue questions as expired"""
        try:
            current_time = datetime.utcnow()

            result = await self.db.execute(
                select(ClarifyingQuestion)
                .where(
                    and_(
                        ClarifyingQuestion.session_id == session_id,
                        ClarifyingQuestion.status == "pending",
                        ClarifyingQuestion.response_deadline < current_time
                    )
                )
            )

            questions = result.scalars().all()

            expired_count = 0
            for question in questions:
                question.status = "expired"
                expired_count += 1

            if expired_count > 0:
                await self.db.commit()
                logger.info(f"Marked {expired_count} questions as expired for session {session_id}")

            return expired_count

        except Exception as e:
            logger.error(f"Failed to mark expired questions for session {session_id}: {e}")
            await self.db.rollback()
            raise

    async def get_questions_by_priority(
        self,
        session_id: str,
        max_questions: int = 5
    ) -> List[ClarifyingQuestion]:
        """Get high-priority questions for a session"""
        try:
            result = await self.db.execute(
                select(ClarifyingQuestion)
                .where(
                    and_(
                        ClarifyingQuestion.session_id == session_id,
                        ClarifyingQuestion.status == "pending"
                    )
                )
                .order_by(ClarifyingQuestion.priority.asc(), ClarifyingQuestion.sequence_number.asc())
                .limit(max_questions)
            )
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Failed to get priority questions for session {session_id}: {e}")
            raise

    async def has_pending_questions(self, session_id: str) -> bool:
        """Check if a session has pending questions"""
        try:
            result = await self.db.execute(
                select(func.count())
                .select_from(
                    select(ClarifyingQuestion)
                    .where(
                        and_(
                            ClarifyingQuestion.session_id == session_id,
                            ClarifyingQuestion.status == "pending"
                        )
                    )
                    .subquery()
                )
            )
            count = result.scalar()
            return count > 0

        except Exception as e:
            logger.error(f"Failed to check pending questions for session {session_id}: {e}")
            return False

    async def get_question_statistics(self, session_id: str) -> Dict[str, Any]:
        """Get question statistics for a session"""
        try:
            # Count questions by status
            status_counts = {}
            for status in ["pending", "answered", "expired", "cancelled"]:
                result = await self.db.execute(
                    select(func.count())
                    .select_from(
                        select(ClarifyingQuestion)
                        .where(
                            and_(
                                ClarifyingQuestion.session_id == session_id,
                                ClarifyingQuestion.status == status
                            )
                        )
                        .subquery()
                    )
                )
                status_counts[status] = result.scalar()

            # Count questions by type
            type_counts = {}
            for question_type in ["clarification", "confirmation", "ambiguity"]:
                result = await self.db.execute(
                    select(func.count())
                    .select_from(
                        select(ClarifyingQuestion)
                        .where(
                            and_(
                                ClarifyingQuestion.session_id == session_id,
                                ClarifyingQuestion.question_type == question_type
                            )
                        )
                        .subquery()
                    )
                )
                type_counts[question_type] = result.scalar()

            # Count questions by priority
            priority_counts = {}
            for priority in [1, 2, 3]:  # high, medium, low
                result = await self.db.execute(
                    select(func.count())
                    .select_from(
                        select(ClarifyingQuestion)
                        .where(
                            and_(
                                ClarifyingQuestion.session_id == session_id,
                                ClarifyingQuestion.priority == priority
                            )
                        )
                        .subquery()
                    )
                )
                priority_counts[f"priority_{priority}"] = result.scalar()

            # Average response time
            avg_response_time_result = await self.db.execute(
                select(func.avg(
                    func.extract('epoch', ClarifyingQuestion.responded_at - ClarifyingQuestion.asked_at)
                ))
                .where(
                    and_(
                        ClarifyingQuestion.session_id == session_id,
                        ClarifyingQuestion.responded_at.isnot(None)
                    )
                )
            )
            avg_response_time = avg_response_time_result.scalar() or 0

            return {
                "status_counts": status_counts,
                "type_counts": type_counts,
                "priority_counts": priority_counts,
                "average_response_time_seconds": float(avg_response_time),
                "total_questions": sum(status_counts.values())
            }

        except Exception as e:
            logger.error(f"Failed to get question statistics for session {session_id}: {e}")
            raise

    async def delete_question(self, question_id: str) -> bool:
        """Delete a clarifying question"""
        try:
            result = await self.db.execute(
                select(ClarifyingQuestion).where(ClarifyingQuestion.id == question_id)
            )
            question = result.scalar_one_or_none()

            if not question:
                return False

            await self.db.delete(question)
            await self.db.commit()

            logger.info(f"Deleted clarifying question {question_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete clarifying question {question_id}: {e}")
            await self.db.rollback()
            raise

    async def cleanup_old_questions(
        self,
        session_id: str,
        days_old: int = 30
    ) -> int:
        """Clean up old questions"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)

            result = await self.db.execute(
                select(ClarifyingQuestion)
                .where(
                    and_(
                        ClarifyingQuestion.session_id == session_id,
                        ClarifyingQuestion.asked_at < cutoff_date,
                        ClarifyingQuestion.status.in_(["answered", "cancelled", "expired"])
                    )
                )
            )

            questions_to_delete = result.scalars().all()

            for question in questions_to_delete:
                await self.db.delete(question)

            await self.db.commit()
            logger.info(f"Cleaned up {len(questions_to_delete)} old questions for session {session_id}")
            return len(questions_to_delete)

        except Exception as e:
            logger.error(f"Failed to cleanup old questions for session {session_id}: {e}")
            await self.db.rollback()
            raise