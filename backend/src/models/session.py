"""
Session model and related database models
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, Text, Integer, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from ..database.connection import Base


class Session(Base):
    """Session model for prompt generation sessions"""

    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_input = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="active")
    final_prompt = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    iteration_count = Column(Integer, default=0)
    user_intervention_count = Column(Integer, default=0)
    max_interventions = Column(Integer, default=3)
    waiting_for_user_since = Column(DateTime(timezone=True), nullable=True)
    current_question_id = Column(UUID(as_uuid=True), nullable=True)
    session_metadata = Column(JSON, default=dict)

    def __repr__(self) -> str:
        return f"<Session(id={self.id}, status={self.status})>"


class AgentMessage(Base):
    """Agent message model"""

    __tablename__ = "agent_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    agent_type = Column(String(20), nullable=False)  # product_manager, technical_developer, team_lead
    message_content = Column(Text, nullable=False)
    message_type = Column(String(20), nullable=False)  # requirement, solution, review, approval, rejection
    sequence_number = Column(Integer, nullable=False)
    parent_message_id = Column(UUID(as_uuid=True), ForeignKey("agent_messages.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processing_time_ms = Column(Integer, nullable=True)
    session_metadata = Column(JSON, default=dict)

    def __repr__(self) -> str:
        return f"<AgentMessage(id={self.id}, agent_type={self.agent_type}, sequence={self.sequence_number})>"


class SupplementaryUserInput(Base):
    """Supplementary user input model"""

    __tablename__ = "supplementary_user_inputs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    input_content = Column(Text, nullable=False)
    input_type = Column(String(20), nullable=False, default="supplementary")
    provided_at = Column(DateTime(timezone=True), server_default=func.now())
    processing_status = Column(String(20), default="pending")
    incorporated_into_requirements = Column(Boolean, default=False)
    sequence_number = Column(Integer, nullable=False)
    session_metadata = Column(JSON, default=dict)

    def __repr__(self) -> str:
        return f"<SupplementaryUserInput(id={self.id}, type={self.input_type}, status={self.processing_status})>"


class ClarifyingQuestion(Base):
    """Clarifying question model"""

    __tablename__ = "clarifying_questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    question_text = Column(Text, nullable=False)
    question_type = Column(String(20), nullable=False)  # ambiguity, clarification, confirmation
    priority = Column(Integer, default=1)  # 1=high, 2=medium, 3=low
    asked_at = Column(DateTime(timezone=True), server_default=func.now())
    response_deadline = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), default="pending")  # pending, answered, expired, cancelled
    response_text = Column(Text, nullable=True)
    responded_at = Column(DateTime(timezone=True), nullable=True)
    agent_type = Column(String(20), default="product_manager")
    sequence_number = Column(Integer, nullable=False)
    session_metadata = Column(JSON, default=dict)

    def __repr__(self) -> str:
        return f"<ClarifyingQuestion(id={self.id}, status={self.status}, priority={self.priority})>"


class SessionWaitingState(Base):
    """Session waiting state model"""

    __tablename__ = "session_waiting_states"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    waiting_type = Column(String(20), nullable=False)  # user_input, clarifying_question_response
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    status = Column(String(20), default="active")  # active, resolved, timeout, cancelled
    related_entity_id = Column(UUID(as_uuid=True), nullable=True)
    timeout_duration_seconds = Column(Integer, default=30)
    session_metadata = Column(JSON, default=dict)

    def __repr__(self) -> str:
        return f"<SessionWaitingState(id={self.id}, type={self.waiting_type}, status={self.status})>"