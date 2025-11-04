"""
Database service layer for orchestrating repository operations
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories import (
    SessionRepository,
    MessageRepository,
    QuestionRepository,
    UserInputRepository
)
from ..models.session import Session as SessionModel, AgentMessage, ClarifyingQuestion, SupplementaryUserInput
from ..core.logging import get_logger

logger = get_logger(__name__)


class DatabaseService:
    """High-level database service for the AI Agent system"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.session_repo = SessionRepository(db)
        self.message_repo = MessageRepository(db)
        self.question_repo = QuestionRepository(db)
        self.user_input_repo = UserInputRepository(db)

    # === Session Operations ===

    async def create_session(
        self,
        user_input: str,
        max_interventions: int = 3,
        max_iterations: int = 5
    ) -> SessionModel:
        """Create a new session with metadata"""
        metadata = {
            "max_iterations": max_iterations,
            "created_via": "orchestration_engine"
        }

        session = await self.session_repo.create_session(
            user_input=user_input,
            max_interventions=max_interventions,
            metadata=metadata
        )

        logger.info(f"Created session {session.id} via database service")
        return session

    async def get_session(self, session_id: str) -> Optional[SessionModel]:
        """Get a session by ID"""
        return await self.session_repo.get_session(session_id)

    async def get_session_full(self, session_id: str) -> Optional[SessionModel]:
        """Get a session with all related data"""
        return await self.session_repo.get_session_with_messages(session_id)

    async def update_session_status(
        self,
        session_id: str,
        status: str,
        final_prompt: Optional[str] = None
    ) -> bool:
        """Update session status"""
        return await self.session_repo.update_session_status(
            session_id=session_id,
            status=status,
            final_prompt=final_prompt
        )

    async def increment_iteration(self, session_id: str) -> bool:
        """Increment session iteration count"""
        return await self.session_repo.increment_session_iteration(session_id)

    async def set_waiting_state(
        self,
        session_id: str,
        waiting_type: str,
        related_entity_id: Optional[str] = None
    ) -> bool:
        """Set session to waiting state"""
        return await self.session_repo.set_waiting_state(
            session_id=session_id,
            waiting_type=waiting_type,
            related_entity_id=related_entity_id
        )

    async def clear_waiting_state(self, session_id: str) -> bool:
        """Clear session waiting state"""
        return await self.session_repo.clear_waiting_state(session_id)

    # === Message Operations ===

    async def create_agent_message(
        self,
        session_id: str,
        agent_type: str,
        content: str,
        message_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AgentMessage:
        """Create an agent message"""
        sequence_number = await self.message_repo.get_next_sequence_number(session_id)

        return await self.message_repo.create_message(
            session_id=session_id,
            agent_type=agent_type,
            message_content=content,
            message_type=message_type,
            sequence_number=sequence_number,
            metadata=metadata
        )

    async def get_session_messages(
        self,
        session_id: str,
        agent_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[AgentMessage]:
        """Get messages for a session"""
        messages, _ = await self.message_repo.get_session_messages(
            session_id=session_id,
            agent_type=agent_type,
            limit=limit
        )
        return messages

    async def get_latest_message(
        self,
        session_id: str,
        agent_type: Optional[str] = None
    ) -> Optional[AgentMessage]:
        """Get the latest message for a session"""
        return await self.message_repo.get_latest_message(
            session_id=session_id,
            agent_type=agent_type
        )

    # === Question Operations ===

    async def create_clarifying_question(
        self,
        session_id: str,
        question_text: str,
        question_type: str = "clarification",
        priority: int = 1,
        agent_type: str = "product_manager"
    ) -> ClarifyingQuestion:
        """Create a clarifying question"""
        return await self.question_repo.create_question(
            session_id=session_id,
            question_text=question_text,
            question_type=question_type,
            priority=priority,
            agent_type=agent_type
        )

    async def get_pending_questions(self, session_id: str) -> List[ClarifyingQuestion]:
        """Get pending questions for a session"""
        return await self.question_repo.get_pending_questions(session_id)

    async def answer_question(
        self,
        question_id: str,
        response_text: str
    ) -> bool:
        """Answer a clarifying question"""
        return await self.question_repo.answer_question(
            question_id=question_id,
            response_text=response_text
        )

    async def has_pending_questions(self, session_id: str) -> bool:
        """Check if session has pending questions"""
        return await self.question_repo.has_pending_questions(session_id)

    # === User Input Operations ===

    async def create_user_input(
        self,
        session_id: str,
        input_content: str,
        input_type: str = "supplementary"
    ) -> SupplementaryUserInput:
        """Create a user input"""
        return await self.user_input_repo.create_user_input(
            session_id=session_id,
            input_content=input_content,
            input_type=input_type
        )

    async def get_user_inputs(
        self,
        session_id: str,
        input_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[SupplementaryUserInput]:
        """Get user inputs for a session"""
        return await self.user_input_repo.get_session_inputs(
            session_id=session_id,
            input_type=input_type,
            limit=limit
        )

    async def mark_input_processed(
        self,
        input_id: str,
        incorporated: bool = False
    ) -> bool:
        """Mark a user input as processed"""
        status = "incorporated" if incorporated else "processed"
        return await self.user_input_repo.update_input_status(
            input_id=input_id,
            processing_status=status,
            incorporated_into_requirements=incorporated
        )

    # === Session State Summary ===

    async def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Get a comprehensive summary of a session"""
        try:
            # Get session
            session = await self.session_repo.get_session(session_id)
            if not session:
                return {"error": "Session not found"}

            # Get messages
            messages = await self.get_session_messages(session_id, limit=10)
            latest_message = await self.get_latest_message(session_id)

            # Get questions
            pending_questions = await self.get_pending_questions(session_id)
            has_questions = await self.question_repo.has_pending_questions(session_id)

            # Get user inputs
            user_inputs = await self.get_user_inputs(session_id, limit=5)
            has_pending_inputs = await self.user_input_repo.has_pending_inputs(session_id)

            # Get statistics
            message_stats = await self.message_repo.get_message_statistics(session_id)
            question_stats = await self.question_repo.get_question_statistics(session_id)
            input_stats = await self.user_input_repo.get_input_statistics(session_id)

            return {
                "session": {
                    "id": str(session.id),
                    "status": session.status,
                    "created_at": session.created_at.isoformat(),
                    "updated_at": session.updated_at.isoformat(),
                    "iteration_count": session.iteration_count,
                    "user_intervention_count": session.user_intervention_count,
                    "waiting_for_user_since": session.waiting_for_user_since.isoformat() if session.waiting_for_user_since else None,
                    "final_prompt": session.final_prompt
                },
                "latest_activity": {
                    "latest_message": {
                        "id": str(latest_message.id) if latest_message else None,
                        "agent_type": latest_message.agent_type if latest_message else None,
                        "message_type": latest_message.message_type if latest_message else None,
                        "created_at": latest_message.created_at.isoformat() if latest_message else None
                    },
                    "pending_questions_count": len(pending_questions),
                    "pending_inputs_count": len([ui for ui in user_inputs if ui.processing_status == "pending"])
                },
                "statistics": {
                    "messages": message_stats,
                    "questions": question_stats,
                    "user_inputs": input_stats
                },
                "waiting_for_input": has_questions or has_pending_inputs or session.waiting_for_user_since is not None
            }

        except Exception as e:
            logger.error(f"Failed to get session summary for {session_id}: {e}")
            return {"error": f"Failed to get session summary: {str(e)}"}

    async def get_active_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get active sessions with basic info"""
        try:
            sessions, _ = await self.session_repo.list_sessions(
                page=1,
                page_size=limit,
                status="active"
            )

            active_sessions = []
            for session in sessions:
                # Get latest message and pending questions
                latest_message = await self.get_latest_message(str(session.id))
                pending_questions = await self.get_pending_questions(str(session.id))

                active_sessions.append({
                    "id": str(session.id),
                    "status": session.status,
                    "created_at": session.created_at.isoformat(),
                    "updated_at": session.updated_at.isoformat(),
                    "iteration_count": session.iteration_count,
                    "user_input_preview": session.user_input[:100] + "..." if len(session.user_input) > 100 else session.user_input,
                    "latest_agent": latest_message.agent_type if latest_message else None,
                    "pending_questions_count": len(pending_questions),
                    "waiting_for_user": session.waiting_for_user_since is not None or len(pending_questions) > 0
                })

            return active_sessions

        except Exception as e:
            logger.error(f"Failed to get active sessions: {e}")
            return []

    async def cleanup_session_data(
        self,
        session_id: str,
        keep_recent_messages: int = 100,
        keep_recent_inputs: int = 50,
        days_old_threshold: int = 30
    ) -> Dict[str, int]:
        """Clean up old session data"""
        try:
            cleanup_results = {}

            # Clean up old messages
            messages_deleted = await self.message_repo.cleanup_old_messages(
                session_id=session_id,
                keep_last_n=keep_recent_messages
            )
            cleanup_results["messages_deleted"] = messages_deleted

            # Clean up old questions
            questions_deleted = await self.question_repo.cleanup_old_questions(
                session_id=session_id,
                days_old=days_old_threshold
            )
            cleanup_results["questions_deleted"] = questions_deleted

            # Clean up old user inputs
            inputs_deleted = await self.user_input_repo.cleanup_old_inputs(
                session_id=session_id,
                days_old=days_old_threshold,
                status="processed"
            )
            cleanup_results["inputs_deleted"] = inputs_deleted

            logger.info(f"Session cleanup completed for {session_id}: {cleanup_results}")
            return cleanup_results

        except Exception as e:
            logger.error(f"Failed to cleanup session {session_id}: {e}")
            return {"error": str(e)}

    # === Statistics and Monitoring ===

    async def get_system_statistics(self) -> Dict[str, Any]:
        """Get system-wide statistics"""
        try:
            session_stats = await self.session_repo.get_session_statistics()
            active_sessions_count = await self.session_repo.get_active_sessions_count()

            return {
                "sessions": session_stats,
                "active_sessions_count": active_sessions_count,
                "timestamp": "datetime.utcnow().isoformat()"  # Placeholder for current timestamp
            }

        except Exception as e:
            logger.error(f"Failed to get system statistics: {e}")
            return {"error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        """Perform database health check"""
        try:
            # Test basic database operations
            await self.session_repo.get_active_sessions_count()

            # Test if we can query different tables
            await self.message_repo.get_next_sequence_number("00000000-0000-0000-0000-000000000000")  # Test with non-existent UUID

            return {
                "status": "healthy",
                "database_connected": True,
                "repositories_available": True,
                "timestamp": "datetime.utcnow().isoformat()"
            }

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": "datetime.utcnow().isoformat()"
            }