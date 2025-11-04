"""
Agent state tracking utilities
"""

from enum import Enum
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json

from .interfaces import AgentType, MessageType


class AgentState(str, Enum):
    """Agent execution states"""
    IDLE = "idle"                    # Not currently processing
    INITIALIZING = "initializing"    # Starting up
    PROCESSING = "processing"        # Working on a request
    WAITING_FOR_USER = "waiting_for_user"  # Waiting for user input
    WAITING_FOR_AGENT = "waiting_for_agent"  # Waiting for another agent
    ERROR = "error"                  # Encountered an error
    COMPLETED = "completed"          # Finished current task
    TIMEOUT = "timeout"              # Processing timed out


class SessionState(str, Enum):
    """Overall session states"""
    CREATED = "created"              # Session created but not started
    ACTIVE = "active"                # Session is running
    PAUSED = "paused"                # Session paused for user input
    WAITING_FOR_APPROVAL = "waiting_for_approval"  # Awaiting final approval
    COMPLETED = "completed"          # Session completed successfully
    FAILED = "failed"                # Session failed
    TIMEOUT = "timeout"              # Session timed out
    CANCELLED = "cancelled"          # Session cancelled by user


@dataclass
class StateTransition:
    """Single state transition record"""
    from_state: str
    to_state: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentStateSnapshot:
    """Snapshot of agent state at a point in time"""
    agent_type: AgentType
    state: AgentState
    timestamp: datetime = field(default_factory=datetime.utcnow)
    current_task: Optional[str] = None
    progress_percentage: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentStateTracker:
    """Tracks and manages agent states throughout sessions"""

    def __init__(self, session_id: str):
        self.session_id = session_id

        # Current states
        self.agent_states: Dict[AgentType, AgentState] = {
            agent_type: AgentState.IDLE for agent_type in AgentType
        }
        self.session_state = SessionState.CREATED

        # State history
        self.agent_state_history: Dict[AgentType, List[AgentStateSnapshot]] = {
            agent_type: [] for agent_type in AgentType
        }
        self.session_state_history: List[StateTransition] = []

        # Active tasks and progress
        self.active_tasks: Dict[AgentType, str] = {}
        self.task_progress: Dict[AgentType, float] = {
            agent_type: 0.0 for agent_type in AgentType
        }

        # Error tracking
        self.error_history: List[Dict[str, Any]] = []

        # Performance metrics
        self.state_durations: Dict[str, List[float]] = {}
        self.transition_counts: Dict[str, int] = {}

        # State change timestamps
        self.state_timestamps: Dict[str, datetime] = {}

    def set_agent_state(
        self,
        agent_type: AgentType,
        new_state: AgentState,
        reason: Optional[str] = None,
        current_task: Optional[str] = None,
        progress_percentage: Optional[float] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Set agent state and record transition"""
        old_state = self.agent_states[agent_type]

        # Only record if state actually changed
        if old_state != new_state:
            # Record state change
            snapshot = AgentStateSnapshot(
                agent_type=agent_type,
                state=new_state,
                current_task=current_task,
                progress_percentage=progress_percentage or 0.0,
                error_message=error_message,
                metadata=metadata or {}
            )

            self.agent_state_history[agent_type].append(snapshot)
            self.agent_states[agent_type] = new_state

            # Update timestamps and durations
            state_key = f"{agent_type.value}:{old_state.value}"
            if state_key in self.state_timestamps:
                duration = (datetime.utcnow() - self.state_timestamps[state_key]).total_seconds()
                if state_key not in self.state_durations:
                    self.state_durations[state_key] = []
                self.state_durations[state_key].append(duration)

            # Set new timestamp
            new_state_key = f"{agent_type.value}:{new_state.value}"
            self.state_timestamps[new_state_key] = datetime.utcnow()

            # Update transition counts
            transition_key = f"{old_state.value}→{new_state.value}"
            self.transition_counts[transition_key] = self.transition_counts.get(transition_key, 0) + 1

            # Log error if transitioning to error state
            if new_state == AgentState.ERROR and error_message:
                self._log_error(agent_type, error_message, metadata)

        # Update active task and progress regardless of state change
        if current_task:
            self.active_tasks[agent_type] = current_task
        if progress_percentage is not None:
            self.task_progress[agent_type] = progress_percentage

    def set_session_state(
        self,
        new_state: SessionState,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Set session state and record transition"""
        old_state = self.session_state

        if old_state != new_state:
            transition = StateTransition(
                from_state=old_state.value,
                to_state=new_state.value,
                reason=reason,
                metadata=metadata or {}
            )

            self.session_state_history.append(transition)
            self.session_state = new_state

            # Update session state timestamp
            state_key = f"session:{old_state.value}"
            if state_key in self.state_timestamps:
                duration = (datetime.utcnow() - self.state_timestamps[state_key]).total_seconds()
                if state_key not in self.state_durations:
                    self.state_durations[state_key] = []
                self.state_durations[state_key].append(duration)

            # Set new timestamp
            new_state_key = f"session:{new_state.value}"
            self.state_timestamps[new_state_key] = datetime.utcnow()

            # Update transition counts
            transition_key = f"{old_state.value}→{new_state.value}"
            self.transition_counts[transition_key] = self.transition_counts.get(transition_key, 0) + 1

    def get_agent_state(self, agent_type: AgentType) -> AgentState:
        """Get current state of an agent"""
        return self.agent_states.get(agent_type, AgentState.IDLE)

    def get_session_state(self) -> SessionState:
        """Get current session state"""
        return self.session_state

    def get_agent_states(self) -> Dict[AgentType, AgentState]:
        """Get all agent states"""
        return self.agent_states.copy()

    def get_active_agents(self) -> List[AgentType]:
        """Get list of currently active agents"""
        return [
            agent_type for agent_type, state in self.agent_states.items()
            if state in [AgentState.PROCESSING, AgentState.WAITING_FOR_USER, AgentState.WAITING_FOR_AGENT]
        ]

    def get_idle_agents(self) -> List[AgentType]:
        """Get list of idle agents"""
        return [
            agent_type for agent_type, state in self.agent_states.items()
            if state == AgentState.IDLE
        ]

    def get_agents_in_state(self, state: AgentState) -> List[AgentType]:
        """Get agents in a specific state"""
        return [
            agent_type for agent_type, agent_state in self.agent_states.items()
            if agent_state == state
        ]

    def get_agent_progress(self, agent_type: AgentType) -> float:
        """Get progress percentage for an agent"""
        return self.task_progress.get(agent_type, 0.0)

    def get_active_task(self, agent_type: AgentType) -> Optional[str]:
        """Get active task for an agent"""
        return self.active_tasks.get(agent_type)

    def update_agent_progress(self, agent_type: AgentType, progress: float) -> None:
        """Update progress for an agent"""
        self.task_progress[agent_type] = max(0.0, min(100.0, progress))

    def increment_agent_progress(self, agent_type: AgentType, increment: float) -> None:
        """Increment progress for an agent"""
        current_progress = self.task_progress.get(agent_type, 0.0)
        self.update_agent_progress(agent_type, current_progress + increment)

    def has_agent_errors(self) -> bool:
        """Check if any agents are in error state"""
        return any(state == AgentState.ERROR for state in self.agent_states.values())

    def get_erroring_agents(self) -> List[AgentType]:
        """Get agents currently in error state"""
        return [
            agent_type for agent_type, state in self.agent_states.items()
            if state == AgentState.ERROR
        ]

    def is_session_complete(self) -> bool:
        """Check if session is in a completed state"""
        return self.session_state in [SessionState.COMPLETED, SessionState.FAILED, SessionState.CANCELLED]

    def is_session_active(self) -> bool:
        """Check if session is currently active"""
        return self.session_state in [SessionState.ACTIVE, SessionState.PAUSED, SessionState.WAITING_FOR_APPROVAL]

    def can_agent_proceed(self, agent_type: AgentType) -> bool:
        """Check if an agent can proceed with its task"""
        state = self.get_agent_state(agent_type)
        return state in [AgentState.IDLE, AgentState.PROCESSING]

    def get_state_duration(self, agent_type: Optional[AgentType] = None, state: Optional[str] = None) -> Optional[float]:
        """Get duration of current state"""
        if agent_type and state:
            state_key = f"{agent_type.value}:{state}"
        elif agent_type:
            current_state = self.agent_states[agent_type]
            state_key = f"{agent_type.value}:{current_state.value}"
        elif state:
            state_key = f"session:{state}"
        else:
            state_key = f"session:{self.session_state.value}"

        if state_key in self.state_timestamps:
            return (datetime.utcnow() - self.state_timestamps[state_key]).total_seconds()
        return None

    def get_average_state_duration(self, agent_type: Optional[AgentType] = None, state: Optional[str] = None) -> Optional[float]:
        """Get average duration for a state"""
        if agent_type and state:
            state_key = f"{agent_type.value}:{state}"
        elif state:
            state_key = f"session:{state}"
        else:
            return None

        durations = self.state_durations.get(state_key, [])
        if durations:
            return sum(durations) / len(durations)
        return None

    def get_state_history(
        self,
        agent_type: Optional[AgentType] = None,
        limit: Optional[int] = None,
        since: Optional[datetime] = None
    ) -> List[AgentStateSnapshot]:
        """Get state history for an agent or all agents"""
        if agent_type:
            history = self.agent_state_history[agent_type].copy()
        else:
            history = []
            for agent_history in self.agent_state_history.values():
                history.extend(agent_history)
            # Sort by timestamp
            history.sort(key=lambda x: x.timestamp)

        # Filter by time if specified
        if since:
            history = [snapshot for snapshot in history if snapshot.timestamp >= since]

        # Limit if specified
        if limit:
            history = history[-limit:]

        return history

    def get_session_state_history(self, limit: Optional[int] = None) -> List[StateTransition]:
        """Get session state transition history"""
        history = self.session_state_history.copy()
        if limit:
            history = history[-limit:]
        return history

    def get_error_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get error history"""
        history = self.error_history.copy()
        if limit:
            history = history[-limit:]
        return history

    def get_transition_statistics(self) -> Dict[str, Any]:
        """Get statistics about state transitions"""
        return {
            "total_transitions": sum(self.transition_counts.values()),
            "transition_counts": self.transition_counts.copy(),
            "most_common_transitions": sorted(
                self.transition_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        metrics = {
            "state_durations": {},
            "average_durations": {},
            "current_durations": {}
        }

        # Calculate average and current durations for all states
        for state_key, durations in self.state_durations.items():
            if durations:
                metrics["average_durations"][state_key] = sum(durations) / len(durations)

        # Get current state durations
        for state_key, timestamp in self.state_timestamps.items():
            current_duration = (datetime.utcnow() - timestamp).total_seconds()
            metrics["current_durations"][state_key] = current_duration

        return metrics

    def get_state_summary(self) -> Dict[str, Any]:
        """Get comprehensive state summary"""
        return {
            "session_id": self.session_id,
            "session_state": self.session_state.value,
            "agent_states": {
                agent_type.value: state.value
                for agent_type, state in self.agent_states.items()
            },
            "active_agents": [agent.value for agent in self.get_active_agents()],
            "idle_agents": [agent.value for agent in self.get_idle_agents()],
            "erroring_agents": [agent.value for agent in self.get_erroring_agents()],
            "agent_progress": {
                agent_type.value: progress
                for agent_type, progress in self.task_progress.items()
            },
            "active_tasks": {
                agent_type.value: task
                for agent_type, task in self.active_tasks.items()
            },
            "total_state_changes": sum(self.transition_counts.values()),
            "total_errors": len(self.error_history),
            "session_duration": self.get_state_duration(state=self.session_state.value)
        }

    def reset_agent_state(self, agent_type: AgentType, reason: Optional[str] = None) -> None:
        """Reset an agent to idle state"""
        self.set_agent_state(
            agent_type=agent_type,
            new_state=AgentState.IDLE,
            reason=reason or "Manual reset",
            current_task=None,
            progress_percentage=0.0,
            error_message=None
        )

        # Clear active task
        if agent_type in self.active_tasks:
            del self.active_tasks[agent_type]

    def reset_all_agents(self, reason: Optional[str] = None) -> None:
        """Reset all agents to idle state"""
        for agent_type in AgentType:
            self.reset_agent_state(agent_type, reason)

    def export_state(self) -> Dict[str, Any]:
        """Export full state for persistence"""
        return {
            "session_id": self.session_id,
            "session_state": self.session_state.value,
            "agent_states": {
                agent_type.value: state.value
                for agent_type, state in self.agent_states.items()
            },
            "active_tasks": {
                agent_type.value: task
                for agent_type, task in self.active_tasks.items()
            },
            "task_progress": {
                agent_type.value: progress
                for agent_type, progress in self.task_progress.items()
            },
            "agent_state_history": {
                agent_type.value: [
                    {
                        "state": snapshot.state.value,
                        "timestamp": snapshot.timestamp.isoformat(),
                        "current_task": snapshot.current_task,
                        "progress_percentage": snapshot.progress_percentage,
                        "error_message": snapshot.error_message,
                        "metadata": snapshot.metadata
                    }
                    for snapshot in history
                ]
                for agent_type, history in self.agent_state_history.items()
            },
            "session_state_history": [
                {
                    "from_state": transition.from_state,
                    "to_state": transition.to_state,
                    "timestamp": transition.timestamp.isoformat(),
                    "reason": transition.reason,
                    "metadata": transition.metadata
                }
                for transition in self.session_state_history
            ],
            "error_history": self.error_history,
            "transition_counts": self.transition_counts,
            "state_durations": self.state_durations
        }

    def import_state(self, exported_state: Dict[str, Any]) -> None:
        """Import state from exported data"""
        self.session_id = exported_state["session_id"]
        self.session_state = SessionState(exported_state["session_state"])

        # Import agent states
        for agent_type_str, state_str in exported_state["agent_states"].items():
            agent_type = AgentType(agent_type_str)
            state = AgentState(state_str)
            self.agent_states[agent_type] = state

        # Import active tasks and progress
        self.active_tasks = {
            AgentType(agent_type_str): task
            for agent_type_str, task in exported_state["active_tasks"].items()
        }
        self.task_progress = {
            AgentType(agent_type_str): progress
            for agent_type_str, progress in exported_state["task_progress"].items()
        }

        # Import history (simplified - just timestamps for now)
        self.transition_counts = exported_state["transition_counts"]
        self.state_durations = exported_state["state_durations"]
        self.error_history = exported_state["error_history"]

    def _log_error(
        self,
        agent_type: AgentType,
        error_message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log an error occurrence"""
        error_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent_type": agent_type.value,
            "error_message": error_message,
            "metadata": metadata or {}
        }
        self.error_history.append(error_entry)

        # Keep only last 100 errors to prevent memory issues
        if len(self.error_history) > 100:
            self.error_history = self.error_history[-100:]