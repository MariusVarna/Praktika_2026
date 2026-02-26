from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.schemas import schemas

router = APIRouter()

@router.post("/join", response_model=schemas.UserResponse)
def join_session(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    """Player joins a session using a code."""
    session = db.query(models.Session).filter(models.Session.join_code == user_in.join_code).first()
    if not session:
        raise HTTPException(status_code=404, detail="Invalid join code or session not found")
        
    # Check if team name already taken in this session
    existing_user = db.query(models.User).filter(
        models.User.session_id == session.id,
        models.User.name == user_in.name
    ).first()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="Team name already taken in this session")

    # Create User
    db_user = models.User(name=user_in.name, session_id=session.id)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Initialize Team State
    team_state = models.TeamState(
        user_id=db_user.id,
        current_battery_mwh=session.battery_initial_mwh,
        total_profit=0.0
    )
    db.add(team_state)
    db.commit()
    
    return db_user
