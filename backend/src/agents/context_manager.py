"""
Agent context management utilities
"""

import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from .interfaces import AgentContext, AgentType, MessageType


class ContextScope(str, Enum):
    """Context scope levels"""
    SESSION = "session"          # Entire session context
    ITERATION = "iteration"      # Current iteration context
    AGENT = "agent"             # Agent-specific context
    MESSAGE = "message"         # Single message context


@dataclass
class ContextEntry:
    """Single context entry"""
    key: str
    value: Any
    scope: ContextScope
    timestamp: datetime = field(default_factory=datetime.utcnow)
    agent_type: Optional[AgentType] = None
    message_type: Optional[MessageType] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationTurn:
    """Single conversation turn"""
    turn_id: str
    agent_type: AgentType
    message_type: MessageType
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    response_to: Optional[str] = None  # ID of the message this responds to


class AgentContextManager:
    """Manages context for AI agents throughout conversations"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.context_entries: List[ContextEntry] = []
        self.conversation_history: List[ConversationTurn] = []
        self.current_iteration = 0
        self.max_iterations = 5
        self.user_intervention_count = 0
        self.max_interventions = 3

        # Context caching for performance
        self._cached_context: Optional[AgentContext] = None
        self._context_cache_timestamp: Optional[datetime] = None
        self._cache_ttl = timedelta(seconds=30)  # Cache for 30 seconds

    def add_context_entry(
        self,
        key: str,
        value: Any,
        scope: ContextScope = ContextScope.SESSION,
        agent_type: Optional[AgentType] = None,
        message_type: Optional[MessageType] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a context entry"""
        entry = ContextEntry(
            key=key,
            value=value,
            scope=scope,
            agent_type=agent_type,
            message_type=message_type,
            metadata=metadata or {}
        )
        self.context_entries.append(entry)

        # Invalidate cache when context changes
        self._invalidate_cache()

    def get_context_entry(
        self,
        key: str,
        scope: Optional[ContextScope] = None,
        agent_type: Optional[AgentType] = None
    ) -> Optional[ContextEntry]:
        """Get a specific context entry"""
        for entry in reversed(self.context_entries):  # Get most recent first
            if entry.key == key:
                if scope and entry.scope != scope:
                    continue
                if agent_type and entry.agent_type != agent_type:
                    continue
                return entry
        return None

    def get_context_value(
        self,
        key: str,
        default: Any = None,
        scope: Optional[ContextScope] = None,
        agent_type: Optional[AgentType] = None
    ) -> Any:
        """Get a context value"""
        entry = self.get_context_entry(key, scope, agent_type)
        return entry.value if entry else default

    def update_context_entry(
        self,
        key: str,
        value: Any,
        scope: Optional[ContextScope] = None,
        agent_type: Optional[AgentType] = None
    ) -> bool:
        """Update an existing context entry"""
        for entry in reversed(self.context_entries):
            if entry.key == key:
                if scope and entry.scope != scope:
                    continue
                if agent_type and entry.agent_type != agent_type:
                    continue
                entry.value = value
                entry.timestamp = datetime.utcnow()
                self._invalidate_cache()
                return True
        return False

    def remove_context_entry(
        self,
        key: str,
        scope: Optional[ContextScope] = None,
        agent_type: Optional[AgentType] = None
    ) -> bool:
        """Remove a context entry"""
        original_length = len(self.context_entries)
        self.context_entries = [
            entry for entry in self.context_entries
            if not (
                entry.key == key and
                (not scope or entry.scope == scope) and
                (not agent_type or entry.agent_type == agent_type)
            )
        ]

        if len(self.context_entries) < original_length:
            self._invalidate_cache()
            return True
        return False

    def add_conversation_turn(
        self,
        agent_type: AgentType,
        message_type: MessageType,
        content: str,
        response_to: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add a conversation turn"""
        turn_id = f"{agent_type.value}_{len(self.conversation_history)}_{int(datetime.utcnow().timestamp())}"

        turn = ConversationTurn(
            turn_id=turn_id,
            agent_type=agent_type,
            message_type=message_type,
            content=content,
            response_to=response_to,
            metadata=metadata or {}
        )

        self.conversation_history.append(turn)
        self._invalidate_cache()

        return turn_id

    def get_conversation_turn(
        self,
        turn_id: str
    ) -> Optional[ConversationTurn]:
        """Get a specific conversation turn"""
        for turn in self.conversation_history:
            if turn.turn_id == turn_id:
                return turn
        return None

    def get_conversation_history(
        self,
        agent_type: Optional[AgentType] = None,
        message_type: Optional[MessageType] = None,
        limit: Optional[int] = None
    ) -> List[ConversationTurn]:
        """Get filtered conversation history"""
        history = self.conversation_history

        if agent_type:
            history = [turn for turn in history if turn.agent_type == agent_type]

        if message_type:
            history = [turn for turn in history if turn.message_type == message_type]

        if limit:
            history = history[-limit:]

        return history

    def get_recent_context(
        self,
        turn_count: int = 5
    ) -> List[Dict[str, Any]]:
        """Get recent conversation context for API calls"""
        recent_turns = self.conversation_history[-turn_count:]

        context = []
        for turn in recent_turns:
            context.append({
                "role": "assistant" if turn.agent_type != AgentType.PRODUCT_MANAGER else "user",
                "content": turn.content,
                "agent_type": turn.agent_type.value,
                "message_type": turn.message_type.value,
                "timestamp": turn.timestamp.isoformat()
            })

        return context

    def build_agent_context(
        self,
        user_requirements: str,
        supplementary_inputs: Optional[List[str]] = None,
        clarifying_questions: Optional[List[Dict[str, Any]]] = None
    ) -> AgentContext:
        """Build AgentContext object from current state"""
        # Check cache first
        if self._is_cache_valid():
            return self._cached_context

        # Get conversation history as dict list
        conversation_history = []
        for turn in self.conversation_history:
            conversation_history.append({
                "agent_type": turn.agent_type.value,
                "message_type": turn.message_type.value,
                "content": turn.content,
                "timestamp": turn.timestamp.isoformat(),
                "metadata": turn.metadata
            })

        # Extract agent outputs
        agent_outputs = {}
        for turn in self.conversation_history:
            if turn.agent_type.value not in agent_outputs:
                agent_outputs[turn.agent_type.value] = []
            agent_outputs[turn.agent_type.value].append({
                "content": turn.content,
                "message_type": turn.message_type.value,
                "timestamp": turn.timestamp.isoformat()
            })

        # Extract metadata from context entries
        metadata = {}
        for entry in self.context_entries:
            if entry.scope == ContextScope.SESSION:
                metadata[entry.key] = entry.value

        context = AgentContext(
            session_id=self.session_id,
            user_requirements=user_requirements,
            conversation_history=conversation_history,
            current_iteration=self.current_iteration,
            max_iterations=self.max_iterations,
            user_intervention_count=self.user_intervention_count,
            max_interventions=self.max_interventions,
            supplementary_inputs=supplementary_inputs or [],
            clarifying_questions=clarifying_questions or [],
            agent_outputs=agent_outputs,
            metadata=metadata
        )

        # Cache the context
        self._cached_context = context
        self._context_cache_timestamp = datetime.utcnow()

        return context

    def increment_iteration(self) -> bool:
        """Increment iteration counter if not at max"""
        if self.current_iteration < self.max_iterations:
            self.current_iteration += 1
            self.add_context_entry(
                "last_iteration_increment",
                {
                    "new_iteration": self.current_iteration,
                    "timestamp": datetime.utcnow().isoformat()
                },
                scope=ContextScope.ITERATION
            )
            self._invalidate_cache()
            return True
        return False

    def increment_user_intervention(self) -> bool:
        """Increment user intervention counter if not at max"""
        if self.user_intervention_count < self.max_interventions:
            self.user_intervention_count += 1
            self.add_context_entry(
                "last_user_intervention",
                {
                    "intervention_count": self.user_intervention_count,
                    "timestamp": datetime.utcnow().isoformat()
                },
                scope=ContextScope.SESSION
            )
            self._invalidate_cache()
            return True
        return False

    def reset_iteration(self) -> None:
        """Reset iteration counter"""
        self.current_iteration = 0
        self.add_context_entry(
            "iteration_reset",
            {"timestamp": datetime.utcnow().isoformat()},
            scope=ContextScope.SESSION
        )
        self._invalidate_cache()

    def get_session_summary(self) -> Dict[str, Any]:
        """Get session summary for monitoring and debugging"""
        return {
            "session_id": self.session_id,
            "current_iteration": self.current_iteration,
            "max_iterations": self.max_iterations,
            "user_intervention_count": self.user_intervention_count,
            "max_interventions": self.max_interventions,
            "total_conversation_turns": len(self.conversation_history),
            "total_context_entries": len(self.context_entries),
            "session_duration": self._get_session_duration(),
            "last_activity": self._get_last_activity(),
            "agent_participation": self._get_agent_participation()
        }

    def export_context(self) -> Dict[str, Any]:
        """Export full context for persistence or transfer"""
        return {
            "session_id": self.session_id,
            "context_entries": [
                {
                    "key": entry.key,
                    "value": entry.value,
                    "scope": entry.scope.value,
                    "timestamp": entry.timestamp.isoformat(),
                    "agent_type": entry.agent_type.value if entry.agent_type else None,
                    "message_type": entry.message_type.value if entry.message_type else None,
                    "metadata": entry.metadata
                }
                for entry in self.context_entries
            ],
            "conversation_history": [
                {
                    "turn_id": turn.turn_id,
                    "agent_type": turn.agent_type.value,
                    "message_type": turn.message_type.value,
                    "content": turn.content,
                    "timestamp": turn.timestamp.isoformat(),
                    "metadata": turn.metadata,
                    "response_to": turn.response_to
                }
                for turn in self.conversation_history
            ],
            "current_iteration": self.current_iteration,
            "max_iterations": self.max_iterations,
            "user_intervention_count": self.user_intervention_count,
            "max_interventions": self.max_interventions
        }

    def import_context(self, exported_context: Dict[str, Any]) -> None:
        """Import context from exported data"""
        self.session_id = exported_context["session_id"]
        self.current_iteration = exported_context["current_iteration"]
        self.max_iterations = exported_context["max_iterations"]
        self.user_intervention_count = exported_context["user_intervention_count"]
        self.max_interventions = exported_context["max_interventions"]

        # Import context entries
        self.context_entries = []
        for entry_data in exported_context["context_entries"]:
            entry = ContextEntry(
                key=entry_data["key"],
                value=entry_data["value"],
                scope=ContextScope(entry_data["scope"]),
                timestamp=datetime.fromisoformat(entry_data["timestamp"]),
                agent_type=AgentType(entry_data["agent_type"]) if entry_data["agent_type"] else None,
                message_type=MessageType(entry_data["message_type"]) if entry_data["message_type"] else None,
                metadata=entry_data["metadata"]
            )
            self.context_entries.append(entry)

        # Import conversation history
        self.conversation_history = []
        for turn_data in exported_context["conversation_history"]:
            turn = ConversationTurn(
                turn_id=turn_data["turn_id"],
                agent_type=AgentType(turn_data["agent_type"]),
                message_type=MessageType(turn_data["message_type"]),
                content=turn_data["content"],
                timestamp=datetime.fromisoformat(turn_data["timestamp"]),
                metadata=turn_data["metadata"],
                response_to=turn_data["response_to"]
            )
            self.conversation_history.append(turn)

        # Invalidate cache
        self._invalidate_cache()

    def _invalidate_cache(self) -> None:
        """Invalidate the context cache"""
        self._cached_context = None
        self._context_cache_timestamp = None

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        if not self._cached_context or not self._context_cache_timestamp:
            return False
        return datetime.utcnow() - self._context_cache_timestamp < self._cache_ttl

    def _get_session_duration(self) -> Optional[float]:
        """Get session duration in seconds"""
        if not self.conversation_history:
            return None

        first_turn = self.conversation_history[0]
        last_turn = self.conversation_history[-1]
        return (last_turn.timestamp - first_turn.timestamp).total_seconds()

    def _get_last_activity(self) -> Optional[str]:
        """Get last activity timestamp"""
        if not self.conversation_history:
            return None
        return self.conversation_history[-1].timestamp.isoformat()

    def _get_agent_participation(self) -> Dict[str, int]:
        """Get agent participation statistics"""
        participation = {}
        for turn in self.conversation_history:
            agent_type = turn.agent_type.value
            participation[agent_type] = participation.get(agent_type, 0) + 1
        return participation