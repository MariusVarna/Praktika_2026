from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app import models
from app.schemas import schemas

router = APIRouter()

@router.post("/", response_model=List[schemas.BidResponse])
def submit_bids(bids_in: List[schemas.BidCreate], user_id: int, round_id: int, db: Session = Depends(get_db)):
    """Player submits bids for a round."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    current_round = db.query(models.Round).filter(models.Round.id == round_id).first()
    if not current_round or current_round.status != "bidding":
        raise HTTPException(status_code=400, detail="Round is not open for bidding")
        
    if current_round.session_id != user.session_id:
        raise HTTPException(status_code=400, detail="User not in this session")
        
    # Optional: Clear existing bids for this round/user before inserting? 
    # Let's assume they can overwrite their entire array of bids
    db.query(models.Bid).filter(models.Bid.user_id == user_id, models.Bid.round_id == round_id).delete()
    
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
        db.add(db_bid)
        db_bids.append(db_bid)
        
    db.commit()
    for b in db_bids:
        db.refresh(b)
        
    return db_bids
