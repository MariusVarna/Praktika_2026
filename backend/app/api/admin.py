from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.schemas import schemas
from app.websockets import manager
from app.services.round_service import RoundService
from typing import Optional

router = APIRouter()

@router.post("/{session_id}/start", response_model=schemas.RoundResponse)
async def start_session(session_id: int, admin_id: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    """Admin starts the session, creating round 1."""
    if not admin_id:
        raise HTTPException(status_code=401, detail="Admin authentication required")
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
async def calculate_round(session_id: int, round_id: int, admin_id: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    """Admin ends bidding for the round and calculates results using the Service Layer."""
    if not admin_id:
        raise HTTPException(status_code=401, detail="Admin authentication required")
    # 1. Validation Logic
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session or session.admin_id != admin_id:
        raise HTTPException(status_code=404, detail="Unauthorized")
        
    # FIX: Add row-level lock to prevent concurrent calculations
    current_round = db.query(models.Round)\
        .with_for_update()\
        .filter(models.Round.id == round_id).first()
    if not current_round or current_round.status != "bidding":
        raise HTTPException(status_code=400, detail="Round is not in bidding state")
        
    # 2. Delegate Business Logic to Service Layer
    round_service = RoundService(db)
    try:
        finished = round_service.calculate_round_results(session_id, round_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Market calculation failed: {str(e)}")

    # 3. Handle External Effects (WebSockets)
    await manager.broadcast_to_session(session_id, {"event": "ROUND_CALCULATED", "round_id": round_id})
    if finished:
        await manager.broadcast_to_session(session_id, {"event": "SESSION_FINISHED"})
    return {"status": "ok", "message": "Round calculated successfully", "session_finished": finished}

@router.post("/{session_id}/next")
async def next_round(session_id: int, admin_id: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    """Admin creates the next round."""
    if not admin_id:
        raise HTTPException(status_code=401, detail="Admin authentication required")
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session or session.admin_id != admin_id:
        raise HTTPException(status_code=404)
        
    if session.status == "finished":
        raise HTTPException(status_code=400, detail="Session already finished")

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

@router.post("/{session_id}/end", response_model=dict)
async def end_session(session_id: int, admin_id: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    """Admin ends the session, setting status to 'finished'."""
    if not admin_id:
        raise HTTPException(status_code=401, detail="Admin authentication required")
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session or session.admin_id != admin_id:
        raise HTTPException(status_code=404, detail="Session not found or unauthorized")
        
    if session.status == "finished":
        raise HTTPException(status_code=400, detail="Session already finished")
        
    session.status = "finished"
    db.commit()
    
    await manager.broadcast_to_session(session.id, {"event": "SESSION_FINISHED"})
    return {"status": "ok", "message": "Session finished successfully"}

@router.get("/{session_id}/round/{round_id}/results", response_model=schemas.RoundResultsResponse)
async def get_round_results(session_id: int, round_id: int, db: Session = Depends(get_db)):
    """
    Admin views detailed round results: market clearing per hour and individual player fills.
    NEW ENDPOINT: Provides comprehensive market analysis for teaching/review.
    """
    # Verify session and round exist
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    current_round = db.query(models.Round).filter(models.Round.id == round_id).first()
    if not current_round or current_round.session_id != session_id:
        raise HTTPException(status_code=404, detail="Round not found in session")
    
    # Get market clearing results for each hour
    market_results = db.query(models.MarketResult).filter(
        models.MarketResult.round_id == round_id
    ).order_by(models.MarketResult.hour).all()
    
    market_clearing = [
        schemas.HourlyMarketClearing(
            hour=mr.hour,
            clearing_price=mr.clearing_price,
            clearing_volume=mr.total_volume_cleared
        )
        for mr in market_results
    ]
    
    # Get all players in session and their bids/stats for this round
    all_players = db.query(models.User).filter(
        models.User.session_id == session_id
    ).all()
    
    player_results = []
    for player in all_players:
        # Get all bids for this player in this round
        player_bids = db.query(models.Bid).filter(
            models.Bid.user_id == player.id,
            models.Bid.round_id == round_id
        ).all()
        
        # Get round stats (profit/penalty)
        round_stats = db.query(models.PlayerRoundStats).filter(
            models.PlayerRoundStats.user_id == player.id,
            models.PlayerRoundStats.round_id == round_id
        ).first()
        
        profit = round_stats.total_profit if round_stats else 0.0
        penalty = round_stats.total_penalty if round_stats else 0.0
        
        # Calculate fills: for each bid, determine if it was accepted at clearing price
        total_bought = 0.0
        total_sold = 0.0
        
        for bid in player_bids:
            # Get the clearing price for this hour
            hour_clearing = next(
                (mr for mr in market_results if mr.hour == bid.hour), 
                None
            )
            if hour_clearing:
                if bid.bid_type:  # Buy bid (charge)
                    if bid.price >= hour_clearing.clearing_price:
                        # Bid accepted: gets filled
                        total_bought += bid.volume_mwh
                else:  # Sell bid (discharge)
                    if bid.price <= hour_clearing.clearing_price:
                        # Bid accepted: gets filled
                        total_sold += bid.volume_mwh
        
        # Format bids for response
        bid_details = [
            schemas.PlayerHourBid(
                hour=b.hour,
                volume_mwh=b.volume_mwh,
                price=b.price,
                bid_type=b.bid_type
            )
            for b in player_bids
        ]
        
        player_results.append(
            schemas.PlayerRoundFill(
                player_name=player.name,
                player_id=player.id,
                total_volume_bought=total_bought,
                total_volume_sold=total_sold,
                round_profit=profit,
                round_penalty=penalty,
                bids=bid_details
            )
        )
    
    # Sort by profit (highest first) for easy leaderboard view
    player_results.sort(key=lambda x: x.round_profit, reverse=True)
    
    return schemas.RoundResultsResponse(
        round_id=round_id,
        round_number=current_round.round_number,
        session_id=session_id,
        status=current_round.status,
        market_clearing=market_clearing,
        player_results=player_results
    )
