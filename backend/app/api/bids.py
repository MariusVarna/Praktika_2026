from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app import models, schemas
from app.services.bid_service import BidService

router = APIRouter()

@router.post("/", response_model=List[schemas.BidResponse])
def submit_bids(bids_in: List[schemas.BidCreate], user_id: int, round_id: int, db: Session = Depends(get_db)):
    """Player submits bids for a round via Service Layer."""
    bid_service = BidService(db)
    return bid_service.submit_round_bids(user_id, round_id, bids_in)
