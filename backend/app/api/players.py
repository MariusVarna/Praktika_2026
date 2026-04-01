from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import schemas
from app.services.player_service import PlayerService

router = APIRouter()

@router.post("/join", response_model=schemas.UserResponse)
def join_session(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    """Player joins a session via Service Layer."""
    player_service = PlayerService(db)
    return player_service.join_session(user_in)
