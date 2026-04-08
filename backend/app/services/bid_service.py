from sqlalchemy.orm import Session
from app import models
from app.schemas import schemas
from typing import List
from fastapi import HTTPException

class BidService:
    def __init__(self, db: Session):
        self.db = db

    def submit_round_bids(self, user_id: int, round_id: int, bids_in: List[schemas.BidCreate]) -> List[models.Bid]:
        # 1. Validation
        user = self.db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        current_round = self.db.query(models.Round).filter(models.Round.id == round_id).first()
        if not current_round or current_round.status != "bidding":
            raise HTTPException(status_code=400, detail="Round is not open for bidding")
        
        # Explicit session status check - session must be active
        session = self.db.query(models.Session).filter(models.Session.id == current_round.session_id).first()
        if not session or session.status != "active":
            raise HTTPException(status_code=400, detail="Session is not active")
            
        if user.session_id and current_round.session_id != user.session_id:
            # Check if user is actually in the session attached to this round
            raise HTTPException(status_code=400, detail="User not in this session")
        
        # Validate each bid (DB constraints will also enforce these)
        for bid in bids_in:
            if not (0 <= bid.hour <= 23):
                raise HTTPException(status_code=400, detail=f"Invalid hour {bid.hour}, must be 0-23")
            if bid.volume_mwh <= 0:
                raise HTTPException(status_code=400, detail="Volume must be positive")
            if bid.price < -100 or bid.price > 500:
                raise HTTPException(status_code=400, detail="Price must be between -100 and 500 €/MWh")

        # 2. Logic: Clear existing and Insert new
        self.db.query(models.Bid).filter(models.Bid.user_id == user_id, models.Bid.round_id == round_id).delete()
        
        db_bids = []
        for bid in bids_in:
            db_bid = models.Bid(
                user_id=user_id,
                round_id=round_id,
                hour=bid.hour,
                volume_mwh=bid.volume_mwh,
                price=bid.price,
                bid_type=bid.bid_type
            )
            self.db.add(db_bid)
            db_bids.append(db_bid)
            
        self.db.commit()
        for b in db_bids:
            self.db.refresh(b)
            
        return db_bids
