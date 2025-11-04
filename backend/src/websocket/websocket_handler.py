"""
WebSocket connection handler for real-time session updates
"""

import json
import logging
from typing import Dict, List, Optional, Any
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_async_session
from ..services.database_service import DatabaseService
from ..agents.orchestration_engine import AgentOrchestrationEngine
from ..core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

# WebSocket connection manager
class ConnectionManager:
    """Manages active WebSocket connections"""

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept and register a WebSocket connection"""
        await websocket.accept()

        if session_id not in self.active_connections:
            self.active_connections[session_id] = []

        self.active_connections[session_id].append(websocket)

        # Store connection metadata
        connection_id = f"{session_id}_{len(self.active_connections[session_id])}"
        self.connection_metadata[connection_id] = {
            "session_id": session_id,
            "connected_at": "datetime.utcnow().isoformat()",
            "last_ping": "datetime.utcnow().isoformat()"
        }

        logger.info(f"WebSocket connected for session {session_id}. Total connections: {len(self.active_connections[session_id])}")
        return connection_id

    def disconnect(self, websocket: WebSocket, session_id: str):
        """Remove a WebSocket connection"""
        if session_id in self.active_connections:
            if websocket in self.active_connections[session_id]:
                self.active_connections[session_id].remove(websocket)

            # Clean up empty session entries
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
                # Clean up metadata
                keys_to_remove = [k for k in self.connection_metadata.keys() if k.startswith(session_id)]
                for key in keys_to_remove:
                    del self.connection_metadata[key]

        logger.info(f"WebSocket disconnected for session {session_id}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a message to a specific WebSocket"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")

    async def broadcast_to_session(self, session_id: str, message: Dict[str, Any]):
        """Broadcast a message to all connections in a session"""
        if session_id in self.active_connections:
            message_str = json.dumps(message)
            disconnected = []

            for connection in self.active_connections[session_id]:
                try:
                    await connection.send_text(message_str)
                except Exception as e:
                    logger.warning(f"Failed to send message to connection in session {session_id}: {e}")
                    disconnected.append(connection)

            # Remove disconnected connections
            for connection in disconnected:
                self.disconnect(connection, session_id)

    async def get_session_connections_count(self, session_id: str) -> int:
        """Get the number of active connections for a session"""
        return len(self.active_connections.get(session_id, []))

    def get_all_connections_count(self) -> int:
        """Get total number of active connections"""
        return sum(len(connections) for connections in self.active_connections.values())

    def get_active_sessions(self) -> List[str]:
        """Get list of sessions with active connections"""
        return list(self.active_connections.keys())

# Global connection manager
manager = ConnectionManager()

# WebSocket message types
class WSMessageType:
    SESSION_STATUS = "session_status"
    AGENT_MESSAGE = "agent_message"
    USER_INPUT = "user_input"
    CLARIFYING_QUESTION = "clarifying_question"
    SESSION_CREATED = "session_created"
    SESSION_COMPLETED = "session_completed"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"

@router.websocket("/ws/sessions/{session_id}")
async def websocket_session_endpoint(
    websocket: WebSocket,
    session_id: str,
    db: AsyncSession = Depends(get_async_session)
):
    """
    WebSocket endpoint for real-time session updates
    """
    db_service = DatabaseService(db)
    orchestration_engine = AgentOrchestrationEngine()

    # Verify session exists
    session = await db_service.get_session(session_id)
    if not session:
        await websocket.close(code=4004, reason="Session not found")
        return

    connection_id = await manager.connect(websocket, session_id)

    try:
        # Send initial session state
        await websocket.send_text(json.dumps({
            "type": WSMessageType.SESSION_STATUS,
            "data": {
                "session_id": session_id,
                "status": session.status,
                "iteration_count": session.iteration_count,
                "user_intervention_count": session.user_intervention_count,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "waiting_for_user_since": session.waiting_for_user_since.isoformat() if session.waiting_for_user_since else None
            }
        }))

        # Send initial messages if they exist
        messages = await db_service.get_session_messages(session_id, limit=10)
        if messages:
            await websocket.send_text(json.dumps({
                "type": WSMessageType.AGENT_MESSAGE,
                "data": {
                    "session_id": session_id,
                    "messages": [
                        {
                            "id": str(msg.id),
                            "agent_type": msg.agent_type,
                            "message_content": msg.message_content,
                            "message_type": msg.message_type,
                            "sequence_number": msg.sequence_number,
                            "created_at": msg.created_at.isoformat(),
                            "processing_time_ms": msg.processing_time_ms
                        }
                        for msg in messages
                    ]
                }
            }))

        # Handle WebSocket messages
        while True:
            try:
                # Receive message with timeout
                data = await websocket.receive_text()
                message = json.loads(data)

                await handle_websocket_message(
                    message, websocket, session_id, db_service, orchestration_engine
                )

            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": WSMessageType.ERROR,
                    "data": {"message": "Invalid JSON format"}
                }))
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                await websocket.send_text(json.dumps({
                    "type": WSMessageType.ERROR,
                    "data": {"message": "Internal server error"}
                }))

    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, session_id)
        logger.info(f"WebSocket connection closed for session {session_id}")

async def handle_websocket_message(
    message: Dict[str, Any],
    websocket: WebSocket,
    session_id: str,
    db_service: DatabaseService,
    orchestration_engine: AgentOrchestrationEngine
):
    """Handle incoming WebSocket messages"""
    message_type = message.get("type")
    data = message.get("data", {})

    if message_type == WSMessageType.PING:
        await websocket.send_text(json.dumps({
            "type": WSMessageType.PONG,
            "data": {"timestamp": "datetime.utcnow().isoformat()"}
        }))

    elif message_type == WSMessageType.USER_INPUT:
        # Handle user input via WebSocket
        user_input = data.get("input_content", "").strip()
        input_type = data.get("input_type", "supplementary")

        if user_input:
            try:
                # Create user input in database
                user_input_record = await db_service.create_user_input(
                    session_id=session_id,
                    input_content=user_input,
                    input_type=input_type
                )

                # Process through orchestration engine
                response = await orchestration_engine.process_user_input(
                    session_id=session_id,
                    user_input=user_input,
                    supplementary_inputs=[user_input] if input_type == "supplementary" else None
                )

                # Broadcast response to all session connections
                await manager.broadcast_to_session(session_id, {
                    "type": WSMessageType.USER_INPUT,
                    "data": {
                        "session_id": session_id,
                        "user_input": {
                            "id": str(user_input_record.id),
                            "input_content": user_input,
                            "input_type": input_type,
                            "provided_at": user_input_record.provided_at.isoformat()
                        },
                        "response": response
                    }
                })

            except Exception as e:
                logger.error(f"Error processing user input via WebSocket: {e}")
                await websocket.send_text(json.dumps({
                    "type": WSMessageType.ERROR,
                    "data": {"message": f"Failed to process user input: {str(e)}"}
                }))

    elif message_type == "continue_without_input":
        # Handle continue without input
        try:
            response = await orchestration_engine.continue_without_input(session_id)

            # Broadcast response to all session connections
            await manager.broadcast_to_session(session_id, {
                "type": WSMessageType.SESSION_STATUS,
                "data": {
                    "session_id": session_id,
                    "status": response.get("status"),
                    "agent_responses": response.get("agent_responses", {}),
                    "next_agent": response.get("next_agent"),
                    "requires_user_input": response.get("requires_user_input", False),
                    "completed": response.get("completed", False),
                    "final_prompt": response.get("final_prompt")
                }
            })

        except Exception as e:
            logger.error(f"Error continuing session via WebSocket: {e}")
            await websocket.send_text(json.dumps({
                "type": WSMessageType.ERROR,
                "data": {"message": f"Failed to continue session: {str(e)}"}
            }))

# WebSocket event broadcasting functions (called from other parts of the application)

async def broadcast_session_status_update(session_id: str, status_data: Dict[str, Any]):
    """Broadcast session status update to all connected clients"""
    await manager.broadcast_to_session(session_id, {
        "type": WSMessageType.SESSION_STATUS,
        "data": {
            "session_id": session_id,
            **status_data
        }
    })

async def broadcast_agent_message(session_id: str, message_data: Dict[str, Any]):
    """Broadcast agent message to all connected clients"""
    await manager.broadcast_to_session(session_id, {
        "type": WSMessageType.AGENT_MESSAGE,
        "data": {
            "session_id": session_id,
            "message": message_data
        }
    })

async def broadcast_clarifying_question(session_id: str, question_data: Dict[str, Any]):
    """Broadcast clarifying question to all connected clients"""
    await manager.broadcast_to_session(session_id, {
        "type": WSMessageType.CLARIFYING_QUESTION,
        "data": {
            "session_id": session_id,
            "question": question_data
        }
    })

async def broadcast_session_created(session_id: str, session_data: Dict[str, Any]):
    """Broadcast session creation to all connected clients"""
    await manager.broadcast_to_session(session_id, {
        "type": WSMessageType.SESSION_CREATED,
        "data": {
            "session_id": session_id,
            **session_data
        }
    })

async def broadcast_session_completed(session_id: str, completion_data: Dict[str, Any]):
    """Broadcast session completion to all connected clients"""
    await manager.broadcast_to_session(session_id, {
        "type": WSMessageType.SESSION_COMPLETED,
        "data": {
            "session_id": session_id,
            **completion_data
        }
    })

async def broadcast_error(session_id: str, error_data: Dict[str, Any]):
    """Broadcast error to all connected clients"""
    await manager.broadcast_to_session(session_id, {
        "type": WSMessageType.ERROR,
        "data": {
            "session_id": session_id,
            **error_data
        }
    })

# Utility functions for connection management

def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance"""
    return manager

async def get_websocket_statistics() -> Dict[str, Any]:
    """Get WebSocket connection statistics"""
    return {
        "total_connections": manager.get_all_connections_count(),
        "active_sessions": len(manager.get_active_sessions()),
        "sessions_with_connections": manager.get_active_sessions(),
        "timestamp": "datetime.utcnow().isoformat()"
    }