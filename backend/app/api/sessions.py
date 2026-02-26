from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import random
import string
from app.database import get_db
from app import models
from app.schemas import schemas

router = APIRouter()

def generate_join_code(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

@router.post("/", response_model=schemas.SessionResponse)
def create_session(session_in: schemas.SessionCreate, db: Session = Depends(get_db)):
    """Admin creates a new session."""
    code = generate_join_code()
    # Ensure uniqueness
    while db.query(models.Session).filter(models.Session.join_code == code).first():
        code = generate_join_code()
        
    db_session = models.Session(
        admin_id=session_in.admin_id,
        join_code=code,
        start_day=session_in.start_day,
        pro_rata_enabled=session_in.pro_rata_enabled,
        battery_max_mwh=session_in.battery_max_mwh,
        battery_initial_mwh=session_in.battery_initial_mwh,
        battery_efficiency_charge=session_in.battery_efficiency_charge,
        battery_efficiency_discharge=session_in.battery_efficiency_discharge,
        penalty_price=session_in.penalty_price,
        base_demand_mw=session_in.base_demand_mw,
        status="pending"
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

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
