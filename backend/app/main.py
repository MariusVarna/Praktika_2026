from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.api import sessions, admin, players, bids, admin_auth
from app.websockets import manager
import os
import logging

logger = logging.getLogger(__name__)

# Create DB Tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Electricity Market Game API")

# Setup CORS
origins = os.getenv("CORS_ORIGINS", "http://localhost:5000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check for Render
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

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