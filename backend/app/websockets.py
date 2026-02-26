from fastapi import WebSocket
from typing import Dict, List
import json

class ConnectionManager:
    def __init__(self):
        # Maps session_id to list of active WebSockets
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: int):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)

    def disconnect(self, websocket: WebSocket, session_id: int):
        if session_id in self.active_connections:
            try:
                self.active_connections[session_id].remove(websocket)
                if not self.active_connections[session_id]:
                    del self.active_connections[session_id]
            except ValueError:
                pass

    async def broadcast_to_session(self, session_id: int, message: dict):
        """Send a JSON payload to everyone in the given session."""
        if session_id in self.active_connections:
            dead_connections = []
            for connection in self.active_connections[session_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception:
                    dead_connections.append(connection)
            
            # Clean up dead connections
            for conn in dead_connections:
                self.disconnect(conn, session_id)

manager = ConnectionManager()
