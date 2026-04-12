from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app import models, schemas
from app.services.player_service import PlayerService

router = APIRouter()

@router.post("/join", response_model=schemas.UserResponse)
def join_session(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    """Player joins a session via Service Layer."""
    player_service = PlayerService(db)
    return player_service.join_session(user_in)

@router.get("/{player_id}/state", response_model=schemas.TeamStateResponse)
def get_player_state(player_id: int, db: Session = Depends(get_db)):
    """Get current player's battery level and total profit."""
    state = db.query(models.TeamState).filter(models.TeamState.user_id == player_id).first()
    if not state:
        raise HTTPException(status_code=404, detail="Player not found")
    return state
