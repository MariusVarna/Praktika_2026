from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.api import sessions, admin, players, bids, admin_auth
from app.websockets import manager
import logging
import signal
import sys

logger = logging.getLogger(__name__)

# Create DB Tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Electricity Market Game API")



# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Since it's a game, allow all for now or specify frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(admin_auth.router, prefix="/api/admin/auth", tags=["auth"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(admin.router, prefix="/api/admin/sessions", tags=["admin"])
app.include_router(players.router, prefix="/api/players", tags=["players"])
app.include_router(bids.router, prefix="/api/bids", tags=["bids"])

# WebSockets Endpoint
@app.websocket("/ws/session/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: int):
    await manager.connect(websocket, session_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Can handle incoming WS data here if needed (e.g. ping/pong)
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
