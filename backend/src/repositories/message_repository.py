"""
Message repository for database operations
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc, func, and_
from sqlalchemy.orm import selectinload

from ..models.session import AgentMessage, Session as SessionModel
from ..core.logging import get_logger

logger = get_logger(__name__)


class MessageRepository:
    """Repository for agent message database operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_message(
        self,
        session_id: str,
        agent_type: str,
        message_content: str,
        message_type: str,
        sequence_number: int,
        parent_message_id: Optional[str] = None,
        processing_time_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AgentMessage:
        """Create a new agent message"""
        try:
            message = AgentMessage(
                session_id=session_id,
                agent_type=agent_type,
                message_content=message_content,
                message_type=message_type,
                sequence_number=sequence_number,
                parent_message_id=parent_message_id,
                processing_time_ms=processing_time_ms,
                metadata=metadata or {}
            )

            self.db.add(message)
            await self.db.commit()
            await self.db.refresh(message)

            logger.info(f"Created message {message.id} for session {session_id}")
            return message

        except Exception as e:
            logger.error(f"Failed to create message: {e}")
            await self.db.rollback()
            raise

    async def get_message(self, message_id: str) -> Optional[AgentMessage]:
        """Get a message by ID"""
        try:
            result = await self.db.execute(
                select(AgentMessage).where(AgentMessage.id == message_id)
            )
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Failed to get message {message_id}: {e}")
            raise

    async def get_session_messages(
        self,
        session_id: str,
        page: int = 1,
        page_size: int = 50,
        agent_type: Optional[str] = None,
        message_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> tuple[List[AgentMessage], int]:
        """Get messages for a session with pagination and filtering"""
        try:
            # Build query
            query = select(AgentMessage).where(AgentMessage.session_id == session_id)

            if agent_type:
                query = query.where(AgentMessage.agent_type == agent_type)

            if message_type:
                query = query.where(AgentMessage.message_type == message_type)

            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            total_count_result = await self.db.execute(count_query)
            total_count = total_count_result.scalar()

            # Apply pagination and ordering
            query = query.order_by(AgentMessage.sequence_number)

            if limit:
                query = query.limit(limit)
            else:
                query = query.offset((page - 1) * page_size).limit(page_size)

            # Execute query
            result = await self.db.execute(query)
            messages = result.scalars().all()

            return messages, total_count

        except Exception as e:
            logger.error(f"Failed to get messages for session {session_id}: {e}")
            raise

    async def get_latest_message(
        self,
        session_id: str,
        agent_type: Optional[str] = None
    ) -> Optional[AgentMessage]:
        """Get the latest message for a session"""
        try:
            query = select(AgentMessage).where(AgentMessage.session_id == session_id)

            if agent_type:
                query = query.where(AgentMessage.agent_type == agent_type)

            query = query.order_by(desc(AgentMessage.sequence_number)).limit(1)

            result = await self.db.execute(query)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Failed to get latest message for session {session_id}: {e}")
            raise

    async def get_next_sequence_number(self, session_id: str) -> int:
        """Get the next sequence number for a session"""
        try:
            result = await self.db.execute(
                select(func.coalesce(func.max(AgentMessage.sequence_number), 0) + 1)
                .where(AgentMessage.session_id == session_id)
            )
            return result.scalar() or 1

        except Exception as e:
            logger.error(f"Failed to get next sequence number for session {session_id}: {e}")
            raise

    async def get_conversation_thread(
        self,
        session_id: str,
        root_message_id: str
    ) -> List[AgentMessage]:
        """Get a conversation thread starting from a root message"""
        try:
            # This is a simplified version - in a full implementation,
            # you might want to use a recursive CTE for better performance
            result = await self.db.execute(
                select(AgentMessage)
                .where(
                    and_(
                        AgentMessage.session_id == session_id,
                        or_(
                            AgentMessage.id == root_message_id,
                            AgentMessage.parent_message_id == root_message_id
                        )
                    )
                )
                .order_by(AgentMessage.sequence_number)
            )

            messages = result.scalars().all()

            # Get child messages recursively
            all_messages = list(messages)
            for message in messages:
                if message.id != root_message_id:
                    continue

                child_messages = await self._get_child_messages_recursive(session_id, message.id)
                all_messages.extend(child_messages)

            return all_messages

        except Exception as e:
            logger.error(f"Failed to get conversation thread for session {session_id}: {e}")
            raise

    async def _get_child_messages_recursive(
        self,
        session_id: str,
        parent_message_id: str
    ) -> List[AgentMessage]:
        """Recursively get child messages"""
        try:
            result = await self.db.execute(
                select(AgentMessage)
                .where(
                    and_(
                        AgentMessage.session_id == session_id,
                        AgentMessage.parent_message_id == parent_message_id
                    )
                )
                .order_by(AgentMessage.sequence_number)
            )

            messages = result.scalars().all()
            all_messages = list(messages)

            for message in messages:
                child_messages = await self._get_child_messages_recursive(session_id, message.id)
                all_messages.extend(child_messages)

            return all_messages

        except Exception as e:
            logger.error(f"Failed to get child messages: {e}")
            return []

    async def update_message_metadata(
        self,
        message_id: str,
        metadata_updates: Dict[str, Any]
    ) -> bool:
        """Update message metadata"""
        try:
            result = await self.db.execute(
                select(AgentMessage).where(AgentMessage.id == message_id)
            )
            message = result.scalar_one_or_none()

            if not message:
                return False

            message.metadata = message.metadata or {}
            message.metadata.update(metadata_updates)

            await self.db.commit()
            return True

        except Exception as e:
            logger.error(f"Failed to update message {message_id} metadata: {e}")
            await self.db.rollback()
            raise

    async def delete_message(self, message_id: str) -> bool:
        """Delete a message"""
        try:
            result = await self.db.execute(
                select(AgentMessage).where(AgentMessage.id == message_id)
            )
            message = result.scalar_one_or_none()

            if not message:
                return False

            await self.db.delete(message)
            await self.db.commit()

            logger.info(f"Deleted message {message_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete message {message_id}: {e}")
            await self.db.rollback()
            raise

    async def get_message_statistics(self, session_id: str) -> Dict[str, Any]:
        """Get message statistics for a session"""
        try:
            # Count messages by agent type
            agent_type_counts = {}
            for agent_type in ["product_manager", "technical_developer", "team_lead"]:
                result = await self.db.execute(
                    select(func.count())
                    .select_from(
                        select(AgentMessage)
                        .where(
                            and_(
                                AgentMessage.session_id == session_id,
                                AgentMessage.agent_type == agent_type
                            )
                        )
                        .subquery()
                    )
                )
                agent_type_counts[agent_type] = result.scalar()

            # Count messages by type
            message_type_counts = {}
            for message_type in ["requirement", "technical_solution", "review", "approval", "rejection", "question"]:
                result = await self.db.execute(
                    select(func.count())
                    .select_from(
                        select(AgentMessage)
                        .where(
                            and_(
                                AgentMessage.session_id == session_id,
                                AgentMessage.message_type == message_type
                            )
                        )
                        .subquery()
                    )
                )
                message_type_counts[message_type] = result.scalar()

            # Average processing time
            avg_time_result = await self.db.execute(
                select(func.avg(AgentMessage.processing_time_ms))
                .where(
                    and_(
                        AgentMessage.session_id == session_id,
                        AgentMessage.processing_time_ms.isnot(None)
                    )
                )
            )
            avg_processing_time = avg_time_result.scalar() or 0

            return {
                "agent_type_counts": agent_type_counts,
                "message_type_counts": message_type_counts,
                "average_processing_time_ms": float(avg_processing_time),
                "total_messages": sum(agent_type_counts.values())
            }

        except Exception as e:
            logger.error(f"Failed to get message statistics for session {session_id}: {e}")
            raise

    async def cleanup_old_messages(self, session_id: str, keep_last_n: int = 100) -> int:
        """Clean up old messages, keeping only the last N messages"""
        try:
            # Get messages to keep
            result = await self.db.execute(
                select(AgentMessage.id)
                .where(AgentMessage.session_id == session_id)
                .order_by(desc(AgentMessage.sequence_number))
                .limit(keep_last_n)
            )

            keep_ids = [row[0] for row in result.all()]

            # Delete messages not in keep list
            if keep_ids:
                delete_result = await self.db.execute(
                    select(AgentMessage)
                    .where(
                        and_(
                            AgentMessage.session_id == session_id,
                            AgentMessage.id.notin_(keep_ids)
                        )
                    )
                )

                messages_to_delete = delete_result.scalars().all()

                for message in messages_to_delete:
                    await self.db.delete(message)

                await self.db.commit()
                logger.info(f"Cleaned up {len(messages_to_delete)} old messages for session {session_id}")
                return len(messages_to_delete)
            else:
                # If no messages to keep, delete all messages
                delete_result = await self.db.execute(
                    select(AgentMessage).where(AgentMessage.session_id == session_id)
                )

                messages_to_delete = delete_result.scalars().all()

                for message in messages_to_delete:
                    await self.db.delete(message)

                await self.db.commit()
                logger.info(f"Deleted all {len(messages_to_delete)} messages for session {session_id}")
                return len(messages_to_delete)

        except Exception as e:
            logger.error(f"Failed to cleanup old messages for session {session_id}: {e}")
            await self.db.rollback()
            raise