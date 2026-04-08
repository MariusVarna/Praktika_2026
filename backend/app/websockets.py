from fastapi import WebSocket
from typing import Dict, List
import json
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Maps session_id to list of active WebSockets
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: int):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)
        logger.info(f"WebSocket connection established for session {session_id}")

    def disconnect(self, websocket: WebSocket, session_id: int):
        if session_id in self.active_connections:
            try:
                self.active_connections[session_id].remove(websocket)
                if not self.active_connections[session_id]:
                    del self.active_connections[session_id]
                logger.info(f"WebSocket connection closed for session {session_id}")
            except ValueError:
                pass

    async def broadcast_to_session(self, session_id: int, message: dict):
        """Send a JSON payload to everyone in the given session."""
        if session_id in self.active_connections:
            dead_connections = []
            for connection in self.active_connections[session_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Failed to broadcast to session {session_id}: {e}")
                    dead_connections.append(connection)
            
            # Clean up dead connections
            for conn in dead_connections:
                self.disconnect(conn, session_id)
    
    async def disconnect_session(self, session_id: int):
        """Disconnect all websockets for a session. FIX: Cleanup on session delete."""
        if session_id in self.active_connections:
            connections = self.active_connections[session_id].copy()
            for connection in connections:
                try:
                    await connection.close(code=1000, reason="Session deleted")
                except Exception as e:
                    logger.warning(f"Error closing websocket for session {session_id}: {e}")
            del self.active_connections[session_id]
            logger.info(f"Disconnected all websockets for session {session_id}")

manager = ConnectionManager()
