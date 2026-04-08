from sqlalchemy.orm import Session
from app import models
from app.schemas import schemas
from fastapi import HTTPException

class PlayerService:
    def __init__(self, db: Session):
        self.db = db

    def join_session(self, user_in: schemas.UserCreate) -> models.User:
        session = self.db.query(models.Session).filter(models.Session.join_code == user_in.join_code).first()
        if not session:
            raise HTTPException(status_code=404, detail="Invalid join code or session not found")
        
        # FIX: Prevent joining finished sessions
        from app.models.session import SessionStatus
        if session.status == SessionStatus.FINISHED:
            raise HTTPException(status_code=400, detail="Session has finished")
            
        existing_user = self.db.query(models.User).filter(
            models.User.session_id == session.id,
            models.User.name == user_in.name
        ).first()
        
        if existing_user:
            raise HTTPException(status_code=400, detail="Team name already taken in this session")

        # Create User
        db_user = models.User(name=user_in.name, session_id=session.id)
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        
        # Initialize Team State
        team_state = models.TeamState(
            user_id=db_user.id,
            session_id=session.id,
            current_battery_mwh=session.battery_initial_mwh,
            total_profit=0.0
        )
        self.db.add(team_state)
        self.db.commit()
        
        return db_user
