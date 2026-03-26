from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.schemas import schemas
from app.websockets import manager
from app.services.round_service import RoundService

router = APIRouter()

@router.post("/{session_id}/start", response_model=schemas.RoundResponse)
async def start_session(session_id: int, admin_id: str, db: Session = Depends(get_db)):
    """Admin starts the session, creating round 1."""
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session or session.admin_id != admin_id:
        raise HTTPException(status_code=404, detail="Session not found or unauthorized")
        
    if session.status != "pending":
        raise HTTPException(status_code=400, detail="Session already started")
        
    session.status = "active"
    
    # Create first round
    new_round = models.Round(session_id=session.id, round_number=1, status="bidding")
    db.add(new_round)
    db.commit()
    db.refresh(new_round)
    
    await manager.broadcast_to_session(session.id, {"event": "SESSION_STARTED", "round_id": new_round.id, "round_number": 1})
    return new_round

@router.post("/{session_id}/round/{round_id}/calculate")
async def calculate_round(session_id: int, round_id: int, admin_id: str, db: Session = Depends(get_db)):
    """Admin ends bidding for the round and calculates results using the Service Layer."""
    # 1. Validation Logic
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session or session.admin_id != admin_id:
        raise HTTPException(status_code=404, detail="Unauthorized")
        
    current_round = db.query(models.Round).filter(models.Round.id == round_id).first()
    if not current_round or current_round.status != "bidding":
        raise HTTPException(status_code=400, detail="Round is not in bidding state")
        
    # 2. Delegate Business Logic to Service Layer
    round_service = RoundService(db)
    try:
        round_service.calculate_round_results(session_id, round_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Market calculation failed: {str(e)}")

    # 3. Handle External Effects (WebSockets)
    await manager.broadcast_to_session(session_id, {"event": "ROUND_CALCULATED", "round_id": round_id})
    return {"status": "ok", "message": "Round calculated successfully"}

@router.post("/{session_id}/next")
async def next_round(session_id: int, admin_id: str, db: Session = Depends(get_db)):
    """Admin creates the next round."""
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session or session.admin_id != admin_id:
        raise HTTPException(status_code=404)
        
    last_round = db.query(models.Round).filter(models.Round.session_id == session.id).order_by(models.Round.round_number.desc()).first()
    
    if last_round and last_round.status != "calculated":
        raise HTTPException(status_code=400, detail="Previous round not calculated")
        
    next_num = last_round.round_number + 1 if last_round else 1
    
    new_round = models.Round(session_id=session.id, round_number=next_num, status="bidding")
    db.add(new_round)
    db.commit()
    db.refresh(new_round)
    
    await manager.broadcast_to_session(session.id, {"event": "NEW_ROUND", "round_id": new_round.id, "round_number": next_num})
    return new_round
