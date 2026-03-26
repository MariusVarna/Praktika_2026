from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.schemas import schemas
from app.services.session_service import SessionService

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
