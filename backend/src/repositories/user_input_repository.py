"""
User input repository for database operations
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc, func, and_, or_
from sqlalchemy.orm import selectinload

from ..models.session import SupplementaryUserInput, Session as SessionModel
from ..core.logging import get_logger

logger = get_logger(__name__)


class UserInputRepository:
    """Repository for supplementary user input database operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_user_input(
        self,
        session_id: str,
        input_content: str,
        input_type: str = "supplementary",
        processing_status: str = "pending",
        metadata: Optional[Dict[str, Any]] = None
    ) -> SupplementaryUserInput:
        """Create a new supplementary user input"""
        try:
            # Get next sequence number
            seq_result = await self.db.execute(
                select(func.coalesce(func.max(SupplementaryUserInput.sequence_number), 0) + 1)
                .where(SupplementaryUserInput.session_id == session_id)
            )
            next_sequence = seq_result.scalar() or 1

            user_input = SupplementaryUserInput(
                session_id=session_id,
                input_content=input_content,
                input_type=input_type,
                sequence_number=next_sequence,
                processing_status=processing_status,
                metadata=metadata or {}
            )

            self.db.add(user_input)
            await self.db.commit()
            await self.db.refresh(user_input)

            logger.info(f"Created user input {user_input.id} for session {session_id}")
            return user_input

        except Exception as e:
            logger.error(f"Failed to create user input: {e}")
            await self.db.rollback()
            raise

    async def get_user_input(self, input_id: str) -> Optional[SupplementaryUserInput]:
        """Get a user input by ID"""
        try:
            result = await self.db.execute(
                select(SupplementaryUserInput).where(SupplementaryUserInput.id == input_id)
            )
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Failed to get user input {input_id}: {e}")
            raise

    async def get_session_inputs(
        self,
        session_id: str,
        input_type: Optional[str] = None,
        processing_status: Optional[str] = None,
        incorporated_only: bool = False,
        limit: Optional[int] = None
    ) -> List[SupplementaryUserInput]:
        """Get supplementary user inputs for a session"""
        try:
            query = select(SupplementaryUserInput).where(SupplementaryUserInput.session_id == session_id)

            if input_type:
                query = query.where(SupplementaryUserInput.input_type == input_type)

            if processing_status:
                query = query.where(SupplementaryUserInput.processing_status == processing_status)

            if incorporated_only:
                query = query.where(SupplementaryUserInput.incorporated_into_requirements == True)

            query = query.order_by(SupplementaryUserInput.sequence_number)

            if limit:
                query = query.limit(limit)

            result = await self.db.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Failed to get user inputs for session {session_id}: {e}")
            raise

    async def get_pending_inputs(self, session_id: str) -> List[SupplementaryUserInput]:
        """Get pending user inputs for a session"""
        try:
            result = await self.db.execute(
                select(SupplementaryUserInput)
                .where(
                    and_(
                        SupplementaryUserInput.session_id == session_id,
                        SupplementaryUserInput.processing_status == "pending"
                    )
                )
                .order_by(SupplementaryUserInput.sequence_number)
            )
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Failed to get pending inputs for session {session_id}: {e}")
            raise

    async def update_input_status(
        self,
        input_id: str,
        processing_status: str,
        incorporated_into_requirements: bool = False,
        metadata_updates: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update user input processing status"""
        try:
            result = await self.db.execute(
                select(SupplementaryUserInput).where(SupplementaryUserInput.id == input_id)
            )
            user_input = result.scalar_one_or_none()

            if not user_input:
                return False

            user_input.processing_status = processing_status
            user_input.incorporated_into_requirements = incorporated_into_requirements

            if metadata_updates:
                user_input.metadata = user_input.metadata or {}
                user_input.metadata.update(metadata_updates)

            await self.db.commit()
            logger.info(f"Updated user input {input_id} status to {processing_status}")
            return True

        except Exception as e:
            logger.error(f"Failed to update user input {input_id} status: {e}")
            await self.db.rollback()
            raise

    async def mark_as_incorporated(self, input_id: str) -> bool:
        """Mark a user input as incorporated into requirements"""
        try:
            result = await self.db.execute(
                select(SupplementaryUserInput).where(SupplementaryUserInput.id == input_id)
            )
            user_input = result.scalar_one_or_none()

            if not user_input:
                return False

            user_input.incorporated_into_requirements = True
            user_input.processing_status = "incorporated"

            await self.db.commit()
            logger.info(f"Marked user input {input_id} as incorporated")
            return True

        except Exception as e:
            logger.error(f"Failed to mark user input {input_id} as incorporated: {e}")
            await self.db.rollback()
            raise

    async def get_latest_input(
        self,
        session_id: str,
        input_type: Optional[str] = None
    ) -> Optional[SupplementaryUserInput]:
        """Get the latest user input for a session"""
        try:
            query = select(SupplementaryUserInput).where(SupplementaryUserInput.session_id == session_id)

            if input_type:
                query = query.where(SupplementaryUserInput.input_type == input_type)

            query = query.order_by(desc(SupplementaryUserInput.sequence_number)).limit(1)

            result = await self.db.execute(query)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Failed to get latest user input for session {session_id}: {e}")
            raise

    async def get_inputs_by_type(
        self,
        session_id: str,
        input_type: str
    ) -> List[SupplementaryUserInput]:
        """Get user inputs by type for a session"""
        try:
            result = await self.db.execute(
                select(SupplementaryUserInput)
                .where(
                    and_(
                        SupplementaryUserInput.session_id == session_id,
                        SupplementaryUserInput.input_type == input_type
                    )
                )
                .order_by(SupplementaryUserInput.sequence_number)
            )
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Failed to get user inputs by type for session {session_id}: {e}")
            raise

    async def has_pending_inputs(self, session_id: str) -> bool:
        """Check if a session has pending user inputs"""
        try:
            result = await self.db.execute(
                select(func.count())
                .select_from(
                    select(SupplementaryUserInput)
                    .where(
                        and_(
                            SupplementaryUserInput.session_id == session_id,
                            SupplementaryUserInput.processing_status == "pending"
                        )
                    )
                    .subquery()
                )
            )
            count = result.scalar()
            return count > 0

        except Exception as e:
            logger.error(f"Failed to check pending inputs for session {session_id}: {e}")
            return False

    async def get_input_statistics(self, session_id: str) -> Dict[str, Any]:
        """Get user input statistics for a session"""
        try:
            # Count inputs by status
            status_counts = {}
            for status in ["pending", "processing", "processed", "incorporated", "failed"]:
                result = await self.db.execute(
                    select(func.count())
                    .select_from(
                        select(SupplementaryUserInput)
                        .where(
                            and_(
                                SupplementaryUserInput.session_id == session_id,
                                SupplementaryUserInput.processing_status == status
                            )
                        )
                        .subquery()
                    )
                )
                status_counts[status] = result.scalar()

            # Count inputs by type
            type_counts = {}
            for input_type in ["supplementary", "clarification_response", "general", "feedback"]:
                result = await self.db.execute(
                    select(func.count())
                    .select_from(
                        select(SupplementaryUserInput)
                        .where(
                            and_(
                                SupplementaryUserInput.session_id == session_id,
                                SupplementaryUserInput.input_type == input_type
                            )
                        )
                        .subquery()
                    )
                )
                type_counts[input_type] = result.scalar()

            # Count incorporated vs not incorporated
            incorporated_result = await self.db.execute(
                select(func.count())
                .select_from(
                    select(SupplementaryUserInput)
                    .where(
                        and_(
                            SupplementaryUserInput.session_id == session_id,
                            SupplementaryUserInput.incorporated_into_requirements == True
                        )
                    )
                    .subquery()
                )
            )
            incorporated_count = incorporated_result.scalar()

            total_result = await self.db.execute(
                select(func.count())
                .select_from(
                    select(SupplementaryUserInput)
                    .where(SupplementaryUserInput.session_id == session_id)
                    .subquery()
                )
            )
            total_count = total_result.scalar()

            return {
                "status_counts": status_counts,
                "type_counts": type_counts,
                "incorporated_count": incorporated_count,
                "not_incorporated_count": total_count - incorporated_count,
                "total_inputs": total_count,
                "incorporation_rate": (incorporated_count / total_count * 100) if total_count > 0 else 0
            }

        except Exception as e:
            logger.error(f"Failed to get input statistics for session {session_id}: {e}")
            raise

    async def delete_user_input(self, input_id: str) -> bool:
        """Delete a user input"""
        try:
            result = await self.db.execute(
                select(SupplementaryUserInput).where(SupplementaryUserInput.id == input_id)
            )
            user_input = result.scalar_one_or_none()

            if not user_input:
                return False

            await self.db.delete(user_input)
            await self.db.commit()

            logger.info(f"Deleted user input {input_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete user input {input_id}: {e}")
            await self.db.rollback()
            raise

    async def cleanup_old_inputs(
        self,
        session_id: str,
        days_old: int = 30,
        status: Optional[str] = None
    ) -> int:
        """Clean up old user inputs"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)

            query = select(SupplementaryUserInput).where(
                and_(
                    SupplementaryUserInput.session_id == session_id,
                    SupplementaryUserInput.provided_at < cutoff_date
                )
            )

            if status:
                query = query.where(SupplementaryUserInput.processing_status == status)
            else:
                # Only clean up processed/failed inputs by default
                query = query.where(
                    SupplementaryUserInput.processing_status.in_(["processed", "incorporated", "failed"])
                )

            result = await self.db.execute(query)
            inputs_to_delete = result.scalars().all()

            for user_input in inputs_to_delete:
                await self.db.delete(user_input)

            await self.db.commit()
            logger.info(f"Cleaned up {len(inputs_to_delete)} old user inputs for session {session_id}")
            return len(inputs_to_delete)

        except Exception as e:
            logger.error(f"Failed to cleanup old user inputs for session {session_id}: {e}")
            await self.db.rollback()
            raise

    async def bulk_update_status(
        self,
        input_ids: List[str],
        processing_status: str,
        metadata_updates: Optional[Dict[str, Any]] = None
    ) -> int:
        """Bulk update status for multiple user inputs"""
        try:
            result = await self.db.execute(
                select(SupplementaryUserInput)
                .where(SupplementaryUserInput.id.in_(input_ids))
            )

            inputs = result.scalars().all()
            updated_count = 0

            for user_input in inputs:
                user_input.processing_status = processing_status

                if metadata_updates:
                    user_input.metadata = user_input.metadata or {}
                    user_input.metadata.update(metadata_updates)

                updated_count += 1

            if updated_count > 0:
                await self.db.commit()
                logger.info(f"Bulk updated {updated_count} user inputs to status {processing_status}")

            return updated_count

        except Exception as e:
            logger.error(f"Failed to bulk update user input status: {e}")
            await self.db.rollback()
            raise