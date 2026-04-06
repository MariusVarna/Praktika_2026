from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.schemas import schemas
from app.services.session_service import SessionService
from app.services.round_service import RoundService

router = APIRouter()

@router.post("/", response_model=schemas.SessionResponse)
def create_session(session_in: schemas.SessionCreate, db: Session = Depends(get_db)):
    """Admin creates a new session via Service Layer."""
    session_service = SessionService(db)
    return session_service.create_session(session_in)

@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: int, admin_id: str, db: Session = Depends(get_db)):
    """Admin deletes a session."""
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.admin_id != admin_id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    db.delete(session)
    db.commit()
    return None

@router.get("/{session_id}/round/{round_id}/forecast", response_model=schemas.ForecastingResponse)
def get_round_forecast(session_id: int, round_id: int, db: Session = Depends(get_db)):
    """Provides a price and profile forecast for the round via Service Layer."""
    session_service = SessionService(db)
    return session_service.get_forecast(session_id, round_id)

@router.get("/{session_id}/round/{round_id}/baseline", response_model=schemas.BaselineResponse)
def get_round_baseline(session_id: int, round_id: int, db: Session = Depends(get_db)):
    """Provides a bot-only baseline graph for the round."""
    round_service = RoundService(db)
    baseline = round_service.get_round_baseline(session_id, round_id)
    return schemas.BaselineResponse(round_id=round_id, baseline=baseline)

@router.get("/{session_id}/standings", response_model=schemas.StandingsResponse)
def get_session_standings(session_id: int, db: Session = Depends(get_db)):
    """Returns team standings (profit ranked) for a session."""
    session_service = SessionService(db)
    return session_service.get_standings(session_id)
