"""
Agent conversation history management utilities
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import uuid

from .interfaces import AgentType, MessageType


class ConversationRole(str, Enum):
    """Roles in conversation"""
    USER = "user"
    PRODUCT_MANAGER = "product_manager"
    TECHNICAL_DEVELOPER = "technical_developer"
    TEAM_LEAD = "team_lead"
    SYSTEM = "system"


@dataclass
class ConversationMessage:
    """Single conversation message"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    role: ConversationRole = ConversationRole.USER
    content: str = ""
    message_type: MessageType = MessageType.REVIEW
    timestamp: datetime = field(default_factory=datetime.utcnow)
    agent_type: Optional[AgentType] = None
    parent_id: Optional[str] = None  # ID of message this responds to
    children_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    turn_number: int = 0
    iteration: int = 0
    is_edited: bool = False
    edit_timestamp: Optional[datetime] = None
    edit_reason: Optional[str] = None


@dataclass
class ConversationThread:
    """A conversation thread (branch)"""
    thread_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_thread_id: Optional[str] = None
    root_message_id: Optional[str] = None
    message_ids: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationSummary:
    """Summary of conversation for quick access"""
    total_messages: int = 0
    messages_by_agent: Dict[str, int] = field(default_factory=dict)
    messages_by_type: Dict[str, int] = field(default_factory=dict)
    start_time: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    current_iteration: int = 0
    total_iterations: int = 0
    key_points: List[str] = field(default_factory=list)
    action_items: List[str] = field(default_factory=list)
    unresolved_questions: List[str] = field(default_factory=list)


class ConversationManager:
    """Manages conversation history and threading for agents"""

    def __init__(self, session_id: str):
        self.session_id = session_id

        # Message storage
        self.messages: Dict[str, ConversationMessage] = {}
        self.threads: Dict[str, ConversationThread] = {}

        # Current state
        self.current_thread_id: Optional[str] = None
        self.current_iteration = 0
        self.current_turn = 0

        # Conversation tracking
        self.message_count = 0
        self.agent_message_counts: Dict[AgentType, int] = {agent_type: 0 for agent_type in AgentType}
        self.type_message_counts: Dict[MessageType, int] = {msg_type: 0 for msg_type in MessageType}

        # Search and indexing
        self.content_index: Dict[str, List[str]] = {}  # Simple keyword index
        self.last_index_update = datetime.utcnow()

    def add_message(
        self,
        content: str,
        role: ConversationRole,
        message_type: MessageType = MessageType.REVIEW,
        agent_type: Optional[AgentType] = None,
        parent_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add a new message to the conversation"""
        message_id = str(uuid.uuid4())

        # Determine thread
        if thread_id is None:
            thread_id = self.current_thread_id
            if thread_id is None:
                # Create initial thread
                thread_id = self._create_thread()

        # Create message
        message = ConversationMessage(
            id=message_id,
            role=role,
            content=content,
            message_type=message_type,
            agent_type=agent_type,
            parent_id=parent_id,
            metadata=metadata or {},
            turn_number=self.current_turn,
            iteration=self.current_iteration
        )

        # Store message
        self.messages[message_id] = message
        self.message_count += 1

        # Update counts
        if agent_type:
            self.agent_message_counts[agent_type] += 1
        self.type_message_counts[message_type] += 1

        # Update parent-child relationships
        if parent_id and parent_id in self.messages:
            self.messages[parent_id].children_ids.append(message_id)

        # Add to thread
        if thread_id in self.threads:
            self.threads[thread_id].message_ids.append(message_id)

        # Update content index
        self._update_content_index(message_id, content)

        return message_id

    def edit_message(
        self,
        message_id: str,
        new_content: str,
        edit_reason: Optional[str] = None
    ) -> bool:
        """Edit an existing message"""
        if message_id not in self.messages:
            return False

        message = self.messages[message_id]
        message.content = new_content
        message.is_edited = True
        message.edit_timestamp = datetime.utcnow()
        message.edit_reason = edit_reason

        # Update content index
        self._update_content_index(message_id, new_content)

        return True

    def delete_message(self, message_id: str, cascade: bool = False) -> bool:
        """Delete a message"""
        if message_id not in self.messages:
            return False

        message = self.messages[message_id]

        # Check if message has children
        if message.children_ids and not cascade:
            return False  # Cannot delete message with children without cascade

        # Remove from parent
        if message.parent_id and message.parent_id in self.messages:
            parent = self.messages[message.parent_id]
            parent.children_ids = [cid for cid in parent.children_ids if cid != message_id]

        # Remove from thread
        for thread in self.threads.values():
            if message_id in thread.message_ids:
                thread.message_ids = [mid for mid in thread.message_ids if mid != message_id]

        # Delete children if cascade
        if cascade:
            for child_id in message.children_ids.copy():
                self.delete_message(child_id, cascade=True)

        # Remove message
        del self.messages[message_id]

        # Remove from content index
        if message_id in self.content_index:
            del self.content_index[message_id]

        return True

    def get_message(self, message_id: str) -> Optional[ConversationMessage]:
        """Get a specific message"""
        return self.messages.get(message_id)

    def get_conversation_history(
        self,
        thread_id: Optional[str] = None,
        agent_type: Optional[AgentType] = None,
        message_type: Optional[MessageType] = None,
        limit: Optional[int] = None,
        since: Optional[datetime] = None,
        include_edited: bool = True
    ) -> List[ConversationMessage]:
        """Get filtered conversation history"""
        messages = []

        # Determine which messages to include
        if thread_id and thread_id in self.threads:
            message_ids = self.threads[thread_id].message_ids
            messages = [self.messages[mid] for mid in message_ids if mid in self.messages]
        else:
            messages = list(self.messages.values())

        # Apply filters
        if agent_type:
            messages = [msg for msg in messages if msg.agent_type == agent_type]

        if message_type:
            messages = [msg for msg in messages if msg.message_type == message_type]

        if since:
            messages = [msg for msg in messages if msg.timestamp >= since]

        if not include_edited:
            messages = [msg for msg in messages if not msg.is_edited]

        # Sort by timestamp
        messages.sort(key=lambda x: x.timestamp)

        # Apply limit
        if limit:
            messages = messages[-limit:]

        return messages

    def get_thread_messages(self, thread_id: str) -> List[ConversationMessage]:
        """Get all messages in a thread"""
        if thread_id not in self.threads:
            return []

        thread = self.threads[thread_id]
        messages = []
        for message_id in thread.message_ids:
            if message_id in self.messages:
                messages.append(self.messages[message_id])

        # Sort by timestamp
        messages.sort(key=lambda x: x.timestamp)
        return messages

    def get_message_chain(self, message_id: str, include_children: bool = False) -> List[ConversationMessage]:
        """Get the full chain of messages leading to a specific message"""
        if message_id not in self.messages:
            return []

        chain = []
        current_id = message_id

        # Trace up the chain
        while current_id:
            if current_id in self.messages:
                chain.insert(0, self.messages[current_id])
                current_id = self.messages[current_id].parent_id
            else:
                break

        # Add children if requested
        if include_children:
            message = self.messages[message_id]
            for child_id in message.children_ids:
                child_chain = self.get_message_chain(child_id, include_children=True)
                chain.extend(child_chain)

        return chain

    def get_recent_context(
        self,
        message_count: int = 10,
        include_system: bool = False
    ) -> List[Dict[str, Any]]:
        """Get recent conversation context for API calls"""
        recent_messages = self.get_conversation_history(limit=message_count)

        context = []
        for message in recent_messages:
            if not include_system and message.role == ConversationRole.SYSTEM:
                continue

            context.append({
                "role": message.role.value,
                "content": message.content,
                "message_type": message.message_type.value,
                "agent_type": message.agent_type.value if message.agent_type else None,
                "timestamp": message.timestamp.isoformat(),
                "turn": message.turn_number,
                "iteration": message.iteration
            })

        return context

    def search_messages(
        self,
        query: str,
        agent_type: Optional[AgentType] = None,
        message_type: Optional[MessageType] = None,
        limit: int = 20
    ) -> List[Tuple[ConversationMessage, float]]:
        """Search messages by content"""
        query_words = query.lower().split()
        results = []

        for message in self.messages.values():
            # Apply filters
            if agent_type and message.agent_type != agent_type:
                continue
            if message_type and message.message_type != message_type:
                continue

            # Simple relevance scoring
            content_lower = message.content.lower()
            score = 0

            for word in query_words:
                if word in content_lower:
                    score += 1
                    # Exact phrase gets higher score
                    if query.lower() in content_lower:
                        score += 2

            if score > 0:
                results.append((message, score))

        # Sort by score (descending) then by timestamp (descending)
        results.sort(key=lambda x: (x[1], x[0].timestamp), reverse=True)

        # Return top results
        return results[:limit]

    def get_conversation_summary(self) -> ConversationSummary:
        """Get a summary of the conversation"""
        if not self.messages:
            return ConversationSummary()

        # Calculate basic stats
        total_messages = len(self.messages)
        messages_by_agent = {
            agent_type.value: count
            for agent_type, count in self.agent_message_counts.items()
        }
        messages_by_type = {
            msg_type.value: count
            for msg_type, count in self.type_message_counts.items()
        }

        # Find start and end times
        timestamps = [msg.timestamp for msg in self.messages.values()]
        start_time = min(timestamps)
        last_activity = max(timestamps)

        # Extract key points and action items (simple keyword-based)
        all_content = " ".join(msg.content for msg in self.messages.values())

        key_points = []
        if "important" in all_content.lower() or "key" in all_content.lower():
            key_points.append("Important points discussed")

        action_items = []
        if "todo" in all_content.lower() or "action" in all_content.lower():
            action_items.append("Action items identified")

        unresolved_questions = []
        for msg in self.messages.values():
            if "?" in msg.content and msg.message_type == MessageType.QUESTION:
                unresolved_questions.append(msg.content)

        return ConversationSummary(
            total_messages=total_messages,
            messages_by_agent=messages_by_agent,
            messages_by_type=messages_by_type,
            start_time=start_time,
            last_activity=last_activity,
            current_iteration=self.current_iteration,
            total_iterations=self.current_iteration + 1,
            key_points=key_points,
            action_items=action_items,
            unresolved_questions=unresolved_questions
        )

    def create_branch(self, parent_message_id: str, branch_name: Optional[str] = None) -> str:
        """Create a new conversation branch"""
        if parent_message_id not in self.messages:
            raise ValueError("Parent message not found")

        # Create new thread
        thread_id = self._create_thread(
            parent_thread_id=self.current_thread_id,
            root_message_id=parent_message_id,
            metadata={"branch_name": branch_name} if branch_name else {}
        )

        return thread_id

    def switch_thread(self, thread_id: str) -> bool:
        """Switch to a different conversation thread"""
        if thread_id not in self.threads:
            return False

        self.current_thread_id = thread_id
        return True

    def start_new_turn(self) -> int:
        """Start a new conversation turn"""
        self.current_turn += 1
        return self.current_turn

    def start_new_iteration(self) -> int:
        """Start a new conversation iteration"""
        self.current_iteration += 1
        return self.current_iteration

    def get_agent_participation_stats(self) -> Dict[str, Any]:
        """Get participation statistics for agents"""
        stats = {}

        for agent_type in AgentType:
            agent_messages = [
                msg for msg in self.messages.values()
                if msg.agent_type == agent_type
            ]

            if agent_messages:
                word_counts = [len(msg.content.split()) for msg in agent_messages]
                avg_word_count = sum(word_counts) / len(word_counts)

                stats[agent_type.value] = {
                    "message_count": len(agent_messages),
                    "average_word_count": avg_word_count,
                    "first_message": min(msg.timestamp for msg in agent_messages).isoformat(),
                    "last_message": max(msg.timestamp for msg in agent_messages).isoformat(),
                    "message_types": {
                        msg_type.value: len([
                            msg for msg in agent_messages
                            if msg.message_type == msg_type
                        ])
                        for msg_type in MessageType
                    }
                }
            else:
                stats[agent_type.value] = {
                    "message_count": 0,
                    "average_word_count": 0,
                    "first_message": None,
                    "last_message": None,
                    "message_types": {msg_type.value: 0 for msg_type in MessageType}
                }

        return stats

    def export_conversation(self, include_metadata: bool = True) -> Dict[str, Any]:
        """Export conversation data"""
        return {
            "session_id": self.session_id,
            "current_iteration": self.current_iteration,
            "current_turn": self.current_turn,
            "current_thread_id": self.current_thread_id,
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role.value,
                    "content": msg.content,
                    "message_type": msg.message_type.value,
                    "timestamp": msg.timestamp.isoformat(),
                    "agent_type": msg.agent_type.value if msg.agent_type else None,
                    "parent_id": msg.parent_id,
                    "children_ids": msg.children_ids,
                    "metadata": msg.metadata if include_metadata else {},
                    "turn_number": msg.turn_number,
                    "iteration": msg.iteration,
                    "is_edited": msg.is_edited,
                    "edit_timestamp": msg.edit_timestamp.isoformat() if msg.edit_timestamp else None,
                    "edit_reason": msg.edit_reason
                }
                for msg in self.messages.values()
            ],
            "threads": [
                {
                    "thread_id": thread.thread_id,
                    "parent_thread_id": thread.parent_thread_id,
                    "root_message_id": thread.root_message_id,
                    "message_ids": thread.message_ids,
                    "created_at": thread.created_at.isoformat(),
                    "is_active": thread.is_active,
                    "metadata": thread.metadata if include_metadata else {}
                }
                for thread in self.threads.values()
            ],
            "summary": self.get_conversation_summary().__dict__
        }

    def import_conversation(self, conversation_data: Dict[str, Any]) -> None:
        """Import conversation data"""
        self.session_id = conversation_data["session_id"]
        self.current_iteration = conversation_data["current_iteration"]
        self.current_turn = conversation_data["current_turn"]
        self.current_thread_id = conversation_data.get("current_thread_id")

        # Import messages
        for msg_data in conversation_data["messages"]:
            message = ConversationMessage(
                id=msg_data["id"],
                role=ConversationRole(msg_data["role"]),
                content=msg_data["content"],
                message_type=MessageType(msg_data["message_type"]),
                timestamp=datetime.fromisoformat(msg_data["timestamp"]),
                agent_type=AgentType(msg_data["agent_type"]) if msg_data["agent_type"] else None,
                parent_id=msg_data["parent_id"],
                children_ids=msg_data["children_ids"],
                metadata=msg_data["metadata"],
                turn_number=msg_data["turn_number"],
                iteration=msg_data["iteration"],
                is_edited=msg_data["is_edited"],
                edit_timestamp=datetime.fromisoformat(msg_data["edit_timestamp"]) if msg_data["edit_timestamp"] else None,
                edit_reason=msg_data["edit_reason"]
            )
            self.messages[message.id] = message

        # Import threads
        for thread_data in conversation_data["threads"]:
            thread = ConversationThread(
                thread_id=thread_data["thread_id"],
                parent_thread_id=thread_data["parent_thread_id"],
                root_message_id=thread_data["root_message_id"],
                message_ids=thread_data["message_ids"],
                created_at=datetime.fromisoformat(thread_data["created_at"]),
                is_active=thread_data["is_active"],
                metadata=thread_data["metadata"]
            )
            self.threads[thread.thread_id] = thread

        # Rebuild counts and indexes
        self._rebuild_counts_and_indexes()

    def _create_thread(
        self,
        parent_thread_id: Optional[str] = None,
        root_message_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new conversation thread"""
        thread = ConversationThread(
            parent_thread_id=parent_thread_id,
            root_message_id=root_message_id,
            metadata=metadata or {}
        )
        self.threads[thread.thread_id] = thread
        self.current_thread_id = thread.thread_id
        return thread.thread_id

    def _update_content_index(self, message_id: str, content: str) -> None:
        """Update the content search index"""
        # Simple keyword indexing
        words = content.lower().split()
        # Filter out common words and keep only meaningful words
        meaningful_words = [
            word.strip('.,!?;:"()[]{}')
            for word in words
            if len(word) > 3 and word not in ['this', 'that', 'with', 'from', 'they', 'have', 'been']
        ]

        self.content_index[message_id] = meaningful_words
        self.last_index_update = datetime.utcnow()

    def _rebuild_counts_and_indexes(self) -> None:
        """Rebuild message counts and content indexes"""
        # Reset counts
        self.message_count = len(self.messages)
        self.agent_message_counts = {agent_type: 0 for agent_type in AgentType}
        self.type_message_counts = {msg_type: 0 for msg_type in MessageType}

        # Rebuild counts
        for message in self.messages.values():
            if message.agent_type:
                self.agent_message_counts[message.agent_type] += 1
            self.type_message_counts[message.message_type] += 1

        # Rebuild content index
        self.content_index = {}
        for message_id, message in self.messages.items():
            self._update_content_index(message_id, message.content)